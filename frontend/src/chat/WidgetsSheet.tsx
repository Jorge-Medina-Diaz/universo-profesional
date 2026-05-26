import { Drawer } from "vaul";
import { WidgetPane } from "./WidgetPane";

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

/**
 * Mobile widgets bottom-sheet (vaul). Extracted into its own module so
 * HomePage can lazy-load it — vaul is 66 KB and not needed on first paint.
 */
export function WidgetsSheet({ open, onOpenChange }: Props) {
  return (
    <Drawer.Root open={open} onOpenChange={onOpenChange}>
      <Drawer.Portal>
        <Drawer.Overlay className="fixed inset-0 bg-ink/30 backdrop-blur-sm z-40" />
        <Drawer.Content className="bg-canvas text-ink flex flex-col fixed bottom-0 left-0 right-0 z-50 h-[85vh] rounded-t-card shadow-lift">
          <Drawer.Title className="sr-only">Widgets</Drawer.Title>
          <div className="mx-auto mt-2 h-1 w-10 rounded-full bg-ink/15" aria-hidden />
          <div className="flex-1 min-h-0">
            <WidgetPane compact />
          </div>
        </Drawer.Content>
      </Drawer.Portal>
    </Drawer.Root>
  );
}
