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
import { toast, ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

// Initialize Supabase client
const supabaseUrl = "https://ojtlrdwysacpdlszfnmu.supabase.co";
const supabaseKey =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9qdGxyZHd5c2FjcGRsc3pmbm11Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzE3NzgzNDUsImV4cCI6MjA0NzM1NDM0NX0.1WTlkiApXe846IMbAYNq9Z3zPp5fXl36-dl63dbtTog";
const supabase = createClient(supabaseUrl, supabaseKey);

export default function CompareBox({ isOpen, onClose }) {
  const [product, setProduct] = useState(null);
  const [alternatives, setAlternatives] = useState([]);
  const [maxSustainability, setMaxSustainability] = useState(null);

  useEffect(() => {
    const fetchProductData = async () => {
      try {
        // Fetch product data
        const { data: productData, error: productError } = await supabase
          .from("product_information")
          .select("*")
          .single();

        if (productError) {
          console.error("Error fetching product data:", productError);
        } else {
          setProduct(productData);
        }

        // Fetch product alternatives
        const { data: alternativeData, error: alternativeError } =
          await supabase.from("product_alternatives").select("*");

        if (alternativeError) {
          console.error(
            "Error fetching product alternatives:",
            alternativeError
          );
        } else {
          setAlternatives(alternativeData);

          // Determine the product with the highest sustainability score
          const allProducts = [productData, ...alternativeData];
          const maxProduct = allProducts.reduce((prev, curr) =>
            curr.sustainability_rating > prev.sustainability_rating
              ? curr
              : prev
          );
          setMaxSustainability(maxProduct);
        }
      } catch (error) {
        console.error("Error fetching data:", error);
      }
    };

    fetchProductData();
  }, []);

  const handleBuyClick = async (selectedProduct) => {
    if (selectedProduct.sustainability_rating > product.sustainability_rating) {
      try {
        // Fetch the current points from Supabase
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

        // Update points in Supabase
        const { error: updateError } = await supabase
          .from("Points")
          .update({ points: updatedPoints })
          .eq("id", 1);

        if (updateError) {
          console.error("Error updating points:", updateError);
        } else {
          // Show toast notification
          toast.success("Congrats!");
          // Close the modal after a short delay to allow the toast to display
          setTimeout(onClose, 2000);
        }
      } catch (error) {
        console.error("Error updating points:", error);
      }
    }
  };

  if (!product) {
    return <div>Loading...</div>;
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
      key: "biodegradable",
      label: "♻️ Biodegradable",
      render: (item) => item.sustainability_biodegradable,
    },
    {
      key: "recyclable",
      label: "♻️ Recyclable",
      render: (item) => item.sustainability_recyclable,
    },
  ];

  return (
    <>
      <ToastContainer />
      <Modal
        isOpen={isOpen}
        onOpenChange={(state) => !state && onClose()}
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
                <Button color="danger" variant="light" onPress={onClose}>
                  Close
                </Button>
              </div>
            </ModalFooter>
          </>
        </ModalContent>
      </Modal>
    </>
  );
}
