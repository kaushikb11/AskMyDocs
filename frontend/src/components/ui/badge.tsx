import * as React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?:
    | "default"
    | "secondary"
    | "destructive"
    | "outline"
    | "success"
    | "warning"
    | "processing"
    | "info";
}

function Badge({ className = "", variant = "default", ...props }: BadgeProps) {
  const baseClasses =
    "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2";

  const variantClasses = {
    default: "border-transparent bg-blue-600 text-white hover:bg-blue-700",
    secondary: "border-transparent bg-gray-200 text-gray-800 hover:bg-gray-300",
    destructive: "border-transparent bg-red-600 text-white hover:bg-red-700",
    outline: "text-gray-700 border-gray-300",
    success:
      "border-transparent bg-green-100 text-green-800 hover:bg-green-200",
    warning:
      "border-transparent bg-yellow-100 text-yellow-800 hover:bg-yellow-200",
    processing:
      "border-transparent bg-blue-100 text-blue-800 hover:bg-blue-200 animate-pulse",
    info: "border-transparent bg-blue-100 text-blue-800 hover:bg-blue-200",
  };

  const classes = `${baseClasses} ${variantClasses[variant]} ${className}`;

  return <div className={classes} {...props} />;
}

export { Badge };
