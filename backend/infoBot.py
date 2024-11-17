from flask import Flask, request, jsonify
import requests
import json
import os
from datetime import datetime
from supabase import create_client, Client
from typing import Dict, Any, List
import re
from dotenv import load_dotenv
import json
from pathlib import Path

from flask import Flask, request, jsonify
from flask.views import MethodView
from asgiref.wsgi import WsgiToAsgi
from hypercorn.config import Config
from hypercorn.asyncio import serve
import asyncio
# Load environment variables

load_dotenv()

app = Flask(__name__)

# Constants from environment variables
PERPLEXITY_API_URL = os.getenv('PERPLEXITY_API_URL')
PERPLEXITY_API_KEY = f"Bearer {os.getenv('PERPLEXITY_API_KEY')}"
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

VISION_PROCESS_PATH = Path("vision_output.json")

def read_vision_process_file() -> str:
    """Read and parse the vision process JSON file to get product name."""
    try:
        if not VISION_PROCESS_PATH.exists():
            raise FileNotFoundError(f"Vision process file not found at {VISION_PROCESS_PATH}")
        
        with open(VISION_PROCESS_PATH, 'r') as file:
            data = json.load(file)
            product_name = data.get("product_name")
            
            if not product_name:
                raise ValueError("No product name found in vision process file")
                
            return product_name
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON in vision process file: {str(e)}")
    except Exception as e:
        raise Exception(f"Error reading vision process file: {str(e)}")

