import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import NavBar from "@/components/NavBar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "EventScout | Never miss a technical opportunity",
  description: "Discover the best technical events, workshops, and hackathons.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${inter.className} bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 min-h-screen flex flex-col`}
        suppressHydrationWarning
      >
        <AuthProvider>
          <NavBar />

          {/* Page Content */}
          <main className="flex-grow">{children}</main>

          {/* Footer */}
          <footer className="border-t border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 py-8 mt-auto">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-gray-500 dark:text-gray-400">
              <p>EventScout — Never miss a technical opportunity.</p>
            </div>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
