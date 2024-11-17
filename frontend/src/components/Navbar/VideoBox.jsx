'use client';

import { useState, useEffect, useRef } from 'react';
import { Camera, StopCircle, PlayCircle } from 'lucide-react';
import {CircularProgress} from "@nextui-org/react";
import InfoBox from "./InfoBox"; // Import the InfoBox component

const API_BASE_URL = 'http://localhost:5002';

export default function Home() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [detectedText, setDetectedText] = useState(null);
  const [error, setError] = useState(null);
  const [streamKey, setStreamKey] = useState(Date.now());
  const [loading, setLoading] = useState(false);
  const [showInfoBox, setShowInfoBox] = useState(false);
  const imgRef = useRef(null);

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
      const data = await response.json();

      setIsProcessing(data.processing);
      if (data.detected_text) {
        setDetectedText(data.detected_text);
        await stopProcessing();

        // Call process_vision API
        setLoading(true); // Show loader
        const processResponse = await fetch("http://localhost:5005/process_vision");
        const processResult = await processResponse.json();

        if (processResult.status === "success") {
          setLoading(false); // Hide loader
          setShowInfoBox(true); // Open InfoBox
        } else {
          setLoading(false);
          setError("Failed to process vision.");
        }
      }
    } catch (err) {
      console.error('Error checking status:', err);
      setError('Error while checking status. Please try again.');
    }
  };

  const handleImageError = () => {
    if (isProcessing) {
      setStreamKey(Date.now()); // Retry with a new key
      setError('Video stream connection lost. Retrying...');
    }
  };

  useEffect(() => {
    let intervalId;

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
              ) : loading ? (
                <CircularProgress label="Loading..." />
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

          {error && (
            <div className="mt-4 p-4 bg-red-50 text-red-600 rounded-lg">
              {error}
            </div>
          )}

          {showInfoBox && <InfoBox />}
        </div>
      </div>
    </main>
  );
}
