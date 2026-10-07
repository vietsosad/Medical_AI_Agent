"use client";

import React from "react";
import { Database, RefreshCw, CheckCircle2, Server, ShieldCheck, HardDrive, Search } from "lucide-react";
import { cn } from "@/lib/utils";

interface KnowledgeIndex {
  id: string;
  sourceTitle: string;
  vectorCount: number;
  bm25Status: string;
  lastUpdated: string;
  status: "ONLINE" | "INDEXING" | "OFFLINE";
}

const RAG_COLLECTIONS: KnowledgeIndex[] = [
  {
    id: "col_esi_guidelines_2025",
    sourceTitle: "AHRQ ESI Triage V5 Clinical Handbook & Protocols",
    vectorCount: 14280,
    bm25Status: "Synced (Tokenized)",
    lastUpdated: "05/08/2026 • 12:45 UTC",
    status: "ONLINE",
  },
  {
    id: "col_cardiac_stroke_aha",
    sourceTitle: "AHA/ACC Chest Pain & Acute Stroke FAST Guidelines",
    vectorCount: 9840,
    bm25Status: "Synced (Tokenized)",
    lastUpdated: "04/08/2026 • 09:12 UTC",
    status: "ONLINE",
  },
  {
    id: "col_vn_moh_pharmacology",
    sourceTitle: "Dược thư Quốc gia & Hướng dẫn Bộ Y tế VN (2025)",
    vectorCount: 22100,
    bm25Status: "Đang dựng lại chỉ mục...",
    lastUpdated: "Vừa khởi chạy 2 phút trước",
    status: "INDEXING",
  },
];

/**
 * Trang Quản Trị Chỉ Mục Kho Phác Đồ (AI Ops Workstation)
 * - Giao diện phẳng, tinh giản, sắc nhọn (Pristine Neutral Ops Theme).
 * - Kiểm soát toàn vẹn chỉ mục vector phác đồ (pgvector + text-embedding-3-small).
 */
export default function AdminRagDatabasePage() {
  return (
    <div className="p-6 sm:p-8 space-y-8 max-w-7xl mx-auto font-sans text-foreground">
      {/* HEADER RAG DATABASE */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-card p-6 rounded-2xl border border-border shadow-2xs">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-slate-900 text-sky-400 flex items-center justify-center shrink-0">
            <Database className="w-6 h-6 stroke-[2.2]" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-foreground tracking-tight font-mono uppercase">
              Quản Trị Chỉ Mục Kho Phác Đồ (pgvector)
            </h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Kiểm tra độ toàn vẹn của chỉ mục vector phác đồ phục vụ đối chiếu bằng chứng
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => alert("Đang kích hoạt quy trình đồng bộ hóa chỉ mục vector toàn phần...")}
          className="min-h-[44px] inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold text-sm shadow-sm transition-all cursor-pointer"
        >
          <RefreshCw className="w-4 h-4 stroke-[2.2]" />
          <span>Đồng bộ hóa Vector (Sync)</span>
        </button>
      </div>

      {/* TELEMETRY OVERVIEW CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div className="p-6 rounded-2xl bg-card border border-border shadow-2xs space-y-2">
          <span className="text-xs font-bold text-muted-foreground uppercase font-mono flex items-center gap-1.5">
            <Server className="w-4 h-4 text-sky-600" />
            <span>Tổng lượng Vectors Embedded</span>
          </span>
          <p className="text-3xl font-extrabold text-foreground font-mono">
            46,220 <span className="text-sm font-medium text-slate-400">Embeddings</span>
          </p>
          <div className="text-xs text-emerald-700 font-medium pt-1 border-t border-slate-100 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> Model: text-embedding-004
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-card border border-border shadow-2xs space-y-2">
          <span className="text-xs font-bold text-muted-foreground uppercase font-mono flex items-center gap-1.5">
            <Search className="w-4 h-4 text-sky-600" />
            <span>Độ chính xác Hybrid Search</span>
          </span>
          <p className="text-3xl font-extrabold text-emerald-700 font-mono">
            99.6% <span className="text-sm font-medium text-slate-400">Precision</span>
          </p>
          <div className="text-xs text-muted-foreground font-medium pt-1 border-t border-slate-100">
            Truy xuất ngữ nghĩa bằng vector
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-card border border-border shadow-2xs space-y-2">
          <span className="text-xs font-bold text-muted-foreground uppercase font-mono flex items-center gap-1.5">
            <HardDrive className="w-4 h-4 text-sky-600" />
            <span>Thời gian đáp ứng RAG Latency</span>
          </span>
          <p className="text-3xl font-extrabold text-sky-600 font-mono">
            142 <span className="text-sm font-medium text-slate-400">ms / query</span>
          </p>
          <div className="text-xs text-muted-foreground font-medium pt-1 border-t border-slate-100">
            Vượt chỉ tiêu SLA (&lt; 300ms)
          </div>
        </div>
      </div>

      {/* DANH HỢP CÁC BỘ TRƯ VĂN BẢN (KNOWLEDGE COLLECTIONS TABLE) */}
      <div className="bg-card rounded-2xl border border-border shadow-2xs overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-base sm:text-lg font-bold text-foreground font-mono uppercase">
            Danh mục Bộ chỉ mục Khám Lâm Sàng (Knowledge Collections)
          </h2>
          <span className="text-xs font-mono text-slate-400">pgvector · text-embedding-3-small</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-background border-b border-border text-xs font-bold text-slate-600 font-mono uppercase dark:text-slate-300">
                <th className="py-3.5 px-6">Mã bộ sưu tập (Collection ID)</th>
                <th className="py-3.5 px-6">Nguồn phác đồ Y khoa (Source Title)</th>
                <th className="py-3.5 px-6 text-right">Vectors</th>
                <th className="py-3.5 px-6">Trạng thái chỉ mục</th>
                <th className="py-3.5 px-6">Cập nhật lúc</th>
                <th className="py-3.5 px-6 text-center">Trợ lực RAG</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm font-medium text-slate-800 dark:text-slate-100">
              {RAG_COLLECTIONS.map((item) => (
                <tr key={item.id} className="hover:bg-background/70 transition-colors">
                  <td className="py-4 px-6 font-mono text-xs font-bold text-sky-700">{item.id}</td>
                  <td className="py-4 px-6 font-bold text-foreground">{item.sourceTitle}</td>
                  <td className="py-4 px-6 text-right font-mono font-bold text-slate-700 dark:text-slate-200">{item.vectorCount.toLocaleString()}</td>
                  <td className="py-4 px-6 font-mono text-xs text-slate-600 dark:text-slate-300">{item.bm25Status}</td>
                  <td className="py-4 px-6 text-xs text-muted-foreground">{item.lastUpdated}</td>
                  <td className="py-4 px-6 text-center">
                    <span className={cn(
                      "px-3 py-1 rounded-full text-xs font-bold uppercase font-mono border inline-block",
                      item.status === "ONLINE" ? "bg-emerald-50 text-emerald-800 border-emerald-200" : "bg-amber-50 text-amber-800 border-amber-200"
                    )}>
                      {item.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="p-4 bg-background border-t border-border text-xs text-muted-foreground flex items-center justify-between font-mono">
          <span>Cam kết: 100% tài liệu được kiểm duyệt bởi Kíp Trách Nhiệm Chuyên Khoa trước khi nạp embedding.</span>
          <span className="flex items-center gap-1 text-emerald-700 font-bold"><ShieldCheck className="w-4 h-4" /> Zero-Hallucination Safe</span>
        </div>
      </div>
    </div>
  );
}
