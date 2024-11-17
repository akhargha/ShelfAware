import React, { useEffect, useState } from "react";
import TopBar from "../components/Navbar/TopBar";
import CouponBox from "../components/Navbar/CouponBox";
import { createClient } from "@supabase/supabase-js";
import InfoBox from "../components/Navbar/InfoBox";
import { Button } from "@nextui-org/react";

// Initialize Supabase client
const supabaseUrl = "https://ojtlrdwysacpdlszfnmu.supabase.co";
const supabaseKey =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9qdGxyZHd5c2FjcGRsc3pmbm11Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE3NzgzNDUsImV4cCI6MjA0NzM1NDM0NX0.1WTlkiApXe846IMbAYNq9Z3zPp5fXl36-dl63dbtTog"; // Replace with your Supabase API key
const supabase = createClient(supabaseUrl, supabaseKey);

export default function Coupon() {
  const [points, setPoints] = useState(0);
  const [coupons, setCoupons] = useState([]);

  // Fetch points and coupons data
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch points from Points table (assuming id = 1 for simplicity)
        const { data: pointsData, error: pointsError } = await supabase
          .from("Points")
          .select("points")
          .eq("id", 1)
          .single();

        if (pointsError) {
          console.error("Error fetching points:", pointsError);
        } else {
          setPoints(pointsData?.points || 0);
        }

        // Fetch all rows from Coupons table
        const { data: couponsData, error: couponsError } = await supabase
          .from("Coupons")
          .select("*");

        if (couponsError) {
          console.error("Error fetching coupons:", couponsError);
        } else {
          setCoupons(couponsData || []);
        }
      } catch (err) {
        console.error("Unexpected error:", err);
      }
    };

    fetchData();
  }, []);

  return (
    <div>
      <div style={{ marginBottom: "40px" }}>
        <TopBar />
      </div>

      <InfoBox />

      {/* Grid layout for coupons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 justify-items-center" style={{paddingBottom: "40px"}}>
        {coupons.map((coupon) => {
          const pointsFulfill = points >= coupon.points ? "Y" : "N";

          return (
            <CouponBox
              key={coupon.id}
              imageSrc={coupon.logo}
              title={coupon.header}
              description={coupon.body}
              buttonText={coupon.code}
              points_fulfill={pointsFulfill}
              points={coupon.points}
            />
          );
        })}
      </div>
    </div>
  );
}
