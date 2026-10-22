import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { getFormattingReport, getPaper, getPaperStatus } from "../api/client";
import StageBadge from "../components/StageBadge";
import FormattingReview from "../components/FormattingReview";
import BackNavigation from "../components/BackNavigation";

const previousSteps: Record<string, { route: string; label: string }> = {
  framing: { route: "framing", label: "problem framing" },
  literature_survey: { route: "framing", label: "problem framing" },
  drafting: { route: "literature", label: "literature survey" },
  verification: { route: "drafting", label: "drafting" },
  formatting: { route: "verification", label: "citation & originality" },
  ready_for_submission: { route: "verification", label: "publisher formatting" },
};

export default function StatusDashboardPage() {
  const { paperId } = useParams<{ paperId: string }>();
  const navigate = useNavigate();

  const paperQuery = useQuery({ queryKey: ["paper", paperId], queryFn: () => getPaper(paperId!), enabled: !!paperId });
  const statusQuery = useQuery({
    queryKey: ["status", paperId],
    queryFn: () => getPaperStatus(paperId!),
    enabled: !!paperId,
    refetchInterval: 5000,
  });
  const hasFormatting = paperQuery.data?.current_stage === "formatting" ||
    paperQuery.data?.current_stage === "ready_for_submission";
  const reportQuery = useQuery({
    queryKey: ["formatting-report", paperId],
    queryFn: () => getFormattingReport(paperId!),
    enabled: !!paperId && hasFormatting,
  });

  const previousStep = previousSteps[paperQuery.data?.current_stage ?? ""];

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <BackNavigation
        to={previousStep ? `/papers/${paperId}/${previousStep.route}` : "/"}
        label={previousStep?.label ?? "papers"}
      />
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{paperQuery.data?.title ?? "Paper status"}</h1>
        <p className="mt-1 text-slate-500">Track progress across every stage of the pipeline.</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {(statusQuery.data ?? []).map((s) => (
          <StageBadge key={s.stage} status={s} />
        ))}
      </div>

      {paperQuery.data?.current_stage === "literature_survey" && (
        <button
          className="rounded-xl bg-brand-600 px-5 py-2.5 font-medium text-white shadow-sm hover:bg-brand-700"
          onClick={() => navigate(`/papers/${paperId}/literature`)}
        >
          Continue to literature survey
        </button>
      )}

      {paperQuery.data?.current_stage === "drafting" && (
        <button
          className="rounded-xl bg-brand-600 px-5 py-2.5 font-medium text-white shadow-sm hover:bg-brand-700"
          onClick={() => navigate(`/papers/${paperId}/drafting`)}
        >
          Continue to drafting
        </button>
      )}

      {paperQuery.data?.current_stage === "verification" && (
        <button
          className="rounded-xl bg-brand-600 px-5 py-2.5 font-medium text-white shadow-sm hover:bg-brand-700"
          onClick={() => navigate(`/papers/${paperId}/verification`)}
        >
          Continue to citation &amp; originality
        </button>
      )}

      {hasFormatting && (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-slate-900">Next step: submission readiness</h2>
          {reportQuery.isLoading && <p className="text-sm text-slate-600">Loading formatting results...</p>}
          {reportQuery.isError && (
            <div role="alert" className="space-y-2 text-sm text-rose-700">
              <p>Could not load the saved formatting report.</p>
              <button onClick={() => reportQuery.refetch()}>Retry loading report</button>
            </div>
          )}
          {reportQuery.data && (
            <FormattingReview
              key={reportQuery.data.id}
              paperId={paperId!}
              report={reportQuery.data}
              ready={paperQuery.data?.current_stage === "ready_for_submission"}
              showStatusLink={false}
            />
          )}
          <button
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700"
            onClick={() => navigate(`/papers/${paperId}/verification`)}
          >
            Continue to publisher formatting
          </button>
        </section>
      )}
    </div>
  );
}
