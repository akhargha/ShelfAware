import React, { useState, useEffect } from "react";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Chip,
  Table,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
} from "@nextui-org/react";
import { createClient } from "@supabase/supabase-js";
import { ToastContainer, toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

const supabaseUrl = "https://ojtlrdwysacpdlszfnmu.supabase.co";
const supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9qdGxyZHd5c2FjcGRsc3pmbm11Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE3NzgzNDUsImV4cCI6MjA0NzM1NDM0NX0.1WTlkiApXe846IMbAYNq9Z3zPp5fXl36-dl63dbtTog"; // Replace with your actual Supabase key
const supabase = createClient(supabaseUrl, supabaseKey);

export default function CompareBox({ isOpen, onClose }) {
  const [product, setProduct] = useState(null);
  const [alternatives, setAlternatives] = useState([]);
  const [maxSustainability, setMaxSustainability] = useState(null);

  const handleClose = async () => {
    try {
      // Send DELETE request to /delete_all endpoint with Authorization header
      const response = await fetch("http://localhost:5005/delete_all", {
        method: "DELETE",
        headers: {
          "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9qdGxyZHd5c2FjcGRsc3pmbm11Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE3NzgzNDUsImV4cCI6MjA0NzM1NDM0NX0.1WTlkiApXe846IMbAYNq9Z3zPp5fXl36-dl63dbtTog"
        }
      });
  
      if (!response.ok) {
        throw new Error(`Error: ${response.status} ${response.statusText}`);
      }
  
      const data = await response.json();
      console.log("Response data:", data);
    } catch (error) {
      console.error("Error deleting data:", error);
    } finally {
      onClose(); // Close the modal after the request
    }
  };

  useEffect(() => {
    let isMounted = true; // To prevent state updates if component is unmounted

    const fetchProductData = async () => {
      try {
        const { data: productData, error: productError } = await supabase
          .from("product_information")
          .select("*")
          .single();

        if (productError) {
          console.error("Error fetching product data:", productError);
        } else if (isMounted) {
          setProduct(productData);
        }

        const { data: alternativeData, error: alternativeError } = await supabase
          .from("product_alternatives")
          .select("*");

        if (alternativeError) {
          console.error("Error fetching product alternatives:", alternativeError);
        } else if (isMounted) {
          setAlternatives(alternativeData);

          const allProducts = [productData, ...alternativeData];
          const maxProduct = allProducts.reduce((prev, curr) =>
            curr.sustainability_rating > prev.sustainability_rating ? curr : prev
          );
          setMaxSustainability(maxProduct);
        }
      } catch (error) {
        console.error("Error fetching data:", error);
      }
    };

    if (isOpen) {
      fetchProductData();
    }

    return () => {
      isMounted = false; // Cleanup to prevent state updates on unmounted component
    };
  }, [isOpen]);

  const handleBuyClick = async (selectedProduct) => {
    if (selectedProduct.sustainability_rating > product.sustainability_rating) {
      try {
        const { data, error: fetchError } = await supabase
          .from("Points")
          .select("points")
          .eq("id", 1)
          .single();

        if (fetchError) {
          console.error("Error fetching points:", fetchError);
          return;
        }

        const updatedPoints = data.points + 100;

        const { error: updateError } = await supabase
          .from("Points")
          .update({ points: updatedPoints })
          .eq("id", 1);

        if (updateError) {
          console.error("Error updating points:", updateError);
        } else {
          toast.success(
            "You just earned points! Congrats on investing in sustainability!"
          );
          setTimeout(onClose, 2000);
        }
      } catch (error) {
        console.error("Error updating points:", error);
      }
    } else {
      // Handle the case when the selected product is not more sustainable
      toast.info("This product is not more sustainable.");
    }
  };

  if (!product) {
    return null; // Do not render anything if data is not available
  }

  const allProducts = [
    { ...product, name: product.product_name },
    ...alternatives.map((alt) => ({ ...alt, name: alt.alternative_name })),
  ];

  const features = [
    {
      key: "price",
      label: "💰 Price",
      render: (item) => `$${item.price.toFixed(2)}`,
    },
    {
      key: "health_index",
      label: "🏥 Health Index",
      render: (item) => `${item.health_index} / 5.0`,
    },
    {
      key: "sustainability_rating",
      label: "🌱 Sustainability Rating",
      render: (item) => `${item.sustainability_rating} / 5.0`,
    },
    {
      key: "reliability_index",
      label: "⚙️ Reliability Rating",
      render: (item) => `${item.reliability_index} / 5.0`,
    },
    {
      key: "sustainability_biodegradable",
      label: "♻️ Biodegradable",
      render: (item) => item.sustainability_biodegradable,
    },
    {
      key: "sustainability_recyclable",
      label: "♻️ Recyclable",
      render: (item) => item.sustainability_recyclable,
    },
  ];

  return (
    <div>
      <ToastContainer />
      <Modal
        isOpen={isOpen}
        onOpenChange={(state) => !state && handleClose()}
        isDismissable={false}
        isKeyboardDismissDisabled={true}
        scrollBehavior="inside"
        size="5xl"
      >
        <ModalContent>
          <>
            <ModalHeader className="flex flex-col gap-1">
              Compare Alternatives
            </ModalHeader>
            <ModalBody>
              <Table aria-label="Comparison Table">
                <TableHeader>
                  <TableColumn>Feature</TableColumn>
                  {allProducts.map((item, index) => (
                    <TableColumn key={index}>
                      {item.id === maxSustainability?.id ? (
                        <Chip color="warning" variant="shadow" size="md">
                          {item.name} *
                        </Chip>
                      ) : (
                        item.name
                      )}
                    </TableColumn>
                  ))}
                </TableHeader>
                <TableBody>
                  {features.map((feature, featureIndex) => (
                    <TableRow key={featureIndex}>
                      <TableCell>{feature.label}</TableCell>
                      {allProducts.map((item, productIndex) => (
                        <TableCell key={productIndex}>
                          {feature.render(item)}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                  <TableRow>
                    <TableCell></TableCell>
                    {allProducts.map((item, index) => (
                      <TableCell key={index}>
                        <Button
                          size="sm"
                          color="primary"
                          onPress={() => handleBuyClick(item)}
                        >
                          Buy
                        </Button>
                      </TableCell>
                    ))}
                  </TableRow>
                </TableBody>
              </Table>
            </ModalBody>
            <ModalFooter>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  width: "100%",
                }}
              >
                <span style={{ fontSize: "12px", fontStyle: "italic" }}>
                  * Sustainably sponsored
                </span>
                <Button color="danger" variant="light" onPress={handleClose}>
                  Close
                </Button>
              </div>
            </ModalFooter>
          </>
        </ModalContent>
      </Modal>
      </div>
  );
}
