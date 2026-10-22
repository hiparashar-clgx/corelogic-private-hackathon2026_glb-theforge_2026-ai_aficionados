import axios from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  exportPaperDocx,
  listConfidentialityFlags,
  resolveConfidentialityFlag,
  type ConfidentialityFlag,
} from "../api/client";

type Resolution = Exclude<ConfidentialityFlag["resolution"], "open">;

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function errorDetail(error: unknown, fallback: string): string {
  return axios.isAxiosError(error) ? error.response?.data?.detail ?? fallback : fallback;
}

export default function PaperDownload({ paperId }: { paperId: string }) {
  const queryClient = useQueryClient();
  const downloadMutation = useMutation({
    mutationFn: () => exportPaperDocx(paperId),
    onSuccess: ({ blob, filename }) => saveBlob(blob, filename),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["flags", paperId] }),
  });
  const blockedByFlags =
    axios.isAxiosError(downloadMutation.error) && downloadMutation.error.response?.status === 409;
  const flagsQuery = useQuery({
    queryKey: ["flags", paperId],
    queryFn: () => listConfidentialityFlags(paperId),
    enabled: blockedByFlags,
  });
  const openFlags = (flagsQuery.data ?? []).filter((flag) => flag.resolution === "open");
  const resolveMutation = useMutation({
    mutationFn: (vars: { flagId: string; resolution: Resolution }) =>
      resolveConfidentialityFlag(vars.flagId, vars.resolution),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["flags", paperId] }),
  });

  return (
    <div className="space-y-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4">
      <div>
        <h4 className="font-semibold text-emerald-900">Download your paper</h4>
        <p className="text-sm text-slate-600">
          Word document with the title, every section in order, and a numbered reference list.
        </p>
      </div>
      <button
        className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
        disabled={downloadMutation.isPending}
        onClick={() => downloadMutation.mutate()}
      >
        {downloadMutation.isPending ? "Preparing document..." : blockedByFlags ? "Try download again" : "Download paper (.docx)"}
      </button>
      {downloadMutation.isSuccess && (
        <p role="status" className="text-sm text-emerald-800">Downloaded {downloadMutation.data.filename}.</p>
      )}
      {downloadMutation.isError && (
        <p role="alert" className="text-sm text-rose-700">
          {errorDetail(downloadMutation.error, "The paper could not be downloaded.")}
        </p>
      )}
      {blockedByFlags && openFlags.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm text-slate-700">
            The final check found text that may be confidential. Redacted or generalized text is replaced with
            [REDACTED] in the file; confirm items that are safe to keep.
          </p>
          <ul className="space-y-2">
            {openFlags.map((flag) => (
              <li key={flag.id} className="flex items-center justify-between gap-4 rounded-lg bg-white px-3 py-2 shadow-sm">
                <div>
                  <p className="text-sm font-medium text-slate-800">&quot;{flag.matched_text}&quot;</p>
                  <p className="text-xs text-slate-500">{flag.flag_reason}</p>
                </div>
                <div className="flex shrink-0 gap-2">
                  {(
                    [
                      ["redacted", "Redact"],
                      ["generalized", "Generalize"],
                      ["confirmed_safe", "Confirm safe"],
                    ] as const
                  ).map(([resolution, label]) => (
                    <button
                      key={resolution}
                      disabled={resolveMutation.isPending}
                      className="rounded-lg bg-slate-100 px-2 py-1 text-xs font-medium hover:bg-slate-200 disabled:opacity-50"
                      onClick={() => resolveMutation.mutate({ flagId: flag.id, resolution })}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
      {blockedByFlags && flagsQuery.isSuccess && openFlags.length === 0 && (
        <p className="text-sm text-slate-700">All flagged items are resolved. Download the paper again.</p>
      )}
      {resolveMutation.isError && (
        <p role="alert" className="text-sm text-rose-700">
          {errorDetail(resolveMutation.error, "The confidentiality flag could not be resolved.")}
        </p>
      )}
    </div>
  );
}
