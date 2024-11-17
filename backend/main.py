from flask import Flask, jsonify, Response
import time
import json
import os
from ultralytics import YOLO
import easyocr
from flask_cors import CORS
import threading
import queue
import numpy as np
import cv2
import subprocess
import sys

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5173"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

class VisionProcessor:
    def __init__(self):
        self.FPS_LIMIT = 10
        self.CONFIDENCE_THRESHOLD = 0.7
        self.output_file = "vision_output.json"
        
        # Initialize YOLO and OCR
        self.reader = easyocr.Reader(['en'], gpu=False)
        self.model = YOLO("yolov8n-seg.pt")
        self.model.overrides["conf"] = 0.5
        self.model.overrides["iou"] = 0.5

        self.processing = False
        self.detected_text = None
        
        # Camera variables
        self.camera = None
        self.camera_index = 0  # Default camera index
        self.frame_queue = queue.Queue(maxsize=10)
        self.result_queue = queue.Queue()
        self.stop_event = threading.Event()
        
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        # Error tracking
        self.error_message = None

    def find_available_camera(self):
        """Try to find an available camera by testing different indices and methods."""
        # Try common camera indices
        for index in range(4):  # Try cameras 0-3
            try:
                cap = cv2.VideoCapture(index)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret:
                        cap.release()
                        self.camera_index = index
                        print(f"Found working camera at index {index}")
                        return True
                cap.release()
            except Exception as e:
                print(f"Error trying camera index {index}: {e}")
                continue

        # If no camera found, try platform-specific device paths
        if sys.platform.startswith('linux'):
            device_paths = [
                '/dev/video0',
                '/dev/video1',
                '/dev/video2',
                '/dev/video3'
            ]
            for path in device_paths:
                try:
                    cap = cv2.VideoCapture(path)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret:
                            cap.release()
                            self.camera_index = path
                            print(f"Found working camera at path {path}")
                            return True
                    cap.release()
                except Exception as e:
                    print(f"Error trying device path {path}: {e}")
                    continue

        self.error_message = "No working camera found"
        return False

    def initialize_camera(self):
        """Initialize the camera using OpenCV."""
        if self.camera is not None:
            self.camera.release()

        try:
            # First try to find an available camera
            if not self.find_available_camera():
                return False

            # Initialize the selected camera
            self.camera = cv2.VideoCapture(self.camera_index)
            
            # Set camera properties
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, self.FPS_LIMIT)

            if not self.camera.isOpened():
                self.error_message = "Failed to open camera"
                return False

            # Test camera by reading a frame
            ret, frame = self.camera.read()
            if not ret or frame is None:
                self.error_message = "Camera opened but failed to read frame"
                return False

            print("Camera initialized successfully")
            self.error_message = None
            return True

        except Exception as e:
            self.error_message = f"Camera initialization error: {str(e)}"
            print(self.error_message)
            return False

    def read_frames(self):
        """Read frames from the camera."""
        while not self.stop_event.is_set():
            if self.camera is None or not self.camera.isOpened():
                print("Camera not available, attempting to reinitialize...")
                if not self.initialize_camera():
                    time.sleep(1)  # Wait before retrying
                    continue

            try:
                ret, frame = self.camera.read()
                if not ret or frame is None:
                    print("Failed to read frame, reinitializing camera...")
                    self.initialize_camera()
                    continue

                # Update current frame with thread safety
                with self.frame_lock:
                    self.current_frame = frame.copy()
                
                # Only add to queue if there's room
                try:
                    self.frame_queue.put_nowait(frame)
                except queue.Full:
                    # Skip frame if queue is full
                    continue
                    
            except Exception as e:
                print(f"Error reading frame: {e}")
                time.sleep(0.1)  # Prevent tight loop on error

    def get_current_frame(self):
        """Thread-safe method to get the current frame."""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None

    def detect_and_extract_text(self, frame):
        """Detect objects and extract text."""
        if frame is None:
            return None
            
        try:
            results = self.model(frame, verbose=False)
            for i, box in enumerate(results[0].boxes.data.tolist()):
                x1, y1, x2, y2, confidence, class_id = box
                
                if confidence < self.CONFIDENCE_THRESHOLD:
                    continue
                    
                object_frame = frame[int(y1):int(y2), int(x1):int(x2)]
                ocr_results = self.reader.readtext(object_frame)
                high_confidence_texts = [
                    res[1] for res in ocr_results if res[2] >= self.CONFIDENCE_THRESHOLD
                ]
                if high_confidence_texts:
                    return " ".join(high_confidence_texts)
        except Exception as e:
            print(f"Error in detection: {e}")
        return None

    def process_frames(self):
        """Process frames for text detection."""
        while not self.stop_event.is_set():
            try:
                frame = self.frame_queue.get(timeout=1)
                detected_text = self.detect_and_extract_text(frame)
                if detected_text:
                    self.detected_text = detected_text
                    self.save_text_to_file(detected_text)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing frame: {e}")

    def start_processing(self):
        """Start processing frames."""
        if not self.processing:
            self.processing = True
            self.detected_text = None
            self.stop_event.clear()
            
            if self.initialize_camera():
                threading.Thread(target=self.read_frames, daemon=True).start()
                threading.Thread(target=self.process_frames, daemon=True).start()
                return True, None
            return False, self.error_message

    def stop_processing(self):
        """Stop processing frames."""
        self.processing = False
        self.stop_event.set()
        
        if self.camera is not None:
            self.camera.release()
            self.camera = None
            
        # Clear queues
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

    def save_text_to_file(self, text):
        """Save detected text to a JSON file."""
        data = {
            "product_name": text,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(self.output_file, "w") as file:
            json.dump(data, file, indent=4)

# Initialize the VisionProcessor
vision_processor = VisionProcessor()

@app.route('/video_feed')
def video_feed():
    """Video feed route for streaming frames."""
    def generate():
        while vision_processor.processing:
            frame = vision_processor.get_current_frame()
            if frame is not None:
                # Add some visual indicators for debugging
                cv2.putText(frame, "Processing", (10, 30),
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                _, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(1/vision_processor.FPS_LIMIT)

    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start', methods=['POST'])
def start_processing():
    """Start processing."""
    if not vision_processor.processing:
        success, error = vision_processor.start_processing()
        if success:
            return jsonify({"status": "started"})
        return jsonify({"status": "error", "message": error or "Failed to start camera"}), 500
    return jsonify({"status": "already running"})

@app.route('/stop', methods=['POST'])
def stop_processing():
    """Stop processing."""
    vision_processor.stop_processing()
    return jsonify({"status": "stopped"})

@app.route('/status', methods=['GET'])
def get_status():
    """Get processing status."""
    return jsonify({
        "processing": vision_processor.processing,
        "detected_text": vision_processor.detected_text,
        "error": vision_processor.error_message,
        "output_file": vision_processor.output_file if os.path.exists(vision_processor.output_file) else None
    })

if __name__ == '__main__':
    app.run(debug=True, port=5002)