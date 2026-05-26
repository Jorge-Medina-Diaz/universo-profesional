/**
 * Strict types for CopilotKit action parameters.
 */

export interface UpsertResponse {
  status: "created" | "merged" | "noop" | "suggested";
  entity_id: string | null;
  diffs: { field: string; old: unknown; new: unknown }[];
  suggestion_id: string | null;
  reason: string | null;
}

export type SavingState = string | null;

export type CopilotParamType =
  | "string"
  | "number"
  | "boolean"
  | "string[]"
  | "object[]"
  | "object";

export interface CopilotActionParam {
  name: string;
  type: CopilotParamType;
  description?: string;
  required?: boolean;
}

export type CopilotActionParams = CopilotActionParam[];
