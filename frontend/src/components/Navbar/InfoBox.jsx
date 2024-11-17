import React, { useState, useEffect } from "react";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  useDisclosure,
  Chip,
  Divider,
} from "@nextui-org/react";
import { createClient } from "@supabase/supabase-js";
import CompareBox from "./CompareBox"; // Import the CompareBox component

// Initialize Supabase client
const supabaseUrl = "https://ojtlrdwysacpdlszfnmu.supabase.co";
const supabaseKey =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9qdGxyZHd5c2FjcGRsc3pmbm11Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE3NzgzNDUsImV4cCI6MjA0NzM1NDM0NX0.1WTlkiApXe846IMbAYNq9Z3zPp5fXl36-dl63dbtTog";
const supabase = createClient(supabaseUrl, supabaseKey);

export default function InfoBox() {
  const { isOpen, onOpen, onOpenChange } = useDisclosure();
  const [isCompareOpen, setCompareOpen] = useState(false); // Manage CompareBox modal state
  const [productData, setProductData] = useState(null);

  useEffect(() => {
    const fetchProductData = async () => {
      const { data, error } = await supabase
        .from("product_information")
        .select("*")
        .single(); // Fetch the single row from the table

      if (error) {
        console.error("Error fetching product data:", error);
      } else {
        setProductData(data);
      }
    };

    fetchProductData();
  }, []);

  if (!productData) {
    return <div>Loading...</div>; // Show a loading state while data is being fetched
  }

  const {
    product_name,
    health_nutrients,
    health_ingredients,
    health_index,
    sustainability_biodegradable,
    sustainability_recyclable,
    sustainability_rating,
    price,
    dustbin_color,
  } = productData;

  // Format health nutrients
  const formattedHealthNutrients = JSON.parse(health_nutrients);

  // Handle Get Alternatives click
  const handleGetAlternatives = () => {
    onOpenChange(false); // Close InfoBox
    setCompareOpen(true); // Open CompareBox
  };

  return (
    <>
      <Button onPress={onOpen}>Open Modal</Button>
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
                {product_name}
              </ModalHeader>
              <ModalBody>
                <h4 style={{ fontWeight: "600", marginBottom: "8px" }}>
                  💰 Cost
                </h4>
                <p style={{ marginBottom: "-10px" }}>${price.toFixed(2)}</p>

                <Divider className="my-4" />

                <h2 style={{ fontWeight: "600", marginBottom: "8px" }}>
                  🏥 Health Information
                </h2>
                <div style={{ marginBottom: "16px" }}>
                  {Object.entries(formattedHealthNutrients).map(([key, value]) => (
                    <Chip key={key} style={{ margin: "3px" }}>
                      {key}: {value}
                    </Chip>
                  ))}
                </div>
                <p>
                  <strong>Ingredients:</strong> {JSON.parse(health_ingredients).join(", ")}
                </p>
                <p style={{ marginBottom: "-10px" }}>
                  <strong>Health Index:</strong> {health_index} / 5.0
                </p>

                <Divider className="my-4" />

                <h4 style={{ fontWeight: "600", marginBottom: "8px" }}>
                  🌱 Sustainability Information
                </h4>
                <p>
                  <strong>Biodegradable:</strong>{" "}
                  <Chip
                    color={
                      sustainability_biodegradable.toLowerCase() === "no"
                        ? "danger"
                        : "success"
                    }
                  >
                    {sustainability_biodegradable}
                  </Chip>
                </p>
                <p>
                  <strong>Recyclable:</strong>{" "}
                  <Chip
                    color={
                      sustainability_recyclable.toLowerCase() === "no"
                        ? "danger"
                        : "success"
                    }
                  >
                    {sustainability_recyclable}
                  </Chip>
                </p>
                <p>
                  <strong>Sustainability Rating:</strong> {sustainability_rating} / 5.0
                </p>
                <p>
                  <strong>Dustbin Color:</strong> {dustbin_color}
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
      <CompareBox isOpen={isCompareOpen} onClose={() => setCompareOpen(false)} />
    </>
  );
}
