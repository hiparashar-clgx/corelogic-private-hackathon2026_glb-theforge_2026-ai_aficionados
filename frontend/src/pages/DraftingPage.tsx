import { useState } from "react";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import BackNavigation from "../components/BackNavigation";
import { useWorkflowState } from "../WorkflowState";
import {
  advancePaper,
  draftSection,
  getDraftSection,
  listConfidentialityFlags,
  resolveConfidentialityFlag,
  updateContentBlock,
  type DraftSection,
  type FormattingComplianceReport,
} from "../api/client";

const sections = [
  ["abstract", "Abstract"],
  ["introduction", "Introduction"],
  ["related_work", "Related work"],
  ["methods", "Methods"],
  ["results", "Results"],
  ["discussion", "Discussion"],
  ["conclusion", "Conclusion"],
] as const;

export default function DraftingPage() {
  const { paperId } = useParams<{ paperId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [sectionType, setSectionType] = useWorkflowState(`${paperId}:drafting:section`, "introduction");
  const [notesBySection, setNotesBySection] = useWorkflowState<Record<string, string>>(`${paperId}:drafting:notes`, {});
  const [, setOriginalityChecked] = useWorkflowState(`${paperId}:verification:checked`, false);
  const [, setFormattingReport] = useWorkflowState<FormattingComplianceReport | null>(`${paperId}:verification:formattingReport`, null);
  const [error, setError] = useState<string | null>(null);

  const flagsQuery = useQuery({
    queryKey: ["flags", paperId],
    queryFn: () => listConfidentialityFlags(paperId!),
    enabled: Boolean(paperId),
  });
  const openFlags = (flagsQuery.data ?? []).filter((flag) => flag.resolution === "open");

  const sectionQueries = useQueries({
    queries: sections.map(([type]) => ({
      queryKey: ["draft-section", paperId, type],
      queryFn: async () => {
        try {
          return await getDraftSection(paperId!, type);
        } catch (queryError) {
          if (axios.isAxiosError(queryError) && queryError.response?.status === 404) {
            return null;
          }
          throw queryError;
        }
      },
      enabled: Boolean(paperId),
    })),
  });
  const sectionIndex = sections.findIndex(([type]) => type === sectionType);
  const sectionQuery = sectionQueries[sectionIndex];
  const section = sectionQuery.data ?? null;
  const allSectionsAccepted = sectionQueries.every(
    (query) => query.data?.blocks.length && query.data.blocks.every((block) => block.accepted)
  );

  const draftMutation = useMutation({
    mutationFn: () => draftSection(paperId!, sectionType, notesBySection[sectionType] ?? ""),
    onSuccess: (result) => {
      setOriginalityChecked(false);
      setFormattingReport(null);
      queryClient.setQueryData(["draft-section", paperId, result.section_type], result);
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["status", paperId] });
    },
    onError: (mutationError: any) => {
      setError(mutationError.response?.data?.detail ?? "The section could not be drafted.");
      flagsQuery.refetch();
    },
  });

  const resolveMutation = useMutation({
    mutationFn: (vars: { flagId: string; resolution: "redacted" | "confirmed_safe" | "generalized" }) =>
      resolveConfidentialityFlag(vars.flagId, vars.resolution),
    onSuccess: () => {
      setError(null);
      flagsQuery.refetch();
    },
    onError: (mutationError: any) =>
      setError(mutationError.response?.data?.detail ?? "The confidentiality flag could not be resolved."),
  });

  const updateMutation = useMutation({
    mutationFn: ({ blockId, sectionType: updatedSectionType, text, accepted }: {
      blockId: string;
      sectionType: string;
      text?: string;
      accepted?: boolean;
    }) =>
      updateContentBlock(paperId!, blockId, { text, accepted }),
    onSuccess: (updated, variables) => {
      if (variables.text !== undefined) {
        setOriginalityChecked(false);
        setFormattingReport(null);
      }
      queryClient.setQueryData<DraftSection | null>(
        ["draft-section", paperId, variables.sectionType],
        (current) => current
          ? { ...current, blocks: current.blocks.map((block) => (block.id === updated.id ? updated : block)) }
          : current
      );
      setError(null);
    },
    onError: (mutationError: any) => setError(mutationError.response?.data?.detail ?? "The block could not be saved."),
  });

  const continueMutation = useMutation({
    mutationFn: () => advancePaper(paperId!, "verification"),
    onSuccess: () => navigate(`/papers/${paperId}/status`),
    onError: (mutationError: any) => setError(mutationError.response?.data?.detail ?? "The paper could not advance."),
  });

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <BackNavigation to={`/papers/${paperId}/literature`} label="literature survey" />
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Guided drafting</h1>
        <p className="mt-1 text-slate-500">Generate one section at a time, then review and accept each content block.</p>
        <button
          className="mt-2 text-sm font-medium text-brand-700 hover:underline"
          onClick={() => navigate(`/papers/${paperId}/literature`)}
        >
          Review and verify literature sources
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <aside className="space-y-2 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
          {sections.map(([value, label]) => (
            <button
              key={value}
              className={`w-full rounded-lg px-3 py-2 text-left text-sm font-medium ${
                sectionType === value ? "bg-brand-100 text-brand-700" : "text-slate-600 hover:bg-slate-100"
              }`}
              onClick={() => setSectionType(value)}
            >
              {label}
            </button>
          ))}
        </aside>

        <div className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <label className="text-sm font-medium text-slate-700" htmlFor="draft-notes">Notes for this section</label>
            <textarea
              id="draft-notes"
              className="mt-1 h-24 w-full rounded-lg border border-slate-300 p-3"
              placeholder="Add emphasis, evidence, or constraints for the draft..."
              value={notesBySection[sectionType] ?? ""}
              onChange={(event) =>
                setNotesBySection((current) => ({ ...current, [sectionType]: event.target.value }))
              }
            />
            <button
              className="mt-3 rounded-xl bg-brand-600 px-5 py-2.5 font-medium text-white shadow-sm hover:bg-brand-700 disabled:opacity-50"
              disabled={draftMutation.isPending}
              onClick={() => draftMutation.mutate()}
            >
              {draftMutation.isPending ? "Drafting..." : `Draft ${sections.find(([value]) => value === sectionType)?.[1]}`}
            </button>
          </div>

          {error && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
          {flagsQuery.isError && (
            <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">
              Confidentiality flags could not be loaded.
            </p>
          )}
          {openFlags.length > 0 && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
              <h2 className="font-semibold text-rose-700">Resolve confidential content before drafting</h2>
              <ul className="mt-2 space-y-2">
                {openFlags.map((flag) => (
                  <li key={flag.id} className="flex items-center justify-between gap-4 rounded-lg bg-white px-3 py-2 shadow-sm">
                    <div>
                      <p className="text-sm font-medium text-slate-800">&quot;{flag.matched_text}&quot;</p>
                      <p className="text-xs text-slate-500">{flag.flag_reason}</p>
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <button
                        disabled={resolveMutation.isPending}
                        className="rounded-lg bg-slate-100 px-2 py-1 text-xs font-medium hover:bg-slate-200 disabled:opacity-50"
                        onClick={() => resolveMutation.mutate({ flagId: flag.id, resolution: "redacted" })}
                      >
                        Redact
                      </button>
                      <button
                        disabled={resolveMutation.isPending}
                        className="rounded-lg bg-slate-100 px-2 py-1 text-xs font-medium hover:bg-slate-200 disabled:opacity-50"
                        onClick={() => resolveMutation.mutate({ flagId: flag.id, resolution: "generalized" })}
                      >
                        Generalize
                      </button>
                      <button
                        disabled={resolveMutation.isPending}
                        className="rounded-lg bg-slate-100 px-2 py-1 text-xs font-medium hover:bg-slate-200 disabled:opacity-50"
                        onClick={() => resolveMutation.mutate({ flagId: flag.id, resolution: "confirmed_safe" })}
                      >
                        Confirm safe
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-rose-700">Resolve all open items, then try drafting again.</p>
            </div>
          )}
          {sectionQuery.isError && (
            <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">
              The saved section could not be loaded.
            </p>
          )}
          {sectionQuery.isLoading && <p className="text-sm text-slate-500">Loading saved section...</p>}

          {section && (
            <div className="space-y-3">
              {section.blocks.map((block) => (
                <div key={block.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                  <textarea
                    className="min-h-32 w-full rounded-lg border border-slate-300 p-3 text-slate-700"
                    value={block.text}
                    onChange={(event) =>
                      queryClient.setQueryData<DraftSection>(
                        ["draft-section", paperId, sectionType],
                        (current) => current
                          ? {
                              ...current,
                              blocks: current.blocks.map((item) =>
                                item.id === block.id ? { ...item, text: event.target.value } : item
                              ),
                            }
                          : current
                      )
                    }
                    onBlur={(event) =>
                      updateMutation.mutate({ blockId: block.id, sectionType, text: event.target.value })
                    }
                  />
                  <label className="mt-3 flex items-center gap-2 text-sm text-slate-600">
                    <input
                      type="checkbox"
                      checked={block.accepted}
                      onChange={(event) =>
                        updateMutation.mutate({ blockId: block.id, sectionType, accepted: event.target.checked })
                      }
                    />
                    Accept this block
                  </label>
                </div>
              ))}
            </div>
          )}
          {!section && !sectionQuery.isLoading && !sectionQuery.isError && (
            <p className="rounded-xl border border-dashed border-slate-300 p-6 text-sm text-slate-500">
              This section has not been drafted yet.
            </p>
          )}
        </div>
      </div>

      {section && (
        <button
          className="rounded-xl bg-emerald-600 px-5 py-2.5 font-medium text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50"
          disabled={!allSectionsAccepted || updateMutation.isPending || continueMutation.isPending}
          onClick={() => continueMutation.mutate()}
        >
          {continueMutation.isPending
            ? "Continuing..."
            : allSectionsAccepted
              ? "Continue to verification"
              : "Accept all section blocks to continue"}
        </button>
      )}
    </div>
  );
}