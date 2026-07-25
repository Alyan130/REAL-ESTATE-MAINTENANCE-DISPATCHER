import type { Metadata } from "next";
import { JetBrains_Mono, Open_Sans } from "next/font/google";

import { DemoBadge } from "@/components/demo/demo-notice";
import { ToastHost } from "@/components/ui/toast-host";

import "./globals.css";

const openSans = Open_Sans({
  variable: "--font-open-sans",
  subsets: ["latin"],
  display: "swap",
});

const jetBrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Maintenance Dispatcher",
  description:
    "Ticket intake, triage, and vendor dispatch for property managers, tenants, and vendors.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${openSans.variable} ${jetBrainsMono.variable} antialiased`}
    >
      <body className="min-h-[100dvh]">
        {children}
        <ToastHost />
        <DemoBadge />
      </body>
    </html>
  );
}
