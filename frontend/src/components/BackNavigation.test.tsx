import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProblemFramingPage from "../pages/ProblemFramingPage";
import LiteratureSurveyPage from "../pages/LiteratureSurveyPage";
import DraftingPage from "../pages/DraftingPage";
import VerificationPage from "../pages/VerificationPage";
import StatusDashboardPage from "../pages/StatusDashboardPage";
import type { FormattingComplianceReport } from "../api/client";

const state = vi.hoisted(() => ({
  stage: "framing",
  originalityChecked: false,
  venue: "ieee",
  report: null as FormattingComplianceReport | null,
}));

vi.mock("react-router-dom", () => ({
  Link: ({ to, children }: { to: string; children: React.ReactNode }) => <a href={to}>{children}</a>,
  useParams: () => ({ paperId: "paper-1" }),
  useNavigate: () => vi.fn(),
}));

vi.mock("../WorkflowState", async (importOriginal) => {
  const original = await importOriginal<typeof import("../WorkflowState")>();
  return {
    ...original,
    useWorkflowState: (key: string, initial: unknown) => {
      return original.useWorkflowState(key, key.endsWith(":checked") && state.originalityChecked ? true : initial);
    },
  };
});

vi.mock("@tanstack/react-query", () => ({
  useQuery: ({ queryKey }: { queryKey: string[] }) => ({
    data: queryKey[0] === "paper" ? { current_stage: state.stage, target_venue: state.venue } :
      queryKey[0] === "formatting-report" ? state.report : [],
    isSuccess: true,
  }),
  useQueries: () => Array.from({ length: 7 }, () => ({ data: null })),
  useMutation: () => ({ mutate: vi.fn(), isPending: false }),
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}));

describe("Previous-step navigation", () => {
  beforeEach(() => {
    state.stage = "framing";
    state.originalityChecked = false;
    state.venue = "ieee";
    state.report = null;
  });

  it.each([
    [ProblemFramingPage, "/", "papers"],
    [LiteratureSurveyPage, "/papers/paper-1/framing", "problem framing"],
    [DraftingPage, "/papers/paper-1/literature", "literature survey"],
    [VerificationPage, "/papers/paper-1/drafting", "drafting"],
  ] as const)("renders a direct previous-step link on %s", (Page, path, label) => {
    const html = renderToStaticMarkup(<Page />);
    expect(html).toContain(`href="${path}"`);
    expect(html).toContain(`Back to ${label}`);
  });

  it.each([
    ["framing", "framing", "problem framing"],
    ["literature_survey", "framing", "problem framing"],
    ["drafting", "literature", "literature survey"],
    ["verification", "drafting", "drafting"],
    ["formatting", "verification", "citation &amp; originality"],
    ["ready_for_submission", "verification", "publisher formatting"],
  ])("uses the previous step on the %s status dashboard", (stage, route, label) => {
    state.stage = stage;
    const html = renderToStaticMarkup(<StatusDashboardPage />);
    expect(html).toContain(`href="/papers/paper-1/${route}"`);
    expect(html).toContain(`Back to ${label}`);
  });

  it("links publisher formatting back to the citation review on the same page", () => {
    state.originalityChecked = true;
    const html = renderToStaticMarkup(<VerificationPage />);
    expect(html).toContain('href="#citation-review"');
    expect(html).toContain('id="citation-review"');
  });

  it("reloads completed formatting and the selected venue from saved paper data", () => {
    state.stage = "ready_for_submission";
    state.venue = "acm";
    state.report = {
      id: "report-1", paper_id: "paper-1", venue: "acm", generated_at: "2026-10-15",
      checks: [{ requirement: "All sections", status: "pass", detail: null }],
    };
    const html = renderToStaticMarkup(<VerificationPage />);
    expect(html).toContain('<option value="acm" selected="">');
    expect(html).toContain("Formatting applied for ACM");
    expect(html).toContain("Ready for submission.");
    expect(html).toContain("Download paper (.docx)");
    expect(html).not.toContain(">Mark ready for submission<");
  });
});
