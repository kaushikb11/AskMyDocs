import * as React from "react";
import { VARIANTS, SPACING } from "../../lib/design-system";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "default" | "lg" | "icon";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { className = "", variant = "primary", size = "default", ...props },
    ref,
  ) => {
    const baseClasses =
      "inline-flex items-center justify-center rounded-lg font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed";

    const variantClasses = {
      primary: VARIANTS.button.primary,
      secondary: VARIANTS.button.secondary,
      outline: VARIANTS.button.outline,
      ghost: VARIANTS.button.ghost,
      danger: VARIANTS.button.danger,
    };

    const sizeClasses = {
      sm: SPACING.padding.xs + " text-sm",
      default: SPACING.padding.sm,
      lg: SPACING.padding.md + " text-lg",
      icon: "p-2.5 w-10 h-10",
    };

    const classes = `${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`;

    return <button className={classes} ref={ref} {...props} />;
  },
);
Button.displayName = "Button";

export { Button };
