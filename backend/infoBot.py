from flask import Flask, request, jsonify
import requests
import json
import os
from datetime import datetime
from supabase import create_client, Client
import re
from dotenv import load_dotenv
from typing import Dict, Any, List, Tuple, Optional
from urllib.parse import unquote

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Constants from environment variables
PERPLEXITY_API_URL = os.getenv('PERPLEXITY_API_URL')
PERPLEXITY_API_KEY = f"Bearer {os.getenv('PERPLEXITY_API_KEY')}"
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

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

def get_product_info_from_url(url: str) -> Dict[str, Any]:
    """Get product information from URL using Perplexity's web access."""
    
    # First, get basic product information and category
    initial_prompt = f"""
    Visit this URL and extract the following information about the product: {url}
    
    I need:
    1. Product name
    2. Description
    3. Price (if found)
    4. Brand
    5. Category (specifically mention if this is a food item or not)
    6. Ingredients or materials
    7. Any health or nutrition information available
    8. Any sustainability or environmental information available
    9. Power consumption or energy efficiency (if applicable)
    10. Product dimensions and specifications
    
    Return the information in a clean, structured format.
    """
    
    messages = [{"role": "user", "content": initial_prompt}]
    response = call_perplexity_api(messages)
    initial_info = response['choices'][0]['message']['content']
    
    # Determine if it's a food item
    is_food = "food" in initial_info.lower() or "ingredient" in initial_info.lower()
    
    # Create nutrients structure based on whether it's a food item
    nutrients_section = """
                "Calories": "actual value kcal",
                "Total_Fat": "actual value g",
                "Saturated_Fat": "actual value g",
                "Trans_Fat": "actual value g",
                "Cholesterol": "actual value mg",
                "Sodium": "actual value mg",
                "Total_Carbohydrates": "actual value g",
                "Dietary_Fiber": "actual value g",
                "Total_Sugars": "actual value g",
                "Added_Sugars": "actual value g",
                "Protein": "actual value g",
                "Vitamin_D": "actual value mcg",
                "Calcium": "actual value mg",
                "Iron": "actual value mg",
                "Potassium": "actual value mg"
    """ if is_food else '"Not a food product"'

    health_index = "0" if not is_food else "decimal between 3.0 to 5.0"
    energy_efficiency = "null" if is_food else '"actual energy rating or consumption"'
    
    # Now use this information to get detailed product data
    detailed_prompt = f"""
    Based on this product information:
    
    {initial_info}
    
    This is {"a food item" if is_food else "not a food item"}. Provide detailed information in this exact JSON format:

    {{
        "Health_Information": {{
            "Nutrients": {{"value": {nutrients_section}}},
            "Ingredients": ["actual ingredients or materials used"],
            "Health_index": {health_index}
        }},
        "Sustainability_Information": {{
            "Biodegradable": "Yes/No",
            "Recyclable": "Yes/No",
            "Sustainability_rating": "decimal between 3.0 to 5.0",
            "Energy_Efficiency": {energy_efficiency},
            "Environmental_Impact": "description of environmental impact"
        }},
        "Price": "actual market price as decimal",
        "Reliability_index": "decimal between 3.0 to 5.0",
        "Color_of_the_dustbin": "one of: blue, green, black",
        "Technical_Specifications": {{
            "Dimensions": "actual dimensions",
            "Weight": "actual weight",
            "Material": "main material",
            "Additional_Features": ["feature1", "feature2"]
        }},
        "Alternatives": [
            {{
                "Name": "alternative product 1",
                "Brand": "brand name",
                "Health_Information": {{
                    "Nutrients": {{"value": {nutrients_section}}},
                    "Ingredients": ["actual ingredients or materials"],
                    "Health_index": {health_index}
                }},
                "Sustainability_Information": {{
                    "Biodegradable": "Yes/No",
                    "Recyclable": "Yes/No",
                    "Sustainability_rating": "3.5",
                    "Energy_Efficiency": {energy_efficiency}
                }},
                "Price": "estimated price 1",
                "Reliability_index": "3.7",
                "Key_Differences": "main differences from original product"
            }}
        ]
    }}

    IMPORTANT RULES:
    1. Must provide EXACTLY 3 alternatives with different properties
    2. For non-food items, all health-related values should be 0 and marked as "Not applicable"
    3. Estimate market prices based on similar products if exact prices aren't available
    4. Make alternatives truly different (different brands, features, prices)
    5. Include specific energy efficiency ratings for appliances
    6. All ratings (health, sustainability, reliability) must be different for each alternative
    7. Include actual technical specifications where applicable
    8. Return valid JSON without any comments or markdown
    """
    
    messages = [{"role": "user", "content": detailed_prompt}]
    response = call_perplexity_api(messages)
    raw_content = response['choices'][0]['message']['content']
    
    # Clean and parse JSON
    json_data = extract_json_from_text(raw_content)
    
    # Ensure different indices and prices for alternatives if they exist
    if "Alternatives" in json_data:
        base_sustain = float(json_data["Sustainability_Information"]["Sustainability_rating"])
        base_price = float(str(json_data["Price"]).replace("$", "").strip() or "999.99")
        
        for i, alt in enumerate(json_data["Alternatives"]):
            # Set different sustainability ratings
            alt["Sustainability_Information"]["Sustainability_rating"] = round(
                max(3.0, min(5.0, base_sustain + (i * 0.3))), 1
            )
            
            # Set different prices (±10-20%)
            price_adjustments = [-0.2, 0.1, 0.2]
            alt["Price"] = round(base_price * (1 + price_adjustments[i]), 2)
            
            # Set different health indices for food items
            if is_food:
                base_health = float(json_data["Health_Information"]["Health_index"])
                alt["Health_Information"]["Health_index"] = round(
                    max(3.0, min(5.0, base_health + (i * 0.2))), 1
                )
            else:
                alt["Health_Information"]["Health_index"] = 0
    
    return json_data
    
    return json_data@app.route('/product', methods=['GET'])
