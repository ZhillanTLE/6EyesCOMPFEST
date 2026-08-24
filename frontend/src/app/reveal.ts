"use client";

/**
 * Reveal-on-scroll, as the handoff specifies.
 *
 * Everything marked data-reveal starts displaced and settles once it has been
 * observed. Elements already on screen at mount settle immediately, so the
 * hero is never blank while waiting for a scroll that may not come.
 *
 * If IntersectionObserver is missing the whole page is shown at once. A
 * landing page that stays invisible because an animation API is unavailable is
 * a worse failure than no animation.
 */
import { useEffect } from "react";

export function useReveal() {
  useEffect(() => {
    const nodes = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    if (!("IntersectionObserver" in window)) {
      nodes.forEach((n) => n.classList.add("wf-shown"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (!e.isIntersecting) return;
          const el = e.target as HTMLElement;
          const delay = Number(el.dataset.revealDelay ?? 0);
          window.setTimeout(() => el.classList.add("wf-shown"), delay);
          io.unobserve(el);
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.05 },
    );
    nodes.forEach((n) => io.observe(n));
    return () => io.disconnect();
  }, []);
}
