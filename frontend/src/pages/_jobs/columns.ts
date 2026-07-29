/** Board column definitions shared by JobsPage and its presentational parts.
 *
 * Lives here so the parts can import them without importing JobsPage itself,
 * which would be circular.
 */
import { Briefcase, Coffee, Heart, Send, Trophy, XCircle } from "lucide-react";

import type { JobStatus } from "@/shared/api";

export interface ColumnDef {
  id: JobStatus;
  label: string;
  Icon: typeof Briefcase;
  tone: "leaf" | "sunbeam" | "stone" | "amber";
}

export const COLUMNS: ColumnDef[] = [
  { id: "interested", label: "Interesado", Icon: Heart, tone: "stone" },
  { id: "applied", label: "Aplicado", Icon: Send, tone: "leaf" },
  { id: "interviewing", label: "Entrevistas", Icon: Coffee, tone: "sunbeam" },
  { id: "offer", label: "Oferta", Icon: Trophy, tone: "leaf" },
  { id: "rejected", label: "Rechazado", Icon: XCircle, tone: "amber" },
];

export const ARCHIVED_TONE: Record<JobStatus, "leaf" | "sunbeam" | "stone" | "amber"> = {
  interested: "stone",
  applied: "leaf",
  interviewing: "sunbeam",
  offer: "leaf",
  rejected: "amber",
  archived: "stone",
};

export type DropAnchor = { id: string; side: "top" | "bottom" } | null;
