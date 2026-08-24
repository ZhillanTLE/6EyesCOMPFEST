/**
 * The three Windfall families, self-hosted at build time.
 *
 * Shared by the console and the landing page so the two cannot drift onto
 * different weights. next/font requires module-scope calls, which is why this
 * is a module rather than a helper.
 *
 * tokens/fonts.css from the design bundle is deliberately not imported
 * anywhere: it pulls these same families from the Google Fonts CDN, and both
 * routes have to render identically inside docker compose with no outbound
 * network. windfall.css rebinds --wf-font-* onto the variables below.
 */
import { Archivo, IBM_Plex_Mono, Instrument_Serif } from "next/font/google";

export const archivo = Archivo({
  variable: "--font-archivo",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
});

export const instrumentSerif = Instrument_Serif({
  variable: "--font-instrument-serif",
  subsets: ["latin"],
  weight: ["400"],
});

export const fontVars = `${archivo.variable} ${plexMono.variable} ${instrumentSerif.variable}`;
