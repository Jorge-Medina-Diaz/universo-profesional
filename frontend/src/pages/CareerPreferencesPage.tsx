import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Briefcase,
  MapPin,
  Coffee,
  Heart,
  Save,
  Globe,
} from "lucide-react";
import { universe, type CareerPreferences } from "@/shared/api";
import {
  Badge,
  Button,
  Card,
  ChipInput,
  Field,
  Input,
  PageHeader,
  PageSkeleton,
  Reveal,
  Stagger,
  Surface,
  Textarea,
  cn,
  toast,
} from "@/ui";
import { queryKeys } from "@/shared/queryKeys";

const EMPTY: CareerPreferences = {
  status: null,
  salary_min: null,
  salary_max: null,
  salary_currency: "EUR",
  contract_types: [],
  remote_preference: null,
  open_to_relocate: null,
  working_areas: [],
  perks_must_have: [],
  perks_nice_to_have: [],
  preferred_competences: [],
  discarded_competences: [],
  preferred_roles: [],
  discarded_roles: [],
  motivations: null,
};

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "open", label: "Abierto a propuestas" },
  { value: "active", label: "Buscando activamente" },
  { value: "passive", label: "Atento sin prisa" },
  { value: "not_looking", label: "No busco ahora" },
];

const REMOTE_OPTIONS: { value: string; label: string }[] = [
  { value: "remote", label: "100% remoto" },
  { value: "hybrid", label: "Híbrido" },
  { value: "onsite", label: "Presencial" },
  { value: "any", label: "Me da igual" },
];

const CONTRACT_OPTIONS = ["Indefinido", "Temporal", "Freelance", "Proyecto", "Práctica"];

