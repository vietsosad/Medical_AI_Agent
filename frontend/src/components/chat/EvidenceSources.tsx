import { useId } from "react";
import { AlertTriangle, FileCheck2, Info, SearchX } from "lucide-react";

import type {
  CaseSupport,
  DecisionStatus,
  EvidenceStatus,
  RagCitation,
} from "@/types/triage-chat";

interface EvidenceSourcesProps {
  citations?: RagCitation[] | null;
  caseSupport?: CaseSupport[] | null;
  decisionStatus?: DecisionStatus | null;
  evidenceStatus?: EvidenceStatus | null;
  retrievalDegradedModes?: string[];
}

function isAuthoritativeCitation(citation: RagCitation): boolean {
  return citation.sourceType === "validated_protocol";
}

function safeSourceUri(uri?: string): string | null {
  if (!uri) return null;
  const normalized = uri.trim();
  return /^https?:\/\//i.test(normalized) ? normalized : null;
}

/**
 * A cosine similarity is not a confidence. Rendering it as "58%" invited
 * exactly the reading it cannot support -- that the system is 58% sure of
 * something clinical -- when it is a distance in an embedding space with no
 * calibrated relationship to a triage decision. The band says what the score
 * can support: how close this case's presentation is to the patient's.
 */
const RELEVANCE_LABELS: Record<CaseSupport["relevanceBand"], string | null> = {
  HIGH: "Mức tương đồng: cao",
  MODERATE: "Mức tương đồng: trung bình",
  LOW: "Mức tương đồng: thấp",
  UNKNOWN: null,
};

function relevanceLabel(support: CaseSupport): string | null {
  return RELEVANCE_LABELS[support.relevanceBand] ?? null;
}

/**
 * What the corpus recorded about the *retrieved* case. UNKNOWN stays UNKNOWN:
 * a case with no agreed level is never rendered as though it had one, and
 * candidate levels are shown as the competing answers they are.
 */
function caseEsiLabel(support: CaseSupport): string {
  if (support.labelStatus === "CONSISTENT" && support.validatedEsiLevel) {
    return `ESI đã kiểm chứng của ca: ${support.validatedEsiLevel}`;
  }
  if (support.candidateEsiLevels.length > 0) {
    return `ESI đề xuất của ca: ${support.candidateEsiLevels.join(" / ")} · chưa thống nhất`;
  }
  return "ESI của ca: chưa xác định";
}

function caseDemographics(support: CaseSupport): string | null {
  const parts = [support.ageBand, support.sex].filter(
    (item): item is string => Boolean(item),
  );
  return parts.length > 0 ? parts.join(" · ") : null;
}

