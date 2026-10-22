import clsx from "clsx";
import type { StageStatus } from "../api/client";

const STAGE_LABELS: Record<string, string> = {
  framing: "Problem Framing",
  literature_survey: "Literature Survey",
  drafting: "Drafting",
  verification: "Citation & Originality",
  formatting: "Publisher Formatting",
  ready_for_submission: "Ready for Submission",
};

const STATE_STYLES: Record<string, string> = {
  done: "bg-emerald-100 text-emerald-700 border-emerald-200",
  in_progress: "bg-brand-100 text-brand-700 border-brand-200",
  blocked: "bg-rose-100 text-rose-700 border-rose-200",
  pending: "bg-slate-100 text-slate-500 border-slate-200",
};

export default function StageBadge({ status }: { status: StageStatus }) {
  return (
    <div
      className={clsx(
        "flex flex-col gap-1 rounded-xl border px-4 py-3 text-sm",
        STATE_STYLES[status.state]
      )}
    >
      <div className="flex items-center justify-between">
        <span className="font-semibold">{STAGE_LABELS[status.stage] ?? status.stage}</span>
        <span className="text-xs uppercase tracking-wide">{status.state.replace("_", " ")}</span>
      </div>
      {status.reason && <p className="text-xs opacity-80">{status.reason}</p>}
    </div>
  );
}
