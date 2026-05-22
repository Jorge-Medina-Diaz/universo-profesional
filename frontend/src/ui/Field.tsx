import { useId, type ReactNode } from "react";
import { cn } from "./cn";

export interface FieldProps {
  label?: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
  required?: boolean;
  className?: string;
  children: (props: { id: string; "aria-invalid"?: boolean; "aria-describedby"?: string }) => ReactNode;
}

export function Field({ label, hint, error, required, className, children }: FieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      {label && (
        <label htmlFor={id} className="text-sm font-medium text-ink">
          {label}
          {required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
      )}
      {children({ id, "aria-invalid": !!error, "aria-describedby": describedBy })}
      {hint && !error && (
        <p id={hintId} className="text-xs text-stone">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-xs text-red-600 font-medium">
          {error}
        </p>
      )}
    </div>
  );
}
