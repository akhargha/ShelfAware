
import React from "react";
import { Routes, Route } from "react-router-dom";
import TopBar from "./components/Navbar/TopBar";
import Home from "./pages/Home";
import Coupon from "./pages/Coupon";

export default function App() {
  return (
    <div>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/scan-products" element={<TopBar />} />
        <Route path="/coupon" element={<Coupon />} />
      </Routes>
    </div>
  );
}