export function CareerPreferencesPage() {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: queryKeys.preferences.all,
    queryFn: () => universe.preferences.get(),
  });

  const [draft, setDraft] = useState<CareerPreferences>(EMPTY);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (query.data) {
      setDraft({ ...EMPTY, ...query.data });
      setDirty(false);
    }
  }, [query.data]);

  const save = useMutation({
    mutationFn: () => universe.preferences.set(draft),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.preferences.all });
      setDirty(false);
      toast.success("Preferencias guardadas", "El agente las usará en próximas CVs.");
    },
    onError: (e: unknown) =>
      toast.error("No pudimos guardar", (e as Error).message),
  });

  const update = <K extends keyof CareerPreferences>(
    key: K,
    value: CareerPreferences[K],
  ) => {
    setDraft((d) => ({ ...d, [key]: value }));
    setDirty(true);
  };

  if (query.isLoading) return <PageSkeleton />;

  return (
    <Surface width="md" spacing="md">
      <PageHeader
        eyebrow="Preferencias"
        title="Qué buscas en tu próximo trabajo"
        subtitle="Cuanto más afinado, mejor adapta tus CVs y prioriza ofertas. Todo opcional."
        actions={
          <Button
            variant="cta"
            onClick={() => save.mutate()}
            loading={save.isPending}
            disabled={!dirty}
            leadingIcon={<Save size={14} />}
          >
            {save.isPending ? "Guardando" : "Guardar"}
          </Button>
        }
      />

      <Stagger className="flex flex-col gap-4 md:gap-6" delayStep={0.05}>
        {/* Status & contract */}
        <Card padding="lg">
          <SectionHeader icon={<Briefcase size={16} />} title="Estado y tipo de contrato" />
          <div className="grid md:grid-cols-2 gap-4">
            <Field label="Tu situación actual">
              {() => (
                <ChipPicker
                  options={STATUS_OPTIONS}
                  value={draft.status}
                  onChange={(v) => update("status", v)}
                />
              )}
            </Field>
            <Field label="Tipo de contrato (puedes elegir varios)">
              {() => (
                <MultiChipPicker
                  options={CONTRACT_OPTIONS.map((v) => ({ value: v, label: v }))}
                  value={draft.contract_types}
                  onChange={(v) => update("contract_types", v)}
                />
              )}
            </Field>
          </div>
        </Card>

        {/* Modalidad y ubicación */}
        <Card padding="lg">
          <SectionHeader icon={<Globe size={16} />} title="Modalidad y ubicación" />
          <div className="grid md:grid-cols-2 gap-4">
            <Field label="Modalidad preferida">
              {() => (
                <ChipPicker
                  options={REMOTE_OPTIONS}
                  value={draft.remote_preference}
                  onChange={(v) => update("remote_preference", v)}
                />
              )}
            </Field>
            <Field
              label="¿Te mudarías por el trabajo correcto?"
              hint="Solo si te interesara mucho"
            >
              {() => (
                <ChipPicker
                  options={[
                    { value: "yes", label: "Sí" },
                    { value: "no", label: "No" },
                    { value: "maybe", label: "Depende" },
                  ]}
                  value={
                    draft.open_to_relocate == null
                      ? null
                      : draft.open_to_relocate
                        ? "yes"
                        : draft.open_to_relocate === false
                          ? "no"
                          : "maybe"
                  }
                  onChange={(v) =>
                    update("open_to_relocate", v === "yes" ? true : v === "no" ? false : null)
                  }
                />
              )}
            </Field>
          </div>
          <Field
            label="Zonas donde trabajarías"
            hint="Ciudades o regiones. Enter o coma para añadir."
            className="mt-4"
          >
            {(p) => (
              <ChipInput
                {...p}
                value={draft.working_areas.map((w) => String(w.name ?? w))}
                onChange={(arr) =>
                  update(
                    "working_areas",
                    arr.map((name) => ({ name })) as CareerPreferences["working_areas"],
                  )
                }
                placeholder="Madrid, Barcelona, remoto Europa…"
                tone="stone"
              />
            )}
          </Field>
        </Card>

        {/* Salario */}
        <Card padding="lg">
          <SectionHeader icon={<MapPin size={16} />} title="Salario" />
          <div className="grid md:grid-cols-[1fr_1fr_100px] gap-4">
            <Field label="Mínimo aceptable">
              {(p) => (
                <Input
                  {...p}
                  type="number"
                  min={0}
                  step={1000}
                  value={draft.salary_min ?? ""}
                  onChange={(e) =>
                    update(
                      "salary_min",
                      e.target.value ? Number(e.target.value) : null,
                    )
                  }
                  placeholder="50000"
                />
              )}
            </Field>
            <Field label="Aspiración">
              {(p) => (
                <Input
                  {...p}
                  type="number"
                  min={0}
                  step={1000}
                  value={draft.salary_max ?? ""}
                  onChange={(e) =>
                    update(
                      "salary_max",
                      e.target.value ? Number(e.target.value) : null,
                    )
                  }
                  placeholder="80000"
                />
              )}
            </Field>
            <Field label="Moneda">
              {(p) => (
                <Input
                  {...p}
                  value={draft.salary_currency ?? "EUR"}
                  onChange={(e) =>
                    update("salary_currency", e.target.value.toUpperCase().slice(0, 3))
                  }
                />
              )}
            </Field>
          </div>
        </Card>

        {/* Roles y stack */}
        <Card padding="lg">
          <SectionHeader icon={<Heart size={16} />} title="Roles y stack" />
          <div className="space-y-4">
            <Field label="Roles que te interesan" hint="Backend, Tech Lead, EM, …">
              {(p) => (
                <ChipInput
                  {...p}
                  value={draft.preferred_roles}
                  onChange={(v) => update("preferred_roles", v)}
                  placeholder="Senior Backend, Staff Engineer…"
                  tone="leaf"
                />
              )}
            </Field>
            <Field label="Roles que NO quieres" hint="Gestión pura, on-call 24/7, etc.">
              {(p) => (
                <ChipInput
                  {...p}
                  value={draft.discarded_roles}
                  onChange={(v) => update("discarded_roles", v)}
                  placeholder="Project Manager…"
                  tone="stone"
                />
              )}
            </Field>
            <Field label="Tecnologías / competencias que disfrutas">
              {(p) => (
                <ChipInput
                  {...p}
                  value={draft.preferred_competences}
                  onChange={(v) => update("preferred_competences", v)}
                  placeholder="Rust, FastAPI, sistemas distribuidos…"
                  tone="leaf"
                />
              )}
            </Field>
            <Field label="Tecnologías que prefieres evitar">
              {(p) => (
                <ChipInput
                  {...p}
                  value={draft.discarded_competences}
                  onChange={(v) => update("discarded_competences", v)}
                  placeholder="PHP legacy, COBOL…"
                  tone="stone"
                />
              )}
            </Field>
          </div>
        </Card>

        {/* Perks */}
        <Card padding="lg">
          <SectionHeader icon={<Coffee size={16} />} title="Perks y cultura" />
          <div className="grid md:grid-cols-2 gap-4">
            <Field label="Imprescindibles" hint="No firmarías sin esto">
              {(p) => (
                <ChipInput
                  {...p}
                  value={draft.perks_must_have}
                  onChange={(v) => update("perks_must_have", v)}
                  placeholder="Trabajo asíncrono, flexibilidad…"
                  tone="leaf"
                />
              )}
            </Field>
            <Field label="Bonito tenerlo" hint="Suma pero no te bloquea">
              {(p) => (
                <ChipInput
                  {...p}
                  value={draft.perks_nice_to_have}
                  onChange={(v) => update("perks_nice_to_have", v)}
                  placeholder="Conferencias, stock options…"
                  tone="sunbeam"
                />
              )}
            </Field>
          </div>
        </Card>

        {/* Motivations */}
        <Card padding="lg">
          <SectionHeader icon={<Heart size={16} />} title="Qué te motiva" />
          <Field label="En tus propias palabras (opcional)">
            {(p) => (
              <Textarea
                {...p}
                rows={4}
                value={draft.motivations ?? ""}
                onChange={(e) =>
                  update("motivations", e.target.value || null)
                }
                placeholder="Producto con impacto, equipo senior, autonomía técnica…"
              />
            )}
          </Field>
        </Card>
      </Stagger>

      {dirty && (
        <Reveal>
          <div className="sticky bottom-4 md:bottom-6 flex justify-center">
            <Card tone="glass" padding="sm" className="flex items-center gap-3 shadow-lift">
              <Badge tone="sunbeam" dot>
                Cambios sin guardar
              </Badge>
              <Button
                onClick={() => save.mutate()}
                loading={save.isPending}
                leadingIcon={<Save size={14} />}
                size="sm"
              >
                Guardar
              </Button>
            </Card>
          </div>
        </Reveal>
      )}
    </Surface>
  );
}

