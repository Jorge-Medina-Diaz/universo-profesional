/**
 * Display-only generative INSIGHT actions — the agent renders rich cards
 * (trajectory / experience / project / skill-gap) from a tool call. No handler,
 * no backend execution, no HITL: pure `render` keyed off the streamed args.
 *
 * Tool names match the `external_execution` descriptors in
 * backend/src/agents/tools/ui_widgets.py.
 */
import { useCopilotAction } from "@copilotkit/react-core";
import {
  TrajectoryCard,
  ExperienceCard,
  ProjectCard,
  SkillGapCard,
  type TrajectoryArgs,
  type ExperienceArgs,
  type ProjectArgs,
  type SkillGapArgs,
} from "../cards/InsightCards";
import type { CopilotActionParams } from "./types";

export function useInsightActions() {
  useCopilotAction({
    name: "present_trajectory",
    description:
      "Render the user's career TRAJECTORY as an animated timeline. Call after a read tool. `milestones` is an ordered list of {period, title, org?, detail?, entity_id?} (oldest→newest). Optional `narrative` framing.",
    available: "enabled",
    parameters: [
      { name: "title", type: "string" },
      { name: "narrative", type: "string" },
      { name: "milestones", type: "object[]", required: true },
    ] satisfies CopilotActionParams,
    render: ({ args, status }: { args: Record<string, unknown>; status?: string }) => (
      <TrajectoryCard args={args as TrajectoryArgs} status={status} />
    ),
  });

  useCopilotAction({
    name: "present_experience_card",
    description:
      "Render a rich EXPERIENCE card (role @ org, period, impact, highlights, skills). Pass `entity_id` so the card can light up that node in the graph.",
    available: "enabled",
    parameters: [
      { name: "entity_id", type: "string" },
      { name: "role", type: "string", required: true },
      { name: "organization", type: "string" },
      { name: "period", type: "string" },
      { name: "impact", type: "string" },
      { name: "highlights", type: "string[]" },
      { name: "skills", type: "string[]" },
      { name: "narrative", type: "string" },
    ] satisfies CopilotActionParams,
    render: ({ args, status }: { args: Record<string, unknown>; status?: string }) => (
      <ExperienceCard args={args as ExperienceArgs} status={status} />
    ),
  });

  useCopilotAction({
    name: "present_project_card",
    description:
      "Render a PROJECT showcase card (name, summary, tech_stack, highlights, impact, url). Pass `entity_id` so the card can reveal that node in the graph.",
    available: "enabled",
    parameters: [
      { name: "entity_id", type: "string" },
      { name: "name", type: "string", required: true },
      { name: "summary", type: "string" },
      { name: "tech_stack", type: "string[]" },
      { name: "highlights", type: "string[]" },
      { name: "impact", type: "string" },
      { name: "url", type: "string" },
    ] satisfies CopilotActionParams,
    render: ({ args, status }: { args: Record<string, unknown>; status?: string }) => (
      <ProjectCard args={args as ProjectArgs} status={status} />
    ),
  });

  useCopilotAction({
    name: "present_skill_gap",
    description:
      "Render a SKILL-GAP / role-fit card for a target role: a match-score ring + have / partial / missing skill chips. Pass `entity_ids` (the have-skill node ids) so the card can light them up in the graph.",
    available: "enabled",
    parameters: [
      { name: "target_role", type: "string", required: true },
      { name: "match_score", type: "number" },
      { name: "have", type: "string[]" },
      { name: "partial", type: "string[]" },
      { name: "missing", type: "string[]" },
      { name: "entity_ids", type: "string[]" },
      { name: "narrative", type: "string" },
    ] satisfies CopilotActionParams,
    render: ({ args, status }: { args: Record<string, unknown>; status?: string }) => (
      <SkillGapCard args={args as SkillGapArgs} status={status} />
    ),
  });
}
