"use client";
import React, { useRef, useEffect, useState } from "react";

const VideoBox = () => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [detections, setDetections] = useState([]);
  const [error, setError] = useState(null);
  const [attempts, setAttempts] = useState(0);
  const maxAttempts = 3;

  const backendBaseUrl = "http://localhost:5001";

  // Start the camera stream
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "environment",
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsStreaming(true);
        setError(null);
      }
    } catch (err) {
      setError("Unable to access camera. Please ensure you have granted camera permissions.");
      console.error("Error accessing camera:", err);
    }
  };

  // Start vision processing
  const startVisionProcessing = async () => {
    try {
      setIsProcessing(true);
      setError(null);
      
      const response = await fetch(`${backendBaseUrl}/start_vision_processing`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "Failed to start vision processing");
      
      pollResults();
    } catch (err) {
      handleProcessingError(err);
    }
  };

  // Handle processing errors
  const handleProcessingError = (err) => {
    setError(err.message || "Error during brand detection");
    setIsProcessing(false);
    setAttempts(prev => prev + 1);
    console.error("Vision processing error:", err);
  };

  // Poll for processed results
  const pollResults = async () => {
    try {
      const response = await fetch(`${backendBaseUrl}/process_vision_results`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.message || "Failed to fetch results");

      if (data.status === "processing") {
        setTimeout(pollResults, 1000);
      } else if (data.processed_data && data.processed_data.length > 0) {
        setDetections(data.processed_data);
        setIsProcessing(false);
        setAttempts(0);
      } else {
        throw new Error("No brands detected. Please try again.");
      }
    } catch (err) {
      handleProcessingError(err);
    }
  };

  // Auto-start processing when camera is ready
  useEffect(() => {
    if (isStreaming && !isProcessing && attempts < maxAttempts) {
      startVisionProcessing();
    }
  }, [isStreaming, attempts]);

  // Initialize camera on component mount
  useEffect(() => {
    startCamera();
    return () => {
      if (videoRef.current && videoRef.current.srcObject) {
        videoRef.current.srcObject.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  // Retry handler
  const handleRetry = () => {
    setAttempts(0);
    setDetections([]);
    setError(null);
    startVisionProcessing();
  };

  // Function to render brand detection result
  const renderBrandDetection = (detection) => {
    return (
      <div key={detection.index} className="mt-2 p-3 bg-white rounded-lg shadow-sm">
        {detection.detected_text && (
          <p className="text-gray-700">
            Detected Text: <span className="font-medium">{detection.detected_text}</span>
          </p>
        )}
        {detection.completed_text && (
          <p className="text-green-700 font-medium">
            Brand: {detection.completed_text}
          </p>
        )}
        <p className="text-sm text-gray-600">
          Confidence: {(detection.confidence * 100).toFixed(1)}%
        </p>
      </div>
    );
  };

  return (
    <div className="max-w-2xl mx-auto p-4">
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-gray-50 border-b flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Brand Scanner</h2>
          {attempts >= maxAttempts && (
            <button
              onClick={handleRetry}
              className="px-4 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-white"
            >
              Try Again
            </button>
          )}
        </div>

        {/* Content */}
        <div className="p-4">
          <div className="space-y-4">
            <div className="relative aspect-video bg-gray-100 rounded-lg overflow-hidden">
              <video
                ref={videoRef}
                className="w-full h-full object-cover"
                autoPlay
                playsInline
              />
              <canvas ref={canvasRef} className="absolute top-0 left-0 w-full h-full" />
              
              {/* Processing overlay */}
              {isProcessing && (
                <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
                  <div className="text-white text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-4 border-white border-t-transparent mx-auto mb-2"></div>
                    <p>Scanning for brands...</p>
                    <p className="text-sm mt-2 text-gray-300">Looking for IZZE or Caprisun</p>
                  </div>
                </div>
              )}
            </div>

            {/* Status Messages */}
            {error && (
              <div className="bg-red-50 text-red-700 p-4 rounded-lg">
                <p>{error}</p>
                {attempts >= maxAttempts && (
                  <p className="mt-2">Maximum attempts reached. Please try again.</p>
                )}
              </div>
            )}

            {/* Detection Results */}
            {detections.length > 0 && (
              <div className="bg-green-50 rounded-lg p-4">
                <h3 className="text-lg font-semibold text-green-800">Brand Detected!</h3>
                <div className="mt-2 space-y-3">
                  {detections.map(renderBrandDetection)}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoBox;