import { forwardRef, type InputHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { cn } from "./cn";

const fieldBase =
  "block w-full rounded-input bg-black/[0.04] text-ink placeholder:text-stone " +
  "px-4 py-3 text-sm font-normal transition-colors duration-180 ease-pirsch " +
  "border border-transparent focus:outline-none focus:border-ink focus:bg-black/[0.06]";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, invalid, ...rest },
  ref,
) {
  return (
    <input
      ref={ref}
      className={cn(fieldBase, invalid && "border-red-500 focus:border-red-500", className)}
      {...rest}
    />
  );
});

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { className, invalid, ...rest },
  ref,
) {
  return (
    <textarea
      ref={ref}
      className={cn(fieldBase, "min-h-[96px] resize-y", invalid && "border-red-500 focus:border-red-500", className)}
      {...rest}
    />
  );
});
