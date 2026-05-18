import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { liveProfile } from "@/shared/api-extra";

export function SuggestionBar() {
  const qc = useQueryClient();
  const list = useQuery({
    queryKey: ["suggestions"],
    queryFn: () => liveProfile.suggestions.list("pending"),
  });
  const regen = useMutation({
    mutationFn: () => liveProfile.suggestions.regenerate(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["suggestions"] }),
  });
  const act = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "accept" | "reject" }) =>
      liveProfile.suggestions.act(id, action),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["suggestions"] }),
  });

  const top = (list.data ?? []).slice(0, 3);

  return (
    <section
      aria-label="Sugerencias"
      className="card border-brand-200 bg-brand-50/30 mb-4"
    >
      <header className="flex items-center justify-between mb-2">
        <h2 className="font-semibold text-sm">Sugerencias para ti</h2>
        <button
          className="text-xs text-brand-700 hover:underline"
          onClick={() => regen.mutate()}
          disabled={regen.isPending}
        >
          {regen.isPending ? "Recalculando…" : "Recalcular"}
        </button>
      </header>
      {top.length === 0 ? (
        <p className="text-xs text-gray-500">Sin sugerencias pendientes — pulsa &laquo;Recalcular&raquo; para regenerar.</p>
      ) : (
        <ul className="space-y-2">
          {top.map((s) => (
            <li key={s.id} className="flex items-start gap-3">
              <div className="flex-1">
                <p className="text-sm font-medium">{s.title}</p>
                {s.body && <p className="text-xs text-gray-600">{s.body}</p>}
              </div>
              <div className="flex gap-1">
                <button
                  className="text-xs bg-brand-600 text-white px-2 py-1 rounded"
                  onClick={() => act.mutate({ id: s.id, action: "accept" })}
                >
                  ✓
                </button>
                <button
                  className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded"
                  onClick={() => act.mutate({ id: s.id, action: "reject" })}
                >
                  ✗
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
