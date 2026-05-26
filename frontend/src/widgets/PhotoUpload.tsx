import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Trash2, Upload, User } from "lucide-react";
import { photo } from "@/shared/api-extra";
import { Button, DropZone, toast } from "@/ui";
import { PhotoCropper } from "./PhotoCropper";
import { queryKeys } from "@/shared/queryKeys";

export function PhotoUpload() {
  const qc = useQueryClient();
  const [preview, setPreview] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [cropping, setCropping] = useState<File | null>(null);

  // Authenticated avatar load (a plain <img> can't send the Bearer header).
  const photoQuery = useQuery({
    queryKey: queryKeys.me.photo(refreshKey),
    queryFn: () => photo.load(),
    staleTime: 60_000,
    retry: false,
  });

  // Revoke the previous object URL when it changes / on unmount.
  useEffect(() => {
    const url = photoQuery.data;
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [photoQuery.data]);

  const upload = useMutation({
    mutationFn: (f: File) => photo.upload(f),
    onSuccess: () => {
      setPreview(null);
      setRefreshKey((k) => k + 1);
      qc.invalidateQueries({ queryKey: queryKeys.me.all });
      toast.success("Foto actualizada");
    },
    onError: (e: unknown) =>
      toast.error("No pudimos subir la foto", (e as Error).message),
  });

  const remove = useMutation({
    mutationFn: () => photo.remove(),
    onSuccess: () => {
      setRefreshKey((k) => k + 1);
      qc.invalidateQueries({ queryKey: queryKeys.me.all });
    },
  });

  const onFiles = (files: File[]) => {
    const f = files[0];
    if (!f) return;
    // Open the cropper instead of uploading directly.
    setCropping(f);
  };

  const onCropped = (blob: Blob) => {
    if (!cropping) return;
    const cropped = new File([blob], cropping.name.replace(/\.[^.]+$/, "") + ".jpg", {
      type: "image/jpeg",
      lastModified: Date.now(),
    });
    const url = URL.createObjectURL(cropped);
    setPreview(url);
    setCropping(null);
    upload.mutate(cropped);
  };

  const src = preview ?? photoQuery.data ?? null;

  return (
    <>
      <div className="flex flex-col sm:flex-row items-start gap-4">
        <div className="relative shrink-0">
          {src ? (
            <img
              src={src}
              alt="Foto de perfil"
              className="h-24 w-24 rounded-full object-cover border border-hairline bg-surface"
            />
          ) : (
            <div
              className="h-24 w-24 rounded-full grid place-items-center border border-hairline bg-surface text-stone"
              aria-label="Sin foto de perfil"
            >
              <User size={32} />
            </div>
          )}
        </div>
        <div className="flex-1 w-full max-w-md space-y-2">
          <DropZone
            accept="image/jpeg,image/png,image/webp"
            label={
              <span className="inline-flex items-center gap-1.5">
                <Upload size={12} />
                {upload.isPending ? "Subiendo…" : "Arrastra una imagen o haz clic"}
              </span>
            }
            hint="JPG, PNG o WebP. Hasta 8 MB. La recortarás antes de subirla."
            loading={upload.isPending}
            maxBytes={8 * 1024 * 1024}
            onFiles={onFiles}
            onError={(msg) => toast.error("Imagen no aceptada", msg)}
            variant="card"
            className="py-5"
          />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => remove.mutate()}
            loading={remove.isPending}
            leadingIcon={<Trash2 size={12} />}
          >
            Eliminar foto
          </Button>
        </div>
      </div>
      {cropping && (
        <PhotoCropper
          file={cropping}
          onCancel={() => setCropping(null)}
          onCrop={onCropped}
        />
      )}
    </>
  );
}
