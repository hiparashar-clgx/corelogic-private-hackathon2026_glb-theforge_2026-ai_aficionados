import axios from "axios";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { advancePaper, type FormattingComplianceReport } from "../api/client";
import PaperDownload from "./PaperDownload";

export default function FormattingReview({
  paperId,
  report,
  ready = false,
  showStatusLink = true,
}: {
  paperId: string;
  report: FormattingComplianceReport;
  ready?: boolean;
  showStatusLink?: boolean;
}) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const advanceMutation = useMutation({
    mutationFn: () => advancePaper(paperId, "ready_for_submission"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["paper", paperId] });
      queryClient.invalidateQueries({ queryKey: ["status", paperId] });
    },
  });
  const checksPassed = report.checks.length > 0 && report.checks.every((check) => check.status === "pass");
  const isReady = ready || advanceMutation.isSuccess;

  return (
    <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4">
      <div>
        <h3 className="font-semibold text-emerald-800">Formatting applied for {report.venue.toUpperCase()}</h3>
        <p className="text-sm text-slate-600">Review the publisher compliance results before marking your paper ready for submission.</p>
      </div>
      <ul className="space-y-2">
        {report.checks.map((check) => (
          <li key={check.requirement} className="text-sm">
            <span className={check.status === "pass" ? "font-medium text-emerald-700" : "font-medium text-rose-700"}>
              {check.status.toUpperCase()}
            </span>
            {" · "}{check.requirement}
            {check.detail && <p className="ml-4 text-slate-600">{check.detail}</p>}
          </li>
        ))}
      </ul>
      {isReady ? (
        <>
          <p role="status" className="font-medium text-emerald-800">
            Ready for submission. This marks your paper ready; it does not submit it to a publisher.
          </p>
          <PaperDownload paperId={paperId} />
        </>
      ) : (
        <>
          {!checksPassed && (
            <p className="text-sm text-amber-800">
              Resolve the failed or missing compliance checks in drafting, then apply formatting again.
            </p>
          )}
          <button
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            disabled={!checksPassed || advanceMutation.isPending}
            onClick={() => advanceMutation.mutate()}
          >
            {advanceMutation.isPending ? "Updating readiness..." : "Mark ready for submission"}
          </button>
        </>
      )}
      {advanceMutation.isError && (
        <p role="alert" className="text-sm text-rose-700">
          {axios.isAxiosError(advanceMutation.error)
            ? advanceMutation.error.response?.data?.detail ?? "Could not mark the paper ready for submission."
            : "Could not mark the paper ready for submission."}
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        <button
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
          onClick={() => navigate(`/papers/${paperId}/drafting`)}
        >
          Return to drafting
        </button>
        <button
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
          onClick={() => navigate(`/papers/${paperId}/verification`)}
        >
          Review citations &amp; reapply formatting
        </button>
        {showStatusLink && (
          <button
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
            onClick={() => navigate(`/papers/${paperId}/status`)}
          >
            View paper status
          </button>
        )}
      </div>
    </section>
  );
}
