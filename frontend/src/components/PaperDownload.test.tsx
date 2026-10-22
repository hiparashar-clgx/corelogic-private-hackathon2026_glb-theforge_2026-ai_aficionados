import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { exportPaperDocx, filenameFromDisposition, listConfidentialityFlags, resolveConfidentialityFlag } from "../api/client";
import PaperDownload from "./PaperDownload";

const state = vi.hoisted(() => ({
  download: {} as Record<string, unknown>,
  flags: [] as unknown[],
  mutations: [] as Array<{ mutationFn: (vars?: unknown) => Promise<unknown>; onSuccess?: (data: unknown) => void }>,
  queries: [] as Array<{ queryKey: string[]; enabled?: boolean; queryFn: () => unknown }>,
}));

vi.mock("../api/client", async (importOriginal) => ({
  ...await importOriginal<typeof import("../api/client")>(),
  exportPaperDocx: vi.fn().mockResolvedValue({ blob: new Blob(["x"]), filename: "paper.docx" }),
  listConfidentialityFlags: vi.fn(),
  resolveConfidentialityFlag: vi.fn(),
}));

vi.mock("@tanstack/react-query", () => ({
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
  useMutation: (options: (typeof state.mutations)[number]) => {
    state.mutations.push(options);
    const base = { isSuccess: false, isPending: false, isError: false, error: null, mutate: vi.fn() };
    return state.mutations.length === 1 ? { ...base, ...state.download } : base;
  },
  useQuery: (options: (typeof state.queries)[number]) => {
    state.queries.push(options);
    return { data: state.flags, isSuccess: true };
  },
}));

const conflict = {
  isAxiosError: true,
  response: { status: 409, data: { detail: "Resolve 1 open confidentiality flag(s) before downloading the paper." } },
};

describe("Paper download", () => {
  beforeEach(() => {
    state.download = {};
    state.flags = [];
    state.mutations = [];
    state.queries = [];
    vi.clearAllMocks();
  });

  it("offers a docx download that calls the export endpoint", async () => {
    const html = renderToStaticMarkup(<PaperDownload paperId="paper-1" />);
    expect(html).toContain("Download paper (.docx)");
    expect(html).toContain("numbered reference list");
    await state.mutations[0].mutationFn();
    expect(exportPaperDocx).toHaveBeenCalledWith("paper-1");
    expect(state.queries[0].enabled).toBe(false);
  });

  it("confirms the downloaded file name", () => {
    state.download = { isSuccess: true, data: { blob: new Blob(), filename: "My paper.docx" } };
    expect(renderToStaticMarkup(<PaperDownload paperId="paper-1" />)).toContain("Downloaded My paper.docx.");
  });

  it("lists open confidentiality flags with resolution actions when the export is blocked", async () => {
    state.download = { isError: true, error: conflict };
    state.flags = [
      { id: "f1", matched_text: "project falcon", flag_reason: "possible internal project codename", resolution: "open" },
      { id: "f2", matched_text: "already safe", flag_reason: "x", resolution: "confirmed_safe" },
    ];
    const html = renderToStaticMarkup(<PaperDownload paperId="paper-1" />);
    expect(html).toContain('role="alert"');
    expect(html).toContain("Resolve 1 open confidentiality flag(s)");
    expect(html).toContain("&quot;project falcon&quot;");
    expect(html).not.toContain("already safe");
    expect(html).toContain("Redact");
    expect(html).toContain("Confirm safe");
    expect(html).toContain("Try download again");
    expect(state.queries[0].enabled).toBe(true);
    await state.queries[0].queryFn();
    expect(listConfidentialityFlags).toHaveBeenCalledWith("paper-1");
    await state.mutations[1].mutationFn({ flagId: "f1", resolution: "confirmed_safe" });
    expect(resolveConfidentialityFlag).toHaveBeenCalledWith("f1", "confirmed_safe");
  });

  it("prompts a retry once every flag is resolved", () => {
    state.download = { isError: true, error: conflict };
    const html = renderToStaticMarkup(<PaperDownload paperId="paper-1" />);
    expect(html).toContain("All flagged items are resolved. Download the paper again.");
  });
});

describe("filenameFromDisposition", () => {
  it("prefers the UTF-8 filename and falls back to the plain one", () => {
    expect(filenameFromDisposition(`attachment; filename="Rsum.docx"; filename*=UTF-8''R%C3%A9sum%C3%A9.docx`)).toBe("Résumé.docx");
    expect(filenameFromDisposition('attachment; filename="plain.docx"')).toBe("plain.docx");
    expect(filenameFromDisposition(undefined)).toBeNull();
  });
});
