from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client
import traceback
import logging.handlers
import sys
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

# Create logs directory if it doesn't exist
Path("logs").mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ProductAnalyzer")
logger.setLevel(logging.DEBUG)

# Create handlers
console_handler = logging.StreamHandler(sys.stdout)
file_handler = logging.handlers.RotatingFileHandler(
    'logs/product_analyzer.log',
    maxBytes=10485760,  # 10MB
    backupCount=5,
    encoding='utf-8'
)

# Create formatters and add it to handlers
log_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
console_handler.setFormatter(log_format)
file_handler.setFormatter(log_format)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

# Custom Exceptions
class ConfigError(Exception):
    """Raised when there's a configuration error"""
    pass

class APIError(Exception):
    """Custom exception for API errors"""
    def __init__(self, message: str, status_code: int = 500, payload: Optional[Dict] = None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self) -> Dict:
        rv = dict(self.payload or ())
        rv['message'] = self.message
        rv['status'] = 'error'
        rv['timestamp'] = datetime.utcnow().isoformat()
        return rv

class DustbinColor(Enum):
    BLUE = "blue"
    GREEN = "green"
    BLACK = "black"

@dataclass
class HealthInformation:
    nutrients: Dict
    ingredients: list
    health_index: float

@dataclass
class SustainabilityInformation:
    biodegradable: str
    recyclable: str
    sustainability_rating: float

@dataclass
class ProductAlternative:
    name: str
    health_info: HealthInformation
    sustainability_info: SustainabilityInformation
    price: float
    reliability_index: float

