import { Link } from "react-router-dom";

export default function BackNavigation({ to, label }: { to: string; label: string }) {
  return (
    <Link
      to={to}
      className="inline-flex rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
    >
      &larr; Back to {label}
    </Link>
  );
}
