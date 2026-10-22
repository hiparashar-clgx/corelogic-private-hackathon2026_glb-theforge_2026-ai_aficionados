import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { createPaper } from "../api/client";

export default function HomePage() {
  const [title, setTitle] = useState("");
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { mutate, isPending } = useMutation({
    mutationFn: createPaper,
    onSuccess: (paper) => {
      queryClient.invalidateQueries();
      navigate(`/papers/${paper.id}/framing`);
    },
  });

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-3xl font-bold tracking-tight text-slate-900">Start a new research paper</h1>
      <p className="mt-2 text-slate-500">
        Describe the problem you have worked on at Cotality. We'll help you frame it, survey the
        literature, draft it, and format it for your target venue — with confidentiality and
        originality checks at every step.
      </p>

      <form
        className="mt-6 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (title.trim()) mutate(title.trim());
        }}
      >
        <input
          className="flex-1 rounded-xl border border-slate-300 px-4 py-2.5 shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
          placeholder="Paper title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <button
          type="submit"
          disabled={isPending}
          className="rounded-xl bg-brand-600 px-5 py-2.5 font-medium text-white shadow-sm transition hover:bg-brand-700 disabled:opacity-50"
        >
          {isPending ? "Creating…" : "Create"}
        </button>
      </form>
    </div>
  );
}
