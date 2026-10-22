# ResearchAssist

Multi-agent system that helps Cotality employees turn a work problem statement into a
submission-ready research paper — problem framing, literature survey, guided drafting, citation and
originality verification, and publisher-format compliance — with confidentiality/IP screening
enforced at every stage. See [specs/001-research-paper-agents](specs/001-research-paper-agents) for
the full spec, plan, research decisions, data model, and API contracts.

## Stack

- **Backend** (`backend/`): Python 3.12, FastAPI, [Google Agent Development Kit](https://github.com/google/adk-python)
  for every agent, Google Gemini through either the native API or a LiteLLM proxy, SQLModel/PostgreSQL for persistence.
- **Frontend** (`frontend/`): React + TypeScript + Vite + Tailwind CSS, web-only (no mobile app).

## Run locally

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
New-Item -ItemType File .env   # configure direct Gemini or the LiteLLM proxy
uvicorn src.api.main:app --reload
```

API docs: http://localhost:8000/docs

The GitHub copy includes only `backend/src/` and `backend/requirements.txt` from the
backend. Environment files (including `.env.example`), databases, virtual environments,
and backend tests stay local. Create and configure `backend/.env` locally before running.
Frontend files are included except `node_modules/`, environment files, and Python caches.
`frontend-backend-README.md` is also excluded.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

Each workflow page has a **Back to ...** link to the previous step. The status dashboard
uses the paper's current stage to choose the previous step, and publisher formatting
includes a link back to the citation review on the same page. These links navigate only;
they do not roll back the paper's stage or undo saved work. Form inputs and selections are
retained per paper while navigating within the app, including search filters, framing choices,
draft section/notes, and verification/formatting choices. This temporary state lives only in
memory: refreshing or closing the tab clears unsubmitted edits. Saved framing, sources, and
draft blocks are reloaded from the server. Save edits before refreshing or closing the tab.
The Papers page is the starting point, so it has no previous step.

## Literature survey results

Literature searches use the search query and each accepted research question separately, merge
duplicate sources, and filter candidates for relevance using their titles and available full
abstracts. Only selected, retrieved sources are displayed with their relevance summaries and links.
If no sources qualify, the page shows **No relevant sources found** instead of offering to accept
an empty source list. Refine the keywords or widen the optional year range and search again.

Before drafting, tick the checkbox on each source you want to use (all sources start selected)
and use **Add a source manually** to add a DOI or URL that the search missed (an optional title
can be supplied; duplicates of an existing DOI/URL are rejected). Then click **Verify / retry
citations** — only selected sources are checked. Each source shows its verification status and
any failure reason. For a failed source, retry the check, correct its DOI/URL and save it (which
resets verification to pending), untick it to exclude it, explicitly remove it, or **manually
accept** it with a required reason (for example, a paywalled source you have checked yourself).
A manually accepted source stays flagged as unverified with your reason recorded in the audit
log, and the acceptance can be revoked. A later successful re-check replaces the override with a
normal verification, and correcting the DOI/URL clears it. Manually accepted sources show a
**manually accepted** badge with your reason and do not block formatting. DOIs whose publisher
site blocks automated requests (for example ACM's `dl.acm.org`, which returns 403) are confirmed
against the CrossRef registry instead.
At least one source must be selected, and every selected source must pass verification (or be
manually accepted) before
**Accept selected sources and continue** is enabled. Excluded sources do not block drafting and
are not passed to the drafting agent. A source already cited in a draft cannot be excluded.
The backend also enforces these requirements before stage advancement and every
draft-generation request, including direct API calls. New searches retain earlier sources.

Citations are verified only once, on the Literature survey page. The post-draft **Citation &
originality** page shows a read-only citation summary (verified / manually accepted, with a
**Manage sources in literature survey** link for any changes) and is where text-similarity
findings are resolved before publisher formatting. DOI/URL verification only
checks source retrievability; authors must still confirm that sources support their claims.

After applying publisher formatting, review the compliance results and click **Mark ready for
submission** once all checks pass. Failed checks require revising the draft and reapplying
formatting. The saved report and next-step actions remain available on the paper status dashboard
after a reload. After successful readiness confirmation, **Ready for Submission** shows **Done**
on the status dashboard, including after a reload. Marking a paper ready does not submit it to a publisher; the backend rechecks
citation, originality, and confidentiality gates before updating readiness.

### Tests

```powershell
cd backend
pytest
```

See [specs/001-research-paper-agents/quickstart.md](specs/001-research-paper-agents/quickstart.md)
for a full end-to-end walkthrough of each user story.

To route Gemini through a LiteLLM proxy, set `LITELLM_API_KEY`, `LITELLM_BASE_URL`, and
`LITELLM_MODEL` in `backend/.env`. Use the model name or deployment alias configured in your
proxy. When `LITELLM_API_KEY` is blank, the backend uses `GOOGLE_API_KEY` and `GEMINI_MODEL`.
