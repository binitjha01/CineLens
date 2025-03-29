# app.py
from flask import Flask, request, jsonify
import requests
import base64
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
OMDB_API_KEY = os.getenv("OMDB_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-7-sonnet-20250219")

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/api/extract-movies', methods=['POST'])
def extract_movies():
    """
    Extract movie titles from an image and get their ratings from OMDB API
    
    Expects a JSON with:
    {
        "image": "base64_encoded_image_string"
    }
    
    Returns:
    {
        "movies": [
            {
                "title": "Movie Title",
                "rating": "8.5",
                "poster": "url_to_poster",
                "year": "2023",
                "plot": "Movie plot summary"
            },
            ...
        ]
    }
    """
    if not request.json or 'image' not in request.json:
        return jsonify({"error": "No image provided"}), 400
    
    try:
        # Extract base64 image
        base64_image = request.json['image']
        
        # Get movie titles from Claude
        movie_titles = extract_movie_titles_from_image(base64_image)
        
        if not movie_titles:
            return jsonify({"movies": []}), 200
            
        # Get movie details from OMDB
        movies_with_details = []
        for title in movie_titles:
            movie_details = get_movie_details(title)
            if movie_details:
                movies_with_details.append(movie_details)
        
        return jsonify({"movies": movies_with_details}), 200
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500


def extract_movie_titles_from_image(base64_image):
    """Extract movie titles from image using Claude API"""
    logger.info("Calling Claude API to extract movie titles")
    
    claude_api_url = "https://api.anthropic.com/v1/messages"
    
    headers = {
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "x-api-key": CLAUDE_API_KEY,
        "Authorization": f"Bearer {CLAUDE_API_KEY}"
    }
    
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 1000,
        "system": "You are an AI assistant specialized in identifying movie titles from images. Look at the provided image and identify all movie titles that appear in it. Return ONLY the movie titles, one per line, with no additional text or explanations. If no movie titles are detected, respond with \"No movie titles detected\".",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64_image
                        }
                    },
                    {
                        "type": "text",
                        "text": "What movie titles do you see in this image? List only the movie titles."
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(claude_api_url, headers=headers, json=payload)
        response.raise_for_status()
        
        response_data = response.json()
        logger.info(f"Claude API response received: {response_data}")
        
        # Extract text from the content array
        movies_text = ""
        for content_item in response_data.get("content", []):
            if content_item.get("type") == "text":
                movies_text += content_item.get("text", "")
        
        # Split by newlines and filter out empty lines and "No movie titles detected"
        movie_titles = [
            title.strip() for title in movies_text.split("\n") 
            if title.strip() and title.strip() != "No movie titles detected"
        ]
        
        logger.info(f"Extracted {len(movie_titles)} movie titles: {movie_titles}")
        return movie_titles
        
    except requests.RequestException as e:
        logger.error(f"Error calling Claude API: {str(e)}")
        if hasattr(e.response, 'text'):
            logger.error(f"Response: {e.response.text}")
        raise Exception(f"Error calling Claude API: {str(e)}")


def get_movie_details(title):
    """Get movie details from OMDB API"""
    logger.info(f"Fetching details for movie: {title}")
    
    try:
        response = requests.get(
            "http://www.omdbapi.com/",
            params={
                "apikey": OMDB_API_KEY,
                "t": title,
                "plot": "short"
            }
        )
        response.raise_for_status()
        
        movie_data = response.json()
        if movie_data.get("Response") == "True":
            return {
                "title": movie_data.get("Title", title),
                "rating": movie_data.get("imdbRating", "N/A"),
                "poster": movie_data.get("Poster", "N/A"),
                "year": movie_data.get("Year", "N/A"),
                "plot": movie_data.get("Plot", "N/A")
            }
        else:
            logger.warning(f"Movie not found: {title}")
            return {
                "title": title,
                "rating": "N/A",
                "poster": "N/A",
                "year": "N/A",
                "plot": "Movie information not found"
            }
            
    except requests.RequestException as e:
        logger.error(f"Error fetching movie details: {str(e)}")
        return {
            "title": title,
            "rating": "Error",
            "poster": "N/A",
            "year": "N/A",
            "plot": f"Error fetching movie details: {str(e)}"
        }


if __name__ == "__main__":
    # For local development - in production, use a proper WSGI server
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
