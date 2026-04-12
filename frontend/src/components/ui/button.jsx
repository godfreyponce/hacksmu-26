import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-full text-sm font-bold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-[#1d9e75] text-[#042f20] hover:bg-[#5dcaa5] border-transparent",
        destructive: "bg-red-600 text-white hover:bg-red-700",
        outline: "border border-[rgba(232,237,229,0.16)] bg-transparent text-[#e8ede5] hover:border-[rgba(126,200,160,0.5)] hover:text-[#7ec8a0]",
        secondary: "bg-[rgba(126,200,160,0.15)] text-[#7ec8a0] hover:bg-[rgba(126,200,160,0.25)] border border-[rgba(126,200,160,0.3)]",
        ghost: "hover:bg-[rgba(255,255,255,0.05)] hover:text-[#7ec8a0]",
        link: "text-[#7ec8a0] underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-5 py-2",
        sm: "h-9 rounded-full px-4 text-xs",
        lg: "h-12 rounded-full px-8 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
)

const Button = React.forwardRef(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  },
)
Button.displayName = "Button"

export { Button, buttonVariants }
