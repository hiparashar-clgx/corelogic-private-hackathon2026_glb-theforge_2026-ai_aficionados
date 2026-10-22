import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { advancePaper, getFormattingReport, type FormattingComplianceReport } from "../api/client";
import StatusDashboardPage from "../pages/StatusDashboardPage";
import FormattingReview from "./FormattingReview";

const state = vi.hoisted(() => ({
  stage: "formatting",
  success: false,
  pending: false,
  error: null as unknown,
  reportError: false,
  reportLoading: false,
  report: undefined as FormattingComplianceReport | undefined,
  invalidateQueries: vi.fn(),
  options: undefined as undefined | { mutationFn: () => Promise<unknown>; onSuccess: () => void },
  queries: [] as Array<{ queryKey: string[]; enabled?: boolean; queryFn: () => unknown }>,
}));

vi.mock("../api/client", async (importOriginal) => ({
  ...await importOriginal<typeof import("../api/client")>(),
  advancePaper: vi.fn().mockResolvedValue({ current_stage: "ready_for_submission" }),
  getFormattingReport: vi.fn(),
}));

vi.mock("@tanstack/react-query", () => ({
  useQueryClient: () => ({ invalidateQueries: state.invalidateQueries }),
  useMutation: (options: typeof state.options) => {
    // Only the first mutation (readiness) follows the test state; nested ones (download) stay idle.
    const first = state.options === undefined;
    state.options ??= options;
    if (!first) {
      return { isSuccess: false, isPending: false, isError: false, error: null, mutate: vi.fn() };
    }
    return {
      isSuccess: state.success,
      isPending: state.pending,
      isError: !!state.error,
      error: state.error,
      mutate: vi.fn(),
    };
  },
  useQuery: (options: { queryKey: string[]; enabled?: boolean; queryFn: () => unknown }) => {
    state.queries.push(options);
    if (options.queryKey[0] === "paper") return { data: { current_stage: state.stage } };
    if (options.queryKey[0] === "status") return { data: [] };
    if (options.queryKey[0] === "flags") return { data: [], isSuccess: true };
    return {
      data: state.report,
      isError: state.reportError,
      isLoading: state.reportLoading,
      refetch: vi.fn(),
    };
  },
}));

vi.mock("react-router-dom", () => ({
  Link: ({ to, children }: { to: string; children: React.ReactNode }) => <a href={to}>{children}</a>,
  useParams: () => ({ paperId: "paper-1" }),
  useNavigate: () => vi.fn(),
}));

const report: FormattingComplianceReport = {
  id: "report-1",
  paper_id: "paper-1",
  venue: "ieee",
  generated_at: "2026-10-14T12:00:00Z",
  checks: [{ requirement: "Abstract present", status: "pass", detail: null }],
};

describe("Post-formatting next steps", () => {
  beforeEach(() => {
    state.stage = "formatting";
    state.success = false;
    state.pending = false;
    state.error = null;
    state.reportError = false;
    state.reportLoading = false;
    state.report = report;
    state.queries = [];
    state.options = undefined;
    vi.clearAllMocks();
  });

  it("offers readiness and revision actions after passing compliance", async () => {
    const html = renderToStaticMarkup(<FormattingReview paperId="paper-1" report={report} />);
    expect(html).toContain("Mark ready for submission");
    expect(html).not.toMatch(/<button[^>]*disabled=""[^>]*>Mark ready for submission/);
    expect(html).toContain("Return to drafting");
    expect(html).toContain("Review citations &amp; reapply formatting");
    expect(html).toContain("View paper status");
    await state.options!.mutationFn();
    expect(advancePaper).toHaveBeenCalledWith("paper-1", "ready_for_submission");
    state.options!.onSuccess();
    expect(state.invalidateQueries).toHaveBeenCalledWith({ queryKey: ["paper", "paper-1"] });
    expect(state.invalidateQueries).toHaveBeenCalledWith({ queryKey: ["status", "paper-1"] });
  });

  it.each(["fail", "missing"] as const)("blocks readiness for %s compliance checks", (status) => {
    const result = {
      ...report,
      checks: status === "missing" ? [] : [{ ...report.checks[0], status }],
    };
    const html = renderToStaticMarkup(<FormattingReview paperId="paper-1" report={result} />);
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Mark ready for submission/);
    expect(html).toContain("then apply formatting again");
  });

  it("disables duplicate advances while saving", () => {
    state.pending = true;
    const html = renderToStaticMarkup(<FormattingReview paperId="paper-1" report={report} />);
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Updating readiness/);
  });

  it("shows backend errors without reporting readiness", () => {
    state.error = {
      isAxiosError: true,
      response: { data: { detail: "1 originality finding(s) are unresolved." } },
    };
    const html = renderToStaticMarkup(<FormattingReview paperId="paper-1" report={report} />);
    expect(html).toContain('role="alert"');
    expect(html).toContain("1 originality finding(s) are unresolved.");
    expect(html).not.toContain("Ready for submission.");
  });

  it("confirms readiness after advancement without claiming submission", () => {
    state.success = true;
    const html = renderToStaticMarkup(<FormattingReview paperId="paper-1" report={report} />);
    expect(html).toContain("Ready for submission.");
    expect(html).toContain("it does not submit it to a publisher");
    expect(html).not.toContain("Mark ready for submission");
    expect(html).toContain("Download paper (.docx)");
  });

  it("does not offer the download before the paper is ready", () => {
    const html = renderToStaticMarkup(<FormattingReview paperId="paper-1" report={report} />);
    expect(html).not.toContain("Download paper (.docx)");
  });

  it("restores the saved formatting review on the status dashboard", async () => {
    const html = renderToStaticMarkup(<StatusDashboardPage />);
    expect(html).toContain("Formatting applied for IEEE");
    expect(html).toContain("Mark ready for submission");
    expect(html).not.toContain("View paper status");
    const query = state.queries.find((q) => q.queryKey[0] === "formatting-report")!;
    expect(query.enabled).toBe(true);
    await query.queryFn();
    expect(getFormattingReport).toHaveBeenCalledWith("paper-1");
  });

  it("preserves the completed state after reloading a ready paper", () => {
    state.stage = "ready_for_submission";
    const html = renderToStaticMarkup(<StatusDashboardPage />);
    expect(html).toContain("Ready for submission.");
    expect(html).not.toContain("Mark ready for submission");
    expect(html).toContain("Download paper (.docx)");
  });

  it("offers recovery when the persisted report cannot be loaded", () => {
    state.report = undefined;
    state.reportError = true;
    const html = renderToStaticMarkup(<StatusDashboardPage />);
    expect(html).toContain("Could not load the saved formatting report.");
    expect(html).toContain("Retry loading report");
    expect(html).toContain("Continue to publisher formatting");
    expect(html).not.toContain("Mark ready for submission");
  });

  it("does not request formatting reports for an earlier stage", () => {
    state.stage = "verification";
    const html = renderToStaticMarkup(<StatusDashboardPage />);
    expect(html).not.toContain("Mark ready for submission");
    expect(state.queries.find((q) => q.queryKey[0] === "formatting-report")!.enabled).toBe(false);
  });
});
