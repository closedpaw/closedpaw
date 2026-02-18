import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SecureSphere AI - Zero-Trust AI Assistant",
  description: "Secure, local-first AI assistant with hardened sandboxing",
  keywords: ["AI", "security", "privacy", "local", "ollama", "zero-trust"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}