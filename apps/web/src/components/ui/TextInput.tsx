import type { InputHTMLAttributes } from "react";

interface TextInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export function TextInput({ label, id, className = "", ...props }: TextInputProps) {
  const inputId = id ?? label.toLowerCase().replace(/\s+/g, "-");
  return (
    <label className="grid gap-2 text-sm text-slate-300" htmlFor={inputId}>
      <span>{label}</span>
      <input
        id={inputId}
        className={`min-h-10 rounded-md border border-slate-700 bg-slate-950 px-3 text-sm text-slate-100 placeholder:text-slate-500 ${className}`}
        {...props}
      />
    </label>
  );
}
