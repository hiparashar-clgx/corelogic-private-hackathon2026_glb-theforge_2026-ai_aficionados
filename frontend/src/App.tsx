import { type ComponentType } from "react";
import { Routes, Route, Link, useLocation, useParams } from "react-router-dom";
import HomePage from "./pages/HomePage";
import ProblemFramingPage from "./pages/ProblemFramingPage";
import StatusDashboardPage from "./pages/StatusDashboardPage";
import LiteratureSurveyPage from "./pages/LiteratureSurveyPage";
import DraftingPage from "./pages/DraftingPage";
import VerificationPage from "./pages/VerificationPage";
import { WorkflowStateProvider } from "./WorkflowState";

function PaperPage({ component: Component }: { component: ComponentType }) {
  const { paperId } = useParams();
  return <Component key={paperId} />;
}

function NavLink({ to, label }: { to: string; label: string }) {
  const location = useLocation();
  const active = location.pathname === to;
  return (
    <Link
      to={to}
      className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
        active ? "bg-brand-100 text-brand-700" : "text-slate-600 hover:bg-slate-100"
      }`}
    >
      {label}
    </Link>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-brand-500 text-white font-bold">CS</div>
            <span className="text-lg font-semibold text-slate-900">CotalityScholar</span>
          </div>
          <nav className="flex gap-1">
            <NavLink to="/" label="New Publication" />
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <WorkflowStateProvider>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/papers/:paperId/framing" element={<PaperPage component={ProblemFramingPage} />} />
            <Route path="/papers/:paperId/literature" element={<PaperPage component={LiteratureSurveyPage} />} />
            <Route path="/papers/:paperId/drafting" element={<PaperPage component={DraftingPage} />} />
            <Route path="/papers/:paperId/verification" element={<PaperPage component={VerificationPage} />} />
            <Route path="/papers/:paperId/status" element={<PaperPage component={StatusDashboardPage} />} />
          </Routes>
        </WorkflowStateProvider>
      </main>
    </div>
  );
}
