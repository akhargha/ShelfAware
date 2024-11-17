import React, { useEffect, useState } from "react";
import { createClient } from "@supabase/supabase-js";
import {
  Navbar,
  NavbarBrand,
  NavbarContent,
  NavbarItem,
  Link,
  DropdownItem,
  DropdownTrigger,
  Dropdown,
  DropdownMenu,
  Avatar,
  Chip,
} from "@nextui-org/react";
import { Link as RouterLink } from "react-router-dom";

// Initialize Supabase client
const supabaseUrl = "https://ojtlrdwysacpdlszfnmu.supabase.co";
const supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9qdGxyZHd5c2FjcGRsc3pmbm11Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE3NzgzNDUsImV4cCI6MjA0NzM1NDM0NX0.1WTlkiApXe846IMbAYNq9Z3zPp5fXl36-dl63dbtTog"; // Replace with your Supabase API Key
const supabase = createClient(supabaseUrl, supabaseKey);

export default function TopBar() {
  const [points, setPoints] = useState(null);

  // Fetch points from Supabase table
  useEffect(() => {
    const fetchPoints = async () => {
      try {
        const { data, error } = await supabase
          .from("Points")
          .select("points") // Ensure "points" matches the column name in your Supabase table
          .eq("id", 1)
          .single(); // Fetch a single record where id = 1

        if (error) {
          console.error("Error fetching points:", error);
        } else {
          setPoints(data?.points || 0); // Set points, default to 0 if not found
        }
      } catch (err) {
        console.error("Unexpected error:", err);
      }
    };

    fetchPoints();
  }, []);

  return (
    <Navbar isBordered>
      <NavbarBrand>
        <p className="font-bold text-inherit">🍃 Shelf Aware</p>
      </NavbarBrand>

      <NavbarContent className="hidden sm:flex gap-10" justify="center">
        <NavbarItem>
          <Link color="foreground" as={RouterLink} to="/scan-products">
            Scan Product
          </Link>
        </NavbarItem>
        <NavbarItem>
          <Link color="foreground" as={RouterLink} to="/coupon">
            Coupons
          </Link>
        </NavbarItem>
      </NavbarContent>

      <NavbarContent as="div" justify="end">
      <Chip color="success" size="lg">⚡ Points: {points !== null ? points : "Loading..."}</Chip>
        <Dropdown placement="bottom-end">
          <DropdownTrigger>
            <Avatar
              isBordered
              as="button"
              className="transition-transform"
              color="secondary"
              name="Jason Hughes"
              size="sm"
              src="https://i.pravatar.cc/150?u=a042581f4e29026704d"
            />
          </DropdownTrigger>
          <DropdownMenu aria-label="Profile Actions" variant="flat">
            <DropdownItem key="profile">Signed in as anupam@wesleyan.edu</DropdownItem>
            <DropdownItem key="settings" href="/settings">My Settings</DropdownItem>
            <DropdownItem key="logout" color="danger">Log Out</DropdownItem>
          </DropdownMenu>
        </Dropdown>
      </NavbarContent>
    </Navbar>
  );
}
