// OJ store singleton wrapper.
// Reuse existing composable implementation and expose it as a module-level
// singleton so all route pages share one reactive state.
import { useOjAuthAndProblems } from '../composables/useOjAuthAndProblems'

const ojStoreSingleton = useOjAuthAndProblems()

export function useOjStore() {
  return ojStoreSingleton
}
