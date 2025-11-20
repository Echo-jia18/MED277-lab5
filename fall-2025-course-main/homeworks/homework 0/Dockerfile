# Author  : Prof. MM Ghassemi <ghassem3@msu.edu>
# Access instance using `docker exec -it ${FLASK_CONTAINER} bash`

# Instantiate Ubuntu 20.04
FROM ubuntu:20.04
LABEL maintainer "Mohammad Ghassemi <ghassem3@msu.edu>"
LABEL description="This is custom Docker Image for Dr. Ghassemi's Web Application Course"

# Update Ubuntu Software repository
RUN apt update
RUN apt-get update -qq

# Install PostgreSQL client libraries for psycopg2
ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get install -y libpq-dev python3-dev postgresql-client

# Add the Flask application and install requirements
RUN apt -y install python3-pip
RUN apt -y install vim
RUN mkdir /app
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Create the startup script directly in the container
RUN echo '#!/bin/bash\n\
echo "Starting Flask application..."\n\
\n\
# Wait for PostgreSQL to be ready\n\
echo "Waiting for PostgreSQL to be ready..."\n\
until pg_isready -h ${DATABASE_HOST} -U ${DATABASE_USER}; do\n\
  echo "PostgreSQL is unavailable - sleeping"\n\
  sleep 2\n\
done\n\
\n\
echo "PostgreSQL is up - starting Flask application"\n\
\n\
# Start the Flask application\n\
exec python3 app.py' > /start.sh && chmod +x /start.sh

# Copy the rest of the application
COPY . .

# Open ports, set environment variables, start the application.
EXPOSE 8080
ENV PORT 8080

ENV FLASK_ENV=development
CMD ["/start.sh"]
# ----------------------------------------------------- 