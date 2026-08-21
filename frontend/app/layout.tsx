import type { Metadata } from "next";
import { Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";
import "leaflet/dist/leaflet.css";
import "./globals.css";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import { cn } from "@/lib/utils";

const sans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-sans",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "SHIFT — Shoreline & River Bank Dynamics System",
  description:
    "SHIFT: Shoreline Intelligence, Forecasting & Trends - An Open-Source System for Shoreline and River Bank Dynamics.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={cn("h-full", "antialiased", sans.variable, mono.variable)}>
      <body className={cn("h-full overflow-hidden bg-slate-50 text-slate-900", sans.className)}>
        <TooltipProvider delay={150}>{children}</TooltipProvider>
        <Toaster theme="light" position="top-right" richColors closeButton />
      </body>
    </html>
  );
}
