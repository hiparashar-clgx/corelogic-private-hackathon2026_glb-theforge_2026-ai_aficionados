import { createContext, useCallback, useContext, useRef, useState, type ReactNode, type SetStateAction } from "react";

const WorkflowStateContext = createContext<Map<string, unknown> | null>(null);

export function WorkflowStateProvider({ children }: { children: ReactNode }) {
  const store = useRef(new Map<string, unknown>());
  return <WorkflowStateContext.Provider value={store.current}>{children}</WorkflowStateContext.Provider>;
}

export function useWorkflowState<T>(key: string, initial: T) {
  const store = useContext(WorkflowStateContext);
  const [value, setValue] = useState<T>(() => store?.has(key) ? store.get(key) as T : initial);
  const current = useRef(value);
  const updateValue = useCallback((update: SetStateAction<T>) => {
    const next = typeof update === "function" ? (update as (previous: T) => T)(current.current) : update;
    current.current = next;
    store?.set(key, next);
    setValue(next);
  }, [store, key]);
  return [value, updateValue] as const;
}
