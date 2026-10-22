import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { useWorkflowState } from "../WorkflowState";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import BackNavigation from "../components/BackNavigation";
import {
  acceptProblemStatement,
  draftProblemStatement,
  getProblemStatement,
  listConfidentialityFlags,
  resolveConfidentialityFlag,
  suggestResearchQuestions,
} from "../api/client";

function splitProblemStatement(refinedStatement: string) {
  const [context = "", ...problemParts] = refinedStatement.trim().split(/\n\s*\n/);
  const problemText = problemParts.length > 0 ? problemParts.join("\n\n") : context;
  const problemContext = problemParts.length > 0 ? context : "";
  const statements = problemText
    .split(/\r?\n/)
    .map((line) => line.replace(/^\s*(?:\d+[.)]|[-*])\s*/, "").trim())
    .filter(Boolean);

  return { context: problemContext, statements };
}

export default function ProblemFramingPage() {
  const { paperId } = useParams<{ paperId: string }>();
  const navigate = useNavigate();
  const [rawInput, setRawInput] = useWorkflowState(`${paperId}:framing:rawInput`, "");
  const [context, setContext] = useWorkflowState(`${paperId}:framing:context`, "");
  const [problemStatements, setProblemStatements] = useWorkflowState<string[]>(`${paperId}:framing:statements`, []);
  const [selectedProblemStatement, setSelectedProblemStatement] = useWorkflowState<number | null>(`${paperId}:framing:selection`, null);
  const selectedProblemStatementRef = useRef<string | null>(
    selectedProblemStatement === null ? null : problemStatements[selectedProblemStatement]?.trim() ?? null
  );
  const [questions, setQuestions] = useWorkflowState<string[]>(`${paperId}:framing:questions`, []);
  const [questionSuggestionError, setQuestionSuggestionError] = useState<string | null>(null);
  const [statementId, setStatementId] = useWorkflowState<string | null>(`${paperId}:framing:statementId`, null);
  const [initialized, setInitialized] = useWorkflowState(`${paperId}:framing:initialized`, false);
  const statementQuery = useQuery({
    queryKey: ["problem-statement", paperId],
    queryFn: () => getProblemStatement(paperId!),
    enabled: !!paperId && !initialized,
  });
  useEffect(() => {
    if (initialized || !statementQuery.isSuccess) return;
    const saved = statementQuery.data;
    if (saved) {
      const framed = splitProblemStatement(saved.refined_statement);
      setStatementId(saved.id);
      setRawInput((current) => current || saved.raw_input);
      setContext(framed.context);
      setProblemStatements(framed.statements);
      setSelectedProblemStatement(saved.status === "accepted" ? 0 : null);
      selectedProblemStatementRef.current = saved.status === "accepted" ? framed.statements[0]?.trim() ?? null : null;
      setQuestions(saved.research_questions);
    }
    setInitialized(true);
  }, [initialized, statementQuery.isSuccess, statementQuery.data, setStatementId, setRawInput,
    setContext, setProblemStatements, setSelectedProblemStatement, setQuestions, setInitialized]);

  const draftMutation = useMutation({
    mutationFn: () => draftProblemStatement(paperId!, rawInput),
    onSuccess: (statement) => {
      setStatementId(statement.id);
      setInitialized(true);
      const framedStatement = splitProblemStatement(statement.refined_statement);
      setContext(framedStatement.context);
      setProblemStatements(framedStatement.statements);
      setSelectedProblemStatement(null);
      selectedProblemStatementRef.current = null;
      setQuestions([]);
      setQuestionSuggestionError(null);
      flagsQuery.refetch();
    },
  });

  const flagsQuery = useQuery({
    queryKey: ["flags", paperId],
    queryFn: () => listConfidentialityFlags(paperId!),
    enabled: !!paperId,
  });

  const resolveMutation = useMutation({
    mutationFn: (vars: { flagId: string; resolution: "redacted" | "confirmed_safe" | "generalized" }) =>
      resolveConfidentialityFlag(vars.flagId, vars.resolution),
    onSuccess: () => flagsQuery.refetch(),
  });

  const questionMutation = useMutation({
    mutationFn: (selectedStatement: string) => suggestResearchQuestions(statementId!, selectedStatement),
    onSuccess: (suggestedQuestions, requestedStatement) => {
      if (selectedProblemStatementRef.current === requestedStatement) {
        setQuestions(suggestedQuestions);
        setQuestionSuggestionError(null);
      }
    },
    onError: (mutationError: any, requestedStatement) => {
      if (selectedProblemStatementRef.current === requestedStatement) {
        setQuestionSuggestionError(
          mutationError.response?.data?.detail ?? "Research questions could not be generated."
        );
      }
      flagsQuery.refetch();
    },
  });

  const selectProblemStatement = (index: number) => {
    const selectedStatement = problemStatements[index]?.trim() ?? "";
    setSelectedProblemStatement(index);
    selectedProblemStatementRef.current = selectedStatement;
    setQuestions([]);
    setQuestionSuggestionError(null);
    if (statementId && selectedStatement) {
      questionMutation.mutate(selectedStatement);
    }
  };

  const requestResearchQuestions = () => {
    if (selectedProblemStatement === null) return;
    const selectedStatement = problemStatements[selectedProblemStatement]?.trim() ?? "";
    if (!selectedStatement || !statementId) return;
    selectedProblemStatementRef.current = selectedStatement;
    setQuestions([]);
    setQuestionSuggestionError(null);
    questionMutation.mutate(selectedStatement);
  };

  const acceptMutation = useMutation({
    mutationFn: () =>
      acceptProblemStatement(
        statementId!,
        [
          context.trim(),
          problemStatements[selectedProblemStatement!].trim(),
        ]
          .filter(Boolean)
          .join("\n\n"),
        questions
      ),
    onSuccess: () => navigate(`/papers/${paperId}/status`),
  });

  const openFlags = (flagsQuery.data ?? []).filter((f) => f.resolution === "open");

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <BackNavigation to="/" label="papers" />
      {statementQuery.isLoading && <p className="text-sm text-slate-500">Loading saved framing...</p>}
      {statementQuery.isError && (
        <div role="alert" className="text-sm text-rose-700">
          <p>{axios.isAxiosError(statementQuery.error)
            ? statementQuery.error.response?.data?.detail ?? "Could not load saved framing."
            : "Could not load saved framing."}</p>
          <button onClick={() => statementQuery.refetch()}>Retry loading framing</button>
        </div>
      )}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Frame your problem statement</h1>
        <p className="mt-1 text-slate-500">
          Describe the problem in your own words. Anything that looks confidential will be
          flagged below for you to resolve before continuing.
        </p>
      </div>

      <textarea
        className="h-32 w-full rounded-xl border border-slate-300 p-4 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
        placeholder="e.g. We noticed our valuation model underperforms for..."
        value={rawInput}
        onChange={(e) => setRawInput(e.target.value)}
      />
      <button
        className="rounded-xl bg-brand-600 px-5 py-2.5 font-medium text-white shadow-sm hover:bg-brand-700 disabled:opacity-50"
        disabled={!rawInput.trim() || draftMutation.isPending || !initialized}
        onClick={() => draftMutation.mutate()}
      >
        {draftMutation.isPending ? "Framing…" : "Generate problem statement"}
      </button>

      {openFlags.length > 0 && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
          <h2 className="font-semibold text-rose-700">Possible confidential content found</h2>
          <ul className="mt-2 space-y-2">
            {openFlags.map((flag) => (
              <li key={flag.id} className="flex items-center justify-between rounded-lg bg-white px-3 py-2 shadow-sm">
                <div>
                  <p className="text-sm font-medium text-slate-800">"{flag.matched_text}"</p>
                  <p className="text-xs text-slate-500">{flag.flag_reason}</p>
                </div>
                <div className="flex gap-2">
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
        </div>
      )}

      {statementId && (
        <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          {context && (
            <div>
              <label className="text-sm font-medium text-slate-700">Context</label>
              <textarea
                className="mt-1 h-20 w-full rounded-lg border border-slate-300 p-3"
                value={context}
                onChange={(e) => setContext(e.target.value)}
              />
            </div>
          )}
          <div>
            <h2 className="text-sm font-medium text-slate-700">Problem Statements:</h2>
            <ol className="mt-2 space-y-2">
              {problemStatements.map((statement, index) => (
                <li key={index} className="flex items-start gap-2 rounded-lg border border-slate-200 p-3">
                  <input
                    type="radio"
                    name="selected-problem-statement"
                    aria-label={`Select problem statement ${index + 1}`}
                    className="mt-3"
                    checked={selectedProblemStatement === index}
                    onChange={() => selectProblemStatement(index)}
                  />
                  <span className="pt-2 text-sm font-medium text-slate-700">{index + 1})</span>
                  <textarea
                    aria-label={`Problem statement ${index + 1}`}
                    className="min-h-12 w-full rounded-lg border border-slate-300 p-3"
                    rows={2}
                    value={statement}
                    onChange={(e) => {
                      const next = [...problemStatements];
                      next[index] = e.target.value;
                      setProblemStatements(next);
                      if (selectedProblemStatement === index && !e.target.value.trim()) {
                        setSelectedProblemStatement(null);
                        selectedProblemStatementRef.current = null;
                        setQuestions([]);
                      } else if (selectedProblemStatement === index) {
                        selectedProblemStatementRef.current = e.target.value.trim();
                        setQuestions([]);
                        setQuestionSuggestionError(null);
                      }
                    }}
                  />
                </li>
              ))}
            </ol>
            {problemStatements.length > 0 && (
              <p className="mt-2 text-sm text-slate-500">
                Select the relevant problem statement for publication.
              </p>
            )}
            {selectedProblemStatement !== null && (
              <div className="mt-3">
                <button
                  type="button"
                  className="rounded-lg bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 disabled:opacity-50"
                  disabled={questionMutation.isPending}
                  onClick={requestResearchQuestions}
                >
                  {questionMutation.isPending
                    ? "Suggesting research questions…"
                    : questions.length > 0
                      ? "Regenerate research questions"
                      : "Suggest research questions"}
                </button>
                {questionSuggestionError && (
                  <p role="alert" className="mt-2 text-sm text-rose-700">{questionSuggestionError}</p>
                )}
              </div>
            )}
          </div>
          {questions.length > 0 && (
            <div>
              <label className="text-sm font-medium text-slate-700">Research questions</label>
              {questions.map((q, i) => (
                <input
                  key={i}
                  className="mt-1 w-full rounded-lg border border-slate-300 p-2"
                  value={q}
                  onChange={(e) => {
                    const next = [...questions];
                    next[i] = e.target.value;
                    setQuestions(next);
                  }}
                />
              ))}
            </div>
          )}
          <button
            className="rounded-xl bg-emerald-600 px-5 py-2.5 font-medium text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50"
            disabled={
              openFlags.length > 0 ||
              acceptMutation.isPending ||
              questionMutation.isPending ||
              selectedProblemStatement === null ||
              !problemStatements[selectedProblemStatement]?.trim()
            }
            onClick={() => acceptMutation.mutate()}
          >
            {openFlags.length > 0 ? "Resolve flags to continue" : "Accept & continue"}
          </button>
        </div>
      )}
    </div>
  );
}
