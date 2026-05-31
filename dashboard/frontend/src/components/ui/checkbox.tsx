import * as React from "react";
import * as CheckboxPrimitive from "@radix-ui/react-checkbox";
import { cn } from "@/lib/utils";

const Checkbox = React.forwardRef<
  React.ElementRef<typeof CheckboxPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root>
>(({ className, ...props }, ref) => (
  <CheckboxPrimitive.Root
    ref={ref}
    className={cn(
      "peer shrink-0 disabled:cursor-not-allowed disabled:opacity-50",
      "focus:outline-none",
      className,
    )}
    style={{
      width: "14px",
      height: "14px",
      border: "1px solid var(--border)",
      borderRadius: "1px",
      backgroundColor: "var(--surface)",
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
    }}
    onFocus={(e) => {
      e.currentTarget.style.borderColor = "var(--border-strong)";
      if (props.onFocus) props.onFocus(e);
    }}
    onBlur={(e) => {
      const checked = e.currentTarget.getAttribute("data-state") === "checked";
      e.currentTarget.style.borderColor = checked ? "var(--accent-border)" : "var(--border)";
      if (props.onBlur) props.onBlur(e);
    }}
    {...props}
  >
    <CheckboxPrimitive.Indicator
      style={{ color: "var(--background)", display: "flex", alignItems: "center", justifyContent: "center" }}
    >
      <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
        <path d="M1 4L3.5 6.5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </CheckboxPrimitive.Indicator>
  </CheckboxPrimitive.Root>
));
Checkbox.displayName = CheckboxPrimitive.Root.displayName;

export { Checkbox };
