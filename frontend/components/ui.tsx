import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";

export function cn(...inputs: Array<string | false | null | undefined>) {
  return twMerge(clsx(inputs));
}

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-lg border border-line bg-panel/80 shadow-glow", className)} {...props} />;
}

export function Button({ className, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn("inline-flex h-10 items-center justify-center rounded-md bg-gold px-4 text-sm font-semibold text-ink transition hover:bg-[#e8c776] disabled:opacity-50", className)}
      {...props}
    />
  );
}

export function Badge({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "hot" | "warm" | "cold" }) {
  const tones = {
    default: "border-line text-slate-200",
    hot: "border-coral/40 bg-coral/10 text-coral",
    warm: "border-gold/40 bg-gold/10 text-gold",
    cold: "border-mint/40 bg-mint/10 text-mint"
  };
  return <span className={cn("rounded-md border px-2 py-1 text-xs font-medium", tones[tone])}>{children}</span>;
}