function SectionHeader({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <span
        aria-hidden
        className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-canvas text-ink"
      >
        {icon}
      </span>
      <h2 className="text-heading-sm font-medium tracking-tight">{title}</h2>
    </div>
  );
}

function ChipPicker({
  options,
  value,
  onChange,
}: {
  options: { value: string; label: string }[];
  value: string | null;
  onChange: (v: string | null) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((opt) => {
        const active = value === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(active ? null : opt.value)}
            aria-pressed={active}
            className={cn(
              "text-xs rounded-tag px-3 py-1.5 border transition-colors duration-180 ease-pirsch",
              active
                ? "bg-ink text-canvas border-ink"
                : "bg-canvas text-stone hover:text-ink border-ink/15 hover:border-ink/30",
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

function MultiChipPicker({
  options,
  value,
  onChange,
}: {
  options: { value: string; label: string }[];
  value: string[];
  onChange: (v: string[]) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((opt) => {
        const active = value.includes(opt.value);
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() =>
              onChange(
                active ? value.filter((v) => v !== opt.value) : [...value, opt.value],
              )
            }
            aria-pressed={active}
            className={cn(
              "text-xs rounded-tag px-3 py-1.5 border transition-colors duration-180 ease-pirsch",
              active
                ? "bg-ink text-canvas border-ink"
                : "bg-canvas text-stone hover:text-ink border-ink/15 hover:border-ink/30",
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
