import { useWorkflowState } from "../WorkflowState";
import type { LiteratureSource } from "../api/client";

interface Props {
  source: LiteratureSource;
  disabled: boolean;
  onAccept: (reason: string) => void;
  onRevoke: () => void;
}

/** Lets the author override a failed retrieval check (e.g. paywalled source) with an audited reason. */
export default function ManualAcceptanceControls({ source, disabled, onAccept, onRevoke }: Props) {
  const [reason, setReason] = useWorkflowState(`${source.paper_id}:source:${source.id}:acceptanceReason`, "");

  if (source.verification_status !== "unverified") return null;

  if (source.manually_accepted) {
    return (
      <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
        <p className="text-sm font-medium text-amber-900">Manually accepted by you</p>
        {source.manual_acceptance_reason && (
          <p className="mt-1 text-sm text-amber-800">Reason: {source.manual_acceptance_reason}</p>
        )}
        <button
          className="mt-2 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-sm font-medium text-amber-900 disabled:opacity-50"
          disabled={disabled}
          onClick={onRevoke}
        >
          Revoke manual acceptance
        </button>
      </div>
    );
  }

  return (
    <div className="mt-3 space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <label htmlFor={`accept-reason-${source.id}`} className="text-sm font-medium text-slate-700">
        Accept anyway (reason required)
      </label>
      <input
        id={`accept-reason-${source.id}`}
        className="w-full rounded-lg border border-slate-300 p-2 text-sm"
        placeholder="e.g. Paywalled; confirmed the paper exists via the library"
        value={reason}
        disabled={disabled}
        onChange={(event) => setReason(event.target.value)}
      />
      <button
        className="rounded-lg bg-amber-600 px-3 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
        disabled={disabled || !reason.trim()}
        onClick={() => {
          if (window.confirm(
            `Accept "${source.title}" even though automatic verification failed? You are confirming the source exists and supports your claims.`
          )) {
            onAccept(reason.trim());
            setReason("");
          }
        }}
      >
        Manually accept source
      </button>
    </div>
  );
}
