from flask import Flask, request, jsonify
import requests
import json
import os
from datetime import datetime
from supabase import create_client, Client
from typing import Dict, Any, List
import re
from dotenv import load_dotenv

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

def get_raw_product_info(product_name: str) -> str:
    """Get detailed raw information about the product."""
    prompt = f"""
    Please provide detailed information about {product_name} in JSON format with the following structure:
    {{
        "Health_Information": {{
            "Nutrients": {{
                "Calories": "amount per serving",
                "Total_Fat": "grams per serving",
                "Saturated_Fat": "grams per serving",
                "Trans_Fat": "grams per serving",
                "Cholesterol": "mg per serving",
                "Sodium": "mg per serving",
                "Total_Carbohydrates": "grams per serving",
                "Dietary_Fiber": "grams per serving",
                "Total_Sugars": "grams per serving",
                "Added_Sugars": "grams per serving",
                "Protein": "grams per serving",
                "Vitamin_D": "mcg per serving",
                "Calcium": "mg per serving",
                "Iron": "mg per serving",
                "Potassium": "mg per serving"
            }},
            "Ingredients": ["ingredient1", "ingredient2", "ingredient3", ...],
            "Health_index": "..." (It must be a decimal from 0 to 5.0)
        }},
        "Sustainability_Information": {{
            "Biodegradable": "...",
            "Recyclable": "...",
            "Sustainability_rating": "..." (It must be a decimal from 0 to 5.0)
        }},
        "Price": "0.00",
        "Reliability_index": "..." (It must be a decimal from 0 to 5.0),
        "Alternatives": [
            {{
                "Name": "...",
                "Health_Information": {{
                    "Nutrients": {{
                        "Calories": "amount per serving",
                        "Total_Fat": "grams per serving",
                        "Saturated_Fat": "grams per serving",
                        "Trans_Fat": "grams per serving",
                        "Cholesterol": "mg per serving",
                        "Sodium": "mg per serving",
                        "Total_Carbohydrates": "grams per serving",
                        "Dietary_Fiber": "grams per serving",
                        "Total_Sugars": "grams per serving",
                        "Added_Sugars": "grams per serving",
                        "Protein": "grams per serving",
                        "Vitamin_D": "mcg per serving",
                        "Calcium": "mg per serving",
                        "Iron": "mg per serving",
                        "Potassium": "mg per serving"
                    }},
                    "Ingredients": ["ingredient1", "ingredient2", "ingredient3", ...],
                    "Health_index": "..." (It must be a decimal from 0 to 5.0)
                }},
                "Sustainability_Information": {{
                    "Biodegradable": "...",
                    "Recyclable": "...",
                    "Sustainability_rating": "..." (It must be a decimal from 0 to 5.0)
                }},
                "Price": "0.00",
                "Reliability_index": "..." (It must be a decimal from 0 to 5.0)
            }}
        ],
        "Color_of_the_dustbin": "..."
    }}
    Return only the JSON, without any additional text or explanation.
    Ensure all nutrient values are numerical values with their units.
    Ingredients should be an array of strings, listed in order of predominance.
    If any of the information is not specified or 0, make up data values for it.
    """
    
    messages = [{"role": "user", "content": prompt}]
    response = call_perplexity_api(messages)
    raw_content = response['choices'][0]['message']['content']
    print("Raw LLM Response:")
    print(raw_content)
    return raw_content

