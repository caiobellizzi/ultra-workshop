import * as React from "react";
import { cn } from "@/lib/utils";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error, style, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          "min-h-[80px] w-full rounded-sm font-mono text-sm px-2.5 py-2 resize-y",
          "focus:outline-none",
          className,
        )}
        style={{
          backgroundColor: "var(--surface-r)",
          border: error ? "1px solid var(--danger-border)" : "1px solid var(--border-s)",
          color: "var(--text)",
          fontFamily: "var(--font-mono)",
          fontSize: "var(--text-sm)",
          borderRadius: "var(--radius-sm)",
          ...style,
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = "var(--accent-bd)";
          if (props.onFocus) props.onFocus(e);
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = error ? "var(--danger-border)" : "var(--border-s)";
          if (props.onBlur) props.onBlur(e);
        }}
        {...props}
      />
    );
  },
);
Textarea.displayName = "Textarea";
