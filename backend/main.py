# main.py
from flask import Flask, request, jsonify
from vision_processor import VisionProcessor
import json
import os
from datetime import datetime
import asyncio
from threading import Thread

app = Flask(__name__)
vision_processor = None

def initialize_vision():
    global vision_processor
    if vision_processor is None:
        vision_processor = VisionProcessor()

# Instead of before_first_request, we'll use an initialization function
# and call it when creating the app
initialize_vision()

@app.route('/start_vision_processing', methods=['POST'])
def start_vision_processing():
    """Start the vision processing in a separate thread"""
    try:
        def process_vision():
            objects_data = vision_processor.process_objects()
            vision_processor.save_results(objects_data)
            
        thread = Thread(target=process_vision)
        thread.start()
        
        return jsonify({
            "status": "success",
            "message": "Vision processing started"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/process_vision_results', methods=['POST'])
async def process_vision_results():
    """Process saved vision results through the AI pipeline"""
    try:
        # Check if results file exists
        if not os.path.exists('vision_output.json'):
            return jsonify({
                "error": "No vision processing results found"
            }), 404

        # Read vision results
        with open('vision_output.json', 'r') as f:
            vision_data = json.load(f)

        # Extract and combine all text
        combined_text = " ".join([obj["text"] for obj in vision_data if obj["text"]])
        
        # Process through your existing pipeline
        raw_info = get_raw_product_info(combined_text)
        json_data = extract_json_from_text(raw_info)
        cleaned_data = clean_json_structure(json_data)
        
        # Save to database
        result = await save_to_supabase(combined_text, cleaned_data)

        return jsonify({
            "status": "success",
            "message": "Vision results processed successfully",
            "product_id": result["product_id"],
            "vision_data": vision_data,
            "processed_data": cleaned_data
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        return jsonify({
            "status": "healthy",
            "vision_processor": "initialized" if vision_processor else "not initialized",
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

# Create an application factory function
def create_app():
    initialize_vision()
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True,port=5001)