def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Extract and parse JSON from text response with improved error handling."""
    try:
        # Clean up common formatting issues
        # Remove any markdown code block indicators
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Find the JSON content
        json_match = re.search(r'\{[\s\S]*\}', text)
        if not json_match:
            raise Exception("No JSON found in response")
        
        json_str = json_match.group()
        
        # Clean up any potential issues
        json_str = json_str.replace('\n', ' ')  # Remove newlines
        json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
        json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas in arrays
        
        # Parse the cleaned JSON
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON Error: {str(e)}")
        print(f"Problematic JSON: {text}")
        raise Exception(f"Invalid JSON format: {str(e)}")
    except Exception as e:
        print(f"Extraction Error: {str(e)}")
        print(f"Raw text: {text}")
        raise Exception(f"Error extracting JSON: {str(e)}")

def clean_json_structure(data: Dict[str, Any]) -> Dict[str, Any]:
    """Clean and validate the JSON structure."""
    try:
        # Default nutrients structure
        default_nutrients = {
            "Calories": "0 kcal",
            "Total_Fat": "0g",
            "Saturated_Fat": "0g",
            "Trans_Fat": "0g",
            "Cholesterol": "0mg",
            "Sodium": "0mg",
            "Total_Carbohydrates": "0g",
            "Dietary_Fiber": "0g",
            "Total_Sugars": "0g",
            "Added_Sugars": "0g",
            "Protein": "0g",
            "Vitamin_D": "0mcg",
            "Calcium": "0mg",
            "Iron": "0mg",
            "Potassium": "0mg"
        }

        cleaned_data = {
            "Health_Information": {
                "Nutrients": data.get("Health_Information", {}).get("Nutrients", default_nutrients),
                "Ingredients": data.get("Health_Information", {}).get("Ingredients", []),
                "Health_index": str(data.get("Health_Information", {}).get("Health_index", "0.0"))
            },
            "Sustainability_Information": {
                "Biodegradable": str(data.get("Sustainability_Information", {}).get("Biodegradable", "Not specified")),
                "Recyclable": str(data.get("Sustainability_Information", {}).get("Recyclable", "Not specified")),
                "Sustainability_rating": str(data.get("Sustainability_Information", {}).get("Sustainability_rating", "0.0"))
            },
            "Price": str(data.get("Price", "0.00")),
            "Reliability_index": str(data.get("Reliability_index", "0.0")),
            "Color_of_the_dustbin": str(data.get("Color_of_the_dustbin", "blue")).lower(),
            "Alternatives": []
        }

        # Ensure ingredients is always an array
        if not isinstance(cleaned_data["Health_Information"]["Ingredients"], list):
            cleaned_data["Health_Information"]["Ingredients"] = []

        # Clean alternatives
        raw_alternatives = data.get("Alternatives", [])
        for alt in raw_alternatives[:3]:  # Ensure exactly 3 alternatives
            cleaned_alt = {
                "Name": str(alt.get("Name", "Not specified")),
                "Health_Information": {
                    "Nutrients": alt.get("Health_Information", {}).get("Nutrients", default_nutrients),
                    "Ingredients": alt.get("Health_Information", {}).get("Ingredients", []),
                    "Health_index": str(alt.get("Health_Information", {}).get("Health_index", "0.0"))
                },
                "Sustainability_Information": {
                    "Biodegradable": str(alt.get("Sustainability_Information", {}).get("Biodegradable", "Not specified")),
                    "Recyclable": str(alt.get("Sustainability_Information", {}).get("Recyclable", "Not specified")),
                    "Sustainability_rating": str(alt.get("Sustainability_Information", {}).get("Sustainability_rating", "0.0"))
                },
                "Price": str(alt.get("Price", "0.00")),
                "Reliability_index": str(alt.get("Reliability_index", "0.0"))
            }
            
            # Ensure ingredients is always an array for alternatives
            if not isinstance(cleaned_alt["Health_Information"]["Ingredients"], list):
                cleaned_alt["Health_Information"]["Ingredients"] = []
                
            cleaned_data["Alternatives"].append(cleaned_alt)

        # Ensure exactly 3 alternatives
        while len(cleaned_data["Alternatives"]) < 3:
            cleaned_data["Alternatives"].append({
                "Name": "Not specified",
                "Health_Information": {
                    "Nutrients": default_nutrients.copy(),
                    "Ingredients": [],
                    "Health_index": "0.0"
                },
                "Sustainability_Information": {
                    "Biodegradable": "Not specified",
                    "Recyclable": "Not specified",
                    "Sustainability_rating": "0.0"
                },
                "Price": "0.00",
                "Reliability_index": "0.0"
            })

        return cleaned_data
    except Exception as e:
        raise Exception(f"Error cleaning JSON structure: {str(e)}")
    

async def save_to_supabase(product_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Save the structured data to Supabase database."""
    try:
        # Ensure nutrients is a valid JSON object
        nutrients = data["Health_Information"]["Nutrients"]
        if isinstance(nutrients, str):
            try:
                nutrients = json.loads(nutrients)
            except json.JSONDecodeError:
                nutrients = {
                    "Calories": "0 kcal",
                    "Total_Fat": "0g",
                    "Saturated_Fat": "0g",
                    "Trans_Fat": "0g",
                    "Cholesterol": "0mg",
                    "Sodium": "0mg",
                    "Total_Carbohydrates": "0g",
                    "Dietary_Fiber": "0g",
                    "Total_Sugars": "0g",
                    "Added_Sugars": "0g",
                    "Protein": "0g",
                    "Vitamin_D": "0mcg",
                    "Calcium": "0mg",
                    "Iron": "0mg",
                    "Potassium": "0mg"
                }

        # Ensure ingredients is a valid JSON array
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
            "health_nutrients": json.dumps(nutrients),  # Ensure valid JSON string
            "health_ingredients": json.dumps(ingredients),  # Ensure valid JSON array string
            "health_index": float(str(data["Health_Information"]["Health_index"]).replace("$", "").strip() or "3.6"),
            "sustainability_biodegradable": data["Sustainability_Information"]["Biodegradable"],
            "sustainability_recyclable": data["Sustainability_Information"]["Recyclable"],
            "sustainability_rating": float(str(data["Sustainability_Information"]["Sustainability_rating"]).replace("$", "").strip() or "2.6"),
            "price": float(str(data["Price"]).replace("$", "").strip() or "10.00"),
            "reliability_index": float(str(data["Reliability_index"]).replace("$", "").strip() or "3.1"),
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
                    alt_nutrients = {
                        "Calories": "0 kcal",
                        "Total_Fat": "0g",
                        "Saturated_Fat": "0g",
                        "Trans_Fat": "0g",
                        "Cholesterol": "0mg",
                        "Sodium": "0mg",
                        "Total_Carbohydrates": "0g",
                        "Dietary_Fiber": "0g",
                        "Total_Sugars": "0g",
                        "Added_Sugars": "0g",
                        "Protein": "0g",
                        "Vitamin_D": "0mcg",
                        "Calcium": "0mg",
                        "Iron": "0mg",
                        "Potassium": "0mg"
                    }

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
                "health_nutrients": json.dumps(alt_nutrients),  # Ensure valid JSON string
                "health_ingredients": json.dumps(alt_ingredients),  # Ensure valid JSON array string
                "health_index": float(str(alt["Health_Information"]["Health_index"]).replace("$", "").strip() or "4.00"),
                "sustainability_biodegradable": alt["Sustainability_Information"]["Biodegradable"],
                "sustainability_recyclable": alt["Sustainability_Information"]["Recyclable"],
                "sustainability_rating": float(str(alt["Sustainability_Information"]["Sustainability_rating"]).replace("$", "").strip() or "3.9"),
                "price": float(str(alt["Price"]).replace("$", "").strip() or "2.05"),
                "reliability_index": float(str(alt["Reliability_index"]).replace("$", "").strip() or "3.90")
            }
            supabase.table("product_alternatives").insert(alternative_data).execute()

        return {"product_id": product_id, "status": "success"}

    except Exception as e:
        print(f"Save error details: {str(e)}")  # Debug print
        raise Exception(f"Database error: {str(e)}")
    

