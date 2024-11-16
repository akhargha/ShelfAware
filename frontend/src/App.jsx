
import React from "react";
import { Routes, Route } from "react-router-dom";
import TopBar from "./components/Navbar/TopBar";
import Home from "./pages/Home";
import Coupon from "./pages/Coupon";
import WebcamDetection from "./components/WebCamDetection";

export default function App() {
  return (
    <div>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/scan-products" element={<WebcamDetection />} />
        <Route path="/coupon" element={<Coupon />} />
      </Routes>
    </div>
  );
}