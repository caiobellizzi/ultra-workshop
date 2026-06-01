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
      "peer inline-flex h-[14px] w-[14px] shrink-0 items-center justify-center rounded-[1px] border outline-none transition-colors",
      "border-[var(--border)] bg-[var(--surface)]",
      // Visible checked state (was missing — a checked box looked identical to unchecked)
      "data-[state=checked]:bg-[var(--accent)] data-[state=checked]:border-[var(--accent-border)]",
      "focus-visible:border-[var(--border-strong)]",
      "disabled:cursor-not-allowed disabled:opacity-50",
      className,
    )}
    {...props}
  >
    <CheckboxPrimitive.Indicator
      className="flex items-center justify-center"
      style={{ color: "var(--background)" }}
    >
      <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
        <path d="M1 4L3.5 6.5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </CheckboxPrimitive.Indicator>
  </CheckboxPrimitive.Root>
));
Checkbox.displayName = CheckboxPrimitive.Root.displayName;

export { Checkbox };
