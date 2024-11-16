// src/components/ObjectDetection/WebcamDetection.jsx
import React, { useState, useRef, useEffect } from 'react';

const WebcamDetection = () => {
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  const [detectedObjects, setDetectedObjects] = useState([]);
  const [processing, setProcessing] = useState(false);
  const videoRef = useRef(null);
  const streamRef = useRef(null);

  const startWebcam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 }
        }
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;
        setIsStreaming(true);
        setError(null);
      }
    } catch (err) {
      setError("Failed to access webcam. Please make sure you have granted camera permissions.");
      console.error("Error accessing webcam:", err);
    }
  };

  const stopWebcam = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
      setIsStreaming(false);
    }
  };

  const captureAndProcess = async () => {
    if (!videoRef.current) return;

    try {
      setProcessing(true);
      
      const canvas = document.createElement('canvas');
      canvas.width = videoRef.current.videoWidth;
      canvas.height = videoRef.current.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(videoRef.current, 0, 0);
      
      const blob = await new Promise(resolve => {
        canvas.toBlob(resolve, 'image/jpeg');
      });

      const formData = new FormData();
      formData.append('image', blob);

      const response = await fetch('http://localhost:5000/api/process-image', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('Failed to process image');
      }

      const data = await response.json();
      setDetectedObjects(data.objects || []);
      
    } catch (err) {
      setError("Failed to process image. Please try again.");
      console.error("Error processing image:", err);
    } finally {
      setProcessing(false);
    }
  };

  useEffect(() => {
    return () => {
      stopWebcam();
    };
  }, []);

  return (
    <div className="container mx-auto p-4">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-4 mb-4">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">Object Detection</h2>
            <div className="space-x-2">
              {!isStreaming ? (
                <button
                  onClick={startWebcam}
                  className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                >
                  Start Camera
                </button>
              ) : (
                <>
                  <button
                    onClick={stopWebcam}
                    className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
                  >
                    Stop Camera
                  </button>
                  <button
                    onClick={captureAndProcess}
                    disabled={processing}
                    className={`bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 ${
                      processing ? 'opacity-50 cursor-not-allowed' : ''
                    }`}
                  >
                    {processing ? 'Processing...' : 'Capture & Detect'}
                  </button>
                </>
              )}
            </div>
          </div>

          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
              {error}
            </div>
          )}

          <div className="relative aspect-video bg-gray-900 rounded-lg overflow-hidden mb-4">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              className="w-full h-full object-contain"
            />
          </div>

          {detectedObjects.length > 0 && (
            <div className="mt-8">
              <h3 className="text-lg font-semibold mb-4">Detected Objects</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {detectedObjects.map((obj, index) => (
                  <div key={index} className="border rounded-lg p-4">
                    <div className="flex justify-between mb-2">
                      <span className="font-medium">{obj.label}</span>
                      <span className="text-sm text-gray-500">
                        {(obj.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                    {obj.text && (
                      <p className="text-sm text-gray-600 mb-2">
                        Detected Text: {obj.text}
                      </p>
                    )}
                    {obj.image_path && (
                      <img
                        src={obj.image_path}
                        alt={`Detected ${obj.label}`}
                        className="w-full h-48 object-contain bg-gray-100 rounded"
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WebcamDetection;