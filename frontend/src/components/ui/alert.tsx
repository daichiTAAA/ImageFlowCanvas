import React from "react";

interface AlertProps {
  children: React.ReactNode;
  className?: string;
}

interface AlertDescriptionProps {
  children: React.ReactNode;
  className?: string;
}

export const Alert: React.FC<AlertProps> = ({ children, className = "" }) => {
  return <div className={`rounded-md border p-4 ${className}`}>{children}</div>;
};

export const AlertDescription: React.FC<AlertDescriptionProps> = ({
  children,
  className = "",
}) => {
  return <div className={`text-sm ${className}`}>{children}</div>;
};
