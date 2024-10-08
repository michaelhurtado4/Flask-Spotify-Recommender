# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port that Waitress will run on
EXPOSE 5000

# Command to run the Flask application using Waitress
CMD ["waitress-serve", "--host=0.0.0.0", "--port=5000", "main:app"]
