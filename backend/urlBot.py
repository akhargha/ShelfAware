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

# Load environment variables
load_dotenv()

app = Flask(__name__)

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
    json_str = re.sub(r'```\s*$', '', json_str)
    
    # Remove comments
    json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
    
    # Clean up any trailing commas before closing braces/brackets
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
    
    # Remove leading/trailing whitespace
    json_str = json_str.strip()
    
    return json_str

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
    """Extract and parse JSON from text response."""
    try:
        # Clean the text
        cleaned_text = clean_json_string(text)
        logger.debug(f"Cleaned JSON text: {cleaned_text}")
        
        # Parse JSON
        json_data = json.loads(cleaned_text)
        return json_data
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
    
    # First, get basic product information
    initial_prompt = f"""
    Visit this URL and extract the following information about the product: {url}
    
    I need:
    1. Product name
    2. Description
    3. Price
    4. Brand
    5. Ingredients or materials
    6. Any health or nutrition information available
    7. Any sustainability or environmental information available
    
    Return the information in a clean, structured format.
    """
    
    messages = [{"role": "user", "content": initial_prompt}]
    response = call_perplexity_api(messages, online=True)
    initial_info = response['choices'][0]['message']['content']
    logger.info("Initial product info retrieved")
    
    # Now use this information to get detailed product data
    detailed_prompt = f"""
    Based on this product information:
    
    {initial_info}
    
    Please provide detailed information in this exact JSON format. Fill in any missing information with reasonable estimates based on similar products. Do not include any comments in the JSON:

    {{
        "Health_Information": {{
            "Nutrients": {{
                "Calories": "value kcal (More than 25 kcal)",
                "Total_Fat": "value g",
                "Saturated_Fat": "value g",
                "Trans_Fat": "value g",
                "Cholesterol": "value mg",
                "Sodium": "value mg",
                "Total_Carbohydrates": "value g",
                "Dietary_Fiber": "value g",
                "Total_Sugars": "value g (More than 2 g)",
                "Added_Sugars": "value g",
                "Protein": "value g",
                "Vitamin_D": "value mcg",
                "Calcium": "value mg",
                "Iron": "value mg",
                "Potassium": "value mg"
            }},
            "Ingredients": ["ingredient1", "ingredient2", "ingredient3"],
            "Health_index": "decimal between 3.0 to 5.0"
        }},
        "Sustainability_Information": {{
            "Biodegradable": "Yes/No",
            "Recyclable": "Yes/No",
            "Sustainability_rating": "decimal between 3.0 to 5.0"
        }},
        "Price": "actual market price as decimal, use 4.99 if unknown",
        "Reliability_index": "decimal between 3.0 to 5.0",
        "Color_of_the_dustbin": "one of: blue, green, black",
        "Alternatives": [
            {{
                "Name": "actual alternative product name",
                "Health_Information": {{
                    "Nutrients": {{same structure as above}},
                    "Ingredients": ["ingredient1", "ingredient2", "ingredient3"],
                    "Health_index": "decimal between 3.0 to 5.0"
                }},
                "Sustainability_Information": {{
                    "Biodegradable": "Yes/No",
                    "Recyclable": "Yes/No",
                    "Sustainability_rating": "decimal between 3.0 to 5.0"
                }},
                "Price": "actual market price as decimal, use 4.99 if unknown",
                "Reliability_index": "decimal between 3.0 to 5.0"
            }}
        ]
    }}

    IMPORTANT:
    1. Return only valid JSON without any comments or explanations
    2. Use actual numeric values (not strings) for all measurements
    3. If price is unknown, use 4.99 as default
    4. Ensure exactly 3 alternatives are provided
    5. Do not include any comments or explanations in the JSON
    """
    
    messages = [{"role": "user", "content": detailed_prompt}]
    response = call_perplexity_api(messages, online=True)
    raw_content = response['choices'][0]['message']['content']
    
    logger.info("Detailed product info retrieved")
    
    # Extract product name from initial info
    try:
        name_match = re.search(r"Product name:?\s*([^\n]+)", initial_info, re.IGNORECASE)
        if not name_match:
            name_match = re.search(r"Name:?\s*([^\n]+)", initial_info, re.IGNORECASE)
        product_name = name_match.group(1).strip() if name_match else "Unknown Product"
    except Exception as e:
        logger.error(f"Error extracting product name: {str(e)}")
        product_name = "Unknown Product"
    
    # Parse the JSON content
    json_data = extract_json_from_text(raw_content)
    
    # Ensure price is set
    if json_data.get("Price", 0) == 0:
        json_data["Price"] = 4.99
    
    # Ensure exactly 3 alternatives
    while len(json_data.get("Alternatives", [])) < 3:
        alt_template = {
            "Name": f"Alternative Product {len(json_data['Alternatives']) + 1}",
            "Health_Information": {
                "Nutrients": json_data["Health_Information"]["Nutrients"].copy(),
                "Ingredients": json_data["Health_Information"]["Ingredients"].copy(),
                "Health_index": 4.0
            },
            "Sustainability_Information": {
                "Biodegradable": "No",
                "Recyclable": "Yes",
                "Sustainability_rating": 4.0
            },
            "Price": 4.99,
            "Reliability_index": 4.0
        }
        json_data["Alternatives"].append(alt_template)
    
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
        logger.info(f"Product info retrieved for {url}")
        
        # Import clean_json_structure from infoBot
        from infoBot import clean_json_structure
        cleaned_data = clean_json_structure(json_data, product_name)
        logger.info("Data cleaned and validated")
        
        # Import save_to_supabase from infoBot
        from infoBot import save_to_supabase
        result = await save_to_supabase(product_name, cleaned_data)
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