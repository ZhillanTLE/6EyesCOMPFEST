import type { Metadata } from "next";
import { fontVars } from "@/lib/windfall/fonts";
import "./windfall.css";

export const metadata: Metadata = {
  title: "Windfall — Recovery Console",
  description:
    "Rebuild abandoned travel carts instead of discounting them. One cart, one decision, one trace.",
};

export default function RecoveryLayout({ children }: { children: React.ReactNode }) {
  return <div className={`${fontVars} wf-root`}>{children}</div>;
}
