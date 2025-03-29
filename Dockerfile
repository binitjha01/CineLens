FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Expose the port the app runs on
EXPOSE 5000

# Run the application
CMD gunicorn --bind 0.0.0.0:$PORT app:app