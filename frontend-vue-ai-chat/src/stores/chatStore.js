// Chat store singleton wrapper.
// Reuse the existing, battle-tested composable implementation and expose it
// as a module-level singleton so all route pages share one reactive state.
import { useChatFeature } from '../composables/useChatFeature'

const chatStoreSingleton = useChatFeature()

export function useChatStore() {
  return chatStoreSingleton
}
