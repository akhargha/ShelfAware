import React from "react";
import TopBar from "../components/Navbar/TopBar";
import CouponBox from "../components/Navbar/CouponBox";
import VideoBox from "../components/Navbar/VideoBox";

export default function Settings() {
  return (
    <div>
      <TopBar />
      <VideoBox />
      <h1>Welcome to Shelf Aware</h1>
      <p>Manage your items efficiently.</p>
    </div>
  );
}
