/**
 * Square photo cropper. Opens as a modal when the user picks an image,
 * lets them pan + zoom with mouse / touch / wheel / pinch, then renders
 * the cropped square to a 512x512 JPEG blob ready to upload.
 *
 * No external deps. Everything is plain canvas + transforms.
 */
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type WheelEvent as ReactWheelEvent,
} from "react";
import { AnimatePresence, motion } from "motion/react";
import { Crop, RotateCw, ZoomIn, ZoomOut, X } from "lucide-react";
import { Button, cn } from "@/ui";

const OUTPUT_SIZE = 512;
const BOX_SIZE = 320; // displayed crop area in px

interface PhotoCropperProps {
  file: File;
  onCancel: () => void;
  onCrop: (blob: Blob) => void;
}

interface ImgState {
  bitmap: ImageBitmap | null;
  width: number;
  height: number;
}

export function PhotoCropper({ file, onCancel, onCrop }: PhotoCropperProps) {
  const [img, setImg] = useState<ImgState>({ bitmap: null, width: 0, height: 0 });
  const [scale, setScale] = useState(1); // multiplier over base "cover" scale
  const [tx, setTx] = useState(0); // translation in canvas px
  const [ty, setTy] = useState(0);
  const [rotation, setRotation] = useState(0); // degrees, 0/90/180/270
  const [busy, setBusy] = useState(false);
  const dragRef = useRef<{ x: number; y: number } | null>(null);
  const pinchRef = useRef<{
    pointers: Map<number, { x: number; y: number }>;
    initialDist: number | null;
    initialScale: number;
  }>({ pointers: new Map(), initialDist: null, initialScale: 1 });

  // Load image
  useEffect(() => {
    let cancelled = false;
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = async () => {
      if (cancelled) return;
      // createImageBitmap honours EXIF orientation in modern browsers.
      try {
        const bm = await createImageBitmap(image, { imageOrientation: "from-image" });
        if (cancelled) {
          bm.close();
          return;
        }
        setImg({ bitmap: bm, width: bm.width, height: bm.height });
      } catch {
        // Fallback: use the HTMLImageElement; no EXIF correction.
        const bm = await createImageBitmap(image).catch(() => null);
        if (cancelled) return;
        if (bm) {
          setImg({ bitmap: bm, width: bm.width, height: bm.height });
        } else {
          setImg({ bitmap: null, width: image.naturalWidth, height: image.naturalHeight });
        }
      }
    };
    image.onerror = () => {
      if (!cancelled) onCancel();
    };
    image.src = url;
    return () => {
      cancelled = true;
      URL.revokeObjectURL(url);
    };
  }, [file, onCancel]);

  // Effective dimensions taking rotation into account.
  const effective = useMemo(() => {
    if (!img.width || !img.height) return { w: 0, h: 0 };
    const rotated = rotation === 90 || rotation === 270;
    return rotated
      ? { w: img.height, h: img.width }
      : { w: img.width, h: img.height };
  }, [img, rotation]);

  // Base scale: "cover" — image fills the box at scale=1.
  const baseScale = useMemo(() => {
    if (!effective.w || !effective.h) return 1;
    return Math.max(BOX_SIZE / effective.w, BOX_SIZE / effective.h);
  }, [effective]);

  // Clamp translation so the image always covers the crop box.
  const clamp = useCallback(
    (nextTx: number, nextTy: number, nextScale: number) => {
      const s = baseScale * nextScale;
      const dispW = effective.w * s;
      const dispH = effective.h * s;
      const maxX = Math.max(0, (dispW - BOX_SIZE) / 2);
      const maxY = Math.max(0, (dispH - BOX_SIZE) / 2);
      return {
        tx: Math.max(-maxX, Math.min(maxX, nextTx)),
        ty: Math.max(-maxY, Math.min(maxY, nextTy)),
      };
    },
    [baseScale, effective.w, effective.h],
  );

  // Re-clamp when scale / rotation changes
  useEffect(() => {
    const { tx: nx, ty: ny } = clamp(tx, ty, scale);
    if (nx !== tx || ny !== ty) {
      setTx(nx);
      setTy(ny);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scale, rotation, baseScale]);

  const onPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    (e.target as Element).setPointerCapture?.(e.pointerId);
    pinchRef.current.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pinchRef.current.pointers.size === 2) {
      const [p1, p2] = Array.from(pinchRef.current.pointers.values());
      pinchRef.current.initialDist = Math.hypot(p2.x - p1.x, p2.y - p1.y);
      pinchRef.current.initialScale = scale;
      dragRef.current = null;
    } else if (pinchRef.current.pointers.size === 1) {
      dragRef.current = { x: e.clientX, y: e.clientY };
    }
  };

  const onPointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (!pinchRef.current.pointers.has(e.pointerId)) return;
    pinchRef.current.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

    if (
      pinchRef.current.pointers.size === 2 &&
      pinchRef.current.initialDist != null
    ) {
      const [p1, p2] = Array.from(pinchRef.current.pointers.values());
      const dist = Math.hypot(p2.x - p1.x, p2.y - p1.y);
      const ratio = dist / pinchRef.current.initialDist;
      const next = Math.max(1, Math.min(4, pinchRef.current.initialScale * ratio));
      setScale(next);
      return;
    }

    if (pinchRef.current.pointers.size === 1 && dragRef.current) {
      const dx = e.clientX - dragRef.current.x;
      const dy = e.clientY - dragRef.current.y;
      dragRef.current = { x: e.clientX, y: e.clientY };
      const { tx: nx, ty: ny } = clamp(tx + dx, ty + dy, scale);
      setTx(nx);
      setTy(ny);
    }
  };

  const onPointerUp = (e: ReactPointerEvent<HTMLDivElement>) => {
    pinchRef.current.pointers.delete(e.pointerId);
    if (pinchRef.current.pointers.size < 2) pinchRef.current.initialDist = null;
    if (pinchRef.current.pointers.size === 0) dragRef.current = null;
  };

  const onWheel = (e: ReactWheelEvent<HTMLDivElement>) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.08 : 0.08;
    setScale((s) => Math.max(1, Math.min(4, s + delta)));
  };

  const onCropClick = async () => {
    if (!img.bitmap) return;
    setBusy(true);
    try {
      const canvas = document.createElement("canvas");
      canvas.width = OUTPUT_SIZE;
      canvas.height = OUTPUT_SIZE;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Canvas no soportado");

      const s = baseScale * scale;
      // Mapping: the image is drawn centred at (BOX_SIZE/2 + tx, BOX_SIZE/2 + ty)
      // at scale `s`, then rotated by `rotation` deg around that centre.
      // We want to capture the BOX_SIZE×BOX_SIZE square at origin and rescale
      // to OUTPUT_SIZE.
      const ratio = OUTPUT_SIZE / BOX_SIZE;
      ctx.fillStyle = "#fff";
      ctx.fillRect(0, 0, OUTPUT_SIZE, OUTPUT_SIZE);
      ctx.save();
      ctx.translate(OUTPUT_SIZE / 2 + tx * ratio, OUTPUT_SIZE / 2 + ty * ratio);
      ctx.rotate((rotation * Math.PI) / 180);
      ctx.scale(s * ratio, s * ratio);
      ctx.drawImage(img.bitmap, -img.width / 2, -img.height / 2);
      ctx.restore();

      const blob = await new Promise<Blob | null>((resolve) =>
        canvas.toBlob((b) => resolve(b), "image/jpeg", 0.9),
      );
      if (!blob) throw new Error("No se pudo generar la imagen");
      onCrop(blob);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        role="dialog"
        aria-modal="true"
        aria-label="Recortar foto"
        className="fixed inset-0 z-[60] flex items-center justify-center p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        <motion.button
          type="button"
          aria-label="Cerrar"
          onClick={onCancel}
          className="absolute inset-0 bg-ink/35 backdrop-blur-sm cursor-default"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        />
        <motion.div
          initial={{ opacity: 0, y: 8, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
          className="relative w-full max-w-md rounded-card bg-canvas shadow-lift border border-ink/8 overflow-hidden"
        >
          <header className="flex items-start justify-between gap-3 px-5 py-4 border-b border-ink/5">
            <div className="flex items-start gap-3">
              <span
                aria-hidden
                className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-leaf-soft text-leaf-ink"
              >
                <Crop size={16} />
              </span>
              <div>
                <h2 className="text-heading-sm font-medium tracking-tight">
                  Ajusta tu foto
                </h2>
                <p className="text-xs text-stone mt-0.5">
                  Arrastra para mover, rueda o pellizca para acercar.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onCancel}
              aria-label="Cerrar"
              className="w-8 h-8 inline-flex items-center justify-center rounded-full text-stone hover:text-ink hover:bg-black/[0.04] transition-colors"
            >
              <X size={14} />
            </button>
          </header>

          <div className="p-5 flex flex-col items-center gap-4">
            <div
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
              onPointerCancel={onPointerUp}
              onWheel={onWheel}
              style={{
                width: BOX_SIZE,
                height: BOX_SIZE,
                touchAction: "none",
              }}
              className={cn(
                "relative rounded-full overflow-hidden bg-surface select-none",
                "ring-2 ring-leaf-soft",
              )}
            >
              {img.bitmap ? (
                <CanvasPreview
                  bitmap={img.bitmap}
                  width={img.width}
                  height={img.height}
                  scale={baseScale * scale}
                  rotation={rotation}
                  tx={tx}
                  ty={ty}
                />
              ) : (
                <div className="absolute inset-0 flex items-center justify-center text-stone text-sm">
                  Cargando…
                </div>
              )}
            </div>

            <div className="flex items-center gap-3 w-full">
              <button
                type="button"
                aria-label="Reducir"
                onClick={() => setScale((s) => Math.max(1, s - 0.1))}
                className="w-9 h-9 inline-flex items-center justify-center rounded-full bg-surface text-ink hover:bg-black/[0.06] transition-colors"
              >
                <ZoomOut size={14} />
              </button>
              <input
                type="range"
                min={1}
                max={4}
                step={0.01}
                value={scale}
                onChange={(e) => setScale(Number(e.target.value))}
                className="flex-1 accent-leaf"
                aria-label="Zoom"
              />
              <button
                type="button"
                aria-label="Aumentar"
                onClick={() => setScale((s) => Math.min(4, s + 0.1))}
                className="w-9 h-9 inline-flex items-center justify-center rounded-full bg-surface text-ink hover:bg-black/[0.06] transition-colors"
              >
                <ZoomIn size={14} />
              </button>
              <button
                type="button"
                aria-label="Rotar 90°"
                onClick={() => setRotation((r) => (r + 90) % 360)}
                className="w-9 h-9 inline-flex items-center justify-center rounded-full bg-surface text-ink hover:bg-black/[0.06] transition-colors"
              >
                <RotateCw size={14} />
              </button>
            </div>
          </div>

          <footer className="flex items-center justify-end gap-2 px-5 py-3 bg-surface/40 border-t border-ink/5">
            <Button variant="ghost" size="sm" onClick={onCancel}>
              Cancelar
            </Button>
            <Button
              size="sm"
              onClick={onCropClick}
              loading={busy}
              disabled={!img.bitmap}
              leadingIcon={<Crop size={12} />}
            >
              Recortar y subir
            </Button>
          </footer>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

/** Canvas that re-renders the cropped preview whenever transforms change. */
function CanvasPreview({
  bitmap,
  width,
  height,
  scale,
  rotation,
  tx,
  ty,
}: {
  bitmap: ImageBitmap;
  width: number;
  height: number;
  scale: number;
  rotation: number;
  tx: number;
  ty: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = BOX_SIZE * dpr;
    canvas.height = BOX_SIZE * dpr;
    canvas.style.width = `${BOX_SIZE}px`;
    canvas.style.height = `${BOX_SIZE}px`;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, BOX_SIZE, BOX_SIZE);
    ctx.fillStyle = "#f8f5ed";
    ctx.fillRect(0, 0, BOX_SIZE, BOX_SIZE);
    ctx.save();
    ctx.translate(BOX_SIZE / 2 + tx, BOX_SIZE / 2 + ty);
    ctx.rotate((rotation * Math.PI) / 180);
    ctx.scale(scale, scale);
    ctx.drawImage(bitmap, -width / 2, -height / 2);
    ctx.restore();
  }, [bitmap, width, height, scale, rotation, tx, ty]);

  return <canvas ref={ref} className="block" aria-hidden />;
}
