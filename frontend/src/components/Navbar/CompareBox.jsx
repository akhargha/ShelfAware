import React from "react";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  useDisclosure,
} from "@nextui-org/react";

export default function CompareBox({ isOpen, onClose }) {
  return (
    <Modal
      isOpen={isOpen}
      onOpenChange={(state) => !state && onClose()}
      isDismissable={false}
      isKeyboardDismissDisabled={true}
      scrollBehavior="inside"
    >
      <ModalContent>
        <>
          <ModalHeader className="flex flex-col gap-1">Compare Alternatives</ModalHeader>
          <ModalBody>
            <p>Here are some sustainable alternatives for your product:</p>
            {/* Add content for comparison here */}
          </ModalBody>
          <ModalFooter>
            <Button color="danger" variant="light" onPress={onClose}>
              Close
            </Button>
          </ModalFooter>
        </>
      </ModalContent>
    </Modal>
  );
}
