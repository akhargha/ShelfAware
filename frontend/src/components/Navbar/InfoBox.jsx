import React, { useState, useEffect } from "react";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Chip,
  Divider,
} from "@nextui-org/react";
import { createClient } from "@supabase/supabase-js";
import { useNavigate } from "react-router-dom"; // Import useNavigate

const supabaseUrl = "https://ojtlrdwysacpdlszfnmu.supabase.co";
const supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9qdGxyZHd5c2FjcGRsc3pmbm11Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE3NzgzNDUsImV4cCI6MjA0NzM1NDM0NX0.1WTlkiApXe846IMbAYNq9Z3zPp5fXl36-dl63dbtTog"; // Replace with your actual Supabase key
const supabase = createClient(supabaseUrl, supabaseKey);

export default function InfoBox({ isOpen, onOpenChange }) {
  const [productData, setProductData] = useState(null);
  const navigate = useNavigate(); // Initialize useNavigate

  useEffect(() => {
    let isMounted = true; // To prevent state updates if component is unmounted

    const fetchProductData = async () => {
      try {
        const { data, error } = await supabase
          .from("product_information")
          .select("*")
          .single();

        if (error) {
          console.error("Error fetching product data:", error);
        } else if (data) {
          if (isMounted) {
            setProductData(data);
          }
        } else {
          console.log("No data found. Retrying in 2 seconds...");
          setTimeout(fetchProductData, 2000); // Retry after 2 seconds
        }
      } catch (err) {
        console.error("Error fetching product data:", err);
      }
    };

    if (isOpen) {
      fetchProductData();
    }

    return () => {
      isMounted = false; // Cleanup to prevent state updates on unmounted component
    };
  }, [isOpen]);

  if (!productData) {
    return null; // Do not render anything if data is not available
  }

  const handleGetAlternatives = () => {
    onOpenChange(false); // Close InfoBox
    navigate("/alternatives"); // Redirect to the /alternatives route
  };

  return (
    <Modal
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      isDismissable={false}
      isKeyboardDismissDisabled={true}
      scrollBehavior="inside"
    >
      <ModalContent>
        {(onClose) => (
          <>
            <ModalHeader className="flex flex-col gap-1">
              {productData.product_name.length > 30
                ? `${productData.product_name.substring(0, 30)}...`
                : productData.product_name}
            </ModalHeader>
            <ModalBody>
              <h4 style={{ fontWeight: "600", marginBottom: "8px" }}>💰 Cost</h4>
              <p style={{ marginBottom: "-10px" }}>${productData.price.toFixed(2)}</p>

              <Divider className="my-4" />

              <h2 style={{ fontWeight: "600", marginBottom: "8px" }}>🏥 Health Information</h2>
              <div style={{ marginBottom: "16px" }}>
                {productData.health_nutrients &&
                  Object.entries(JSON.parse(productData.health_nutrients)).map(([key, value]) => (
                    <Chip key={key} style={{ margin: "3px" }}>
                      {key}: {value}
                    </Chip>
                  ))}
              </div>
              <p>
                <strong>Ingredients:</strong>{" "}
                {productData.health_ingredients &&
                  JSON.parse(productData.health_ingredients).join(", ")}
              </p>
              <p style={{ marginBottom: "-10px" }}>
                <strong>Health Index:</strong> {productData.health_index} / 5.0
              </p>

              <Divider className="my-4" />

              <h4 style={{ fontWeight: "600", marginBottom: "8px" }}>
                🌱 Sustainability Information
              </h4>
              <p>
                <strong>Biodegradable:</strong>{" "}
                <Chip
                  color={
                    productData.sustainability_biodegradable &&
                    productData.sustainability_biodegradable.toLowerCase() ===
                      "no"
                      ? "danger"
                      : "success"
                  }
                >
                  {productData.sustainability_biodegradable}
                </Chip>
              </p>
              <p>
                <strong>Recyclable:</strong>{" "}
                <Chip
                  color={
                    productData.sustainability_recyclable &&
                    productData.sustainability_recyclable.toLowerCase() ===
                      "no"
                      ? "danger"
                      : "success"
                  }
                >
                  {productData.sustainability_recyclable}
                </Chip>
              </p>
              <p>
                <strong>Sustainability Rating:</strong>{" "}
                {productData.sustainability_rating} / 5.0
              </p>
              <p>
                <strong>Dustbin Color:</strong> {productData.dustbin_color}
              </p>
            </ModalBody>
            <ModalFooter>
              <Button color="danger" variant="light" onPress={onClose}>
                Close
              </Button>
              <Button color="primary" onPress={handleGetAlternatives}>
                Get Alternatives
              </Button>
            </ModalFooter>
          </>
        )}
      </ModalContent>
    </Modal>
  );
}
