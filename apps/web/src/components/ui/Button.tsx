import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  icon?: ReactNode;
}

const variantClass: Record<ButtonVariant, string> = {
  primary: "border-cyan-300 bg-cyan-300 text-slate-950 hover:bg-cyan-200",
  secondary: "border-slate-700 bg-slate-900 text-slate-100 hover:border-slate-500",
  ghost: "border-transparent bg-transparent text-slate-300 hover:bg-slate-900 hover:text-slate-100",
  danger: "border-red-400/50 bg-red-500/10 text-red-200 hover:bg-red-500/20"
};

export function Button({ variant = "secondary", icon, children, className = "", type = "button", ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-md border px-3 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${variantClass[variant]} ${className}`}
      {...props}
    >
      {icon}
      <span>{children}</span>
    </button>
  );
}
