'use client';

import { useState, useEffect, useRef } from 'react';
import { Camera, StopCircle, PlayCircle } from 'lucide-react';

const API_BASE_URL = 'http://localhost:5001';

interface ProcessingStatus {
  processing: boolean;
  detected_text: string | null;
}

export default function Home() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [detectedText, setDetectedText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [streamKey, setStreamKey] = useState(Date.now());
  const imgRef = useRef<HTMLImageElement>(null);

  const startProcessing = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/start`, {
        method: 'POST',
      });
      const data = await response.json();
      
      if (data.status === 'started') {
        setIsProcessing(true);
        setError(null);
        setStreamKey(Date.now()); // Force reload the stream
      } else if (data.status === 'error') {
        setError(data.message || 'Failed to start camera');
      }
    } catch (err) {
      setError('Failed to start processing. Please try again.');
    }
  };

  const stopProcessing = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/stop`, {
        method: 'POST',
      });
      const data = await response.json();
      
      if (data.status === 'stopped') {
        setIsProcessing(false);
        setError(null);
      }
    } catch (err) {
      setError('Failed to stop processing. Please try again.');
    }
  };

  const checkStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/status`);
      const data: ProcessingStatus = await response.json();
      
      setIsProcessing(data.processing);
      if (data.detected_text) {
        setDetectedText(data.detected_text);
        await stopProcessing();
      }
    } catch (err) {
      console.error('Error checking status:', err);
    }
  };

  const handleImageError = () => {
    if (isProcessing) {
      // Retry loading the stream with a new key
      setStreamKey(Date.now());
      setError('Video stream connection lost. Retrying...');
    }
  };

  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    if (isProcessing) {
      intervalId = setInterval(checkStatus, 1000);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [isProcessing]);

  return (
    <main className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Vision Processor
            </h1>
            <p className="text-gray-600">
              Real-time object detection and text extraction
            </p>
          </div>

          <div className="mb-8 rounded-lg overflow-hidden border-2 border-gray-200">
            <div className="aspect-video bg-gray-100 flex items-center justify-center">
              {isProcessing ? (
                <img 
                  ref={imgRef}
                  key={streamKey}
                  src={`${API_BASE_URL}/video_feed`}
                  alt="Video Feed"
                  className="w-full h-full object-contain"
                  onError={handleImageError}
                />
              ) : (
                <Camera className="h-16 w-16 text-gray-400" />
              )}
            </div>
          </div>

          <div className="flex justify-center gap-4 mb-8">
            <button
              onClick={startProcessing}
              disabled={isProcessing}
              className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium ${
                isProcessing
                  ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                  : 'bg-green-600 text-white hover:bg-green-700'
              }`}
            >
              <PlayCircle className="h-5 w-5" />
              Start Processing
            </button>
            <button
              onClick={stopProcessing}
              disabled={!isProcessing}
              className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium ${
                !isProcessing
                  ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                  : 'bg-red-600 text-white hover:bg-red-700'
              }`}
            >
              <StopCircle className="h-5 w-5" />
              Stop Processing
            </button>
          </div>

          <div className="bg-gray-50 rounded-lg p-6">
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                Status
              </h2>
              <p className="text-gray-600">
                {isProcessing ? (
                  <span className="flex items-center gap-2">
                    Processing...
                    <span className="inline-block h-2 w-2 bg-green-500 rounded-full animate-pulse"></span>
                  </span>
                ) : (
                  'Not processing'
                )}
              </p>
            </div>

            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-2">
                Detected Text
              </h2>
              <p className="text-gray-600">
                {detectedText || 'No text detected'}
              </p>
            </div>

            {error && (
              <div className="mt-4 p-4 bg-red-50 text-red-600 rounded-lg">
                {error}
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