# Validate environment variables
if not all([PERPLEXITY_API_URL, PERPLEXITY_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
    raise EnvironmentError("Missing required environment variables. Please check your .env file.")

# Initialize Supabase client
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    raise Exception(f"Failed to initialize Supabase client: {str(e)}")

def call_perplexity_api(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Helper function to make requests to the Perplexity API."""
    headers = {
        "Authorization": PERPLEXITY_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-sonar-small-128k-online",
        "messages": messages
    }
    
    response = requests.post(PERPLEXITY_API_URL, json=payload, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"API Error: {response.status_code}, {response.text}")
    
    return response.json()

def get_raw_product_info(product_name: str) -> str:
    """Get detailed raw information about the product with improved prompt engineering."""
    prompt = f"""
    Provide ONLY a JSON object for {product_name} with EXACT numeric values (no text descriptions in numeric fields).
    Follow this STRICT format:

    {{
        "Health_Information": {{
            "Nutrients": {{
                "Calories": "number kcal",
                "Total_Fat": "number g",
                "Saturated_Fat": "number g",
                "Trans_Fat": "number g",
                "Cholesterol": "number mg",
                "Sodium": "number mg",
                "Total_Carbohydrates": "number g",
                "Dietary_Fiber": "number g",
                "Total_Sugars": "number g",
                "Added_Sugars": "number g",
                "Protein": "number g",
                "Vitamin_D": "number mcg",
                "Calcium": "number mg",
                "Iron": "number mg",
                "Potassium": "number mg"
            }},
            "Ingredients": ["ingredient1", "ingredient2", "ingredient3"], (Find the ingredients of product or make it up)
            "Health_index": number
        }},
        "Sustainability_Information": {{
            "Biodegradable": "Yes/No",
            "Recyclable": "Yes/No",
            "Sustainability_rating": number
        }},
        "Price": number,
        "Reliability_index": number,
        "Color_of_the_dustbin": "blue/green/black",
        "Technical_Specifications": {{
            "Material": "string"
        }},
        "Alternatives": [
            {{
                "Name": "string",
                "Brand": "string",
                "Health_Information": {{
                    "Nutrients": {{same as above}},
                    "Ingredients": ["ingredient1", "ingredient2"],
                    "Health_index": number
                }},
                "Sustainability_Information": {{
                    "Biodegradable": "Yes/No",
                    "Recyclable": "Yes/No",
                    "Sustainability_rating": number
                }},
                "Price": number,
                "Reliability_index": number,
            }}
        ]
    }}
    
    (IMPORTANT) All the data values for indexes should be different and non 0

    CRITICAL RULES:
    1. ALL numeric values must be plain numbers (e.g., 7.50 not "$7.50" or "7.50 per liter")
    2. ALL ratings must be numbers between 2.0 and 5.0
    3. Prices must be numbers only (no currency symbols or units)
    4. Health_index and other indices must be numbers only
    5. Return exactly 3 alternatives
    6. No additional text or explanations - ONLY the JSON object
    7. No placeholders or text descriptions in numeric fields
    8. All the alternatives should be real market alternatives
    9. All the ingredients should be real market ingredients
    """
    
    messages = [{"role": "user", "content": prompt}]
    response = call_perplexity_api(messages)
    raw_content = response['choices'][0]['message']['content']
    return raw_content


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Extract and parse JSON from text response with improved error handling."""
    try:
        # Clean up common formatting issues
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'\s*', '', text)
        text = re.sub(r'\n\s*#.*$', '', text, flags=re.MULTILINE)  # Remove comments
        
        # Find the JSON content
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            raise Exception("No JSON found in response")
        
        json_str = json_match.group()
        parsed_json = json.loads(json_str)
        
        # Validate required fields
        required_fields = ['Health_Information', 'Sustainability_Information', 'Price', 'Reliability_index', 'Alternatives']
        missing_fields = [field for field in required_fields if field not in parsed_json]
        if missing_fields:
            raise Exception(f"Missing required fields: {', '.join(missing_fields)}")
        
        return parsed_json
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON format: {str(e)}")
    except Exception as e:
        raise Exception(f"Error extracting JSON: {str(e)}")

def clean_json_structure(data: Dict[str, Any], product_name: str) -> Dict[str, Any]:
    """Clean and validate the JSON structure with improved error handling."""
    try:
        # Define valid values and defaults
        VALID_DUSTBIN_COLORS = ["blue", "green", "black"]
        DEFAULT_RATING = 4.0
        DEFAULT_PRICE = 9.99
        
        def clean_number(value: Any, default: float) -> float:
            """Clean and validate numeric values."""
            try:
                if isinstance(value, (int, float)):
                    return float(value)
                if isinstance(value, str):
                    # Remove any non-numeric characters except dots
                    clean_str = re.sub(r'[^\d.]', '', value)
                    return float(clean_str) if clean_str else default
                return default
            except (ValueError, TypeError):
                return default

        def clean_rating(value: Any) -> float:
            """Clean and validate rating values to be between 3.0 and 5.0."""
            rating = clean_number(value, DEFAULT_RATING)
            return max(3.0, min(5.0, rating))

        # Clean main product data
        cleaned_data = {
            "Health_Information": {
                "Nutrients": data.get("Health_Information", {}).get("Nutrients", {}),
                "Ingredients": data.get("Health_Information", {}).get("Ingredients", []),
                "Health_index": clean_rating(data.get("Health_Information", {}).get("Health_index", DEFAULT_RATING))
            },
            "Sustainability_Information": {
                "Biodegradable": str(data.get("Sustainability_Information", {}).get("Biodegradable", "No")).capitalize(),
                "Recyclable": str(data.get("Sustainability_Information", {}).get("Recyclable", "Yes")).capitalize(),
                "Sustainability_rating": clean_rating(data.get("Sustainability_Information", {}).get("Sustainability_rating", DEFAULT_RATING))
            },
            "Price": clean_number(data.get("Price", DEFAULT_PRICE), DEFAULT_PRICE),
            "Reliability_index": clean_rating(data.get("Reliability_index", DEFAULT_RATING)),
            "Color_of_the_dustbin": data.get("Color_of_the_dustbin", "blue").lower(),
            "Alternatives": []
        }

        # Process alternatives
        alternatives = data.get("Alternatives", [])
        for alt in alternatives[:3]:
            cleaned_alt = {
                "Name": str(alt.get("Name", "Alternative Product")),
                "Brand": str(alt.get("Brand", "Unknown Brand")),
                "Health_Information": {
                    "Nutrients": alt.get("Health_Information", {}).get("Nutrients", {}),
                    "Ingredients": alt.get("Health_Information", {}).get("Ingredients", []),
                    "Health_index": clean_rating(alt.get("Health_Information", {}).get("Health_index", DEFAULT_RATING))
                },
                "Sustainability_Information": {
                    "Biodegradable": str(alt.get("Sustainability_Information", {}).get("Biodegradable", "No")).capitalize(),
                    "Recyclable": str(alt.get("Sustainability_Information", {}).get("Recyclable", "Yes")).capitalize(),
                    "Sustainability_rating": clean_rating(alt.get("Sustainability_Information", {}).get("Sustainability_rating", DEFAULT_RATING))
                },
                "Price": clean_number(alt.get("Price", DEFAULT_PRICE), DEFAULT_PRICE),
                "Reliability_index": clean_rating(alt.get("Reliability_index", DEFAULT_RATING)),
                "Key_Differences": str(alt.get("Key_Differences", "Alternative product option"))
            }
            cleaned_data["Alternatives"].append(cleaned_alt)

        # Ensure exactly 3 alternatives
        while len(cleaned_data["Alternatives"]) < 3:
            cleaned_data["Alternatives"].append({
                "Name": f"Alternative {len(cleaned_data['Alternatives'])+1}",
                "Brand": "Generic Brand",
                "Health_Information": {
                    "Nutrients": {},
                    "Ingredients": [],
                    "Health_index": DEFAULT_RATING
                },
                "Sustainability_Information": {
                    "Biodegradable": "No",
                    "Recyclable": "Yes",
                    "Sustainability_rating": DEFAULT_RATING
                },
                "Price": DEFAULT_PRICE,
                "Reliability_index": DEFAULT_RATING,
                "Key_Differences": "Alternative product option"
            })

        return cleaned_data

    except Exception as e:
        raise Exception(f"Error cleaning JSON structure: {str(e)}")
    
    
async def save_to_supabase(product_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Save the structured data to Supabase database."""
    try:
        # Ensure nutrients and ingredients are valid JSON
        nutrients = data["Health_Information"]["Nutrients"]
        if isinstance(nutrients, str):
            try:
                nutrients = json.loads(nutrients)
            except json.JSONDecodeError:
                nutrients = {}
                
        ingredients = data["Health_Information"]["Ingredients"]
        if isinstance(ingredients, str):
            try:
                ingredients = json.loads(ingredients)
            except json.JSONDecodeError:
                ingredients = []
        if not isinstance(ingredients, list):
            ingredients = [str(ingredients)]

        # Prepare main product data
        main_product_data = {
            "product_name": product_name,
            "health_nutrients": json.dumps(nutrients),
            "health_ingredients": json.dumps(ingredients),
            "health_index": float(str(data["Health_Information"]["Health_index"]).replace("$", "").strip() or "4.0"),
            "sustainability_biodegradable": data["Sustainability_Information"]["Biodegradable"],
            "sustainability_recyclable": data["Sustainability_Information"]["Recyclable"],
            "sustainability_rating": float(str(data["Sustainability_Information"]["Sustainability_rating"]).replace("$", "").strip() or "4.0"),
            "price": float(str(data["Price"]).replace("$", "").strip() or "9.99"),
            "reliability_index": float(str(data["Reliability_index"]).replace("$", "").strip() or "4.0"),
            "dustbin_color": data["Color_of_the_dustbin"].lower()
        }

        # Insert main product
        result = supabase.table("product_information").insert(main_product_data).execute()
        product_id = result.data[0]["id"]

        # Insert alternatives
        for alt in data["Alternatives"]:
            # Process alternative nutrients
            alt_nutrients = alt["Health_Information"]["Nutrients"]
            if isinstance(alt_nutrients, str):
                try:
                    alt_nutrients = json.loads(alt_nutrients)
                except json.JSONDecodeError:
                    alt_nutrients = {}

            # Process alternative ingredients
            alt_ingredients = alt["Health_Information"]["Ingredients"]
            if isinstance(alt_ingredients, str):
                try:
                    alt_ingredients = json.loads(alt_ingredients)
                except json.JSONDecodeError:
                    alt_ingredients = []
            if not isinstance(alt_ingredients, list):
                alt_ingredients = [str(alt_ingredients)]

            alternative_data = {
                "product_id": product_id,
                "alternative_name": alt["Name"],
                "health_nutrients": json.dumps(alt_nutrients),
                "health_ingredients": json.dumps(alt_ingredients),
                "health_index": float(str(alt["Health_Information"]["Health_index"]).replace("$", "").strip() or "4.0"),
                "sustainability_biodegradable": alt["Sustainability_Information"]["Biodegradable"],
                "sustainability_recyclable": alt["Sustainability_Information"]["Recyclable"],
                "sustainability_rating": float(str(alt["Sustainability_Information"]["Sustainability_rating"]).replace("$", "").strip() or "4.0"),
                "price": float(str(alt["Price"]).replace("$", "").strip() or "9.99"),
                "reliability_index": float(str(alt["Reliability_index"]).replace("$", "").strip() or "4.0")
            }
            supabase.table("product_alternatives").insert(alternative_data).execute()

        return {"product_id": product_id, "status": "success"}

    except Exception as e:
        print(f"Save error details: {str(e)}")
        raise Exception(f"Database error: {str(e)}")
    
async def delete_all_data() -> Dict[str, Any]:
    
    try:
        # First count the records that will be deleted
        alternatives_count = supabase.table("product_alternatives").select("id", count="exact").execute()
        products_count = supabase.table("product_information").select("id", count="exact").execute()
        
        # Delete all records using proper conditions for UUID columns
        alternatives_result = supabase.table("product_alternatives").delete().gte('id', '00000000-0000-0000-0000-000000000000').execute()
        products_result = supabase.table("product_information").delete().gte('id', '00000000-0000-0000-0000-000000000000').execute()
        
        return {
            "status": "success",
            "deleted_alternatives": alternatives_count.count if hasattr(alternatives_count, 'count') else 0,
            "deleted_products": products_count.count if hasattr(products_count, 'count') else 0
        }
    except Exception as e:
        print(f"Detailed error: {str(e)}")
        raise Exception(f"Database deletion error: {str(e)}")
    

class VisionProcessView(MethodView):
    async def get(self):
        """
        Endpoint to process vision data from JSON file and store in database.
        Expects a JSON file with just the product name.
        """
        try:
            # Read product name from vision process file
            product_name = read_vision_process_file()
            print("\nProduct name from vision:", product_name)
            
            # Get product information from Perplexity API
            raw_info = get_raw_product_info(product_name)
            print("\nRaw API info:", raw_info)
            
            # Extract and clean JSON from API response
            json_data = extract_json_from_text(raw_info)
            print("\nExtracted JSON:", json_data)
            
            # Clean and validate the JSON structure
            cleaned_data = clean_json_structure(json_data, product_name)
            print("\nCleaned data:", cleaned_data)
            
            # Save to Supabase
            result = await save_to_supabase(product_name, cleaned_data)
            print("\nSave result:", result)
            
            return jsonify({
                "status": "success",
                "message": "Vision data successfully processed and saved",
                "product_id": result["product_id"],
                "data": cleaned_data,
                "product_name": product_name,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except FileNotFoundError as e:
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 404
        except ValueError as e:
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 400
        except Exception as e:
            print(f"Error details: {str(e)}")
            return jsonify({
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500

# Add this line after the class definition
app.add_url_rule('/process_vision', view_func=VisionProcessView.as_view('process_vision'))
@app.route('/fetch_product', methods=['POST'])
async def fetch_product():
    """Endpoint to fetch and process product information."""
    try:
        data = request.get_json()
        product_name = data.get('product_name')
        
        if not product_name:
            return jsonify({
                "status": "error",
                "error": "Product name is required"
            }), 400
        
        # Get raw product information
        raw_info = get_raw_product_info(product_name)
        print("\nRaw info:", raw_info)
        
        # Extract JSON from the response
        json_data = extract_json_from_text(raw_info)
        print("\nExtracted JSON:", json_data)
        
        # Clean and validate the JSON structure
        cleaned_data = clean_json_structure(json_data, product_name)
        print("\nCleaned data:", cleaned_data)
        
        # Save to Supabase
        result = await save_to_supabase(product_name, cleaned_data)
        print("\nSave result:", result)
        
        return jsonify({
            "status": "success",
            "message": "Data successfully processed and saved to Supabase",
            "product_id": result["product_id"],
            "data": cleaned_data,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"Error details: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


async def delete_all_data_route():
    """
    Endpoint to delete all data from the database.
    Requires authentication via Bearer token.
    """
    try:
        # Validate authentication
        auth_header = request.headers.get('Authorization')
        expected_auth = f"Bearer {os.getenv('SUPABASE_KEY')}"
        
        if not auth_header:
            return jsonify({
                "status": "error",
                "error": "Authentication required"
            }), 401
            
        if auth_header != expected_auth:
            return jsonify({
                "status": "error",
                "error": "Invalid authentication credentials"
            }), 401
        
        # Perform deletion
        result = await delete_all_data()
            
        return jsonify({
            "status": "success",
            "message": "All data successfully deleted",
            "details": {
                "deleted_at": datetime.utcnow().isoformat(),
                "alternatives_deleted": result["deleted_alternatives"],
                "products_deleted": result["deleted_products"]
            }
        }), 200
            
    except Exception as e:
        print(f"Request error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Invalid request",
            "details": str(e)
        }), 400

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify service status.
    Tests database connectivity and returns service status.
    """
    try:
        # Test database connection
        supabase.table("product_information").select("id").limit(1).execute()
        
        return jsonify({
            "status": "healthy",
            "service": "online",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "environment": os.getenv('FLASK_ENV', 'production')
        }), 200
        
    except Exception as e:
        print(f"Health check error: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "service": "online",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "environment": os.getenv('FLASK_ENV', 'production')
        }), 500

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    return jsonify({
        "status": "error",
        "error": "Resource not found",
        "path": request.path
    }), 404

@app.errorhandler(405)
def method_not_allowed_error(error):
    """Handle 405 errors."""
    return jsonify({
        "status": "error",
        "error": "Method not allowed",
        "method": request.method,
        "path": request.path,
        "allowed_methods": list(request.url_rule.methods) if request.url_rule else None
    }), 405

@app.errorhandler(500)
def internal_server_error(error):
    """Handle 500 errors."""
    return jsonify({
        "status": "error",
        "error": "Internal server error",
        "details": str(error)
    }), 500

if __name__ == '__main__':
    config = Config()
    config.bind = [f"0.0.0.0:{int(os.getenv('PORT', 5000))}"]
    config.use_reloader = os.getenv('FLASK_ENV', 'production') == 'development'
    
    asgi_app = WsgiToAsgi(app)
    asyncio.run(serve(asgi_app, config))
    