async def get_product():
    """GET endpoint to fetch product information from URL."""
    try:
        url = request.args.get('url')
        if not url:
            return jsonify({
                "status": "error",
                "error": "URL parameter is required"
            }), 400
            
        # Decode URL if it's encoded
        decoded_url = unquote(url)
        
        # Get and process product information
        product_data = get_product_info_from_url(decoded_url)
        
        return jsonify({
            "status": "success",
            "data": product_data,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error processing URL: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

def extract_product_name(info: str) -> str:
    """Extract product name from information text."""
    try:
        name_match = re.search(r"Product name:?\s*([^\n]+)", info, re.IGNORECASE)
        if not name_match:
            name_match = re.search(r"Name:?\s*([^\n]+)", info, re.IGNORECASE)
        return name_match.group(1).strip() if name_match else "Unknown Product"
    except Exception as e:
        logger.error(f"Error extracting product name: {str(e)}")
        return "Unknown Product"

def process_product_data(data: Dict[str, Any], is_food: bool) -> Dict[str, Any]:
    """Post-process the product data to ensure consistency and proper values."""
    try:
        # Ensure base price is reasonable
        if "Price" in data:
            price_str = str(data["Price"]).replace("$", "").strip()
            try:
                base_price = float(price_str)
                if base_price <= 0:
                    base_price = 99.99  # Default price for invalid values
            except ValueError:
                base_price = 99.99
            data["Price"] = base_price

        # Process alternatives
        if "Alternatives" in data:
            base_sustain = float(data["Sustainability_Information"]["Sustainability_rating"])
            
            for i, alt in enumerate(data["Alternatives"]):
                # Set different sustainability ratings
                alt["Sustainability_Information"]["Sustainability_rating"] = round(
                    max(3.0, min(5.0, base_sustain + (i * 0.3))), 1
                )
                
                # Set different prices (±10-30%)
                price_adjustments = [-0.2, 0.1, 0.3]
                alt["Price"] = round(base_price * (1 + price_adjustments[i]), 2)
                
                # Handle health indices
                if is_food:
                    base_health = float(data["Health_Information"]["Health_index"])
                    alt["Health_Information"]["Health_index"] = round(
                        max(3.0, min(5.0, base_health + (i * 0.2))), 1
                    )
                else:
                    alt["Health_Information"]["Health_index"] = 0
                    alt["Health_Information"]["Nutrients"] = {"value": "Not a food product"}

                # Set different reliability indices
                base_reliability = float(data["Reliability_index"])
                alt["Reliability_index"] = round(
                    max(3.0, min(5.0, base_reliability + (i * 0.15))), 1
                )

        return data
    except Exception as e:
        logger.error(f"Error processing product data: {str(e)}")
        raise

def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Extract and parse JSON from text response with improved error handling."""
    try:
        # Clean up common formatting issues
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Find the JSON content
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            raise Exception("No JSON found in response")
        
        json_str = json_match.group()
        json_str = json_str.replace('\n', ' ')
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON Error: {str(e)}")
        print(f"Problematic JSON: {text}")
        raise Exception(f"Invalid JSON format: {str(e)}")
    except Exception as e:
        print(f"Extraction Error: {str(e)}")
        print(f"Raw text: {text}")
        raise Exception(f"Error extracting JSON: {str(e)}")

def clean_json_structure(data: Dict[str, Any], product_name: str) -> Dict[str, Any]:
    """Clean and validate the JSON structure."""
    try:
        # Define valid dustbin colors
        VALID_DUSTBIN_COLORS = ["blue", "green", "yellow", "red", "black", "brown"]
        
        # Default nutrients structure
        default_nutrients = {
            "Calories": "150 kcal",
            "Total_Fat": "5g",
            "Saturated_Fat": "2g",
            "Trans_Fat": "0.1g",
            "Cholesterol": "10mg",
            "Sodium": "200mg",
            "Total_Carbohydrates": "25g",
            "Dietary_Fiber": "3g",
            "Total_Sugars": "5g",
            "Added_Sugars": "2g",
            "Protein": "8g",
            "Vitamin_D": "2mcg",
            "Calcium": "100mg",
            "Iron": "2mg",
            "Potassium": "200mg"
        }

        # Get or validate dustbin color
        dustbin_color = data.get("Color_of_the_dustbin", "").lower()
        if not dustbin_color or dustbin_color not in VALID_DUSTBIN_COLORS:
            dustbin_color = "blue"

        cleaned_data = {
            "Health_Information": {
                "Nutrients": data.get("Health_Information", {}).get("Nutrients", default_nutrients),
                "Ingredients": data.get("Health_Information", {}).get("Ingredients", []),
                "Health_index": float(str(data.get("Health_Information", {}).get("Health_index", "4.0")))
            },
            "Sustainability_Information": {
                "Biodegradable": str(data.get("Sustainability_Information", {}).get("Biodegradable", "Yes")),
                "Recyclable": str(data.get("Sustainability_Information", {}).get("Recyclable", "Yes")),
                "Sustainability_rating": float(str(data.get("Sustainability_Information", {}).get("Sustainability_rating", "4.0")))
            },
            "Price": float(str(data.get("Price", "9.99")).replace("$", "").strip()),
            "Reliability_index": float(str(data.get("Reliability_index", "4.0"))),
            "Color_of_the_dustbin": dustbin_color,
            "Alternatives": []
        }

        # Ensure ingredients is always an array
        if not isinstance(cleaned_data["Health_Information"]["Ingredients"], list):
            cleaned_data["Health_Information"]["Ingredients"] = []

        # Process alternatives
        alternatives = data.get("Alternatives", [])
        for alt in alternatives[:3]:  # Ensure exactly 3 alternatives
            cleaned_alt = {
                "Name": str(alt.get("Name", f"Alternative {len(cleaned_data['Alternatives'])+1}")),
                "Health_Information": {
                    "Nutrients": alt.get("Health_Information", {}).get("Nutrients", default_nutrients.copy()),
                    "Ingredients": alt.get("Health_Information", {}).get("Ingredients", []),
                    "Health_index": float(str(alt.get("Health_Information", {}).get("Health_index", "4.0")))
                },
                "Sustainability_Information": {
                    "Biodegradable": str(alt.get("Sustainability_Information", {}).get("Biodegradable", "Yes")),
                    "Recyclable": str(alt.get("Sustainability_Information", {}).get("Recyclable", "Yes")),
                    "Sustainability_rating": float(str(alt.get("Sustainability_Information", {}).get("Sustainability_rating", "4.0")))
                },
                "Price": float(str(alt.get("Price", "9.99")).replace("$", "").strip()),
                "Reliability_index": float(str(alt.get("Reliability_index", "4.0")))
            }
            
            # Ensure ingredients is always an array for alternatives
            if not isinstance(cleaned_alt["Health_Information"]["Ingredients"], list):
                cleaned_alt["Health_Information"]["Ingredients"] = []
                
            cleaned_data["Alternatives"].append(cleaned_alt)

        # Ensure exactly 3 alternatives with default values
        while len(cleaned_data["Alternatives"]) < 3:
            cleaned_data["Alternatives"].append({
                "Name": f"Alternative {len(cleaned_data['Alternatives'])+1}",
                "Health_Information": {
                    "Nutrients": default_nutrients.copy(),
                    "Ingredients": [],
                    "Health_index": 4.0
                },
                "Sustainability_Information": {
                    "Biodegradable": "Yes",
                    "Recyclable": "Yes",
                    "Sustainability_rating": 4.0
                },
                "Price": 9.99,
                "Reliability_index": 4.0
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

@app.route('/delete_all_data', methods=['GET'])
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
    # Set default port
    port = int(os.getenv('PORT', 5000))
    
    # Set debug mode based on environment
    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    
    # Run the application
    app.run(
        host='0.0.0.0',  # Make the server publicly available
        port=port,
        debug=debug
    )