class ProductAnalyzer:
    def __init__(self, openai_client: OpenAI, supabase_client: Client):
        self.openai_client = openai_client
        self.supabase = supabase_client
        logger.debug("ProductAnalyzer instance created")

    async def analyze_product_url(self, url: str) -> Dict[str, Any]:
        """Analyze product URL using OpenAI."""
        try:
            logger.info(f"Starting analysis for URL: {url}")
            
            system_prompt = """You are a product analysis expert. Analyze the given URL and provide 
            comprehensive product information including sustainability metrics and market alternatives. 
            For electronics and appliances, focus on energy efficiency and recyclability."""

            user_prompt = f"""Analyze the product at {url} and provide detailed information including:
            1. Product name and specifications
            2. Sustainability metrics (recyclability, energy efficiency)
            3. Price and reliability information
            4. Three similar market alternatives with comparative analysis
            5. The color of the dustbin should be black or blue only

            Format the response as a structured JSON object matching exactly:
            {{
                "product_name": "string",
                "Health_Information": {{
                    "Nutrients": {{}},
                    "Ingredients": [],
                    "Health_index": float
                }},
                "Sustainability_Information": {{
                    "Biodegradable": "Yes/No",
                    "Recyclable": "Yes/No",
                    "Sustainability_rating": float (1-5)
                }},
                "Price": float,
                "Reliability_index": float (1-5),
                "Color_of_the_dustbin": "blue/green/black",
                "Alternatives": [
                    {{
                        "Name": "string",
                        "Health_Information": {{
                            "Nutrients": {{}},
                            "Ingredients": [],
                            "Health_index": float
                        }},
                        "Sustainability_Information": {{
                            "Biodegradable": "Yes/No",
                            "Recyclable": "Yes/No",
                            "Sustainability_rating": float
                        }},
                        "Price": float,
                        "Reliability_index": float
                    }}
                ]
            }}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.debug(f"Analysis result: {json.dumps(result, indent=2)}")
            return result

        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse OpenAI response: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            raise APIError(error_msg, status_code=500)
            
        except Exception as e:
            error_msg = f"Error in OpenAI analysis: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            raise APIError(error_msg, status_code=500)

    def validate_product_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize product data."""
        try:
            product_name = data.get("product_name")
            if not product_name:
                raise APIError("Product name is required", status_code=400)

            health_info = data.get("Health_Information", {})
            sustainability_info = data.get("Sustainability_Information", {})
            
            dustbin_color = data.get("Color_of_the_dustbin", "blue")
            if dustbin_color not in ["blue", "green", "black"] or dustbin_color == "N/A":
                dustbin_color = "blue"
            
            # Normalize numeric values
            health_index = float(str(health_info.get("Health_index", "4.0")).replace("N/A", "4.0"))
            sustainability_rating = float(str(sustainability_info.get("Sustainability_rating", "4.0")))
            price = float(str(data.get("Price", "0.0")))
            reliability_index = float(str(data.get("Reliability_index", "4.0")))

            # Validate ranges
            if not (0 <= health_index <= 10):
                health_index = 4.0
            if not (0 <= sustainability_rating <= 5):
                sustainability_rating = 4.3
            if not (0 <= reliability_index <= 5):
                reliability_index = 4.8
            if price < 0:
                price = 1000.0

            # Normalize sustainability values
            biodegradable = sustainability_info.get("Biodegradable", "No")
            if biodegradable not in ["Yes", "No"]:
                biodegradable = "No"
            recyclable = sustainability_info.get("Recyclable", "Yes")
            if recyclable not in ["Yes", "No"]:
                recyclable = "Yes"

            validated_data = {
                "product_name": product_name,
                "Health_Information": {
                    "Nutrients": health_info.get("Nutrients", {}),
                    "Ingredients": health_info.get("Ingredients", []),
                    "Health_index": health_index
                },
                "Sustainability_Information": {
                    "Biodegradable": biodegradable,
                    "Recyclable": recyclable,
                    "Sustainability_rating": sustainability_rating
                },
                "Price": price,
                "Reliability_index": reliability_index,
                "Color_of_the_dustbin": data.get("Color_of_the_dustbin", "blue"),
                "Alternatives": []
            }

            # Validate alternatives
            alternatives = data.get("Alternatives", [])
            for alt in alternatives[:3]:
                validated_alt = self.validate_alternative(alt)
                validated_data["Alternatives"].append(validated_alt)

            return validated_data

        except APIError:
            raise
        except Exception as e:
            error_msg = f"Error validating product data: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            raise APIError(error_msg, status_code=500)

    def validate_alternative(self, alt: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize alternative product data."""
        try:
            health_info = alt.get("Health_Information", {})
            sustainability_info = alt.get("Sustainability_Information", {})

            health_index = float(str(health_info.get("Health_index", "4.0")).replace("N/A", "4.0"))
            sustainability_rating = float(str(sustainability_info.get("Sustainability_rating", "4.0")))
            price = float(str(alt.get("Price", "0.0")))
            reliability_index = float(str(alt.get("Reliability_index", "4.0")))

            # Normalize ranges
            if not (0 <= health_index <= 10):
                health_index = 4.0
            if not (0 <= sustainability_rating <= 5):
                sustainability_rating = 4.0
            if not (0 <= reliability_index <= 5):
                reliability_index = 4.0
            if price < 0:
                price = 0.0

            return {
                "Name": alt.get("Name", "Alternative Product"),
                "Health_Information": {
                    "Nutrients": health_info.get("Nutrients", {}),
                    "Ingredients": health_info.get("Ingredients", []),
                    "Health_index": health_index
                },
                "Sustainability_Information": {
                    "Biodegradable": sustainability_info.get("Biodegradable", "No"),
                    "Recyclable": sustainability_info.get("Recyclable", "Yes"),
                    "Sustainability_rating": sustainability_rating
                },
                "Price": price,
                "Reliability_index": reliability_index
            }

        except Exception as e:
            logger.error(f"Error validating alternative: {str(e)}")
            return {
                "Name": "Alternative Product",
                "Health_Information": {
                    "Nutrients": {},
                    "Ingredients": [],
                    "Health_index": 4.0
                },
                "Sustainability_Information": {
                    "Biodegradable": "No",
                    "Recyclable": "Yes",
                    "Sustainability_rating": 4.0
                },
                "Price": 0.0,
                "Reliability_index": 4.0
            }

    async def save_to_supabase(self, product_name: str, product_data: Dict[str, Any]) -> str:
        """Save product data to Supabase."""
        try:
            logger.info(f"Saving product to Supabase: {product_name}")
            
            # Prepare main product data
            main_product_data = {
                "product_name": product_name,
                "health_nutrients": json.dumps(product_data["Health_Information"]["Nutrients"]),
                "health_ingredients": json.dumps(product_data["Health_Information"]["Ingredients"]),
                "health_index": float(str(product_data["Health_Information"]["Health_index"]).replace("N/A", "4.0")),
                "sustainability_biodegradable": product_data["Sustainability_Information"]["Biodegradable"],
                "sustainability_recyclable": product_data["Sustainability_Information"]["Recyclable"],
                "sustainability_rating": float(product_data["Sustainability_Information"]["Sustainability_rating"]),
                "price": float(product_data["Price"]),
                "reliability_index": float(product_data["Reliability_index"]),
                "dustbin_color": product_data.get("Color_of_the_dustbin", "blue")
            }

            # Insert main product
            result = self.supabase.table("product_information").insert(main_product_data).execute()
            product_id = result.data[0]["id"]
            
            # Insert alternatives
            for alt in product_data["Alternatives"]:
                alternative_data = {
                    "product_id": product_id,
                    "alternative_name": alt["Name"],
                    "health_nutrients": json.dumps(alt["Health_Information"]["Nutrients"]),
                    "health_ingredients": json.dumps(alt["Health_Information"]["Ingredients"]),
                    "health_index": float(str(alt["Health_Information"]["Health_index"]).replace("N/A", "4.0")),
                    "sustainability_biodegradable": alt["Sustainability_Information"]["Biodegradable"],
                    "sustainability_recyclable": alt["Sustainability_Information"]["Recyclable"],
                    "sustainability_rating": float(alt["Sustainability_Information"]["Sustainability_rating"]),
                    "price": float(alt["Price"]),
                    "reliability_index": float(alt["Reliability_index"])
                }
                self.supabase.table("product_alternatives").insert(alternative_data).execute()
            
            logger.info(f"Successfully saved product with ID: {product_id}")
            return product_id
            
        except Exception as e:
            logger.error(f"Error saving to Supabase: {str(e)}\n{traceback.format_exc()}")
            raise APIError(f"Database error: {str(e)}", status_code=500)

# Initialize Flask app and clients
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:5173"]}})
logger.info("Flask app initialized with CORS")

# Initialize OpenAI and Supabase clients
try:
    openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    logger.info("OpenAI client initialized successfully")
    
    supabase: Client = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_KEY')
    )
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.critical(f"Failed to initialize clients: {str(e)}\n{traceback.format_exc()}")
    raise

# Request logging middleware
@app.before_request
def log_request_info():
    """Log details of incoming requests."""
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request Method: {request.method}")
    logger.info(f"Request Headers: {dict(request.headers)}")
    if request.data:
        logger.info(f"Request Body: {request.get_data(as_text=True)}")

@app.after_request
def log_response_info(response):
    """Log details of outgoing responses."""
    logger.info(f"Response Status: {response.status}")
    logger.info(f"Response Headers: {dict(response.headers)}")
    return response

# Error handlers
@app.errorhandler(APIError)
def handle_api_error(error):
    """Handle custom API errors."""
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.errorhandler(Exception)
def handle_generic_error(error):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled error: {str(error)}\n{traceback.format_exc()}")
    response = jsonify({
        'status': 'error',
        'message': 'An unexpected error occurred',
        'error': str(error),
        'timestamp': datetime.utcnow().isoformat()
    })
    response.status_code = 500
    return response

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        supabase.table("product_information").select("id").limit(1).execute()
        
        return jsonify({
            "status": "healthy",
            "service": "online",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": os.getenv('FLASK_ENV', 'production')
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "service": "online",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500

@app.route('/analyze_url', methods=['POST'])
async def analyze_url():
    """Endpoint to analyze a product URL."""
    request_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
    logger.info(f"Starting new request {request_id}")
    
    try:
        # Validate request
        data = request.get_json()
        if not data or 'url' not in data:
            logger.warning(f"Request {request_id}: Missing URL in request body")
            raise APIError("URL is required", status_code=400)

        url = data['url']
        logger.info(f"Request {request_id}: Analyzing URL: {url}")

        # Initialize analyzer
        analyzer = ProductAnalyzer(openai_client, supabase)
        
        # Analyze URL with OpenAI
        logger.info(f"Request {request_id}: Starting OpenAI analysis")
        analysis_result = await analyzer.analyze_product_url(url)
        logger.info(f"Request {request_id}: OpenAI analysis completed")
        
        # Validate and clean the data
        logger.info(f"Request {request_id}: Validating data")
        validated_data = analyzer.validate_product_data(analysis_result)
        logger.info(f"Request {request_id}: Validation completed")
        
        # Save to Supabase
        logger.info(f"Request {request_id}: Saving to Supabase")
        product_id = await analyzer.save_to_supabase(
            validated_data['product_name'],
            validated_data
        )
        logger.info(f"Request {request_id}: Save completed")
        
        response_data = {
            "status": "success",
            "message": "Product analysis completed successfully",
            "data": validated_data,
            "product_id": product_id,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Request {request_id}: Successfully processed")
        return jsonify(response_data)

    except APIError:
        raise
    except Exception as e:
        logger.error(f"Request {request_id}: Unexpected error: {str(e)}\n{traceback.format_exc()}")
        raise APIError(f"Error processing URL: {str(e)}", status_code=500)

@app.route('/product/<product_id>', methods=['GET'])
async def get_product(product_id: str):
    """Get product information by ID."""
    try:
        logger.info(f"Retrieving product information for ID: {product_id}")
        
        # Get main product information
        product_result = supabase.table("product_information") \
            .select("*") \
            .eq("id", product_id) \
            .execute()
            
        if not product_result.data:
            logger.warning(f"Product not found: {product_id}")
            raise APIError("Product not found", status_code=404)
            
        product_data = product_result.data[0]
        
        # Get alternatives
        alternatives_result = supabase.table("product_alternatives") \
            .select("*") \
            .eq("product_id", product_id) \
            .execute()
            
        # Combine the data
        response_data = {
            "product_info": {
                "product_name": product_data["product_name"],
                "Health_Information": {
                    "Nutrients": json.loads(product_data["health_nutrients"]),
                    "Ingredients": json.loads(product_data["health_ingredients"]),
                    "Health_index": product_data["health_index"]
                },
                "Sustainability_Information": {
                    "Biodegradable": product_data["sustainability_biodegradable"],
                    "Recyclable": product_data["sustainability_recyclable"],
                    "Sustainability_rating": product_data["sustainability_rating"]
                },
                "Price": product_data["price"],
                "Reliability_index": product_data["reliability_index"],
                "Color_of_the_dustbin": product_data["dustbin_color"]
            },
            "alternatives": [
                {
                    "Name": alt["alternative_name"],
                    "Health_Information": {
                        "Nutrients": json.loads(alt["health_nutrients"]),
                        "Ingredients": json.loads(alt["health_ingredients"]),
                        "Health_index": alt["health_index"]
                    },
                    "Sustainability_Information": {
                        "Biodegradable": alt["sustainability_biodegradable"],
                        "Recyclable": alt["sustainability_recyclable"],
                        "Sustainability_rating": alt["sustainability_rating"]
                    },
                    "Price": alt["price"],
                    "Reliability_index": alt["reliability_index"]
                }
                for alt in alternatives_result.data
            ]
        }
        
        return jsonify({
            "status": "success",
            "data": response_data,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except APIError:
        raise
    except Exception as e:
        logger.error(f"Error retrieving product: {str(e)}\n{traceback.format_exc()}")
        raise APIError(f"Error retrieving product: {str(e)}", status_code=500)

@app.route('/stats', methods=['GET'])
async def get_stats():
    """Get basic statistics about the products in the database."""
    try:
        logger.info("Retrieving database statistics")
        
        # Get total products count
        products_count = supabase.table("product_information") \
            .select("id", count="exact") \
            .execute()
            
        # Get average sustainability rating
        sustainability_stats = supabase.table("product_information") \
            .select("sustainability_rating") \
            .execute()
            
        # Get average price
        price_stats = supabase.table("product_information") \
            .select("price") \
            .execute()
            
        # Calculate averages
        if sustainability_stats.data:
            avg_sustainability = sum(p["sustainability_rating"] for p in sustainability_stats.data) / len(sustainability_stats.data)
        else:
            avg_sustainability = 0
            
        if price_stats.data:
            avg_price = sum(p["price"] for p in price_stats.data) / len(price_stats.data)
        else:
            avg_price = 0
            
        return jsonify({
            "status": "success",
            "stats": {
                "total_products": products_count.count if hasattr(products_count, 'count') else 0,
                "average_sustainability_rating": round(avg_sustainability, 2),
                "average_price": round(avg_price, 2)
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error retrieving stats: {str(e)}\n{traceback.format_exc()}")
        raise APIError(f"Error retrieving stats: {str(e)}", status_code=500)

if __name__ == '__main__':
    # Verify required environment variables
    required_vars = ['OPENAI_API_KEY', 'SUPABASE_URL', 'SUPABASE_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ConfigError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    
    logger.info(f"Starting server on port {port} with debug={debug}")
    app.run(host='0.0.0.0', port=port, debug=debug)