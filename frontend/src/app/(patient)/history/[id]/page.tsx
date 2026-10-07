import React from "react";
import { Metadata } from "next";
import { HistoryDetailTerminal } from "@/components/history/HistoryDetailTerminal";

export const metadata: Metadata = {
  title: "Chi Tiết Ký Ức & Tái Hiện Hội Thoại Triage | Clinical AI System",
  description:
    "Trình tái hiện luồng hỏi bệnh cấu trúc và phiếu chẩn đoán SBAR quá khứ theo phong cách Bàn Đạp Chuyên Gia 2 cột chuẩn y khoa.",
};

interface HistoryDetailPageProps {
  params: Promise<{ id: string }>;
}

/**
 * ⭐ [SCR-HIST-02] DYNAMIC ROUTE MÀN HÌNH CHI TIẾT KÝ ỨC (/patient/history/[id])
 * Cam kết tuân thủ tuyệt đối cảnh báo phá vỡ cấu trúc của Next.js 15 App Router:
 * Dynamic route params là Bất đồng bộ (Async Promise) -> Buộc phải thi hành `await params`.
 */
export default async function HistoryDetailPage({ params }: HistoryDetailPageProps) {
  // 🚨 NEXT.JS 15 BREAKING CHANGE COMPLIANCE: Await dynamic route params before consumption
  const { id } = await params;

  return <HistoryDetailTerminal sessionId={id} />;
}
