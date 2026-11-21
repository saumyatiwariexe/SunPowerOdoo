import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva("inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-semibold", {
  variants: { variant: { default: "border-brand-600 bg-brand-600 text-white", outline: "border-brand-200 bg-brand-50 text-brand-800" } },
  defaultVariants: { variant: "outline" },
})
type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>
function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}
export { Badge }
