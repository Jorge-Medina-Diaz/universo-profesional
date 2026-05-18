/**
 * Curated `useCopilotReadable` payloads — what the agent sees each turn.
 * Token-budget conscious: we inject a SUMMARY, not the whole universe.
 */
import { useCopilotReadable } from "@copilotkit/react-core";
import { useQuery } from "@tanstack/react-query";
import { universe } from "@/shared/api";
import { liveProfile } from "@/shared/api-extra";

export function UniverseReadable() {
  const summary = useQuery({
    queryKey: ["universe", "summary"],
    queryFn: () => universe.summary(),
  });
  const suggestions = useQuery({
    queryKey: ["suggestions"],
    queryFn: () => liveProfile.suggestions.list("pending"),
  });

  useCopilotReadable({
    description:
      "Compact summary of the user's professional universe (counts, headline, top skills, recent experiences, languages, integration status).",
    value: summary.data ?? { counts: {} },
  });

  useCopilotReadable({
    description: "Pending suggestions for the user's universe (skills to add, certs expiring, stale entries).",
    value: suggestions.data ?? [],
  });

  return null;
}
