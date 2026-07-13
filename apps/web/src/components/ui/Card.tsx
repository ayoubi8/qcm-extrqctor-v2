import type { HTMLAttributes, ReactNode } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  title?: string;
  actions?: ReactNode;
}

export function Card({ title, actions, children, className = "", ...props }: CardProps) {
  return (
    <section className={`rounded-lg border border-slate-800 bg-slate-900 ${className}`} {...props}>
      {(title || actions) && (
        <header className="flex min-h-12 items-center justify-between gap-3 border-b border-slate-800 px-4">
          {title ? <h2 className="text-sm font-semibold text-slate-100">{title}</h2> : <span />}
          {actions}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}
