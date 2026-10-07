"use client";

import React, { useState } from "react";
import { CheckCircle2, FileText, ShieldCheck, Unlock, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

interface AuditEvent {
  id: string;
  timestamp: string;
  operator: string;
  role: string;
  eventType: "BREAK_GLASS_PII" | "HITL_OVERRIDE" | "RAG_RELOAD" | "LOGIN_GUARD";
  patientSession: string;
  justification: string;
  status: "VERIFIED_ACID" | "FLAGGED";
}

const AUDIT_LOGS_LIST: AuditEvent[] = [
  {
    id: "AUDIT-20260805-001",
    timestamp: "05/08/2026 • 21:14:02 UTC",
    operator: "BS. Lê Trần Chuyên Gia (hitl-doc-01)",
    role: "DOCTOR",
    eventType: "HITL_OVERRIDE",
    patientSession: "session-er-1002",
    justification: "Can thiệp nâng từ ESI 3 lên ESI 2: Bệnh nhân xuất hiện loạn nhịp thất đột ngột trên monitor theo dõi.",
    status: "VERIFIED_ACID",
  },
  {
    id: "AUDIT-20260805-002",
    timestamp: "05/08/2026 • 20:42:15 UTC",
    operator: "ĐD. Phạm Thu Hà (hitl-nurse-01)",
    role: "CLINICAL_NURSE",
    eventType: "BREAK_GLASS_PII",
    patientSession: "session-er-1001",
    justification: "Điều phối gọi gấp xe cứu thương 115 tới hiện trường vụ tai nạn giao thông.",
    status: "VERIFIED_ACID",
  },
  {
    id: "AUDIT-20260805-003",
    timestamp: "05/08/2026 • 19:10:44 UTC",
    operator: "Hệ Thống AI Ops (System Automated)",
    role: "AI_OPS",
    eventType: "RAG_RELOAD",
    patientSession: "N/A - System",
    justification: "Cập nhật và tái chuẩn hóa bảng chỉ mục phác đồ đau ngực cấp AHRQ ESI V5.",
    status: "VERIFIED_ACID",
  },
];

/**
 * Trang Sổ Kiểm Cứu Bất Biến (ACID Audit Logs)
 * - Không gian tinh giản, minh bạch, phục vụ truy vết trách nhiệm trên từng thay đổi lâm sàng.
 * - Hiển thị rành mạch nguyên nhân phác đồ Break-Glass PII Unmasking.
 */
export default function AdminAuditLogsPage() {
  const [filterType, setFilterType] = useState<string>("ALL");

  return (
    <div className="p-6 sm:p-8 space-y-8 max-w-7xl mx-auto font-sans text-foreground">
      {/* HEADER AUDIT LOGS */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-card p-6 rounded-2xl border border-border shadow-2xs">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-slate-900 text-emerald-400 flex items-center justify-center shrink-0">
            <ShieldCheck className="w-6 h-6 stroke-[2.2]" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-foreground tracking-tight font-mono uppercase">
              Hồ Sơ Kiểm Cứu Bất Biến (ACID Audit Logs &amp; PII Ledger)
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Sổ nhật ký chống giả mạo ghi nhận toàn bộ thao tác can thiệp phác đồ HITL và lịch sử mở khóa danh tính Break-Glass
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 px-3.5 py-2 rounded-xl">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 stroke-[2.2]" />
          <span>Tamper-Proof Ledger: Locked</span>
        </div>
      </div>

      {/* FILTER BUTTONS (FLAT LOW NOISE STYLE) */}
      <div className="flex flex-wrap items-center gap-2 pb-2 border-b border-border">
        {[
          { label: "Tất cả giao dịch (All)", val: "ALL" },
          { label: "Mở khóa PII Break-Glass", val: "BREAK_GLASS_PII" },
          { label: "Phán quyết Override ESI", val: "HITL_OVERRIDE" },
          { label: "Đồng bộ RAG System", val: "RAG_RELOAD" },
        ].map((btn) => (
          <button
            key={btn.val}
            type="button"
            onClick={() => setFilterType(btn.val)}
            className={cn(
              "min-h-[40px] px-4 py-2 rounded-xl font-semibold text-xs sm:text-sm transition-all border cursor-pointer",
              filterType === btn.val
                ? "bg-slate-900 text-white border-slate-900 font-bold"
                : "bg-card text-slate-600 border-border hover:bg-background dark:text-slate-300"
            )}
          >
            {btn.label}
          </button>
        ))}
      </div>

      {/* DANH SÁCH NHỰT KÝ KIỂM TOÁN (CLEAN TIMELINE TABLE) */}
      <div className="bg-card rounded-2xl border border-border shadow-2xs overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-base sm:text-lg font-bold text-foreground font-mono uppercase">
            Sổ ghi nhận hành vi y tá &amp; Bác sĩ
          </h2>
          <span className="text-xs font-mono text-slate-400">Hệ quản trị an ninh dữ liệu lâm sàng</span>
        </div>

        <div className="divide-y divide-slate-100">
          {AUDIT_LOGS_LIST
            .filter((item) => filterType === "ALL" || item.eventType === filterType)
            .map((ev) => (
              <div key={ev.id} className="p-6 hover:bg-background/60 transition-colors space-y-3 font-sans">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className={cn(
                      "px-3 py-1 rounded-lg font-mono text-xs font-bold uppercase border flex items-center gap-1.5",
                      ev.eventType === "BREAK_GLASS_PII" && "bg-amber-50 text-amber-900 border-amber-200",
                      ev.eventType === "HITL_OVERRIDE" && "bg-rose-50 text-rose-900 border-rose-200",
                      ev.eventType === "RAG_RELOAD" && "bg-sky-50 text-sky-900 border-sky-200"
                    )}>
                      {ev.eventType === "BREAK_GLASS_PII" && <Unlock className="w-3.5 h-3.5 text-amber-600 stroke-[2.2]" />}
                      {ev.eventType === "HITL_OVERRIDE" && <Zap className="w-3.5 h-3.5 text-rose-600 stroke-[2.2]" />}
                      {ev.eventType === "RAG_RELOAD" && <FileText className="w-3.5 h-3.5 text-sky-600 stroke-[2.2]" />}
                      <span>{ev.eventType}</span>
                    </span>

                    <span className="text-xs font-mono text-muted-foreground">{ev.timestamp}</span>
                  </div>

                  <span className="text-xs font-mono font-bold text-emerald-800 bg-emerald-50 px-3 py-1 rounded-md border border-emerald-200/60">
                    {ev.status}
                  </span>
                </div>

                <div className="space-y-1 pt-1">
                  <div className="text-xs font-bold text-muted-foreground uppercase font-mono">
                    Người thi hành (Operator): <strong className="text-foreground font-sans font-bold">{ev.operator}</strong> [{ev.role}] • Phiên làm việc: <span className="text-sky-700">{ev.patientSession}</span>
                  </div>
                  <p className="text-sm font-medium text-slate-800 bg-background/80 p-3.5 rounded-xl border border-border/80 leading-relaxed dark:text-slate-100">
                    &quot;{ev.justification}&quot;
                  </p>
                </div>
              </div>
            ))}
        </div>

        <div className="p-4 bg-background border-t border-border text-xs text-muted-foreground font-mono flex items-center justify-between">
          <span>Sổ nhật ký được mã hóa HMAC-SHA256 trên tầng cơ sở dữ liệu PostgreSQL. Cấm tẩy xóa dưới mọi hình thức.</span>
          <span className="text-slate-700 font-bold dark:text-slate-200">100% Verified Compliant</span>
        </div>
      </div>
    </div>
  );
}
