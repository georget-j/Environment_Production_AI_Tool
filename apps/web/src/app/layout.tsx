import type { Metadata } from "next";
import { SiteNav } from "@/components/site-nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "ProdReady AI",
  description:
    "AI-powered production coding simulator. The missing bridge between coding tutorials and a first production software engineering job.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        {/* Hint the browser to fetch Pyodide's loader script early so by the
         * time the learner lands on a challenge page it's already in cache.
         * The full ~10 MB WASM bundle is still fetched lazily inside the
         * runner. */}
        <link
          rel="preload"
          as="script"
          href="https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js"
          crossOrigin="anonymous"
        />
      </head>
      <body className="min-h-screen antialiased">
        <SiteNav />
        {/* No py-* here — each page owns its own vertical padding so the
         * lesson workspace can claim the full viewport height below the
         * nav. Non-lesson pages add their own py-8 / py-10. */}
        <main className="mx-auto max-w-6xl px-6">{children}</main>
      </body>
    </html>
  );
}
