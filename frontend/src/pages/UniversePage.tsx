/**
 * UniversePage = the interactive universe surface (route "/universe").
 *
 * A thin wrapper over the shared {@link UniverseSurface} in "workspace" mode —
 * graph/outline/trajectory lenses (agent-driven), a controls rail, node
 * inspector, and the shared agent chat. The "/" home is the same surface in
 * "ambient" mode (see HomePage), so the two routes share one implementation.
 */
import { UniverseSurface } from "./_universe/UniverseSurface";

export function UniversePage() {
  return <UniverseSurface mode="workspace" />;
}
