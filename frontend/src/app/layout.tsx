import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { fontVars } from "@/lib/windfall/fonts";
import "./globals.css";
import "./recovery/windfall.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Windfall — Rebuild carts, don't discount them",
  description:
    "B2B abandoned-cart recovery for online travel agencies. Three agents rebuild the cart to fit the traveler instead of discounting it.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    /*
     * The Windfall font variables must live on <html>, not on a wrapper div:
     * windfall.css and the vendored design-system tokens rebind
     * --wf-font-* / --wf-text-* at :root, and a custom property that
     * references var(--font-plex-mono) is substituted AT :root. With the
     * variables only on a descendant, every font token computed to
     * guaranteed-invalid and the whole console silently rendered in Arial.
     */
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${fontVars} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
