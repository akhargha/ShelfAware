import React, { useState, useEffect } from "react";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Chip,
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
        const { data: alternativeData, error: alternativeError } = await supabase
          .from("product_alternatives")
          .select("*");

        if (alternativeError) {
          console.error("Error fetching product alternatives:", alternativeError);
        } else {
          setAlternatives(alternativeData);

          // Determine the product with the highest sustainability score
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
            <ModalHeader className="flex flex-col gap-1">Compare Alternatives</ModalHeader>
            <ModalBody>
              <div style={{ overflowX: "auto" }}>
                <table
                  style={{
                    width: "100%",
                    borderCollapse: "collapse",
                    textAlign: "left",
                  }}
                >
                  <thead>
                    <tr>
                      <th
                        style={{
                          padding: "12px",
                          fontWeight: "bold",
                          borderBottom: "2px solid #ccc",
                        }}
                      >
                        Feature
                      </th>
                      <th
                        style={{
                          padding: "12px",
                          fontWeight: "bold",
                          borderBottom: "2px solid #ccc",
                          paddingLeft: "55px",
                        }}
                      >
                        {product.product_name}
                      </th>
                      {alternatives.map((alt, index) => (
                        <th
                          key={index}
                          style={{
                            padding: "12px",
                            fontWeight: "bold",
                            borderBottom: "2px solid #ccc",
                            paddingLeft: "40px",
                          }}
                        >
                          {alt.id === maxSustainability?.id ? (
                            <Chip
                              color="warning"
                              variant="shadow"
                              size="md"
                              style={{ fontWeight: "bold" }}
                            >
                              {alt.alternative_name} *
                            </Chip>
                          ) : (
                            alt.alternative_name
                          )}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      {
                        label: "💰 Price",
                        value: (item) => `$${item.price.toFixed(2)}`,
                      },
                      {
                        label: "🏥 Health Index",
                        value: (item) => `${item.health_index} / 5.0`,
                      },
                      {
                        label: "🌱 Sustainability Rating",
                        value: (item) => `${item.sustainability_rating} / 5.0`,
                      },
                      {
                        label: "⚙️ Reliability Rating",
                        value: (item) => `${item.reliability_index} / 5.0`,
                      },
                      {
                        label: "♻️ Biodegradable",
                        value: (item) => item.sustainability_biodegradable,
                      },
                      {
                        label: "♻️ Recyclable",
                        value: (item) => item.sustainability_recyclable,
                      },
                      {
                        label: "",
                        value: (item) => (
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "center",
                              alignItems: "center",
                            }}
                          >
                            <Button
                              size="sm"
                              color="primary"
                              onPress={() => handleBuyClick(item)}
                            >
                              Buy
                            </Button>
                          </div>
                        ),
                      },
                    ].map((feature, rowIndex) => (
                      <tr key={rowIndex}>
                        <td
                          style={{
                            padding: "12px",
                            fontWeight: "bold",
                            borderBottom: "1px solid #eee",
                          }}
                        >
                          {feature.label}
                        </td>
                        <td
                          style={{
                            padding: "12px",
                            borderBottom: "1px solid #eee",
                            textAlign: "center",
                          }}
                        >
                          {feature.value(product)}
                        </td>
                        {alternatives.map((alt, colIndex) => (
                          <td
                            key={colIndex}
                            style={{
                              padding: "12px",
                              borderBottom: "1px solid #eee",
                              textAlign: "center",
                            }}
                          >
                            {feature.value(alt)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </ModalBody>
            <ModalFooter>
              <div
                style={{
                  width: "100%",
                  display: "flex",
                  justifyContent: "space-between",
                }}
              >
                <span style={{ fontSize: "12px", fontStyle: "italic" }}>
                  * sustainabily sponsored
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