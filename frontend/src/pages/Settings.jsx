import React, { useState } from "react";
import { createClient } from "@supabase/supabase-js";
import TopBar from "../components/Navbar/TopBar";

const supabaseUrl = "https://ojtlrdwysacpdlszfnmu.supabase.co";
const supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9qdGxyZHd5c2FjcGRsc3pmbm11Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE3NzgzNDUsImV4cCI6MjA0NzM1NDM0NX0.1WTlkiApXe846IMbAYNq9Z3zPp5fXl36-dl63dbtTog";
const supabase = createClient(supabaseUrl, supabaseKey);

const defaultPriorities = ["Health", "Sustainability", "Cost", "Reliability"];

const Settings = () => {
  const [priorities, setPriorities] = useState(defaultPriorities);
  const [draggedItem, setDraggedItem] = useState(null);
  const [savedRankings, setSavedRankings] = useState(null);
  const [isSaving, setIsSaving] = useState(false);

  const handleDragStart = (index) => {
    setDraggedItem(priorities[index]);
  };

  const handleDragOver = (event) => {
    event.preventDefault(); // Prevent default to allow drop
  };

  const handleDrop = (index) => {
    const reorderedPriorities = [...priorities];
    const draggedIndex = reorderedPriorities.indexOf(draggedItem);

    // Remove the dragged item and insert it at the new position
    reorderedPriorities.splice(draggedIndex, 1);
    reorderedPriorities.splice(index, 0, draggedItem);

    setPriorities(reorderedPriorities);
    setDraggedItem(null);
  };

  const handleSave = async () => {
    const prioritiesString = `My priority is ${priorities
      .map((priority, index) => {
        if (index === 0) return `${priority} first`;
        if (index === priorities.length - 1) return `${priority} last`;
        return `${priority} ${index + 1}th`;
      })
      .join(", ")}.`;

    setIsSaving(true);
    const { error } = await supabase.from("priority").insert([{ pr: prioritiesString }]);

    if (error) {
      alert("Error saving priorities: " + error.message);
    } else {
      alert("Rankings saved to Supabase!");
      setSavedRankings(priorities);
    }
    setIsSaving(false);
  };

  return (
    <div
      style={{
        backgroundColor: "#121212",
        color: "#FFFFFF",
        minHeight: "100vh",
        padding: "20px",
      }}
    >
      <TopBar />
      <div
        style={{
          maxWidth: "400px",
          margin: "0 auto",
          textAlign: "center",
          marginTop: "40px",
        }}
      >
        <h1>Rank Your Priorities</h1>
        <ul
          style={{
            listStyle: "none",
            padding: 0,
            margin: "0 auto",
            textAlign: "left",
          }}
        >
          {priorities.map((priority, index) => (
            <li
              key={index}
              draggable
              onDragStart={() => handleDragStart(index)}
              onDragOver={handleDragOver}
              onDrop={() => handleDrop(index)}
              style={{
                padding: "10px",
                margin: "5px 0",
                backgroundColor: "#1E1E1E",
                borderRadius: "5px",
                border: "1px solid #444",
                cursor: "grab",
                color: "#FFFFFF", // White font color for priorities
              }}
            >
              {priority}
            </li>
          ))}
        </ul>
        <button
          onClick={handleSave}
          style={{
            marginTop: "10px",
            padding: "10px 20px",
            backgroundColor: isSaving ? "#6c757d" : "#007BFF",
            color: "white",
            border: "none",
            borderRadius: "5px",
            cursor: isSaving ? "not-allowed" : "pointer",
          }}
          disabled={isSaving}
        >
          {isSaving ? "Saving..." : "Save Rankings"}
        </button>
        {savedRankings && (
          <div style={{ marginTop: "20px" }}>
            <h2>Saved Rankings:</h2>
            <ol>
              {savedRankings.map((rank, index) => (
                <li key={index}>{rank}</li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </div>
  );
};

export default Settings;
