import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ClosedPaw - Zero-Trust AI Assistant",
  description: "Secure, local-first AI assistant with hardened sandboxing",
  keywords: ["AI", "security", "privacy", "local", "ollama", "zero-trust", "closedpaw"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-slate-950">
        {children}
      </body>
    </html>
  );
}