import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import LiteratureSurveyPage from "./LiteratureSurveyPage";

const state = vi.hoisted(() => ({
  sources: [] as Array<Record<string, unknown>>,
  isSuccess: false,
  isPending: false,
  queryError: false,
  isFetching: false,
  invalidateQueries: vi.fn(),
  mutationOptions: [] as Array<{ onSuccess?: () => Promise<void> }>,
}));

vi.mock("@tanstack/react-query", () => ({
  useQuery: ({ queryKey }: { queryKey: string[] }) => ({
    data: queryKey[0] === "literature-sources" ? state.sources : [],
    isSuccess: !state.queryError,
    isError: state.queryError,
    isFetching: state.isFetching,
    refetch: vi.fn(),
  }),
  useQueryClient: () => ({ invalidateQueries: state.invalidateQueries }),
  useMutation: (options: { onSuccess?: () => Promise<void> }) => {
    state.mutationOptions.push(options);
    return {
      isSuccess: state.isSuccess,
      isPending: state.isPending,
      mutate: vi.fn(),
    };
  },
}));

vi.mock("react-router-dom", () => ({
  Link: ({ to, children }: { to: string; children: React.ReactNode }) => <a href={to}>{children}</a>,
  useParams: () => ({ paperId: "paper-1" }),
  useNavigate: () => vi.fn(),
}));

