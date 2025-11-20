# Author: Prof. MM Ghassemi <ghassem3@msu.edu>

from flask import current_app as app
from flask import render_template, redirect, request, session, url_for, jsonify, send_from_directory
from .utils.database import database
from .utils.llm import ChatGPTClient
from .utils.llm import handle_ai_chat_request
from bs4 import BeautifulSoup
import json

#--------------------------------------------------
# GLOBAL INSTANCES
#--------------------------------------------------
db = database()

#--------------------------------------------------
# MAIN APPLICATION ROUTES
#--------------------------------------------------

@app.route('/')
def home():
    return render_template('dynamic-page.html', user=db.get_user_email(), page_type='home')

@app.route('/agents')
def agents():
    return render_template('dynamic-page.html', user=db.get_user_email(), page_type='agents')

@app.route('/agents/resume')
def resume():
    return render_template('dynamic-page.html', user=db.get_user_email(), page_type='resume')

@app.route('/api/resume')
def api_resume():
    """API endpoint to serve resume data as JSON for Vue.js frontend."""
    resume_data = db.getResumeData()
    return jsonify({ "success": True, "data": resume_data})

#--------------------------------------------------
# CHAT ROUTES
#--------------------------------------------------
@app.route('/chat/ai', methods=['POST'])
def chat_with_ai():
    # Get message, page content, and system prompt from request data
    data          = request.get_json()
    message       = data.get('message', '').strip()
    page_content  = data.get('pageContent', {})
    
    # Log the received data for debugging
    print(f"Received message: {message}")
    print(f"Received page content: {page_content}")
    
    # Create LLM client and pass it to the handler
    chatGPT = ChatGPTClient()
    
    # Create a dynamic system prompt that leverages page content when relevant
    if page_content and page_content.get('content'):
        
        # Clean HTML content to get clean text
        clean_content = clean_html_content(page_content.get('content', ''))
        
        #Specify prompt to use when responding to the user's message.
        system_prompt = f""" 
            You are a helpful AI assistant. You have access to the current page content that the user is viewing.
            IMPORTANT INSTRUCTIONS:
            1. If the user's question is related to the content on the current page, use that content to provide accurate and relevant answers.
            2. Reference specific information from the page when it helps answer the user's question.
            3. If the user asks about something not covered on the current page, provide general helpful information.
            4. Be conversational and helpful while maintaining accuracy.

            CURRENT PAGE CONTENT:
            Title:   {page_content.get('title', 'Unknown page')}
            URL:     {page_content.get('url', 'N/A')}
            Content: {clean_content}

            Use this content to provide contextually relevant responses when appropriate.
        """

    else:
        # Fallback system prompt when no page content is available
        system_prompt = "You are a helpful AI assistant."
        print("Using fallback system prompt (no page content available)")

    return handle_ai_chat_request(llm_client=chatGPT, message=message, system_prompt=system_prompt, room='main', page_content=page_content)

#--------------------------------------------------
# AUTHENTICATION ROUTES
#--------------------------------------------------
@app.route('/login')
def login():
    return render_template('dynamic-page.html', user=db.get_user_email(), page_type='login')

@app.route('/processlogin', methods=["POST", "GET"])
def processlogin():
    data     = request.get_json()
    email    = data.get('email')
    password = data.get('password')

    # Validate required fields
    if not email or not password:
        return json.dumps({"success": 0,"error": "Email and password are required"})
    
    # Check if the username and password match
    status = db.authenticate(email=email, password=password)

    # Encrypt email and store it in the session
    session['email'] = db.reversibleEncrypt('encrypt', email) 

    return json.dumps(status)

@app.route('/logout')
def logout():
    # Clear the entire session
    session.clear()
    return redirect('/')


#--------------------------------------------------
# UTILITY ROUTES
#--------------------------------------------------

@app.route("/static/<path:path>")
def static_dir(path):
    return send_from_directory("static", path)

@app.after_request
def add_header(r):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r

def clean_html_content(html_content):
    """
    Clean HTML content by removing tags and extracting clean text.
    
    Args:
        html_content (str): Raw HTML content
        
    Returns:
        str: Clean text content without HTML tags
    """
    if not html_content:
        return ""
    
    try:
        # Parse HTML with Beautiful Soup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script, style, and other non-content elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()
        
        # Get text and clean it up
        text = soup.get_text()
        
        # Clean up whitespace and normalize
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        return text
    except Exception as e:
        print(f"Error cleaning HTML content: {e}")
        # Fallback: return original content if cleaning fails
        return html_content
