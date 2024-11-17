import React, { useState } from "react";
import TopBar from "../components/Navbar/TopBar";
import CompareBox from "../components/Navbar/CompareBox";
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = "https://ojtlrdwysacpdlszfnmu.supabase.co";
const supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9qdGxyZHd5c2FjcGRsc3pmbm11Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE3NzgzNDUsImV4cCI6MjA0NzM1NDM0NX0.1WTlkiApXe846IMbAYNq9Z3zPp5fXl36-dl63dbtTog"; // Replace with your actual Supabase key
const supabase = createClient(supabaseUrl, supabaseKey);

export default function Alternatives() {
  const [isCompareOpen, setCompareOpen] = useState(true); // Initialize CompareBox as open

  const handleClose = async () => {
    try {
      // Delete all rows from the product_information table
      const { data, error } = await supabase
        .from("product_information")
        .delete()

      if (error) {
        console.error("Error deleting data from product_information:", error);
      } else {
        console.log("All rows deleted from product_information:", data);
      }
    } catch (error) {
      console.error("Unexpected error:", error);
    } finally {
      setCompareOpen(false); // Close CompareBox
    }
  };

  return (
    <div>
      <TopBar />
      {isCompareOpen ? (
        <CompareBox isOpen={isCompareOpen} onClose={handleClose} />
      ) : (
        <p style={{ textAlign: "center", marginTop: "20px" }}>
          CompareBox is closed. Navigate back or refresh to open it again.
        </p>
      )}
    </div>
  );
}
