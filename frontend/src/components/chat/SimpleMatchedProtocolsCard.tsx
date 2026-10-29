"use client";

import React from "react";
import { BookOpen, ListChecks } from "lucide-react";
import { formatCriterionValue } from "@/components/chat/pilot/pilot-transcript";

/**
 * Shown once a pilot session reaches RETURN_MATCH: which specific protocol
 * atom(s) actually produced the ESI result (see agent.py's `_result()` ->
 * `matched_atoms`), instead of leaving the patient with a bare ESI number.
 *
 * Deliberately NOT modeled on production's `EvidenceSources.tsx`/
 * `RagCitationDTO`: that shape carries publishing metadata (issuing body,
 * version, effective date, content hash) that `protocol_atoms.jsonl` (a mock
 * corpus) simply does not have. `criteria_text` is shown as-is in English --
 * the same clinical-register sentence the corpus already uses for retrieval
 * -- rather than inventing a translation, matching how SBAR's citations are
 * already shown as opaque atom codes without translation.
 */

// EQ/NEQ/GT/GTE/LT/LTE -> ký hiệu toán học dễ đọc.
const OPERATOR_SYMBOLS: Record<string, string> = {
  EQ: "=",
  NEQ: "≠",
  GT: ">",
  GTE: "≥",
  LT: "<",
  LTE: "≤",
};

interface SatisfiedRequirement {
  fact_target_id: string;
  name: string;
  operator: string;
  expected_value: string | number | boolean | null;
  actual_value: string | number | boolean | null;
}

interface MatchedAtom {
  atom_id: string;
  decision_point: string | null;
  criteria_text: string | null;
  satisfied_requirements?: SatisfiedRequirement[];
}

export function SimpleMatchedProtocolsCard({ matchedAtoms }: { matchedAtoms: MatchedAtom[] }) {
  if (matchedAtoms.length === 0) return null;

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
      <h3 className="flex items-center gap-2 text-sm font-bold text-slate-950 dark:text-slate-50">
        <ListChecks className="size-5 text-sky-700" aria-hidden="true" />
        Tiêu chí phác đồ đã khớp
      </h3>
      <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">
        Đây là (các) tiêu chí trong bộ dữ liệu mô phỏng mà thông tin bạn cung cấp đã thỏa mãn đầy
        đủ, dẫn tới kết luận ESI ở trên -- không phải chẩn đoán chính thức.
      </p>
      <ul className="mt-4 space-y-3">
        {matchedAtoms.map((atom) => (
          <li key={atom.atom_id} className="rounded-xl border border-sky-100 bg-sky-50/60 p-4 dark:border-sky-900 dark:bg-sky-950/40">
            <div className="flex flex-wrap items-center gap-2">
              <BookOpen className="size-4 shrink-0 text-sky-700" aria-hidden="true" />
              {atom.decision_point && (
                <span className="rounded-lg border border-sky-200 bg-card px-2 py-0.5 font-mono text-xs font-bold text-sky-900">
                  {atom.decision_point}
                </span>
              )}
              <span className="font-mono text-xs text-muted-foreground">{atom.atom_id}</span>
            </div>
            {atom.criteria_text && (
              <p className="mt-2 text-sm leading-6 text-slate-800 dark:text-slate-100">{atom.criteria_text}</p>
            )}
            {atom.satisfied_requirements && atom.satisfied_requirements.length > 0 && (
              <ul className="mt-2 space-y-1 text-sm font-semibold text-sky-950 dark:text-sky-100">
                {atom.satisfied_requirements.map((req) => (
                  <li key={req.fact_target_id}>
                    {req.name} {OPERATOR_SYMBOLS[req.operator] ?? req.operator} {formatCriterionValue(req.expected_value)} —
                    bạn báo cáo: {formatCriterionValue(req.actual_value)}
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
