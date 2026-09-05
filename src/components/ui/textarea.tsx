import * as React from "react";
import { cn } from "@/lib/cn";

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "flex min-h-[9rem] w-full rounded-md bg-bg px-3 py-3 text-sm text-fg shadow-[var(--shadow-border)] placeholder:text-subtle",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60",
      "disabled:cursor-not-allowed disabled:opacity-50",
      "resize-y font-mono leading-relaxed",
      className,
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";
