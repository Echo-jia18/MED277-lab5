# Author: Prof. MM Ghassemi <ghassem3@msu.edu>

import os
import requests
import time
from typing import Dict, List, Optional
from flask import current_app, session, jsonify
from flask_app import socketio
from .socket_events import process_and_emit_message

class ChatGPTClient:
    """Client for interacting with OpenAI's ChatGPT API"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = None, max_tokens: int = None, temperature: float = None):
        """Initialize the ChatGPT client
        
        Args:
            api_key: OpenAI API key. If not provided, will try to get from environment variable OPENAI_API_KEY
            model: OpenAI model to use. If not provided, will use config default
            max_tokens: Maximum tokens in response. If not provided, will use config default
            temperature: Response randomness (0.0-1.0). If not provided, will use config default
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Get configuration values
        self.model       = model       or current_app.config.get('OPENAI_MODEL')
        self.max_tokens  = max_tokens  or current_app.config.get('OPENAI_MAX_TOKENS')
        self.temperature = temperature or current_app.config.get('OPENAI_TEMPERATURE')
    
    def send_message(self, message: str, conversation_history: Optional[List[Dict]] = None, system_prompt: Optional[str] = None) -> Dict:
        """Send a message to ChatGPT and get a response
        
        Args:
            message: The user's message
            conversation_history: List of previous messages in the conversation
            system_prompt: Custom system prompt to define AI behavior (optional)
            
        Returns:
            Dictionary containing the response and metadata
        """
        if conversation_history is None:
            conversation_history = []
        
        # Prepare the messages for the API
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history
        messages.extend(conversation_history)
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract the assistant's response
            assistant_message = result['choices'][0]['message']['content']
            
            return {
                "success": True,
                "response": assistant_message,
                "usage": result.get('usage', {}),
                "model": self.model
            }
            
        except (requests.exceptions.RequestException, KeyError, IndexError) as e:
            return {
                "success": False,
                "error": f"Request or response error: {str(e)}",
                "response": "I'm sorry, I'm having trouble right now. Please try again later."
            }


def handle_ai_chat_request(llm_client: ChatGPTClient, message: str, system_prompt: str = None, room: str = 'main', page_content: dict = None):
    """
    Handle AI chat requests with LLM and broadcast responses via SocketIO.
    
    Args:
        llm_client: Pre-configured LLM client instance
        message: The user's message to send to the LLM
        system_prompt: Custom system prompt to define AI behavior (optional)
        room: Chat room to emit the AI response to (default: 'main')
        page_content: Dictionary containing page content information (optional)
        
    Returns:
        Response: JSON response with LLM reply or error message
    """
    try:
        # Get conversation history from session if available
        conversation_history = session.get('chat_history', [])
        system_prompt = system_prompt or current_app.config.get('OPENAI_SYSTEM_PROMPT')
  
        result = llm_client.send_message(message, conversation_history, system_prompt=system_prompt)
        
        if result["success"]:

            # update conversation history
            conversation_history.append({"role": "user", "content": message})
            conversation_history.append({"role": "assistant", "content": result["response"]})
            max_history = current_app.config.get('OPENAI_MAX_CONVERSATION_HISTORY')
            if len(conversation_history) > max_history:
                conversation_history = conversation_history[-max_history:]
            session['chat_history'] = conversation_history
        
            # Use centralized message processing for AI responses
            process_and_emit_message(socketio, result["response"], 'ai', room)

        return jsonify(result)
        
    except Exception as e:
        print(f"Error in handle_ai_chat_request: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "response": f"An error occurred: {str(e)}"
        }), 500