async def delete_all_data() -> Dict[str, Any]:
    """Delete all data from both tables in the database."""
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
        print(f"Detailed error: {str(e)}")  # For debugging
        raise Exception(f"Database deletion error: {str(e)}")

@app.route('/fetch_product', methods=['POST'])
async def fetch_product():
    try:
        data = request.get_json()
        product_name = data.get('product_name')
        
        if not product_name:
            return jsonify({"error": "Product name is required"}), 400
        
        # Get raw product information
        raw_info = get_raw_product_info(product_name)
        
        # Extract JSON from the response
        json_data = extract_json_from_text(raw_info)
        
        # Clean and validate the JSON structure
        cleaned_data = clean_json_structure(json_data)
        
        # Save to Supabase
        result = await save_to_supabase(product_name, cleaned_data)
        
        return jsonify({
            "message": "Data successfully processed and saved to Supabase",
            "product_id": result["product_id"],
            "data": cleaned_data
        })
        
    except Exception as e:
        print(f"Error details: {str(e)}")  # For debugging
        return jsonify({"error": str(e)}), 500

@app.route('/delete_all_data', methods=['GET'])
async def delete_all_data_route():
    try:
        # Add basic authentication check
        auth_header = request.headers.get('Authorization')
        expected_auth = f"Bearer {os.getenv('SUPABASE_KEY')}"
        
        if not auth_header or auth_header != expected_auth:
            return jsonify({"error": "Unauthorized"}), 401
        
        result = await delete_all_data()
        
        return jsonify({
            "message": "All data successfully deleted",
            "details": {
                "alternatives_deleted": result["deleted_alternatives"],
                "products_deleted": result["deleted_products"]
            }
        })
        
    except Exception as e:
        print(f"Error during deletion: {str(e)}")  # For debugging
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    try:
        # Test database connection
        supabase.table("product_information").select("id").limit(1).execute()
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

if __name__ == '__main__':
    app.run(debug=True)