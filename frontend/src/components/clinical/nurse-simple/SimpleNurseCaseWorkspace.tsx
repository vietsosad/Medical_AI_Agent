"use client";

import { useMemo } from "react";
import { useSearchParams } from "next/navigation";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  FileText,
  Lock,
  MessagesSquare,
  Quote,
  ShieldAlert,
  UserRoundCheck,
  XCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { SimpleAgentCitationDTO } from "@/types/simple-nurse";
import { MessageItem } from "@/components/chat/MessageItem";
import { SimpleDecisionForm } from "@/components/clinical/nurse-simple/SimpleDecisionForm";
import { SimpleCaseChatDock } from "@/components/clinical/nurse-simple/SimpleCaseChatDock";
import { SimplePatientContactPanel } from "@/components/clinical/nurse-simple/SimplePatientContactPanel";
import { esiTheme } from "@/components/clinical/nurse-simple/esi-theme";
import { useClaimSimpleCase, useSimpleNurseCase } from "@/queries/useSimpleNurseQueries";
import { useAuthStore } from "@/store/useAuthStore";
import type { SimpleNurseTranscriptRowDTO } from "@/types/simple-nurse";
import type { ChatMessage } from "@/types/triage-chat";

/**
 * Màn thẩm định một ca Triage Agent.
 *
 * Bố cục theo trạm rà soát lâm sàng: cột trái là hồ sơ để đọc (danh tính &
 * đường liên lạc -> phiếu SBAR -> phác đồ đã tham chiếu -> toàn bộ hội thoại),
 * cột phải ghim bàn ra quyết định để điều dưỡng không phải cuộn ngược lên khi
 * đã đọc xong. Thứ tự này cố ý: biết gọi cho ai trước, rồi mới tới nội dung
 * lâm sàng, và chốt ESI sau cùng.
 */

function mapTranscriptRow(row: SimpleNurseTranscriptRowDTO, sessionId: string): ChatMessage {
  return {
    id: `${sessionId}-${row.turn_index}-${row.sender}`,
    sender: row.sender === "PATIENT" ? "user" : "bot",
    timestamp: row.created_at,
    content: row.content,
    step: row.turn_index + 1,
  };
}

function noopSelectAnswer() {}

const SBAR_SECTIONS: {
  key: "situation" | "background" | "assessment" | "recommendation";
  letter: string;
  label: string;
  hint: string;
}[] = [
  { key: "situation", letter: "S", label: "Tình huống", hint: "Situation — chuyện gì đang xảy ra" },
  { key: "background", letter: "B", label: "Bối cảnh", hint: "Background — tiền sử và dữ kiện nền" },
  { key: "assessment", letter: "A", label: "Đánh giá", hint: "Assessment — nhận định mức độ" },
  { key: "recommendation", letter: "R", label: "Khuyến nghị", hint: "Recommendation — đề xuất xử trí" },
];

// EQ/NEQ/GT/GTE/LT/LTE -> ký hiệu toán học dễ đọc -- mirror
// SimplePilotSbarAccordion.tsx's identical helper (patient-facing side).
const OPERATOR_SYMBOLS: Record<string, string> = {
  EQ: "=",
  NEQ: "≠",
  GT: ">",
  GTE: "≥",
  LT: "<",
  LTE: "≤",
};

function citationStatusMeta(status: SimpleAgentCitationDTO["status"]) {
  switch (status) {
    case "SATISFIED":
      return { label: "Đã thỏa mãn", className: "border-sky-200 bg-sky-50 text-sky-900", icon: CheckCircle2 };
    case "MISSING_INFO":
      return { label: "Chưa đủ dữ liệu", className: "border-amber-200 bg-amber-50 text-amber-900", icon: AlertCircle };
    case "CONTRADICTED":
    default:
      return { label: "Không khớp", className: "border-rose-200 bg-rose-50 text-rose-900", icon: XCircle };
  }
}

