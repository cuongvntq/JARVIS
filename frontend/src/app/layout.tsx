import type { Metadata } from "next";
import { Orbitron, Inter } from "next/font/google";
import "./globals.css";
import QueryProvider from "@/providers/QueryProvider";
import AuthGuard from "@/components/auth/AuthGuard";

const orbitron = Orbitron({
  subsets: ["latin"],
  variable: "--font-orbitron",
  weight: ["400", "600", "700", "900"],
  display: "swap",
});

const inter = Inter({
  subsets: ["latin", "vietnamese"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "J.A.R.V.I.S",
  description: "Trợ lý cá nhân AI — lấy cảm hứng từ J.A.R.V.I.S của Iron Man",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi" className={`${orbitron.variable} ${inter.variable}`}>
      <body className={`${inter.className} antialiased h-full overflow-hidden bg-jarvis-bg text-jarvis-fg`}>
        <QueryProvider>
          <AuthGuard>{children}</AuthGuard>
        </QueryProvider>
      </body>
    </html>
  );
}
