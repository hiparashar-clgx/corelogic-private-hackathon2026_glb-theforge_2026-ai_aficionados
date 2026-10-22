import { useState } from "react";
import axios from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import {
  addLiteratureSource,
  advancePaper,
  correctLiteratureSourceIdentifier,
  listConfidentialityFlags,
  listLiteratureSources,
  removeUnverifiedLiteratureSource,
  resolveConfidentialityFlag,
  runLiteratureSurvey,
  setLiteratureSourceManualAcceptance,
  setLiteratureSourceSelection,
  verifyCitations,
  isSourceCleared,
  type LiteratureSource,
} from "../api/client";
import ManualAcceptanceControls from "../components/ManualAcceptanceControls";
import BackNavigation from "../components/BackNavigation";
import { useWorkflowState } from "../WorkflowState";

function errorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError(error) && typeof error.response?.data?.detail === "string") {
    return error.response.data.detail;
  }
  return fallback;
}

export default function LiteratureSurveyPage() {
  const { paperId } = useParams<{ paperId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [query, setQuery] = useWorkflowState(`${paperId}:literature:query`, "");
  const [yearRange, setYearRange] = useWorkflowState(`${paperId}:literature:yearRange`, "");
  const [error, setError] = useState<string | null>(null);
  const [identifierEdits, setIdentifierEdits] = useWorkflowState<Record<string, string>>(`${paperId}:literature:identifierEdits`, {});
  const [manualIdentifier, setManualIdentifier] = useWorkflowState(`${paperId}:literature:manualIdentifier`, "");
  const [manualTitle, setManualTitle] = useWorkflowState(`${paperId}:literature:manualTitle`, "");

  const sourcesQuery = useQuery({
    queryKey: ["literature-sources", paperId],
    queryFn: () => listLiteratureSources(paperId!),
    enabled: !!paperId,
  });

  const flagsQuery = useQuery({
    queryKey: ["flags", paperId],
    queryFn: () => listConfidentialityFlags(paperId!),
    enabled: !!paperId,
  });

  const resolveMutation = useMutation({
    mutationFn: (vars: { flagId: string; resolution: "redacted" | "confirmed_safe" | "generalized" }) =>
      resolveConfidentialityFlag(vars.flagId, vars.resolution),
    onSuccess: () => {
      setError(null);
      flagsQuery.refetch();
    },
    onError: (error: unknown) => setError(errorMessage(error, "The confidentiality flag could not be resolved.")),
  });

  const refreshSources = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["literature-sources", paperId] }),
      queryClient.invalidateQueries({ queryKey: ["status", paperId] }),
    ]);
  };

  const surveyMutation = useMutation({
    mutationFn: () => runLiteratureSurvey(paperId!, query.trim(), yearRange.trim() || undefined),
    onSuccess: async () => {
      setError(null);
      await refreshSources();
    },
    onError: (mutationError: any) => {
      setError(mutationError.response?.data?.detail ?? "The literature survey failed.");
      flagsQuery.refetch();
    },
  });

  const verifyMutation = useMutation({
    mutationFn: () => verifyCitations(paperId!),
    onSuccess: async () => {
      setError(null);
      await refreshSources();
    },
    onError: (error: unknown) => setError(errorMessage(error, "Source verification failed. Please retry.")),
  });

  const correctMutation = useMutation({
    mutationFn: ({ sourceId, identifier }: { sourceId: string; identifier: string }) =>
      correctLiteratureSourceIdentifier(paperId!, sourceId, identifier),
    onSuccess: async (source) => {
      setError(null);
      setIdentifierEdits((current) => ({ ...current, [source.id]: source.doi_or_url }));
      await refreshSources();
    },
    onError: (error: unknown) =>
      setError(errorMessage(error, "The source could not be corrected. Enter a DOI or an HTTP(S) URL.")),
  });

  const removeMutation = useMutation({
    mutationFn: (sourceId: string) => removeUnverifiedLiteratureSource(paperId!, sourceId),
    onSuccess: async () => {
      setError(null);
      await refreshSources();
    },
    onError: (error: unknown) => setError(errorMessage(error, "The source could not be removed.")),
  });

  const addMutation = useMutation({
    mutationFn: () => addLiteratureSource(paperId!, manualIdentifier.trim(), manualTitle.trim()),
    onSuccess: async () => {
      setError(null);
      setManualIdentifier("");
      setManualTitle("");
      await refreshSources();
    },
    onError: (error: unknown) =>
      setError(errorMessage(error, "The source could not be added. Enter a DOI or an HTTP(S) URL.")),
  });

  const selectionMutation = useMutation({
    mutationFn: ({ sourceId, selected }: { sourceId: string; selected: boolean }) =>
      setLiteratureSourceSelection(paperId!, sourceId, selected),
    onSuccess: async () => {
      setError(null);
      await refreshSources();
    },
    onError: (error: unknown) => setError(errorMessage(error, "The source selection could not be updated.")),
  });

  const acceptanceMutation = useMutation({
    mutationFn: ({ sourceId, accepted, reason }: { sourceId: string; accepted: boolean; reason?: string }) =>
      setLiteratureSourceManualAcceptance(paperId!, sourceId, accepted, reason),
    onSuccess: async () => {
      setError(null);
      await refreshSources();
    },
    onError: (error: unknown) => setError(errorMessage(error, "The manual acceptance could not be saved.")),
  });

  const continueMutation = useMutation({
    mutationFn: () => advancePaper(paperId!, "drafting"),
    onSuccess: () => navigate(`/papers/${paperId}/status`),
    onError: (mutationError: any) => setError(mutationError.response?.data?.detail ?? "The paper could not advance."),
  });

  const sources = sourcesQuery.data ?? [];
  const selectedSources = sources.filter((source) => source.selected !== false);
  const openFlags = (flagsQuery.data ?? []).filter((flag) => flag.resolution === "open");
  const busy = surveyMutation.isPending || verifyMutation.isPending ||
    correctMutation.isPending || removeMutation.isPending || continueMutation.isPending ||
    addMutation.isPending || selectionMutation.isPending || acceptanceMutation.isPending;
  const allVerified = selectedSources.length > 0 && selectedSources.every(isSourceCleared);
  const unsavedCorrections = selectedSources.some((source) =>
    identifierEdits[source.id] !== undefined && identifierEdits[source.id].trim() !== source.doi_or_url
  );
  const canContinue = allVerified && !unsavedCorrections && !busy &&
    sourcesQuery.isSuccess && !sourcesQuery.isFetching &&
    flagsQuery.isSuccess && !flagsQuery.isFetching && openFlags.length === 0;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <BackNavigation to={`/papers/${paperId}/framing`} label="problem framing" />
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Literature survey</h1>
        <p className="mt-1 text-slate-500">Search for relevant research, then verify your sources before drafting.</p>
      </div>

      <form
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
        onSubmit={(event) => {
          event.preventDefault();
          if (query.trim()) surveyMutation.mutate();
        }}
      >
        <div>
          <label className="text-sm font-medium text-slate-700" htmlFor="literature-query">Search query</label>
          <input
            id="literature-query"
            className="mt-1 w-full rounded-lg border border-slate-300 p-3"
            placeholder="e.g. property valuation model accuracy"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <div>
          <label className="text-sm font-medium text-slate-700" htmlFor="year-range">Year range (optional)</label>
          <input
            id="year-range"
            className="mt-1 w-full rounded-lg border border-slate-300 p-3"
            placeholder="e.g. 2020-2026"
            value={yearRange}
            onChange={(event) => setYearRange(event.target.value)}
          />
        </div>
        <button
          type="submit"
          disabled={!query.trim() || busy}
          className="rounded-xl bg-brand-600 px-5 py-2.5 font-medium text-white shadow-sm hover:bg-brand-700 disabled:opacity-50"
        >
          {surveyMutation.isPending ? "Searching..." : "Run literature survey"}
        </button>
      </form>

      {error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
      {sourcesQuery.isLoading && <p role="status">Loading sources...</p>}
      {sourcesQuery.isError && (
        <p role="alert" className="text-sm text-rose-700">Sources could not be loaded. Reload the page to retry.</p>
      )}
      {flagsQuery.isError && (
        <p role="alert" className="text-sm text-rose-700">Confidentiality flags could not be loaded. Reload the page to retry.</p>
      )}

      {surveyMutation.isSuccess && sources.length === 0 && (
        <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <h2 className="font-semibold text-amber-900">No relevant sources found</h2>
          <p className="mt-1 text-sm text-amber-800">
            No sources matched your query and research questions. Try more focused keywords or a wider year range,
            or add a known source manually by DOI or URL below.
          </p>
        </div>
      )}

      <form
        className="space-y-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
        onSubmit={(event) => {
          event.preventDefault();
          if (manualIdentifier.trim()) addMutation.mutate();
        }}
      >
        <h2 className="font-semibold text-slate-900">Add a source manually</h2>
        <p className="text-sm text-slate-600">Missed a paper in the search? Add it by DOI or URL. It will need verification before drafting.</p>
        <div>
          <label className="text-sm font-medium text-slate-700" htmlFor="manual-identifier">DOI or URL</label>
          <input
            id="manual-identifier"
            className="mt-1 w-full rounded-lg border border-slate-300 p-2"
            placeholder="e.g. 10.1145/1234567 or https://arxiv.org/abs/..."
            value={manualIdentifier}
            disabled={busy}
            onChange={(event) => setManualIdentifier(event.target.value)}
          />
        </div>
        <div>
          <label className="text-sm font-medium text-slate-700" htmlFor="manual-title">Title (optional)</label>
          <input
            id="manual-title"
            className="mt-1 w-full rounded-lg border border-slate-300 p-2"
            value={manualTitle}
            disabled={busy}
            onChange={(event) => setManualTitle(event.target.value)}
          />
        </div>
        <button
          type="submit"
          disabled={!manualIdentifier.trim() || busy}
          className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-900 disabled:opacity-50"
        >
          {addMutation.isPending ? "Adding..." : "Add source"}
        </button>
      </form>

      {openFlags.length > 0 && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
          <h2 className="font-semibold text-rose-700">Resolve confidential content before searching</h2>
          <ul className="mt-2 space-y-2">
            {openFlags.map((flag) => (
              <li key={flag.id} className="flex items-center justify-between gap-4 rounded-lg bg-white px-3 py-2 shadow-sm">
                <div>
                  <p className="text-sm font-medium text-slate-800">&quot;{flag.matched_text}&quot;</p>
                  <p className="text-xs text-slate-500">{flag.flag_reason}</p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button
                    className="rounded-lg bg-slate-100 px-2 py-1 text-xs font-medium hover:bg-slate-200"
                    onClick={() => resolveMutation.mutate({ flagId: flag.id, resolution: "redacted" })}
                  >
                    Redact
                  </button>
                  <button
                    className="rounded-lg bg-slate-100 px-2 py-1 text-xs font-medium hover:bg-slate-200"
                    onClick={() => resolveMutation.mutate({ flagId: flag.id, resolution: "confirmed_safe" })}
                  >
                    Confirm safe
                  </button>
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-rose-700">After resolving all items, run the literature survey again.</p>
        </div>
      )}

      {sources.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-slate-900">Sources found</h2>
          <p className="text-sm text-slate-600">
            Tick the sources to use for drafting. Only selected sources are verified and passed to the drafting agent.
            Retry failed checks, correct the identifier, exclude, or remove an invalid source.
            A retrievable source still needs review for relevance and claim support.
          </p>
          <p role="status" className="text-sm font-medium text-slate-700">
            {selectedSources.length} of {sources.length} source(s) selected
          </p>
          <button
            className="rounded-xl bg-brand-600 px-5 py-2.5 font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            disabled={busy || unsavedCorrections || sourcesQuery.isFetching || selectedSources.length === 0}
            onClick={() => verifyMutation.mutate()}
          >
            {verifyMutation.isPending ? "Verifying sources..." : "Verify / retry citations"}
          </button>
          {sources.map((source: LiteratureSource) => (
            <article
              key={source.id}
              className={`rounded-xl border border-slate-200 bg-white p-4 shadow-sm ${source.selected === false ? "opacity-60" : ""}`}
            >
              <label className="flex items-start gap-3">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4"
                  checked={source.selected !== false}
                  disabled={busy}
                  aria-label={`Use "${source.title}" for drafting`}
                  onChange={(event) => selectionMutation.mutate({
                    sourceId: source.id, selected: event.target.checked,
                  })}
                />
                <h3 className="font-semibold text-slate-900">{source.title}</h3>
              </label>
              {source.selected === false && (
                <p className="mt-1 text-xs font-medium text-slate-500">Excluded — not verified or used for drafting.</p>
              )}
              <p className="mt-1 text-sm text-slate-500">{source.authors.join(", ")} {source.year ? `(${source.year})` : ""}</p>
              <p className="mt-2 text-sm text-slate-700">{source.relevance_summary}</p>
              <a className="mt-2 inline-block text-sm text-brand-700 hover:underline" href={source.doi_or_url} target="_blank" rel="noreferrer">
                View source
              </a>
              <p className="mt-2 text-sm font-medium">Verification: {source.verification_status}</p>
              {source.verification_failure_reason && (
                <p className="mt-1 text-sm text-rose-700">{source.verification_failure_reason}</p>
              )}
              {source.verification_status !== "verified" && (
                <div className="mt-3 space-y-2">
                  <label htmlFor={`identifier-${source.id}`} className="text-sm font-medium text-slate-700">
                    Correct DOI or URL
                  </label>
                  <input
                    id={`identifier-${source.id}`}
                    className="w-full rounded-lg border border-slate-300 p-2"
                    value={identifierEdits[source.id] ?? source.doi_or_url}
                    disabled={busy}
                    onChange={(event) => setIdentifierEdits((current) => ({
                      ...current, [source.id]: event.target.value,
                    }))}
                  />
                  <button
                    className="rounded-lg bg-slate-100 px-3 py-2 text-sm font-medium disabled:opacity-50"
                    disabled={busy || !identifierEdits[source.id]?.trim() ||
                      identifierEdits[source.id].trim() === source.doi_or_url}
                    onClick={() => correctMutation.mutate({
                      sourceId: source.id, identifier: identifierEdits[source.id].trim(),
                    })}
                  >
                    Save correction (verification required)
                  </button>
                </div>
              )}
              {source.verification_status === "unverified" && (
                <ManualAcceptanceControls
                  source={source}
                  disabled={busy}
                  onAccept={(reason) => acceptanceMutation.mutate({ sourceId: source.id, accepted: true, reason })}
                  onRevoke={() => acceptanceMutation.mutate({ sourceId: source.id, accepted: false })}
                />
              )}
              {source.verification_status === "unverified" && (
                <button
                  className="mt-3 rounded-lg border border-rose-200 px-3 py-2 text-sm font-medium text-rose-700 disabled:opacity-50"
                  disabled={busy}
                  onClick={() => {
                    if (window.confirm(
                      `Remove "${source.title}" and its verification history from this paper? Existing draft text will not be changed.`
                    )) {
                      removeMutation.mutate(source.id);
                    }
                  }}
                >
                  Remove unverified source
                </button>
              )}
            </article>
          ))}
        </div>
      )}

      {sources.length > 0 && (
        <div className="space-y-2">
          {selectedSources.length === 0 && (
            <p role="status" className="text-sm text-amber-800">Select at least one source to use for drafting.</p>
          )}
          {selectedSources.length > 0 && !allVerified && (
            <p role="status" className="text-sm text-amber-800">Verify, manually accept, correct, or exclude every selected source before drafting.</p>
          )}
          {unsavedCorrections && <p role="status" className="text-sm text-amber-800">Save source corrections before verifying or continuing.</p>}
          <button
            disabled={!canContinue}
            className="rounded-xl bg-emerald-600 px-5 py-2.5 font-medium text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50"
            onClick={() => continueMutation.mutate()}
          >
            {continueMutation.isPending ? "Continuing..." : "Accept selected sources and continue"}
          </button>
        </div>
      )}
    </div>
  );
}