/** Khối nội dung có tiêu đề, dùng lặp lại cho các mục của hồ sơ ca. */
function Panel({
  icon: Icon,
  title,
  subtitle,
  order = 0,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle?: string;
  /** Thứ tự đọc của khối, dùng để các khối hiện lên nối tiếp nhau. */
  order?: number;
  children: React.ReactNode;
}) {
  return (
    <section
      style={{ "--rise-delay": `${order * 80}ms` } as React.CSSProperties}
      className="group/panel glow-soft glow-sky rise-in overflow-hidden rounded-2xl border border-border bg-card shadow-xs"
    >
      <header className="flex items-start gap-3 border-b border-slate-100 bg-background/70 px-4 py-3.5 sm:px-5">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-card text-sky-700 shadow-xs transition-[background-color,color] duration-300 group-hover/panel:bg-sky-700 group-hover/panel:text-white">
          <Icon className="size-4.5" aria-hidden="true" />
        </span>
        <div className="min-w-0">
          <h2 className="text-base font-bold text-slate-950 dark:text-slate-50">{title}</h2>
          {subtitle && <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-300">{subtitle}</p>}
        </div>
      </header>
      <div className="p-4 sm:p-5">{children}</div>
    </section>
  );
}

export function SimpleNurseCaseWorkspace({ sessionId }: { sessionId: string }) {
  const { data, isLoading, isError, error } = useSimpleNurseCase(sessionId);
  const currentUserId = useAuthStore((state) => state.user?.id);
  const claim = useClaimSimpleCase(sessionId);
  const searchParams = useSearchParams();

  const messages = useMemo<ChatMessage[]>(
    () => (data?.messages ?? []).map((row) => mapTranscriptRow(row, sessionId)),
    [data?.messages, sessionId],
  );

  if (isLoading) {
    // Khung chờ dựng đúng bố cục thật của màn thẩm định (đầu hồ sơ, cột đọc,
    // cột quyết định) nên trang không nhảy một nhịp khi dữ liệu về.
    return (
      <div className="mx-auto max-w-7xl space-y-5 p-4 sm:p-6">
        <span className="sr-only" role="status">
          Đang tải ca
        </span>
        <div className="skeleton-sweep relative h-36 overflow-hidden rounded-2xl border border-border bg-card shadow-xs">
          <span className="absolute inset-y-0 left-0 w-1.5 bg-slate-200 dark:bg-slate-700" aria-hidden="true" />
          <div className="space-y-3 py-5 pl-6 pr-4">
            <div className="h-3 w-32 animate-pulse rounded bg-muted" />
            <div className="h-7 w-64 animate-pulse rounded-md bg-slate-200 dark:bg-slate-700" />
            <div className="h-4 w-full max-w-xl animate-pulse rounded bg-muted" />
          </div>
        </div>
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_22rem] xl:items-start">
          <div className="space-y-5">
            {[0, 1].map((key) => (
              <div
                key={key}
                style={{ "--rise-delay": `${key * 90}ms` } as React.CSSProperties}
                className="rise-in skeleton-sweep relative h-56 overflow-hidden rounded-2xl border border-border bg-card shadow-xs"
              >
                <div className="border-b border-slate-100 bg-background/70 px-5 py-3.5">
                  <div className="h-4 w-44 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
                </div>
                <div className="space-y-2.5 p-5">
                  <div className="h-4 w-full animate-pulse rounded bg-muted" />
                  <div className="h-4 w-5/6 animate-pulse rounded bg-muted" />
                  <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />
                </div>
              </div>
            ))}
          </div>
          <div className="skeleton-sweep relative h-64 overflow-hidden rounded-2xl border border-border bg-card shadow-xs">
            <div className="border-b border-slate-100 bg-background/70 px-5 py-3.5">
              <div className="h-4 w-40 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
            </div>
            <div className="space-y-3 p-5">
              <div className="h-20 w-full animate-pulse rounded-xl bg-muted" />
              <div className="h-11 w-full animate-pulse rounded-xl bg-muted" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div role="alert" className="rise-in mx-auto max-w-xl rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center">
        <p className="text-sm font-semibold text-rose-900">Không thể tải ca này.</p>
        <p className="mt-2 text-sm text-rose-800">{error instanceof Error ? error.message : "Vui lòng thử lại."}</p>
      </div>
    );
  }

  const mine = data.assigned_nurse_id === currentUserId;
  const ownedByOther = Boolean(data.assigned_nurse_id) && !mine;
  const isClosed = data.review_status === "HANDED_OFF";
  const canDecide = mine && !isClosed;

  const aiTheme = esiTheme(data.ai_proposed_esi);
  const finalTheme = esiTheme(data.final_esi);
  const patientName = data.patient.profile?.full_name ?? data.patient.account.full_name ?? "Chưa rõ danh tính";

  return (
    <div className="mx-auto max-w-7xl space-y-5 p-4 sm:p-6">

      {/* ------------------------------------------------------ ĐẦU HỒ SƠ CA */}
      <header className="glow-soft glow-sky rise-in relative overflow-hidden rounded-2xl border border-border bg-card shadow-xs">
        {/* Dải mức độ của ca. Chỉ hồi sức và cấp cứu mới có ánh sáng chạy dọc --
            ở màn này cũng như ở bảng điều phối, chuyển động là tín hiệu ưu tiên. */}
        <span
          className={cn(
            "absolute inset-y-0 left-0 w-1.5",
            aiTheme.rail,
            data.ai_proposed_esi !== null && data.ai_proposed_esi <= 2 && "acuity-pulse",
          )}
          aria-hidden="true"
        />

        <div className="flex flex-col gap-4 py-5 pl-5 pr-4 sm:pl-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Hồ sơ ca sàng lọc</p>
            <h1 className="mt-1 truncate text-2xl font-black tracking-tight text-slate-950 dark:text-slate-50">{patientName}</h1>
            <p className="mt-2 max-w-2xl text-base leading-6 text-slate-700 dark:text-slate-200">
              {data.initial_message.trim() || "Chưa có mô tả triệu chứng ban đầu"}
            </p>

            {data.attention_required && (
              <p
                role="status"
                className="mt-3 flex max-w-2xl items-start gap-2 rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-base text-rose-950"
              >
                <ShieldAlert className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
                <span>
                  <strong>Cần xem ngay:</strong> sàng lọc tự động phát hiện{" "}
                  {data.attention_reason ?? "dấu hiệu nguy kịch"} trong lời người bệnh. Đây không phải mức ESI.
                  {data.session_status === "ACTIVE" && " Người bệnh vẫn đang trò chuyện với trợ lý."}
                </span>
              </p>
            )}

            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-bold",
                  aiTheme.chip,
                )}
              >
                {data.ai_proposed_esi ? `AI đề xuất: ESI ${data.ai_proposed_esi}` : "AI: chưa đủ dữ liệu kết luận"}
                {data.ai_proposed_esi && <span className="font-semibold opacity-80">· {aiTheme.label}</span>}
              </span>

              {isClosed && (
                <span
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-bold",
                    finalTheme.chip,
                  )}
                >
                  <CheckCircle2 className="size-4" aria-hidden="true" />
                  Đã chốt: ESI {data.final_esi ?? "—"}
                </span>
              )}

              <span className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-3 py-1.5 text-sm font-semibold text-slate-600 dark:text-slate-300">
                <MessagesSquare className="size-4" aria-hidden="true" />
                {messages.length} lượt hội thoại
              </span>
            </div>
          </div>

          {/* Nhận ca -- chỉ hiện khi ca còn trống và chưa đóng */}
          {!mine && !ownedByOther && !isClosed && (
            <Button
              onClick={() => claim.mutate({ version: data.case_version, action: "CLAIM" })}
              disabled={claim.isPending}
              className="glow-soft glow-sky min-h-12 shrink-0 border border-sky-700 bg-sky-700 px-6 text-white hover:bg-sky-800"
            >
              <UserRoundCheck className="mr-2 size-4" aria-hidden="true" />
              {claim.isPending ? "Đang nhận ca..." : "Nhận ca này"}
            </Button>
          )}
        </div>

        {ownedByOther && (
          <p className="flex items-center gap-2.5 border-t border-amber-200 bg-amber-50 px-5 py-3 text-sm font-semibold text-amber-950 sm:px-6">
            <AlertTriangle className="size-4 shrink-0" aria-hidden="true" />
            Ca này đang được một y tá khác phụ trách — bạn xem được hồ sơ nhưng không ra quyết định.
          </p>
        )}
      </header>

      {/* Cột trái đọc hồ sơ, cột phải ghim bàn quyết định */}
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_22rem] xl:items-start">

        <div className="min-w-0 space-y-5">
          <SimplePatientContactPanel patient={data.patient} />

          {data.sbar && (
            <Panel
              icon={ClipboardList}
              order={1}
              title="Phiếu bàn giao SBAR"
              subtitle="Tổng hợp tự động từ dữ kiện đã thu thập trong phiên"
            >
              <div className="space-y-3">
                {SBAR_SECTIONS.map(({ key, letter, label, hint }, index) => (
                  <div
                    key={key}
                    style={{ "--rise-delay": `${index * 70}ms` } as React.CSSProperties}
                    className="group/sbar glow-soft glow-sky rise-in flex gap-3 rounded-xl border border-border bg-background/70 p-3.5"
                  >
                    <span
                      aria-hidden="true"
                      className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-sky-700 text-base font-black text-white transition-transform duration-300 ease-out group-hover/sbar:scale-105 motion-reduce:group-hover/sbar:scale-100"
                    >
                      {letter}
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-bold text-foreground">
                        {label}
                        <span className="ml-2 font-medium text-muted-foreground">{hint}</span>
                      </p>
                      <p className="mt-1 text-sm leading-6 text-slate-800 dark:text-slate-100">{data.sbar![key]}</p>
                    </div>
                  </div>
                ))}
              </div>
            </Panel>
          )}

          {data.sbar && data.sbar.citations.length > 0 && (
            <Panel
              icon={Quote}
              order={2}
              title="Phác đồ đã tham chiếu"
              subtitle="Từng tiêu chí kèm giá trị bệnh nhân đã khai báo, để rà soát lại căn cứ của AI"
            >
              <div className="space-y-2.5">
                {data.sbar.citations.map((citation) => {
                  const meta = citationStatusMeta(citation.status);
                  const StatusIcon = meta.icon;
                  return (
                    <div
                      key={citation.atom_id}
                      className={cn(
                        "glow-soft glow-sky rounded-xl border p-3 transition-transform duration-200 hover:-translate-y-0.5 motion-reduce:hover:translate-y-0",
                        meta.className,
                      )}
                    >
                      <div className="flex flex-wrap items-center gap-1.5 text-xs">
                        <StatusIcon className="size-3.5 shrink-0" aria-hidden="true" />
                        <span className="font-bold uppercase tracking-wide">{meta.label}</span>
                        {citation.decision_point && (
                          <span className="rounded border border-white/70 bg-card/70 px-1.5 py-0.5 font-mono font-bold">
                            {citation.decision_point}
                          </span>
                        )}
                        <span className="font-mono opacity-70">{citation.atom_id}</span>
                      </div>

                      {citation.criteria_text && (
                        <p className="mt-2 text-sm leading-6">{citation.criteria_text}</p>
                      )}

                      {citation.satisfied_requirements.length > 0 && (
                        <ul className="mt-2 space-y-1 border-t border-current/15 pt-2 text-sm font-semibold">
                          {citation.satisfied_requirements.map((req) => (
                            <li key={req.fact_target_id} className="flex flex-wrap items-baseline gap-1">
                              <span>{req.name}</span>
                              <span className="font-mono">
                                {OPERATOR_SYMBOLS[req.operator] ?? req.operator} {String(req.expected_value)}
                              </span>
                              <span className="font-normal opacity-80">
                                — bệnh nhân báo cáo: <strong>{String(req.actual_value)}</strong>
                              </span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  );
                })}
              </div>
            </Panel>
          )}

          <Panel
            icon={MessagesSquare}
            order={3}
            title="Toàn bộ hội thoại với AI"
            subtitle="Bản ghi đầy đủ để đối chiếu khi cần"
          >
            <div className="space-y-1">
              {messages.map((msg) => (
                <MessageItem key={msg.id} message={msg} onSelectAnswer={noopSelectAnswer} disabled />
              ))}
            </div>
          </Panel>
        </div>

        {/* -------------------------------------------------- BÀN QUYẾT ĐỊNH */}
        <div className="min-w-0 space-y-5 xl:sticky xl:top-6">
          {canDecide ? (
            <Panel
              icon={FileText}
              title="Quyết định phân luồng"
              subtitle="Giữ nguyên hoặc điều chỉnh mức ESI mà AI đề xuất"
            >
              <SimpleDecisionForm sessionId={sessionId} caseVersion={data.case_version} aiEsi={data.ai_proposed_esi} />
            </Panel>
          ) : isClosed ? (
            <Panel icon={CheckCircle2} title="Ca đã đóng" subtitle="Quyết định cuối cùng đã được ghi nhận">
              <div className="space-y-3">
                <div className={cn("rounded-xl border p-3.5", finalTheme.chip)}>
                  <p className="text-xs font-bold uppercase tracking-wide opacity-80">Mức ESI cuối cùng</p>
                  <p className="mt-1 text-2xl font-black leading-none">ESI {data.final_esi ?? "—"}</p>
                  <p className="mt-1 text-sm font-semibold opacity-90">{finalTheme.label}</p>
                </div>
                {data.decision_note && (
                  <div className="rounded-xl border border-border bg-background p-3.5">
                    <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">
                      Ghi chú của y tá khi đóng ca
                    </p>
                    <p className="mt-1 text-sm leading-6 text-slate-800 dark:text-slate-100">{data.decision_note}</p>
                  </div>
                )}
              </div>
            </Panel>
          ) : (
            <Panel icon={Lock} title="Chưa thể ra quyết định" subtitle="Bạn cần nhận ca trước khi chốt mức ESI">
              <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
                {ownedByOther
                  ? "Ca này thuộc về một y tá khác. Bạn vẫn đọc được toàn bộ hồ sơ để phối hợp."
                  : "Nhấn “Nhận ca này” ở đầu trang để mở bàn quyết định."}
              </p>
            </Panel>
          )}
        </div>
      </div>

      {!ownedByOther && (
        <SimpleCaseChatDock sessionId={sessionId} initialOpen={searchParams.get("openChat") === "1"} />
      )}
    </div>
  );
}
