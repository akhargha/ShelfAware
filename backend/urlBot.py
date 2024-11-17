from flask import Flask, request, jsonify
import requests
import json
import os
from datetime import datetime
from supabase import create_client, Client
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv
import logging
import re
from flask_cors import CORS

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5173"]
    }
})

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants from environment variables
PERPLEXITY_API_URL = os.getenv('PERPLEXITY_API_URL')
PERPLEXITY_API_KEY = f"Bearer {os.getenv('PERPLEXITY_API_KEY')}"
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Initialize Supabase client
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    raise Exception(f"Failed to initialize Supabase client: {str(e)}")

def clean_json_string(json_str: str) -> str:
    """Clean JSON string by removing markdown code blocks, comments, and unnecessary whitespace."""
    # Remove markdown code blocks
    json_str = re.sub(r'```json\s*', '', json_str)
    json_str = re.sub(r'```.*$', '', json_str, flags=re.MULTILINE | re.DOTALL)
    
    # Remove comments and descriptions
    json_str = re.sub(r'###.*$', '', json_str, flags=re.MULTILINE | re.DOTALL)
    json_str = re.sub(r'####.*$', '', json_str, flags=re.MULTILINE | re.DOTALL)
    json_str = re.sub(r'- \*\*.*$', '', json_str, flags=re.MULTILINE)
    json_str = re.sub(r'\*\*.*?\*\*', '', json_str)
    
    # Find the JSON object
    match = re.search(r'({[\s\S]*})', json_str)
    if match:
        json_str = match.group(1)
    
    # Remove any trailing text after the JSON object
    json_str = re.sub(r'}[\s\S]*$', '}', json_str)
    
    return json_str.strip()


def call_perplexity_api(messages: List[Dict[str, str]], online: bool = True) -> Dict[str, Any]:
    """Helper function to make requests to the Perplexity API."""
    headers = {
        "Authorization": PERPLEXITY_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-sonar-small-128k-online" if online else "llama-3.1-sonar-small-128k",
        "messages": messages
    }
    
    response = requests.post(PERPLEXITY_API_URL, json=payload, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"API Error: {response.status_code}, {response.text}")
    
    logger.debug("Raw API Response:", response.json())
    return response.json()

