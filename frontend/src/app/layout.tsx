import type { Metadata } from "next";
import { Inter, Orbitron } from "next/font/google";
import "./globals.css";
import AuthGuard from "@/components/auth/AuthGuard";
import { ReminderPolling } from "@/components/reminders/ReminderPolling";
import QueryProvider from "@/providers/QueryProvider";
import { Toaster } from "sonner";

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
      <body
        className={`${inter.className} antialiased h-full overflow-hidden bg-jarvis-bg text-jarvis-fg`}
      >
        <QueryProvider>
          <AuthGuard>{children}</AuthGuard>
          <ReminderPolling />
          <Toaster
            position="bottom-right"
            theme="dark"
            toastOptions={{
              style: {
                background: "rgba(10,20,30,0.95)",
                border: "1px solid rgba(0,180,216,0.3)",
                color: "#e2e8f0",
              },
            }}
          />
        </QueryProvider>
      </body>
    </html>
  );
}
