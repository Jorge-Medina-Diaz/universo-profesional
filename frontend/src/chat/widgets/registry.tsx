/**
 * Widget registry — maps WidgetKind to its renderer.
 *
 * Adding a new widget kind:
 *   1. Add the literal to `WidgetKind` in `state.ts`.
 *   2. Implement `Foo.tsx` accepting `{ data }`.
 *   3. Register it here.
 *   4. Document the prompt regla 8 in HomePage.tsx so the agent learns to
 *      call `present_widget` with this kind.
 *
 * Note: the universe's structured entities (skills, experiences,
 * projects, …) are no longer surfaced as flat widgets — they live in the
 * navigable graph at /universe (see `present_graph_view`). The widgets
 * that remain are derived/analytical views that don't map onto a single
 * graph node.
 */
import type { ComponentType } from "react";
import type { WidgetKind } from "@/chat/state";
import { GoalProgressWidget } from "./GoalProgressWidget";
import { InterviewQAWidget } from "./InterviewQAWidget";
import { TechRadarWidget } from "./TechRadarWidget";
import { AgentPatternsWidget } from "./AgentPatternsWidget";
import { SignalCoverageWidget } from "./SignalCoverageWidget";
import { DocumentPreviewWidget } from "./DocumentPreviewWidget";
import { JobMatchWidget } from "./JobMatchWidget";
import { CloudCoverageWidget } from "./CloudCoverageWidget";
import { DataStackTopologyWidget } from "./DataStackTopologyWidget";
import { SecurityPostureWidget } from "./SecurityPostureWidget";
import { ArchitecturePatternsWidget } from "./ArchitecturePatternsWidget";
import { PortfolioRadarWidget } from "./PortfolioRadarWidget";
import { LearningTrajectoryWidget } from "./LearningTrajectoryWidget";

type WidgetComponent = ComponentType<{ data: Record<string, unknown> }>;

export const widgetRegistry: Partial<Record<WidgetKind, WidgetComponent>> = {
  goals_progress: GoalProgressWidget as unknown as WidgetComponent,
  interview_qa: InterviewQAWidget as unknown as WidgetComponent,
  tech_radar: TechRadarWidget as unknown as WidgetComponent,
  agent_patterns: AgentPatternsWidget as unknown as WidgetComponent,
  signal_coverage: SignalCoverageWidget as unknown as WidgetComponent,
  document_preview: DocumentPreviewWidget as unknown as WidgetComponent,
  job_match: JobMatchWidget as unknown as WidgetComponent,
  cloud_coverage: CloudCoverageWidget as unknown as WidgetComponent,
  data_stack_topology: DataStackTopologyWidget as unknown as WidgetComponent,
  security_posture: SecurityPostureWidget as unknown as WidgetComponent,
  architecture_patterns: ArchitecturePatternsWidget as unknown as WidgetComponent,
  portfolio_radar: PortfolioRadarWidget as unknown as WidgetComponent,
  learning_trajectory: LearningTrajectoryWidget as unknown as WidgetComponent,
};

export function getWidgetComponent(kind: WidgetKind): WidgetComponent | null {
  return widgetRegistry[kind] ?? null;
}
