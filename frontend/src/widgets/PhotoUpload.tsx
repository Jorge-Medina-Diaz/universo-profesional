import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { photo } from "@/shared/api-extra";

export function PhotoUpload() {
  const qc = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const upload = useMutation({
    mutationFn: (f: File) => photo.upload(f),
    onSuccess: () => {
      setPreview(null);
      setRefreshKey((k) => k + 1);
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });

  const remove = useMutation({
    mutationFn: () => photo.remove(),
    onSuccess: () => {
      setRefreshKey((k) => k + 1);
      qc.invalidateQueries({ queryKey: ["me"] });
    },
  });

  const onSelect = (f: File | null) => {
    if (!f) return;
    const url = URL.createObjectURL(f);
    setPreview(url);
    upload.mutate(f);
  };

  const src = preview ?? `${photo.url()}?v=${refreshKey}`;

  return (
    <div className="flex items-center gap-4">
      <div className="relative">
        <img
          src={src}
          alt="Profile photo"
          className="h-24 w-24 rounded-full object-cover border border-gray-200 bg-gray-100"
          onError={(e) => {
            (e.target as HTMLImageElement).src =
              "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23bbb'><circle cx='12' cy='8' r='4'/><path d='M4 21c0-4 4-7 8-7s8 3 8 7'/></svg>";
          }}
        />
      </div>
      <div className="flex flex-col gap-2">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="btn-primary"
          disabled={upload.isPending}
        >
          {upload.isPending ? "Subiendo…" : "Cambiar foto"}
        </button>
        <button
          type="button"
          onClick={() => remove.mutate()}
          className="btn-secondary text-xs"
          disabled={remove.isPending}
        >
          Eliminar
        </button>
        <p className="text-xs text-gray-500">JPG, PNG o WebP. Max 5 MB.</p>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={(e) => onSelect(e.target.files?.[0] ?? null)}
        />
      </div>
    </div>
  );
}
