import { beforeEach, describe, expect, it, vi } from "vitest";
import { useWorkflowState } from "./WorkflowState";

const state = vi.hoisted(() => ({ store: new Map<string, unknown>() }));

vi.mock("react", async (importOriginal) => ({
  ...await importOriginal<typeof import("react")>(),
  useContext: () => state.store,
  useState: (initial: () => unknown) => [initial(), vi.fn()],
  useRef: (initial: unknown) => ({ current: initial }),
  useCallback: (callback: unknown) => callback,
}));

describe("Per-paper workflow state", () => {
  beforeEach(() => state.store.clear());

  it("restores a selection when the page mounts again", () => {
    const [, select] = useWorkflowState("paper-1:drafting:section", "introduction");
    select("methods");
    expect(useWorkflowState("paper-1:drafting:section", "introduction")[0]).toBe("methods");
  });

  it("retains sequential functional edits", () => {
    const [, edit] = useWorkflowState<Record<string, string>>("paper-1:drafting:notes", {});
    edit((previous) => ({ ...previous, methods: "Method notes" }));
    edit((previous) => ({ ...previous, results: "Result notes" }));
    expect(useWorkflowState("paper-1:drafting:notes", {})[0]).toEqual({
      methods: "Method notes", results: "Result notes",
    });
  });

  it("isolates papers and fields", () => {
    const [, edit] = useWorkflowState("paper-1:literature:query", "");
    edit("vehicle features");
    expect(useWorkflowState("paper-2:literature:query", "")[0]).toBe("");
    expect(useWorkflowState("paper-1:literature:yearRange", "")[0]).toBe("");
  });

  it("preserves framing options, selection, and questions together", () => {
    useWorkflowState<string[]>("paper-1:framing:statements", [])[1](["First", "Second"]);
    useWorkflowState<number | null>("paper-1:framing:selection", null)[1](1);
    useWorkflowState<string[]>("paper-1:framing:questions", [])[1](["Why?"]);
    expect(useWorkflowState("paper-1:framing:statements", [])[0]).toEqual(["First", "Second"]);
    expect(useWorkflowState("paper-1:framing:selection", null)[0]).toBe(1);
    expect(useWorkflowState("paper-1:framing:questions", [])[0]).toEqual(["Why?"]);
  });

  it("retains explicit false, empty, and null values rather than using defaults", () => {
    useWorkflowState("checked", true)[1](false);
    useWorkflowState("query", "default")[1]("");
    useWorkflowState<string | null>("report", "old")[1](null);
    expect(useWorkflowState("checked", true)[0]).toBe(false);
    expect(useWorkflowState("query", "default")[0]).toBe("");
    expect(useWorkflowState("report", "old")[0]).toBeNull();
  });

  it("records updates immediately, including results arriving after leaving the page", () => {
    const [, complete] = useWorkflowState("paper-1:verification:checked", false);
    complete(true);
    expect(state.store.get("paper-1:verification:checked")).toBe(true);
  });
});