export function EvidenceSources({
  citations,
  caseSupport,
  decisionStatus,
  evidenceStatus,
  retrievalDegradedModes,
}: EvidenceSourcesProps) {
  const authoritativeTitleId = useId();
  const caseSupportTitleId = useId();
  const allCitations = citations ?? [];
  const authoritativeCitations = allCitations.filter(isAuthoritativeCitation);
  const nonAuthoritativeCitations = allCitations.filter(
    (citation) => !isAuthoritativeCitation(citation),
  );
  const supportCases = (caseSupport ?? []).filter(
    (item) => item.retrievalScope === "CASE_SUPPORT" && item.authorityStatus === "NOT_PROTOCOL",
  );
  const retrievalFailed = evidenceStatus === "RETRIEVAL_FAILURE"
    || decisionStatus === "RETRIEVAL_FAILURE";
  const evidenceInsufficient = evidenceStatus === "INSUFFICIENT_EVIDENCE"
    || decisionStatus === "INSUFFICIENT_EVIDENCE";
  const caseOnlyEvidence = evidenceStatus === "CASE_EXAMPLE_SUPPORT";
  const hasDegradedRetrieval = Boolean(retrievalDegradedModes?.length);

  if (
    !retrievalFailed
    && !evidenceInsufficient
    && !caseOnlyEvidence
    && !hasDegradedRetrieval
    && authoritativeCitations.length === 0
    && nonAuthoritativeCitations.length === 0
    && supportCases.length === 0
  ) {
    return null;
  }

  if (retrievalFailed) {
    return (
      <aside
        role="alert"
        className="flex gap-3 border-t border-rose-200 pt-4 text-sm leading-6 text-rose-950 dark:border-rose-800 dark:text-rose-100"
      >
        <SearchX className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
        <div>
          <p className="font-bold">Không thể truy xuất nguồn ở lượt này</p>
          <p>
            Không có nguồn nào trong kết quả này được dùng để xác lập mức ESI. Hệ thống cần thử
            lại hoặc chuyển nhân viên y tế đánh giá.
          </p>
        </div>
      </aside>
    );
  }

  return (
    <aside className="space-y-4 border-t border-slate-200/80 pt-4 dark:border-slate-800" aria-label="Nguồn hỗ trợ">
      {evidenceInsufficient && (
        <div
          role="status"
          className="flex gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm leading-6 text-amber-950 dark:border-amber-800 dark:bg-amber-950/60 dark:text-amber-100"
        >
          <AlertTriangle className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-bold">Nguồn hiện có chưa đủ để hỗ trợ phân loại</p>
            <p>Không suy ra hoặc chốt mức ESI từ các nguồn đang hiển thị.</p>
          </div>
        </div>
      )}

      {hasDegradedRetrieval && (
        <div className="flex gap-3 text-sm leading-6 text-amber-900 dark:text-amber-200">
          <Info className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
          <p>
            Một phần kênh truy xuất đang suy giảm. Chỉ các nguồn đạt đủ điều kiện xác minh bên
            dưới mới được coi là bằng chứng có thẩm quyền.
          </p>
        </div>
      )}

      {authoritativeCitations.length > 0 && (
        <section className="space-y-3" aria-labelledby={authoritativeTitleId}>
          <h3
            id={authoritativeTitleId}
            className="flex items-center gap-2 text-sm font-bold text-emerald-800 dark:text-emerald-300"
          >
            <FileCheck2 className="size-5 shrink-0" aria-hidden="true" />
            Nguồn phác đồ đã duyệt
          </h3>
          <div className="space-y-2">
            {authoritativeCitations.map((citation) => {
              const sourceUri = safeSourceUri(citation.sourceUri);
              const provenance = [
                citation.issuingBody,
                citation.validationStatus === "approved" ? "đã duyệt" : null,
                citation.version ? `phiên bản ${citation.version}` : null,
                citation.section ? `mục ${citation.section}` : null,
                citation.effectiveDate ? `hiệu lực ${citation.effectiveDate}` : null,
                citation.reviewedBy ? `rà soát bởi ${citation.reviewedBy}` : null,
                citation.reviewedAt ? `rà soát ${citation.reviewedAt}` : null,
                citation.calibrationId ? `calibration ${citation.calibrationId}` : null,
                citation.contentHash ? `mã kiểm chứng ${citation.contentHash}` : null,
              ].filter((item): item is string => Boolean(item));
              return (
                <article
                  key={citation.id}
                  className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4 text-sm leading-6 text-slate-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-slate-200"
                >
                  <p className="font-bold text-slate-950 dark:text-white">
                    {sourceUri ? (
                      <a
                        href={sourceUri}
                        target="_blank"
                        rel="noreferrer noopener"
                        className="underline decoration-emerald-300 underline-offset-4 hover:text-emerald-800 focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 dark:hover:text-emerald-200"
                      >
                        {citation.title}
                      </a>
                    ) : citation.title}
                    {citation.protocolId ? ` (${citation.protocolId})` : ""}
                  </p>
                  {provenance.length > 0 && (
                    <p className="mt-1 text-slate-600 dark:text-slate-300">
                      {provenance.join(" · ")}
                    </p>
                  )}
                  <p className="mt-2">{citation.excerpt}</p>
                </article>
              );
            })}
          </div>
        </section>
      )}

      {(supportCases.length > 0 || caseOnlyEvidence) && (
        <section
          className="space-y-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-950 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-100"
          aria-labelledby={caseSupportTitleId}
        >
          <div className="flex items-start gap-2 text-sm leading-6">
            <Info className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
            <div>
              <h3 id={caseSupportTitleId} className="font-bold">Ca tương tự — chỉ hỗ trợ tham khảo</h3>
              <p className="mt-1 flex flex-wrap gap-2 font-mono text-xs font-bold">
                <span className="rounded border border-amber-400 px-2 py-0.5">CASE_SUPPORT</span>
                <span className="rounded border border-amber-400 px-2 py-0.5">NOT_PROTOCOL</span>
              </p>
              <p>
                Đây không phải phác đồ và không có thẩm quyền xác lập mức ESI.
                Mức ESI ghi ở mỗi ca là nhãn của chính ca đó trong kho dữ liệu,
                không phải mức ưu tiên của bạn.
              </p>
            </div>
          </div>
          {supportCases.length > 0 && (
            <div className="space-y-2">
              {supportCases.map((support) => {
                const relevance = relevanceLabel(support);
                const demographics = caseDemographics(support);
                return (
                  <article
                    key={support.caseId}
                    className="rounded-lg border border-amber-200 bg-white/70 p-3 text-sm leading-6 dark:border-amber-900 dark:bg-amber-950/40"
                  >
                    <p className="font-bold">
                      Ca {support.caseId}
                      {demographics ? ` · ${demographics}` : ""}
                    </p>
                    <p className="mt-1">{support.excerpt}</p>
                    {support.symptomConcepts.length > 0 && (
                      <p className="mt-2 flex flex-wrap gap-1.5 text-xs">
                        {support.symptomConcepts.slice(0, 6).map((concept) => (
                          <span
                            key={concept}
                            className="rounded border border-amber-300 px-1.5 py-0.5 font-mono"
                          >
                            {concept}
                          </span>
                        ))}
                      </p>
                    )}
                    <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs font-medium">
                      <span>{caseEsiLabel(support)}</span>
                      {relevance && <span>{relevance}</span>}
                    </p>
                  </article>
                );
              })}
            </div>
          )}
          {supportCases.length === 0 && caseOnlyEvidence && (
            <p className="text-sm leading-6">
              Không có ca nào đủ tương đồng để hiển thị. Hiển thị ít ca — hoặc
              không ca nào — tốt hơn là đưa ra những ca không thực sự giống tình
              trạng hiện tại.
            </p>
          )}
        </section>
      )}

      {nonAuthoritativeCitations.length > 0 && (
        <div className="flex gap-3 text-sm leading-6 text-amber-900 dark:text-amber-200">
          <Info className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
          <p>
            {nonAuthoritativeCitations.length} nguồn tham khảo không được hệ thống xác nhận là phác
            đồ có thẩm quyền đã bị loại khỏi bằng chứng dùng cho phân loại.
          </p>
        </div>
      )}
    </aside>
  );
}
