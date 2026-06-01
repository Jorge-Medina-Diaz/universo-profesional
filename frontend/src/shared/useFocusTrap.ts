import { useEffect, type RefObject } from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Trap keyboard focus within `ref` while `active`: move focus in on open, cycle
 * Tab/Shift+Tab inside, pull focus back if it escapes, optionally lock body
 * scroll, and restore focus to the previously-focused element on close.
 *
 * Lifts the hand-rolled trap that lived only in InlineEntityEditor so every
 * modal surface (Dialog, CommandPalette) gets consistent keyboard/screen-reader
 * behaviour — previously these declared aria-modal but never trapped focus, so
 * keyboard users tabbed straight into the page behind the modal.
 */
export function useFocusTrap(
  ref: RefObject<HTMLElement | null>,
  active: boolean,
  opts: { lockScroll?: boolean } = {},
): void {
  const { lockScroll = true } = opts;
  useEffect(() => {
    if (!active) return;
    const node = ref.current;
    if (!node) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;

    // Move focus into the modal (first focusable, else the container itself).
    const focusables0 = node.querySelectorAll<HTMLElement>(FOCUSABLE);
    if (focusables0.length > 0) focusables0[0].focus();
    else node.focus();

    const prevOverflow = lockScroll ? document.body.style.overflow : "";
    if (lockScroll) document.body.style.overflow = "hidden";

    const handler = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;
      const focusables = Array.from(
        node.querySelectorAll<HTMLElement>(FOCUSABLE),
      ).filter((el) => el.offsetParent !== null || el === document.activeElement);
      if (focusables.length === 0) {
        e.preventDefault();
        return;
      }
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const activeEl = document.activeElement;
      if (e.shiftKey && activeEl === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && activeEl === last) {
        e.preventDefault();
        first.focus();
      } else if (activeEl && !node.contains(activeEl)) {
        // Focus escaped the modal (e.g. after a click) — pull it back.
        e.preventDefault();
        first.focus();
      }
    };
    node.addEventListener("keydown", handler);

    return () => {
      node.removeEventListener("keydown", handler);
      if (lockScroll) document.body.style.overflow = prevOverflow;
      previouslyFocused?.focus?.();
    };
  }, [ref, active, lockScroll]);
}
