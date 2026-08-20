import type { Metadata } from "next";
import { Archivo, IBM_Plex_Mono, Instrument_Serif } from "next/font/google";
import "./windfall.css";

/**
 * Fonts are self-hosted at build time by next/font rather than pulled from the
 * Google Fonts CDN as the design bundle did. The console has to render
 * identically inside docker compose with no outbound network.
 */
const archivo = Archivo({
  variable: "--font-archivo",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
});

const instrumentSerif = Instrument_Serif({
  variable: "--font-instrument-serif",
  subsets: ["latin"],
  weight: ["400"],
});

export const metadata: Metadata = {
  title: "Windfall — Recovery Console",
  description:
    "Rebuild abandoned travel carts instead of discounting them. One cart, one decision, one trace.",
};

export default function RecoveryLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className={`${archivo.variable} ${plexMono.variable} ${instrumentSerif.variable} wf-root`}>
      {children}
    </div>
  );
}
