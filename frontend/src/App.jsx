
import React from "react";
import { Routes, Route } from "react-router-dom";
import TopBar from "./components/Navbar/TopBar";
import Home from "./pages/Home";
import Coupon from "./pages/Coupon";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <div>
      <Routes>
        <Route path="/" element={<Coupon />} />
        <Route path="/scan-products" element={<Home />} />
        <Route path="/coupon" element={<Coupon />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </div>
  );
}