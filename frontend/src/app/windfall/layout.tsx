import type { Metadata } from "next";
import { fontVars } from "@/lib/windfall/fonts";
import "../recovery/windfall.css";

export const metadata: Metadata = {
  title: "Windfall — Rebuild carts, don't discount them",
  description:
    "B2B abandoned-cart recovery for online travel agencies. Three agents rebuild the cart to fit the traveler instead of discounting it.",
};

export default function WindfallLandingLayout({ children }: { children: React.ReactNode }) {
  return <div className={`${fontVars} wf-root`}>{children}</div>;
}
