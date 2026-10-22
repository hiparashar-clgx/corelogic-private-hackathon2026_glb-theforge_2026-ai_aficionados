import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
});

export interface Paper {
  id: string;
  owner_user_id: string;
  title: string;
  current_stage: string;
  target_venue: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface StageStatus {
  stage: string;
  state: "done" | "in_progress" | "blocked" | "pending";
  reason?: string | null;
}

export interface ConfidentialityFlag {
  id: string;
  paper_id: string;
  source_field: string;
  matched_text: string;
  flag_reason: string;
  resolution: "open" | "redacted" | "generalized" | "confirmed_safe";
}

export interface ProblemStatement {
  id: string;
  paper_id: string;
  raw_input: string;
  refined_statement: string;
  research_questions: string[];
  status: "draft" | "accepted";
  confirmed_at: string | null;
}

export interface LiteratureSource {
  id: string;
  paper_id: string;
  title: string;
  authors: string[];
  year: number | null;
  venue: string;
  doi_or_url: string;
  theme: string;
  relevance_summary: string;
  verification_status: "pending" | "verified" | "unverified";
  verification_failure_reason: string | null;
  selected: boolean;
  manually_accepted?: boolean;
  manual_acceptance_reason?: string | null;
}

export interface OriginalityFinding {
  id: string;
  paper_id: string;
  draft_section_id: string;
  flagged_text: string;
  matching_source: string;
  similarity_score: number;
  is_self_plagiarism: boolean;
  status: "open" | "rewritten" | "accepted_with_justification";
  justification: string | null;
}

export interface CitationVerificationResult {
  id: string;
  literature_source_id: string;
  status: "verified" | "unverified" | "pending";
  failure_reason: string | null;
}

export interface FormattingComplianceReport {
  id: string;
  paper_id: string;
  venue: "ieee" | "acm" | "arxiv";
  generated_at: string;
  checks: Array<{
    requirement: string;
    status: "pass" | "fail";
    detail: string | null;
  }>;
}

export interface ContentBlock {
  id: string;
  order: number;
  text: string;
  origin: string;
  accepted: boolean;
}

export interface DraftSection {
  id: string;
  paper_id: string;
  section_type: string;
  blocks: ContentBlock[];
}

export const createPaper = (title: string) => api.post<Paper>("/papers", { title }).then((r) => r.data);

export const getPaper = (paperId: string) => api.get<Paper>(`/papers/${paperId}`).then((r) => r.data);

export const getPaperStatus = (paperId: string) =>
  api.get<StageStatus[]>(`/papers/${paperId}/status`).then((r) => r.data);

export const draftProblemStatement = (paperId: string, rawInput: string) =>
  api
    .post<ProblemStatement>(`/papers/${paperId}/problem-statement:draft`, { raw_input: rawInput })
    .then((r) => r.data);

export const getProblemStatement = (paperId: string) =>
  api.get<ProblemStatement | null>(`/papers/${paperId}/problem-statement`).then((r) => r.data);

export const suggestResearchQuestions = (statementId: string, selectedProblemStatement: string) =>
  api
    .post<{ research_questions: string[] }>(`/problem-statements/${statementId}:research-questions`, {
      selected_problem_statement: selectedProblemStatement,
    })
    .then((r) => r.data.research_questions);

export const acceptProblemStatement = (
  statementId: string,
  refinedStatement: string,
  researchQuestions: string[]
) =>
  api
    .post<ProblemStatement>(`/problem-statements/${statementId}:accept`, {
      refined_statement: refinedStatement,
      research_questions: researchQuestions,
    })
    .then((r) => r.data);

export const listConfidentialityFlags = (paperId: string) =>
  api.get<ConfidentialityFlag[]>(`/papers/${paperId}/confidentiality-flags`).then((r) => r.data);

export const resolveConfidentialityFlag = (
  flagId: string,
  resolution: ConfidentialityFlag["resolution"]
) =>
  api
    .post<ConfidentialityFlag>(`/confidentiality-flags/${flagId}:resolve`, { resolution })
    .then((r) => r.data);

export const runLiteratureSurvey = (paperId: string, query: string, yearRange?: string) =>
  api
    .post<LiteratureSource[]>(`/papers/${paperId}/literature-survey`, {
      query,
      year_range: yearRange || null,
    })
    .then((r) => r.data);

export const listLiteratureSources = (paperId: string) =>
  api.get<LiteratureSource[]>(`/papers/${paperId}/literature-sources`).then((r) => r.data);

export const removeUnverifiedLiteratureSource = (paperId: string, sourceId: string) =>
  api.delete(`/papers/${paperId}/literature-sources/${sourceId}`);

export const correctLiteratureSourceIdentifier = (paperId: string, sourceId: string, doiOrUrl: string) =>
  api.patch<LiteratureSource>(`/papers/${paperId}/literature-sources/${sourceId}`, {
    doi_or_url: doiOrUrl,
  }).then((r) => r.data);

export const addLiteratureSource = (paperId: string, doiOrUrl: string, title = "") =>
  api.post<LiteratureSource>(`/papers/${paperId}/literature-sources`, {
    doi_or_url: doiOrUrl,
    title,
  }).then((r) => r.data);

export const setLiteratureSourceSelection = (paperId: string, sourceId: string, selected: boolean) =>
  api.put<LiteratureSource>(`/papers/${paperId}/literature-sources/${sourceId}/selection`, {
    selected,
  }).then((r) => r.data);

export const setLiteratureSourceManualAcceptance = (
  paperId: string, sourceId: string, accepted: boolean, reason = "",
) =>
  api.put<LiteratureSource>(`/papers/${paperId}/literature-sources/${sourceId}/manual-acceptance`, {
    accepted,
    reason,
  }).then((r) => r.data);

/** A source counts as usable once it is verified or the user manually accepted a failed check. */
export const isSourceCleared = (source: LiteratureSource) =>
  source.verification_status === "verified" ||
  (source.verification_status === "unverified" && !!source.manually_accepted);

export const verifyCitations = (paperId: string) =>
  api.post<CitationVerificationResult[]>(`/papers/${paperId}/citations:verify`).then((r) => r.data);

export const checkOriginality = (paperId: string) =>
  api.post<OriginalityFinding[]>(`/papers/${paperId}/originality:check`).then((r) => r.data);

export const listOriginalityFindings = (paperId: string) =>
  api.get<OriginalityFinding[]>(`/papers/${paperId}/originality-findings`).then((r) => r.data);

export const getRewriteSuggestion = (findingId: string) =>
  api.post<{ suggestion: string }>(`/originality-findings/${findingId}:rewrite-suggestion`).then((r) => r.data);

export const resolveOriginalityFinding = (
  findingId: string,
  status: OriginalityFinding["status"],
  justification?: string
) =>
  api
    .post<OriginalityFinding>(`/originality-findings/${findingId}:resolve`, { status, justification })
    .then((r) => r.data);

export const applyFormatting = (paperId: string, venue: FormattingComplianceReport["venue"]) =>
  api
    .post<FormattingComplianceReport>(`/papers/${paperId}/formatting:apply`, { venue })
    .then((r) => r.data);

export const getFormattingReport = (paperId: string) =>
  api.get<FormattingComplianceReport>(`/papers/${paperId}/formatting/compliance-report`).then((r) => r.data);

export function filenameFromDisposition(header: string | undefined): string | null {
  if (!header) return null;
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (encoded) {
    try {
      return decodeURIComponent(encoded[1].trim());
    } catch {
      // fall through to the plain filename parameter
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(header);
  return plain ? plain[1].trim() : null;
}

export async function exportPaperDocx(paperId: string): Promise<{ blob: Blob; filename: string }> {
  try {
    const response = await api.post<Blob>(`/papers/${paperId}/export`, null, {
      params: { format: "docx" },
      responseType: "blob",
    });
    return { blob: response.data, filename: filenameFromDisposition(response.headers["content-disposition"]) ?? "paper.docx" };
  } catch (error) {
    // Blob responses hide the JSON error detail; decode it so callers can read response.data.detail.
    if (axios.isAxiosError(error) && error.response?.data instanceof Blob) {
      try {
        error.response.data = JSON.parse(await error.response.data.text());
      } catch {
        // leave the original payload in place
      }
    }
    throw error;
  }
}

export const advancePaper = (paperId: string, targetStage: string) =>
  api.post<Paper>(`/papers/${paperId}:advance`, { target_stage: targetStage }).then((r) => r.data);

export const draftSection = (paperId: string, sectionType: string, userNotes = "") =>
  api
    .post<DraftSection>(`/papers/${paperId}/sections/${sectionType}:draft`, { user_notes: userNotes })
    .then((r) => r.data);

export const getDraftSection = (paperId: string, sectionType: string) =>
  api.get<DraftSection>(`/papers/${paperId}/sections/${sectionType}`).then((r) => r.data);

export const updateContentBlock = (
  paperId: string,
  blockId: string,
  changes: { text?: string; accepted?: boolean }
) =>
  api.patch<ContentBlock>(`/papers/${paperId}/sections/blocks/${blockId}`, changes).then((r) => r.data);
