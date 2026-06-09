import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default:     "border-transparent bg-emerald-500/20 text-emerald-400",
        secondary:   "border-transparent bg-white/10 text-gray-300",
        destructive: "border-transparent bg-red-500/20 text-red-400",
        outline:     "border-white/20 text-gray-300",
        yellow:      "border-yellow-500/20 bg-yellow-500/10 text-yellow-400",
        blue:        "border-blue-500/20 bg-blue-500/10 text-blue-400",
        purple:      "border-purple-500/20 bg-purple-500/10 text-purple-400",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
