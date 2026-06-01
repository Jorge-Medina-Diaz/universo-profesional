/**
 * HomePage = the authenticated landing surface (route "/").
 *
 * The home IS the universe: it renders the shared {@link UniverseSurface} in
 * "ambient" mode (living constellation backdrop + hero + floating agent chat).
 * The interactive workspace is the same surface in "workspace" mode (/universe).
 */
import { UniverseSurface } from "./_universe/UniverseSurface";

export function HomePage() {
  return <UniverseSurface mode="ambient" />;
}
