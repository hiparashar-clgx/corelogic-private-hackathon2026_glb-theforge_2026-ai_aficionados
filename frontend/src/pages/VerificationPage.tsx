import axios from "axios";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  applyFormatting,
  checkOriginality,
  getDraftSection,
  getPaper,
  getFormattingReport,
  getRewriteSuggestion,
  listLiteratureSources,
  listOriginalityFindings,
  resolveOriginalityFinding,
  updateContentBlock,
  isSourceCleared,
  type OriginalityFinding,
  type FormattingComplianceReport,
} from "../api/client";
import FormattingReview from "../components/FormattingReview";
import BackNavigation from "../components/BackNavigation";
import { useWorkflowState } from "../WorkflowState";

const sections = [
  "abstract",
  "introduction",
  "related_work",
  "methods",
  "results",
  "discussion",
  "conclusion",
] as const;

function errorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail ?? fallback;
  }
  return fallback;
}

export default function VerificationPage() {
  const { paperId } = useParams<{ paperId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const paperQuery = useQuery({
    queryKey: ["paper", paperId],
    queryFn: () => getPaper(paperId!),
    enabled: Boolean(paperId),
  });
  const hasSavedFormatting = paperQuery.data?.current_stage === "formatting" ||
    paperQuery.data?.current_stage === "ready_for_submission";
  const savedReportQuery = useQuery({
    queryKey: ["formatting-report", paperId],
    queryFn: () => getFormattingReport(paperId!),
    enabled: Boolean(paperId) && hasSavedFormatting,
  });
  const sourcesQuery = useQuery({
    queryKey: ["literature-sources", paperId],
    queryFn: () => listLiteratureSources(paperId!),
    enabled: Boolean(paperId),
  });
  const findingsQuery = useQuery({
    queryKey: ["originality-findings", paperId],
    queryFn: () => listOriginalityFindings(paperId!),
    enabled: Boolean(paperId),
  });
  const sectionQueries = useQueries({
    queries: sections.map((sectionType) => ({
      queryKey: ["draft-section", paperId, sectionType],
      queryFn: async () => {
        try {
          return await getDraftSection(paperId!, sectionType);
        } catch (error) {
          if (axios.isAxiosError(error) && error.response?.status === 404) {
            return null;
          }
          throw error;
        }
      },
      enabled: Boolean(paperId),
    })),
  });
  const [error, setError] = useState<string | null>(null);
  const [checked, setOriginalityChecked] = useWorkflowState<boolean | null>(`${paperId}:verification:checked`, null);
  const originalityChecked = checked ?? hasSavedFormatting;
  const [selectedVenue, setVenue] = useWorkflowState<"ieee" | "acm" | "arxiv" | null>(`${paperId}:verification:venue`, null);
  const savedVenue = paperQuery.data?.target_venue;
  const venue = selectedVenue ?? (savedVenue === "acm" || savedVenue === "arxiv" ? savedVenue : "ieee");
  const [justifications, setJustifications] = useWorkflowState<Record<string, string>>(`${paperId}:verification:justifications`, {});
  const [suggestions, setSuggestions] = useWorkflowState<Record<string, string>>(`${paperId}:verification:suggestions`, {});
  const [localReport, setFormattingReport] = useWorkflowState<FormattingComplianceReport | null | undefined>(
    `${paperId}:verification:formattingReport`, undefined
  );
  const formattingReport = localReport === undefined ? savedReportQuery.data : localReport;
  const sectionsData = sectionQueries.map((query) => query.data);

  const refreshPaperState = () => {
    queryClient.invalidateQueries({ queryKey: ["status", paperId] });
  };
  const originalityMutation = useMutation({
    mutationFn: () => checkOriginality(paperId!),
    onSuccess: () => {
      setError(null);
      setOriginalityChecked(true);
      queryClient.invalidateQueries({ queryKey: ["originality-findings", paperId] });
      refreshPaperState();
    },
    onError: (mutationError: unknown) =>
      setError(errorMessage(mutationError, "The originality check could not be completed.")),
  });
  const formattingMutation = useMutation({
    mutationFn: () => applyFormatting(paperId!, venue),
    onSuccess: (report) => {
      setFormattingReport(report);
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["paper", paperId] });
      queryClient.invalidateQueries({ queryKey: ["formatting-report", paperId] });
      refreshPaperState();
    },
    onError: (mutationError: unknown) =>
      setError(errorMessage(mutationError, "Publisher formatting could not be applied.")),
  });
  const suggestionMutation = useMutation({
    mutationFn: getRewriteSuggestion,
    onSuccess: ({ suggestion }, findingId) => {
      setSuggestions((current) => ({ ...current, [findingId]: suggestion }));
      setError(null);
    },
    onError: (mutationError: unknown) =>
      setError(errorMessage(mutationError, "A rewrite suggestion could not be generated.")),
  });
  const justifyMutation = useMutation({
    mutationFn: (finding: OriginalityFinding) =>
      resolveOriginalityFinding(
        finding.id,
        "accepted_with_justification",
        justifications[finding.id]?.trim()
      ),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["originality-findings", paperId] });
      refreshPaperState();
    },
    onError: (mutationError: unknown) =>
      setError(errorMessage(mutationError, "The finding could not be resolved.")),
  });
  const rewriteMutation = useMutation({
    mutationFn: async ({
      finding,
      blockId,
      text,
    }: {
      finding: OriginalityFinding;
      blockId: string;
      text: string;
    }) => {
      await updateContentBlock(paperId!, blockId, { text });
      return resolveOriginalityFinding(finding.id, "rewritten");
    },
    onSuccess: () => {
      setError(null);
      setOriginalityChecked(false);
      setFormattingReport(null);
      queryClient.invalidateQueries({ queryKey: ["originality-findings", paperId] });
      queryClient.invalidateQueries({ queryKey: ["draft-section", paperId] });
      refreshPaperState();
    },
    onError: (mutationError: unknown) =>
      setError(errorMessage(mutationError, "The rewritten passage could not be saved.")),
  });

  const sources = (sourcesQuery.data ?? []).filter((source) => source.selected !== false);
  const findings = findingsQuery.data ?? [];
  const openFindings = findings.filter((finding) => finding.status === "open");
  const citationsVerified = sources.every(isSourceCleared);
  const canApplyFormatting =
    originalityChecked &&
    citationsVerified &&
    openFindings.length === 0 &&
    !findingsQuery.isFetching &&
    !sourcesQuery.isFetching &&
    !findingsQuery.isError &&
    !sourcesQuery.isError;

  const findMatchingBlock = (finding: OriginalityFinding) =>
    sectionsData
      .find((section) => section?.id === finding.draft_section_id)
      ?.blocks.find((block) => block.text === finding.flagged_text);

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <BackNavigation to={`/papers/${paperId}/drafting`} label="drafting" />
      <header id="citation-review">
        <h1 className="text-2xl font-bold text-slate-900">Citation &amp; originality</h1>
        <p className="mt-1 text-slate-500">
          Review your verified references and potential text similarities before continuing.
        </p>
      </header>

      {error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
      {paperQuery.isError && (
        <div role="alert" className="text-sm text-rose-700">
          <p>Could not restore the paper's saved verification and formatting state.</p>
          <button onClick={() => paperQuery.refetch()}>Retry loading paper</button>
        </div>
      )}

      <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Citation summary</h2>
            <p className="text-sm text-slate-500">
              Sources were verified on the Literature survey page before drafting. This summary is read-only.
            </p>
          </div>
          <Link
            to={`/papers/${paperId}/literature`}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
          >
            Manage sources in literature survey
          </Link>
        </div>

        {sourcesQuery.isLoading && <p className="text-sm text-slate-500">Loading sources…</p>}
        {sourcesQuery.isError && (
          <p role="alert" className="text-sm text-rose-700">Sources could not be loaded.</p>
        )}
        {!sourcesQuery.isLoading && sources.length === 0 && (
          <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
            No literature sources are selected for this paper.
          </p>
        )}
        <ul className="space-y-3">
          {sources.map((source) => (
            <li key={source.id} className="rounded-lg border border-slate-200 p-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <a
                  className="font-medium text-brand-700 hover:underline"
                  href={source.doi_or_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {source.title}
                </a>
                <span
                  className={`rounded-full px-2 py-1 text-xs font-medium ${
                    source.verification_status === "verified"
                      ? "bg-emerald-100 text-emerald-800"
                      : source.manually_accepted
                        ? "bg-amber-100 text-amber-800"
                        : source.verification_status === "unverified"
                          ? "bg-rose-100 text-rose-800"
                          : "bg-slate-100 text-slate-600"
                  }`}
                >
                  {source.manually_accepted ? "manually accepted" : source.verification_status}
                </span>
              </div>
              {source.manually_accepted && source.manual_acceptance_reason && (
                <p className="mt-1 text-sm text-slate-500">Reason: {source.manual_acceptance_reason}</p>
              )}
              {!isSourceCleared(source) && source.verification_failure_reason && (
                <p className="mt-1 text-sm text-rose-700">{source.verification_failure_reason}</p>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Originality review</h2>
            <p className="text-sm text-slate-500">Check draft passages against the surveyed sources.</p>
          </div>
          <button
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            disabled={originalityMutation.isPending}
            onClick={() => originalityMutation.mutate()}
          >
            {originalityMutation.isPending ? "Checking…" : "Run originality check"}
          </button>
        </div>

        {findingsQuery.isLoading && <p className="text-sm text-slate-500">Loading findings…</p>}
        {findingsQuery.isError && (
          <p role="alert" className="text-sm text-rose-700">Existing findings could not be loaded.</p>
        )}
        {!findingsQuery.isLoading && findings.length === 0 && (
          <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-600">
            {originalityChecked
              ? "Check complete. No similar passages were found in the surveyed sources."
              : "No findings are recorded yet. Run an originality check to review the draft."}
          </p>
        )}
        {findings.length > 0 && openFindings.length === 0 && (
          <p className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">
            All originality findings have been resolved.
          </p>
        )}

        <div className="space-y-4">
          {findings.map((finding) => {
            const block = findMatchingBlock(finding);
            const suggestion = suggestions[finding.id];
            return (
              <article key={finding.id} className="space-y-3 rounded-lg border border-slate-200 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-medium text-slate-900">
                    {finding.status === "open" ? "Needs review" : "Resolved"}
                  </h3>
                  <span className="text-xs text-slate-500">
                    Similarity: {(finding.similarity_score * 100).toFixed(0)}%
                    {finding.is_self_plagiarism ? " · possible self-plagiarism" : ""}
                  </span>
                </div>
                <blockquote className="border-l-2 border-amber-400 pl-3 text-sm text-slate-700">
                  {finding.flagged_text}
                </blockquote>
                <a
                  className="text-sm text-brand-700 hover:underline"
                  href={finding.matching_source}
                  target="_blank"
                  rel="noreferrer"
                >
                  Matching source
                </a>

                {finding.status === "open" && (
                  <div className="space-y-3 border-t border-slate-100 pt-3">
                    {block ? (
                      <>
                        <button
                          className="rounded-lg bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 disabled:opacity-50"
                          disabled={suggestionMutation.isPending}
                          onClick={() => suggestionMutation.mutate(finding.id)}
                        >
                          {suggestionMutation.isPending && suggestionMutation.variables === finding.id
                            ? "Generating…"
                            : "Suggest a rewrite"}
                        </button>
                        {suggestion !== undefined && (
                          <div>
                            <label className="text-sm font-medium text-slate-700" htmlFor={`rewrite-${finding.id}`}>
                              Rewrite passage
                            </label>
                            <textarea
                              id={`rewrite-${finding.id}`}
                              className="mt-1 min-h-24 w-full rounded-lg border border-slate-300 p-3 text-sm"
                              value={suggestion}
                              onChange={(event) =>
                                setSuggestions((current) => ({ ...current, [finding.id]: event.target.value }))
                              }
                            />
                            <button
                              className="mt-2 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                              disabled={!suggestion.trim() || rewriteMutation.isPending}
                              onClick={() =>
                                rewriteMutation.mutate({ finding, blockId: block.id, text: suggestion.trim() })
                              }
                            >
                              {rewriteMutation.isPending ? "Saving rewrite…" : "Apply rewrite to draft"}
                            </button>
                          </div>
                        )}
                      </>
                    ) : (
                      <p className="text-sm text-amber-800">
                        The original draft passage is no longer available to replace here. Edit it in drafting, then resolve with a justification.
                      </p>
                    )}

                    <div>
                      <label className="text-sm font-medium text-slate-700" htmlFor={`justification-${finding.id}`}>
                        Justification
                      </label>
                      <textarea
                        id={`justification-${finding.id}`}
                        className="mt-1 min-h-16 w-full rounded-lg border border-slate-300 p-3 text-sm"
                        placeholder="Explain why this passage is acceptable."
                        value={justifications[finding.id] ?? ""}
                        onChange={(event) =>
                          setJustifications((current) => ({ ...current, [finding.id]: event.target.value }))
                        }
                      />
                      <button
                        className="mt-2 rounded-lg bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 disabled:opacity-50"
                        disabled={!justifications[finding.id]?.trim() || justifyMutation.isPending}
                        onClick={() => justifyMutation.mutate(finding)}
                      >
                        Accept with justification
                      </button>
                    </div>
                  </div>
                )}
                {finding.justification && (
                  <p className="text-sm text-slate-600">Justification: {finding.justification}</p>
                )}
              </article>
            );
          })}
        </div>
      </section>

      {originalityChecked && (
        <section className="space-y-4 rounded-xl border border-brand-200 bg-brand-50 p-5">
          <a href="#citation-review" className="inline-flex rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100">
            &larr; Back to citation &amp; originality review
          </a>
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Next step: publisher formatting</h2>
            <p className="mt-1 text-sm text-slate-600">
              Choose a target venue and apply its formatting once citations are verified and all originality findings are resolved.
            </p>
          </div>

          {!citationsVerified && (
            <p className="text-sm text-amber-800">
              Some selected sources are not verified or manually accepted. Fix them on the{" "}
              <Link className="underline" to={`/papers/${paperId}/literature`}>literature survey page</Link>{" "}
              before continuing.
            </p>
          )}
          {openFindings.length > 0 && (
            <p className="text-sm text-amber-800">
              Resolve the {openFindings.length} open originality finding{openFindings.length === 1 ? "" : "s"} above before continuing.
            </p>
          )}
          {(findingsQuery.isFetching || sourcesQuery.isFetching) && (
            <p className="text-sm text-slate-600">Refreshing verification results…</p>
          )}

          <div>
            <label className="text-sm font-medium text-slate-700" htmlFor="target-venue">
              Target venue
            </label>
            <select
              id="target-venue"
              className="mt-1 block w-full rounded-lg border border-slate-300 bg-white p-2.5"
              value={venue}
              onChange={(event) => setVenue(event.target.value as typeof venue)}
            >
              <option value="ieee">IEEE</option>
              <option value="acm">ACM</option>
              <option value="arxiv">arXiv</option>
            </select>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              className="rounded-xl bg-emerald-600 px-5 py-2.5 font-medium text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50"
              disabled={!canApplyFormatting || formattingMutation.isPending}
              onClick={() => formattingMutation.mutate()}
            >
              {formattingMutation.isPending ? "Applying formatting…" : "Apply formatting & continue"}
            </button>
            <button
              className="rounded-xl border border-slate-300 bg-white px-5 py-2.5 font-medium text-slate-700 hover:bg-slate-50"
              onClick={() => navigate(`/papers/${paperId}/drafting`)}
            >
              Return to drafting
            </button>
          </div>

          {formattingReport && (
            <FormattingReview
              key={formattingReport.id}
              paperId={paperId!}
              report={formattingReport}
              ready={paperQuery.data?.current_stage === "ready_for_submission"}
            />
          )}
          {localReport === undefined && savedReportQuery.isLoading && (
            <p className="text-sm text-slate-600">Loading saved formatting report...</p>
          )}
          {localReport === undefined && savedReportQuery.isError && (
            <div role="alert" className="text-sm text-rose-700">
              <p>Could not load the saved formatting report.</p>
              <button onClick={() => savedReportQuery.refetch()}>Retry loading report</button>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