def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Extract and parse JSON from text response with improved error handling."""
    try:
        # Find JSON content between ```json and ``` markers
        json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', text)
        
        if json_match:
            json_str = json_match.group(1)
        else:
            # If no markers, try to find JSON object directly
            json_match = re.search(r'(\{[\s\S]*?\})\s*(?:###|$)', text)
            if not json_match:
                raise Exception("No JSON object found in response")
            json_str = json_match.group(1)

        # Parse the JSON
        parsed_json = json.loads(json_str)
        
        # Fix null/None values and validate fields
        if parsed_json.get('Color_of_the_dustbin') is None or parsed_json['Color_of_the_dustbin'] not in ['blue', 'green', 'black']:
            parsed_json['Color_of_the_dustbin'] = 'blue'
            
        # Ensure all required fields exist
        required_fields = ['Health_Information', 'Sustainability_Information', 'Price', 'Reliability_index', 'Alternatives']
        for field in required_fields:
            if field not in parsed_json:
                parsed_json[field] = {
                    'Health_Information': {
                        'Nutrients': {},
                        'Ingredients': [],
                        'Health_index': 0
                    },
                    'Sustainability_Information': {
                        'Biodegradable': 'No',
                        'Recyclable': 'Yes',
                        'Sustainability_rating': 4.0
                    },
                    'Price': 499.99,
                    'Reliability_index': 4.0,
                    'Color_of_the_dustbin': 'blue',
                    'Alternatives': []
                }[field]
        
        # Ensure exactly 3 alternatives
        alternatives = parsed_json.get('Alternatives', [])
        while len(alternatives) < 3:
            alternatives.append({
                'Name': f'Alternative Product {len(alternatives) + 1}',
                'Health_Information': {
                    'Nutrients': {},
                    'Ingredients': [],
                    'Health_index': 0
                },
                'Sustainability_Information': {
                    'Biodegradable': 'No',
                    'Recyclable': 'Yes',
                    'Sustainability_rating': 4.0
                },
                'Price': 499.99,
                'Reliability_index': 4.0
            })
        parsed_json['Alternatives'] = alternatives[:3]  # Keep only 3 alternatives
        
        return parsed_json
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON Decode Error: {str(e)}")
        logger.error(f"Problematic text: {text}")
        raise Exception(f"Invalid JSON format: {str(e)}")
    except Exception as e:
        logger.error(f"Extraction Error: {str(e)}")
        logger.error(f"Raw text: {text}")
        raise Exception(f"Error extracting JSON: {str(e)}")
    
def get_product_info_from_url(url: str) -> Tuple[str, Dict[str, Any]]:
    """Get product information from URL using Perplexity's web access."""
    # ... (previous code remains the same until detailed_prompt)
    
    detailed_prompt = f"""
    Return a JSON object following this exact format for the product at {url}:

    ```json
    {{
        "Health_Information": {{
            "Nutrients": {{}},
            "Ingredients": [],
            "Health_index": 0
        }},
        "Sustainability_Information": {{
            "Biodegradable": "No",
            "Recyclable": "Yes",
            "Sustainability_rating": 4.5
        }},
        "Price": 809.99,
        "Reliability_index": 4.8,
        "Color_of_the_dustbin": "blue",
        "Alternatives": [
            {{
                "Name": "Actual competing product name",
                "Health_Information": {{
                    "Nutrients": {{}},
                    "Ingredients": [],
                    "Health_index": 0
                }},
                "Sustainability_Information": {{
                    "Biodegradable": "No",
                    "Recyclable": "Yes",
                    "Sustainability_rating": 4.2
                }},
                "Price": 799.99,
                "Reliability_index": 4.3
            }}
        ]
    }}
    ```

    CRITICAL:
    1. Keep the ```json markers in your response
    2. Use "blue", "green", or "black" for Color_of_the_dustbin, not null
    3. Ensure all non-edible products have empty Health_Information
    4. Use exact price format: XXX.XX
    5. Include real market alternatives
    """
    
    messages = [{"role": "user", "content": detailed_prompt}]
    response = call_perplexity_api(messages, online=True)
    raw_content = response['choices'][0]['message']['content']
    
    # Extract product name from initial info
    try:
        name_match = re.search(r"Product name:?\s*([^\n]+)", initial_info, re.IGNORECASE)
        if not name_match:
            name_match = re.search(r"Name:?\s*([^\n]+)", initial_info, re.IGNORECASE)
        product_name = name_match.group(1).strip() if name_match else "Unknown Product"
    except Exception as e:
        logger.error(f"Error extracting product name: {str(e)}")
        product_name = "Unknown Product"
    
    json_data = extract_json_from_text(raw_content)
    
    # Ensure exactly 3 alternatives
    while len(json_data.get("Alternatives", [])) < 3:
        json_data["Alternatives"] = json_data.get("Alternatives", []) + [{
            "Name": f"Alternative Product {len(json_data.get('Alternatives', [])) + 1}",
            "Health_Information": {
                "Nutrients": {},
                "Ingredients": [],
                "Health_index": 0
            },
            "Sustainability_Information": {
                "Biodegradable": "No",
                "Recyclable": "Yes",
                "Sustainability_rating": 4.0
            },
            "Price": 799.99,
            "Reliability_index": 4.0
        }]
    
    return product_name, json_data

@app.route('/fetch_product_from_url', methods=['POST'])
async def fetch_product_from_url():
    """Endpoint to fetch and process product information from a URL."""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({
                "status": "error",
                "error": "URL is required"
            }), 400
        
        # Get product information from URL using Perplexity
        product_name, json_data = get_product_info_from_url(url)
        print("\nProduct info retrieved:", json_data)
        logger.info(f"Product info retrieved for {url}")
        
        # Import clean_json_structure from infoBot
        from infoBot import clean_json_structure
        cleaned_data = clean_json_structure(json_data, product_name)
        print("\nCleaned data:", cleaned_data)
        logger.info("Data cleaned and validated")
        
        # Import save_to_supabase from infoBot
        from infoBot import save_to_supabase
        result = await save_to_supabase(product_name, cleaned_data)
        print("\nSave result:", result)
        logger.info("Data saved to Supabase")
        
        return jsonify({
            "status": "success",
            "message": "Data successfully processed and saved to Supabase",
            "product_id": result["product_id"],
            "data": cleaned_data,
            "original_url": url,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error processing URL: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )