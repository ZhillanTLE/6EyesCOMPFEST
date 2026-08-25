/**
 * Windfall design-system components.
 *
 * Ported from the design_handoff_windfall bundle. BrowserFrame is deliberately
 * absent: fake browser chrome with a localhost:5000 bar does not belong in a
 * real console, and it was already unused in the source prototype.
 */
export { Button, ModelTag, PreviewTag, StatusPill, TierBadge, Skeleton } from "./primitives";
export { AgentStage } from "./AgentStage";
export { AgentAvatar, avatarState } from "./AgentAvatar";
export type { AvatarAgent, AvatarState } from "./AgentAvatar";
export type { StageStatus } from "./AgentStage";
export { FareLedger } from "./FareLedger";
export { OutcomeCard, OutcomeNote } from "./OutcomeCard";
export { PricePanel, EmailPreview, WhatsAppPreview } from "./previews";
export { TravelerCard } from "./TravelerCard";
export { BrowseView } from "./BrowseView";
export { PipelineLoading } from "./PipelineLoading";
export { PipelineView } from "./PipelineView";
export { PreviewsView } from "./PreviewsView";
export { ApprovalBar } from "./ApprovalBar";
export { HoldPanel } from "./HoldPanel";
