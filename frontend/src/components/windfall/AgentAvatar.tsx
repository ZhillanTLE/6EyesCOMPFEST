/**
 * AgentAvatar -- the sleep / awake / finished mark beside a pipeline stage.
 *
 * All three states are rendered stacked and crossfaded by opacity. The handoff
 * is explicit that the src must never be swapped: swapping it unloads the
 * decoded image and the browser paints a broken frame for a tick, which on a
 * stage that changes state three times per run is three visible flashes.
 *
 * Stacking costs three tiny SVG fetches once, then nothing. All nine files are
 * already served from public/windfall/agents/.
 *
 * background-image rather than <img> is deliberate: the mark is decoration for
 * a state the stage already announces in text, so it must not reach the
 * accessibility tree at all. AgentStage carries the spoken status.
 */
export type AvatarState = "sleep" | "awake" | "finished";

export type AvatarAgent = "classifier" | "searcher" | "notifier";

const STATES: AvatarState[] = ["sleep", "awake", "finished"];

export function AgentAvatar({
  agent,
  state,
  size = 34,
  well = 50,
}: {
  agent: AvatarAgent;
  state: AvatarState;
  size?: number;
  well?: number;
}) {
  return (
    <span
      aria-hidden
      style={{
        position: "absolute",
        /* Centred on the 2px timeline rail, matching the dot it replaces:
           the rail's centre sits 1px outside the padding box. */
        left: -(well / 2 + 1),
        top: -10,
        width: well,
        height: well,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: "50%",
        background: "var(--wf-avatar-bg)",
        boxShadow: "inset 0 0 0 1px var(--wf-border)",
        overflow: "hidden",
        zIndex: 2,
      }}
    >
      <span style={{ position: "relative", width: size, height: size, display: "block" }}>
        {STATES.map((s) => (
          <span
            key={s}
            style={{
              position: "absolute",
              inset: 0,
              backgroundImage: `url(/windfall/agents/${agent}-${s}.svg)`,
              backgroundSize: "contain",
              backgroundRepeat: "no-repeat",
              backgroundPosition: "center",
              opacity: s === state ? 1 : 0,
              transition: "opacity .32s ease",
            }}
          />
        ))}
      </span>
    </span>
  );
}

/**
 * Phase-to-state mapping, lifted from the prototype's stFor().
 *
 * The halted case is the one worth reading twice: the Classifier still
 * finishes, because the gate resolves from history the search never touches.
 * Everything downstream stays asleep -- it was never woken, which is a
 * different thing from having run and found nothing.
 */
export function avatarState(phase: number, stage: 0 | 1 | 2, halted = false): AvatarState {
  if (halted && phase >= 2) return stage === 0 ? "finished" : "sleep";
  if (phase === 0) return "sleep";
  if (stage === 0) return phase >= 2 ? "finished" : "awake";
  if (stage === 1) return phase < 2 ? "sleep" : phase >= 3 ? "finished" : "awake";
  return phase < 3 ? "sleep" : phase >= 4 ? "finished" : "awake";
}
