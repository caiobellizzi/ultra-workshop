import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "text-[--danger] bg-[--danger-bg] border border-[--danger-bd]",
        outline: "text-foreground",
        success: "text-[--success] bg-[--success-bg] border border-[--success-bd]",
        warning: "text-[--warning] bg-[--warn-bg] border border-[--warn-bd]",
        info: "text-[--info] bg-[--info-bg] border border-[--info-bd]",
        danger: "text-[--danger] bg-[--danger-bg] border border-[--danger-bd]",
        error: "text-[--danger] bg-[--danger-bg] border border-[--danger-bd]",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
