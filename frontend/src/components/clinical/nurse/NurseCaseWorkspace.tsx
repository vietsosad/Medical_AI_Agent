"use client";

import {
  AlertTriangle,
  ArrowLeft,
  Bot,
  CheckCircle2,
  Clock3,
  FileCheck2,
  HeartPulse,
  Info,
  ShieldAlert,
  UserRound,
} from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useClaimCase } from "@/hooks/mutations/use-hitl-mutations";
import { useNurseCase } from "@/hooks/queries/use-clinical-hitl";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/useAuthStore";
import type { EsiLevel, ReviewStatus } from "@/types/clinical-hitl";

import { CaseChatDock } from "./CaseChatDock";
import { ChiefComplaintForm } from "./ChiefComplaintForm";
import { DecisionForm } from "./DecisionForm";
import { EmergencyContactCard } from "./EmergencyContactCard";
import { HandoffForm } from "./HandoffForm";
import { ObservationForm } from "./ObservationForm";
import { NurseCitationList } from "./NurseCitationList";
import { PiiAccessDialog } from "./PiiAccessDialog";
import { ReleaseCaseDialog } from "./ReleaseCaseDialog";

const statusLabels: Record<ReviewStatus, string> = {
  WAITING_REVIEW: "Chưa nhận",
  ASSIGNED: "Đã phân công",
  IN_REVIEW: "Đang rà soát",
  NEEDS_MORE_INFO: "Thiếu dữ liệu",
  SPECIALIST_REVIEW_REQUIRED: "Cần đánh giá chuyên sâu",
  TRIAGE_DECIDED: "Đã chốt ESI",
  HANDED_OFF: "Đã bàn giao",
};

function formatElapsed(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  if (minutes < 1) return "Dưới 1 phút";
  if (minutes < 60) return `${minutes} phút`;
  return `${Math.floor(minutes / 60)} giờ ${minutes % 60} phút`;
}

function esiClass(esi: EsiLevel | null): string {
  if (esi === 1) return "border-rose-300 bg-rose-50 text-rose-950";
  if (esi === 2) return "border-amber-300 bg-amber-50 text-amber-950";
  if (esi === 3) return "border-sky-200 bg-sky-50 text-sky-950";
  if (esi === 4 || esi === 5) return "border-emerald-200 bg-emerald-50 text-emerald-950";
  return "border-border bg-muted text-slate-700 dark:text-slate-200";
}

function EmptyValue() {
  return <span className="text-muted-foreground">Chưa có dữ liệu</span>;
}

function ValueList({ values }: { values: string[] }) {
  if (values.length === 0) return <EmptyValue />;
  return (
    <ul className="space-y-2 text-base text-slate-800 dark:text-slate-100">
      {values.map((value) => (
        <li key={value} className="flex gap-2">
          <span className="mt-2 size-2 shrink-0 rounded-full bg-slate-400" aria-hidden="true" />
          {value}
        </li>
      ))}
    </ul>
  );
}

const reportedVitalLabels: Record<string, string> = {
  blood_pressure: "Huyết áp",
  heart_rate: "Mạch",
  spo2: "SpO₂",
  temperature_c: "Nhiệt độ",
  respiratory_rate: "Nhịp thở",
  gcs: "GCS",
};

const ehrConfirmationLabels: Record<string, string> = {
  CONFIRMED: "Đã được người bệnh xác nhận lại trong phiên",
  UPDATED_BY_PATIENT: "Người bệnh đã báo thay đổi; EHR cũ không được dùng để suy luận",
  UNCERTAIN: "Người bệnh chưa chắc thông tin EHR còn đúng",
  NOT_REVIEWED: "Chưa được xác nhận lại trong phiên",
};

function formatReportedVitals(vitals: Record<string, string | number>): string {
  return Object.entries(vitals)
    .filter(([key]) => !["systolic_bp", "diastolic_bp"].includes(key))
    .map(([key, value]) => `${reportedVitalLabels[key] || key}: ${value}`)
    .join("; ");
}

