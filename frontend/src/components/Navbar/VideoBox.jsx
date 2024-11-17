'use client';

import { useState, useRef, useEffect } from 'react';
import { Camera, StopCircle, PlayCircle, Search } from 'lucide-react';
import { CircularProgress } from "@nextui-org/react";
import InfoBox from "./InfoBox"; // Import InfoBox

const API_BASE_URL = 'http://localhost:5002';

export default function Home() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [streamKey, setStreamKey] = useState(Date.now());
  const [loading, setLoading] = useState(false);
  const [showInfoBox, setShowInfoBox] = useState(false);
  const [searchUrl, setSearchUrl] = useState(""); // State for the search bar input
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

      if (data.detected_text) {
        await stopProcessing();

        // Call process_vision API
        setLoading(true); // Show loader
        const processResponse = await fetch("http://localhost:5005/process_vision");
        const processResult = await processResponse.json();

        if (processResult.status === "success") {
          setLoading(false); // Hide loader
          setShowInfoBox(true); // Open InfoBox modal
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

  const handleSearch = async () => {
    try {
      setShowInfoBox(false);
      setLoading(true);
      const response = await fetch(`http://localhost:5008/analyze_url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: searchUrl }),
      });

      const result = await response.json();
      if (result.status === "success") {
        setLoading(false);
        setShowInfoBox(true);
        setError(null);
      } else {
        setLoading(false);
        setError(result.message || "URL analysis failed.");
      }
    } catch (err) {
      setLoading(false);
      setError("Failed to analyze URL. Please try again.");
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
    <main className="min-h-screen bg-gray-900 text-gray-200 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <div className="bg-gray-800 rounded-lg shadow-md p-6">
          <div className="text-center mb-8">
            <h1 className="text-xl font-bold text-white mb-2">
              Item Detector
            </h1>
          </div>

          <div className="mb-8 rounded-lg overflow-hidden border-2 border-gray-700">
            <div className="aspect-video bg-gray-700 flex items-center justify-center">
              {isProcessing ? (
                <img
                  ref={imgRef}
                  key={streamKey}
                  src={`${API_BASE_URL}/video_feed`}
                  alt="Video Feed"
                  className="w-full h-full object-contain"
                />
              ) : loading ? (
                <CircularProgress label="Loading..." />
              ) : (
                <Camera className="h-16 w-16 text-gray-500" />
              )}
            </div>
          </div>

          <div className="flex justify-center gap-4 mb-8">
            <button
              onClick={startProcessing}
              disabled={isProcessing}
              className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium ${
                isProcessing
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
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
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-red-600 text-white hover:bg-red-700'
              }`}
            >
              <StopCircle className="h-5 w-5" />
              Stop Processing
            </button>
          </div>

          <div className="flex items-center gap-4 mb-8">
            <input
              type="text"
              value={searchUrl}
              onChange={(e) => setSearchUrl(e.target.value)}
              placeholder="Enter URL to analyze"
              className="flex-1 px-4 py-2 bg-gray-700 text-gray-200 border border-gray-600 rounded-lg"
            />
            <button
              onClick={handleSearch}
              disabled={loading || !searchUrl}
              className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium ${
                loading || !searchUrl
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              <Search className="h-5 w-5" />
              Search
            </button>
          </div>

          {error && (
            <div className="mt-4 p-4 bg-red-700 text-gray-200 rounded-lg">
              {error}
            </div>
          )}

          {/* Conditionally render InfoBox */}
          {showInfoBox && (
            <InfoBox isOpen={showInfoBox} onOpenChange={setShowInfoBox} />
          )}
        </div>
      </div>
    </main>
  );
}
