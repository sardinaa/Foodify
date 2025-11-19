import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import TabNavigation from "@/components/TabNavigation";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Foodify - AI-Powered Food Assistant",
  description: "Discover recipes, plan meals, and chat with your AI cooking assistant",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased`}>
        <TabNavigation />
        <main className="md:ml-20 mb-16 md:mb-0">
          {children}
        </main>
      </body>
    </html>
  );
}
