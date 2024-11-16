import React from "react";
import { Card, CardHeader, CardBody, CardFooter, Divider, Image, Button, Snippet } from "@nextui-org/react";

export default function CouponBox({ imageSrc, title, description, buttonText, points, points_fulfill }) {
  const buttonColor = points_fulfill === "Y" ? "success" : "default";

  return (
    <Card className="max-w-[400px]">
      <CardHeader className="flex gap-3">
        <Image
          alt={`${title} logo`}
          height={40}
          radius="sm"
          src={imageSrc}
          width={40}
        />
        <div className="flex flex-col">
          <p className="text-md">{title}</p>
        </div>
      </CardHeader>
      <Divider />
      <CardBody>
        <p>{description}</p>
        <p className="text-sm text-gray-500">Points Required: {points}</p>
      </CardBody>
      <Divider />
      <CardFooter>
        <Snippet radius="full" disabled={points_fulfill === "N"} color={buttonColor}>
          {points_fulfill === "N" ? "Locked" : buttonText}
        </Snippet>
      </CardFooter>
    </Card>
  );
}
