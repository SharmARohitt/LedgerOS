import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LedgerOS — Autonomous Financial Control Plane",
  description: "Every dollar. Every decision. Every action. Proven.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