export function NurseCaseWorkspace({ caseId }: { caseId: string }) {
  const detail = useNurseCase(caseId);
  const claim = useClaimCase(caseId);
  const currentUserId = useAuthStore((state) => state.user?.id);

  if (detail.isLoading) {
    return (
      <div className="space-y-4" aria-busy="true" aria-label="Đang tải ca phân luồng">
        <div className="h-32 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-700" />
        <div className="h-80 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-700" />
      </div>
    );
  }

  if (detail.isError || !detail.data) {
    return (
      <section className="rounded-xl border border-rose-200 bg-card p-8 text-center" role="alert">
        <AlertTriangle className="mx-auto size-10 text-rose-700" aria-hidden="true" />
        <h1 className="mt-4 text-2xl font-semibold text-slate-950 dark:text-slate-50">Không tải được dữ liệu ca</h1>
        <p className="mt-2 text-base text-slate-600 dark:text-slate-300">{detail.error?.message ?? "Không tìm thấy ca."}</p>
        <Link className="mt-6 inline-flex min-h-11 items-center text-sm font-semibold text-sky-800" href="/clinical/queue">
          <ArrowLeft className="mr-2 size-4" aria-hidden="true" />
          Về hàng đợi
        </Link>
      </section>
    );
  }

  const data = detail.data;
  const mine = data.assignee?.id === currentUserId;
  const ownedByOther = Boolean(data.assignee && !mine);
  const canEdit = mine && ["ASSIGNED", "IN_REVIEW", "NEEDS_MORE_INFO"].includes(data.review_status);
  const canRelease = canEdit;
  const needsHandoff = mine && data.review_status === "TRIAGE_DECIDED";

  return (
    <div className="space-y-6 pb-8">
      <Link href="/clinical/queue" className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-sky-800">
        <ArrowLeft className="size-4" aria-hidden="true" />
        Về hàng đợi
      </Link>

      <header className="sticky top-0 z-20 border-b border-border bg-background/95 py-4 backdrop-blur">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="min-w-0">
            <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Ca {data.case_id}</p>
            <h1 className="mt-2 truncate text-2xl font-semibold text-slate-950 dark:text-slate-50">
              {data.patient_name} · {data.chief_complaint.trim() || "Chưa ghi nhận triệu chứng chính"}
            </h1>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className={cn("inline-flex min-h-11 items-center rounded-lg border px-4 text-base font-bold", esiClass(data.ai_recommended_esi))}>
                AI: {data.ai_recommended_esi ? `ESI ${data.ai_recommended_esi}` : "Chưa có ESI"}
              </span>
              {data.final_esi && (
                <span className="inline-flex min-h-11 items-center rounded-lg border border-emerald-200 bg-emerald-50 px-4 text-base font-bold text-emerald-950">
                  Đã chốt: ESI {data.final_esi}
                </span>
              )}
              {data.is_red_flag && (
                <span className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-rose-700 px-4 text-base font-bold text-white">
                  <ShieldAlert className="size-5" aria-hidden="true" />
                  Red Flag
                </span>
              )}
              <span className="inline-flex min-h-11 items-center gap-2 px-2 text-base font-semibold text-slate-800 dark:text-slate-100">
                <Clock3 className="size-5" aria-hidden="true" />
                {formatElapsed(data.wait_time_seconds)}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {mine && <PiiAccessDialog caseId={caseId} />}
            {canRelease && <ReleaseCaseDialog caseId={caseId} caseVersion={data.case_version} />}
            {!mine && (
              <Button
                type="button"
                disabled={ownedByOther || claim.isPending}
                onClick={() => claim.mutate({ case_version: data.case_version, action: "CLAIM" })}
                className="min-h-11 bg-sky-700 text-white hover:bg-sky-800"
              >
                {ownedByOther ? `Đang do ${data.assignee?.name} phụ trách` : claim.isPending ? "Đang nhận ca..." : "Nhận ca để xử lý"}
              </Button>
            )}
          </div>
        </div>
        {claim.isError && (
          <p className="mt-4 text-sm text-rose-700" role="alert">
            {claim.error.message}
          </p>
        )}
      </header>

      <nav
        className="flex flex-col gap-3 border-y border-border bg-card px-4 py-4 lg:flex-row lg:items-center"
        aria-label="Công cụ trong hồ sơ lâm sàng"
      >
        <p className="shrink-0 text-sm font-semibold text-slate-950 dark:text-slate-50">Công cụ đã hợp nhất:</p>
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm font-semibold text-sky-800">
          <a className="inline-flex min-h-11 items-center hover:text-sky-950" href="#tom-tat-ca">
            Triệu chứng chính
          </a>
          <a className="inline-flex min-h-11 items-center hover:text-sky-950" href="#lien-lac">
            Liên hệ khẩn cấp
          </a>
          <a className="inline-flex min-h-11 items-center hover:text-sky-950" href="#sinh-hieu">
            Sinh hiệu có nguồn
          </a>
          <a className="inline-flex min-h-11 items-center hover:text-sky-950" href="#sbar-can-cu">
            SBAR &amp; căn cứ AI
          </a>
          <a className="inline-flex min-h-11 items-center hover:text-sky-950" href="#transcript">
            Transcript lâm sàng
          </a>
          {canEdit && (
            <a className="inline-flex min-h-11 items-center hover:text-sky-950" href="#quyet-dinh-esi">
              Chốt / điều chỉnh ESI
            </a>
          )}
          {needsHandoff && (
            <a className="inline-flex min-h-11 items-center hover:text-sky-950" href="#ban-giao">
              Bàn giao ca
            </a>
          )}
        </div>
      </nav>

      <section
        id="tom-tat-ca"
        className="scroll-mt-36 rounded-xl border border-border bg-card p-6"
        aria-labelledby="case-summary-title"
      >
        <div className="flex items-center gap-2">
          <UserRound className="size-5 text-sky-800" aria-hidden="true" />
          <h2 id="case-summary-title" className="text-xl font-semibold text-slate-950 dark:text-slate-50">1. Tóm tắt ca</h2>
        </div>
        <dl className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt className="text-sm text-slate-600 dark:text-slate-300">Bệnh nhân</dt>
            <dd className="mt-2 text-base font-semibold text-slate-950 dark:text-slate-50">{data.patient_name}</dd>
          </div>
          <div>
            <dt className="text-sm text-slate-600 dark:text-slate-300">Tuổi / giới tính</dt>
            <dd className="mt-2 text-base font-semibold text-slate-950 dark:text-slate-50">
              {[data.age !== null ? `${data.age} tuổi` : null, data.sex].filter(Boolean).join(" · ") || <EmptyValue />}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-slate-600 dark:text-slate-300">Trạng thái rà soát</dt>
            <dd className="mt-2 text-base font-semibold text-slate-950 dark:text-slate-50">{statusLabels[data.review_status]}</dd>
          </div>
          <div>
            <dt className="text-sm text-slate-600 dark:text-slate-300">Người phụ trách</dt>
            <dd className="mt-2 text-base font-semibold text-slate-950 dark:text-slate-50">{data.assignee?.name ?? <EmptyValue />}</dd>
          </div>
        </dl>
        {canEdit ? (
          <ChiefComplaintForm
            key={`${caseId}:${data.case_version}`}
            caseId={caseId}
            caseVersion={data.case_version}
            chiefComplaint={data.chief_complaint}
          />
        ) : (
          <div className="mt-6 border-l-4 border-sky-600 bg-sky-50 p-4">
            <p className="text-sm font-medium text-sky-900">Triệu chứng chính</p>
            <p className="mt-2 text-lg font-semibold leading-7 text-slate-950 dark:text-slate-50">
              {data.chief_complaint.trim() || "Chưa ghi nhận triệu chứng chính"}
            </p>
          </div>
        )}
      </section>

      {data.is_red_flag && (
        <section className="border-l-4 border-rose-600 bg-rose-50 p-6" role="alert" aria-live="assertive">
          <div className="flex items-center gap-2">
            <ShieldAlert className="size-6 text-rose-800" aria-hidden="true" />
            <h2 className="text-xl font-bold text-rose-950">Dấu hiệu nguy cấp đã được phát hiện</h2>
          </div>
          <p className="mt-4 text-base text-rose-900">
            {data.red_flags.length > 0 ? data.red_flags.join(", ") : "Red Flag từ bộ phát hiện an toàn"}. Cảnh báo này không thay thế việc rà soát và chốt ESI.
          </p>
        </section>
      )}

      {data.specialist_review.required && (
        <section className="border-l-4 border-amber-500 bg-amber-50 p-6" role="status">
          <div className="flex items-center gap-2">
            <FileCheck2 className="size-5 text-amber-900" aria-hidden="true" />
            <h2 className="text-xl font-semibold text-amber-950">Ca cần đánh giá chuyên sâu</h2>
          </div>
          <p className="mt-4 text-base text-amber-950">
            Lý do: {data.specialist_review.reason_code ?? "Chưa ghi nhận mã lý do"}
          </p>
          {data.specialist_review.note && (
            <p className="mt-2 text-base leading-6 text-amber-900">{data.specialist_review.note}</p>
          )}
        </section>
      )}

      <section
        id="sinh-hieu"
        className="scroll-mt-36 rounded-xl border border-border bg-card p-6"
        aria-labelledby="observations-title"
      >
        <div className="flex items-center gap-2">
          <HeartPulse className="size-5 text-sky-800" aria-hidden="true" />
          <h2 id="observations-title" className="text-xl font-semibold text-slate-950 dark:text-slate-50">2. Cảnh báo và sinh hiệu</h2>
        </div>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Mỗi giá trị phải có nguồn và thời điểm đo. Trường chưa đo được ghi rõ, không tự điền.</p>
        {Object.keys(data.risk_context.patient_reported_vitals ?? {}).length > 0 && (
          <div className="mt-4 border-l-4 border-amber-400 bg-amber-50 p-4 text-amber-950" role="note">
            <p className="text-sm font-semibold">Sinh hiệu do người bệnh khai trong phiên</p>
            <p className="mt-2 text-base leading-6">
              {formatReportedVitals(data.risk_context.patient_reported_vitals)}
            </p>
            <p className="mt-2 text-sm leading-6">
              Nguồn: {data.risk_context.patient_reported_vitals_source ?? "Chưa rõ"}
              {data.risk_context.patient_reported_vitals_measured_at
                ? ` · Thời điểm đo: ${data.risk_context.patient_reported_vitals_measured_at}`
                : " · Chưa ghi thời điểm đo"}
            </p>
            <p className="mt-2 text-sm leading-6">
              Chưa phải số đo đã được nhân viên y tế xác minh. Cần đo lại và ghi nguồn, thời điểm bên dưới.
            </p>
          </div>
        )}
        <div className="mt-6">
          {canEdit ? (
            <ObservationForm caseId={caseId} caseVersion={data.case_version} observations={data.observations} />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.observations.length > 0 ? (
                data.observations.map((observation) => (
                  <dl key={observation.id} className="border-l-4 border-slate-300 pl-4 dark:border-slate-700">
                    <dt className="text-sm font-medium text-slate-600 dark:text-slate-300">{observation.kind}</dt>
                    <dd className="mt-2 text-lg font-semibold text-slate-950 dark:text-slate-50">
                      {observation.availability === "MEASURED"
                        ? `${observation.value} ${observation.unit}`
                        : observation.availability === "NOT_MEASURED"
                          ? "Chưa đo"
                          : observation.availability === "NOT_APPLICABLE"
                            ? "Không áp dụng"
                            : "Không biết"}
                    </dd>
                    <dd className="mt-2 text-sm text-slate-600 dark:text-slate-300">Nguồn: {observation.source}</dd>
                  </dl>
                ))
              ) : (
                <p className="text-base text-muted-foreground">Chưa có dữ liệu sinh hiệu có nguồn gốc.</p>
              )}
            </div>
          )}
        </div>
      </section>

      <section className="rounded-xl border border-border bg-card p-6" aria-labelledby="risk-title">
        <div className="flex items-center gap-2">
          <Info className="size-5 text-sky-800" aria-hidden="true" />
          <h2 id="risk-title" className="text-xl font-semibold text-slate-950 dark:text-slate-50">3. Yếu tố nguy cơ liên quan</h2>
        </div>
        <div className="mt-6 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          <div>
            <h3 className="mb-4 text-base font-semibold text-slate-950 dark:text-slate-50">Hồ sơ cơ thể</h3>
            <ValueList values={[
              data.risk_context.age !== null ? `${data.risk_context.age} tuổi` : "Tuổi: Chưa có",
              `Giới tính: ${data.risk_context.gender ?? "Chưa có"}`,
              data.risk_context.height_cm !== null && data.risk_context.weight_kg !== null
                ? `${data.risk_context.height_cm} cm · ${data.risk_context.weight_kg} kg`
                : "Chiều cao/cân nặng: Chưa có",
              `BMI: ${data.risk_context.bmi ?? "Chưa có"}`,
              `Nhóm máu: ${data.risk_context.blood_type ?? "Chưa rõ"}`,
            ]} />
          </div>
          <div>
            <h3 className="mb-4 text-base font-semibold text-slate-950 dark:text-slate-50">Bệnh nền</h3>
            <ValueList values={data.risk_context.chronic_conditions} />
          </div>
          <div>
            <h3 className="mb-4 text-base font-semibold text-slate-950 dark:text-slate-50">Dị ứng</h3>
            <ValueList values={data.risk_context.allergies} />
          </div>
          <div>
            <h3 className="mb-4 text-base font-semibold text-slate-950 dark:text-slate-50">Thuốc đang dùng</h3>
            <ValueList values={data.risk_context.active_medications} />
          </div>
        </div>
        <div className="mt-6 border-t border-border pt-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
          <p>
            Trạng thái EHR trong phiên:{" "}
            {ehrConfirmationLabels[data.risk_context.ehr_confirmation_status]
              || data.risk_context.ehr_confirmation_status}
            {data.risk_context.ehr_profile_updated_at
              ? ` · Hồ sơ cập nhật lúc ${new Date(data.risk_context.ehr_profile_updated_at).toLocaleString("vi-VN")}`
              : ""}
          </p>
          {data.risk_context.patient_context_note && (
            <p className="mt-2 text-slate-800 dark:text-slate-100">
              Đính chính của người bệnh: {data.risk_context.patient_context_note}
            </p>
          )}
        </div>
      </section>

      <section
        id="sbar-can-cu"
        className="scroll-mt-36 rounded-xl border border-border bg-card p-6"
        aria-labelledby="ai-title"
      >
        <div className="flex items-center gap-2">
          <Bot className="size-5 text-sky-800" aria-hidden="true" />
          <h2 id="ai-title" className="text-xl font-semibold text-slate-950 dark:text-slate-50">4. Đề xuất phân luồng của AI</h2>
        </div>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Đây là đề xuất hỗ trợ; nhân viên lâm sàng chịu trách nhiệm xác nhận hoặc điều chỉnh ESI.</p>
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div>
            <h3 className="text-base font-semibold text-slate-950 dark:text-slate-50">SBAR rút gọn</h3>
            <dl className="mt-4 space-y-4 text-base leading-7">
              {[
                ["Tình trạng", data.sbar.situation],
                ["Bối cảnh", data.sbar.background],
                ["Nhận định nguy cơ", data.sbar.assessment],
                ["Đề xuất phân luồng", data.sbar.recommendation],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="font-semibold text-slate-950 dark:text-slate-50">{label}</dt>
                  <dd className="mt-2 text-slate-700 dark:text-slate-200">{value || <EmptyValue />}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-950 dark:text-slate-50">Độ đầy đủ dữ liệu</h3>
            <p className={cn("mt-4 flex items-center gap-2 text-base font-semibold", data.data_completeness.is_complete ? "text-emerald-800" : "text-amber-900")}>
              {data.data_completeness.is_complete ? <CheckCircle2 className="size-5" aria-hidden="true" /> : <AlertTriangle className="size-5" aria-hidden="true" />}
              {data.data_completeness.is_complete ? "Đủ dữ liệu nền tảng để chốt ESI" : "Cần xử lý dữ liệu còn thiếu"}
            </p>
            {!data.data_completeness.is_complete && (
              <ValueList values={data.data_completeness.missing_fields} />
            )}
            <details className="mt-6 border-t border-border pt-4">
              <summary className="min-h-11 cursor-pointer text-sm font-semibold text-sky-800">Xem mã nguồn tham chiếu</summary>
              <div className="mt-4">
                {data.citations.length > 0 ? (
                  <NurseCitationList caseId={caseId} citations={data.citations} />
                ) : (
                  <EmptyValue />
                )}
              </div>
            </details>
            {mine && (
              <details id="transcript" className="scroll-mt-36 mt-4 border-t border-border pt-4">
                <summary className="min-h-11 cursor-pointer text-sm font-semibold text-sky-800">
                  Xem lịch sử trao đổi phục vụ đánh giá chuyên sâu
                </summary>
                <ol className="mt-4 space-y-4">
                  {data.transcript.length > 0 ? (
                    data.transcript.map((message) => (
                      <li key={message.id} className="border-l-4 border-slate-300 pl-4 dark:border-slate-700">
                        <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                          {message.sender === "PATIENT"
                            ? "Bệnh nhân"
                            : message.sender === "SYSTEM_SHIELD"
                              ? "Hệ thống an toàn"
                              : "Trợ lý Triage"}
                        </p>
                        <p className="mt-2 whitespace-pre-wrap text-base leading-6 text-slate-800 dark:text-slate-100">
                          {message.content}
                        </p>
                      </li>
                    ))
                  ) : (
                    <li className="text-base text-muted-foreground">Chưa có lịch sử trao đổi.</li>
                  )}
                </ol>
              </details>
            )}
          </div>
        </div>
      </section>

      {/* Liên hệ khẩn cấp và hội thoại đặt trước bước quyết định: khi cần gọi
          gấp hoặc hỏi thêm người bệnh thì phải với tới được ngay, không phải
          cuộn qua toàn bộ phần đánh giá. */}
      <section id="lien-lac" className="scroll-mt-36" aria-labelledby="contact-title">
        <h2 id="contact-title" className="sr-only">
          Liên lạc với người bệnh
        </h2>
        <EmergencyContactCard caseId={caseId} isAssignedToMe={mine} />
      </section>

      {canEdit && (
        <section
          id="quyet-dinh-esi"
          className="scroll-mt-36 rounded-xl border border-sky-200 bg-card p-6"
          aria-labelledby="decision-title"
        >
          <div className="flex items-center gap-2">
            <FileCheck2 className="size-5 text-sky-800" aria-hidden="true" />
            <h2 id="decision-title" className="text-xl font-semibold text-slate-950 dark:text-slate-50">5. Quyết định phân luồng</h2>
          </div>
          <div className="mt-6">
            <DecisionForm
              caseId={caseId}
              caseVersion={data.case_version}
              aiEsi={data.ai_recommended_esi}
              canDecide={data.data_completeness.is_complete}
              missingFields={data.data_completeness.missing_fields}
            />
          </div>
        </section>
      )}

      {needsHandoff && (
        <section
          id="ban-giao"
          className="scroll-mt-36 rounded-xl border border-sky-200 bg-card p-6"
          aria-labelledby="handoff-title"
        >
          <h2 id="handoff-title" className="text-xl font-semibold text-slate-950 dark:text-slate-50">6. Bàn giao và hoàn tất</h2>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Chỉ hoàn tất sau khi máy chủ lưu bàn giao thành công.</p>
          <div className="mt-6">
            <HandoffForm
              caseId={caseId}
              caseVersion={data.case_version}
              finalEsi={data.final_esi}
            />
          </div>
        </section>
      )}

      {/* Hội thoại luôn trong tầm với ở mọi bước làm việc thay vì nằm kẹp giữa
          hồ sơ, nơi nhân viên phải cuộn đi tìm mới thấy tin nhắn mới. */}
      <CaseChatDock
        caseId={caseId}
        isAssignedToMe={mine}
        patientName={data.patient_name}
      />

      {data.review_status === "HANDED_OFF" && (
        <section className="border-l-4 border-emerald-600 bg-emerald-50 p-6" role="status">
          <h2 className="text-xl font-semibold text-emerald-950">Ca đã được bàn giao</h2>
          <p className="mt-2 text-base text-emerald-900">Phần việc phân luồng lâm sàng đã hoàn tất trên máy chủ.</p>
        </section>
      )}
    </div>
  );
}