describe("Literature survey results", () => {
  beforeEach(() => {
    state.sources = [];
    state.isSuccess = false;
    state.isPending = false;
    state.queryError = false;
    state.isFetching = false;
    state.mutationOptions = [];
    state.invalidateQueries.mockClear();
  });

  it("explains an empty search without offering to accept nonexistent sources", () => {
    state.isSuccess = true;

    const html = renderToStaticMarkup(<LiteratureSurveyPage />);

    expect(html).toContain("No relevant sources found");
    expect(html).not.toContain("Accept selected sources and continue");
    expect(html).toContain('href="/papers/paper-1/framing"');
    expect(html).toContain("Back to problem framing");
  });

  it("displays verified sources and allows accepting them", () => {
    state.isSuccess = true;
    state.sources = [{
      id: "source-1",
      title: "Property valuation accuracy",
      authors: ["Research Author"],
      year: 2024,
      relevance_summary: "Compares valuation models.",
      doi_or_url: "https://doi.org/10/example",
      verification_status: "verified",
    }];

    const html = renderToStaticMarkup(<LiteratureSurveyPage />);

    expect(html).toContain("Property valuation accuracy");
    expect(html).toContain("Compares valuation models.");
    expect(html).toContain("https://doi.org/10/example");
    expect(html).toContain("Accept selected sources and continue");
    expect(html).not.toMatch(/<button[^>]*disabled=""[^>]*>Accept selected sources and continue/);
    expect(html).not.toContain("No relevant sources found");
  });

  it("does not show an empty-results message before searching or during a search", () => {
    expect(renderToStaticMarkup(<LiteratureSurveyPage />)).not.toContain("No relevant sources found");

    state.isPending = true;
    const html = renderToStaticMarkup(<LiteratureSurveyPage />);
    expect(html).toContain("Searching...");
    expect(html).not.toContain("No relevant sources found");
    expect(html).not.toContain("Accept selected sources and continue");
  });

  it.each(["pending", "unverified"])("blocks accepting %s sources and offers correction and retry", (verification_status) => {
    state.sources = [{
      id: "source-1", title: "Source", authors: [], doi_or_url: "https://example.com",
      verification_status, verification_failure_reason: verification_status === "unverified" ? "URL did not resolve" : null,
    }];
    const html = renderToStaticMarkup(<LiteratureSurveyPage />);
    expect(html).toContain("Verify / retry citations");
    expect(html).toContain("Correct DOI or URL");
    expect(html).toContain("Verify, manually accept, correct, or exclude every selected source before drafting.");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Accept selected sources and continue/);
    if (verification_status === "unverified") {
      expect(html).toContain("Remove unverified source");
      expect(html).toContain("URL did not resolve");
    } else {
      expect(html).not.toContain("Remove unverified source");
    }
  });

  it.each(["queryError", "isFetching"] as const)("blocks continuation when %s prevents trusting results", (key) => {
    state.sources = [{
      id: "source-1", title: "Source", authors: [], doi_or_url: "https://example.com",
      verification_status: "verified",
    }];
    state[key] = true;
    expect(renderToStaticMarkup(<LiteratureSurveyPage />)).toMatch(
      /<button[^>]*disabled=""[^>]*>Accept selected sources and continue/
    );
  });

  it("reloads all retained sources and stage status after a new survey", async () => {
    renderToStaticMarkup(<LiteratureSurveyPage />);
    await state.mutationOptions[1].onSuccess?.();
    expect(state.invalidateQueries).toHaveBeenCalledWith({ queryKey: ["literature-sources", "paper-1"] });
    expect(state.invalidateQueries).toHaveBeenCalledWith({ queryKey: ["status", "paper-1"] });
  });

  it("renders a selection checkbox per source and ignores excluded failed sources", () => {
    state.sources = [
      { id: "good", title: "Good", authors: [], doi_or_url: "https://example.com/good",
        verification_status: "verified", selected: true },
      { id: "bad", title: "Bad", authors: [], doi_or_url: "https://example.com/bad",
        verification_status: "unverified", verification_failure_reason: "404", selected: false },
    ];
    const html = renderToStaticMarkup(<LiteratureSurveyPage />);
    expect(html).toContain('aria-label="Use &quot;Good&quot; for drafting" checked=""');
    expect(html).toContain('aria-label="Use &quot;Bad&quot; for drafting"/>');
    expect(html).toContain("1 of 2 source(s) selected");
    expect(html).toContain("Excluded — not verified or used for drafting.");
    expect(html).not.toMatch(/<button[^>]*disabled=""[^>]*>Accept selected sources and continue/);
  });

  it("blocks continuation when no sources are selected", () => {
    state.sources = [{ id: "s", title: "S", authors: [], doi_or_url: "https://example.com",
      verification_status: "verified", selected: false }];
    const html = renderToStaticMarkup(<LiteratureSurveyPage />);
    expect(html).toContain("Select at least one source to use for drafting.");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Accept selected sources and continue/);
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Verify \/ retry citations/);
  });

  it("offers manual acceptance next to removal for a failed source and lets it unblock continuation", () => {
    state.sources = [{ id: "s", title: "Paywalled", authors: [], doi_or_url: "https://example.com",
      verification_status: "unverified", verification_failure_reason: "403", selected: true }];
    let html = renderToStaticMarkup(<LiteratureSurveyPage />);
    expect(html).toContain("Accept anyway (reason required)");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Manually accept source/);
    expect(html).toContain("Remove unverified source");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Accept selected sources and continue/);

    state.sources = [{ ...state.sources[0], manually_accepted: true, manual_acceptance_reason: "Library copy" }];
    html = renderToStaticMarkup(<LiteratureSurveyPage />);
    expect(html).toContain("Manually accepted by you");
    expect(html).toContain("Reason: Library copy");
    expect(html).toContain("Revoke manual acceptance");
    expect(html).toContain("Remove unverified source");
    expect(html).not.toMatch(/<button[^>]*disabled=""[^>]*>Accept selected sources and continue/);
  });

  it("offers manual DOI or URL entry even when the search found nothing", () => {
    state.isSuccess = true;
    const html = renderToStaticMarkup(<LiteratureSurveyPage />);
    expect(html).toContain("Add a source manually");
    expect(html).toContain('id="manual-identifier"');
    expect(html).toContain('id="manual-title"');
    expect(html).toMatch(/<button type="submit" disabled=""[^>]*>Add source/);
  });
});
