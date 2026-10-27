"use client";

import { useEffect } from "react";

/**
 * Lưới an toàn cuối cùng khi chính layout gốc hỏng. Next thay toàn bộ tài liệu
 * bằng file này và không nạp CSS toàn cục, nên giao diện dùng style nội tuyến
 * và không phụ thuộc component nào của ứng dụng. Cùng quy tắc với `error.tsx`:
 * không hiện chi tiết lỗi, luôn có lối gọi 115.
 */
export default function GlobalError({
  error,
  unstable_retry,
}: {
  error: Error & { digest?: string };
  unstable_retry: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang="vi">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
          background: "#f8fafc",
          color: "#0f172a",
        }}
      >
        <title>Hệ thống gặp sự cố</title>
        <main style={{ maxWidth: 480, padding: 32, textAlign: "center" }}>
          <h1 style={{ fontSize: 22, margin: "0 0 16px" }}>Hệ thống đang gặp sự cố</h1>
          <p style={{ fontSize: 16, lineHeight: 1.6, margin: "0 0 24px" }}>
            Ứng dụng chưa tải được. Vui lòng thử lại sau ít phút.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 16, alignItems: "center" }}>
            <button
              type="button"
              onClick={() => unstable_retry()}
              style={{
                minHeight: 48,
                padding: "0 24px",
                borderRadius: 12,
                border: "1px solid #cbd5e1",
                background: "#ffffff",
                fontSize: 16,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Thử lại
            </button>
            <p style={{ fontSize: 16, fontWeight: 600, color: "#881337", margin: 0 }}>
              Nếu đang có dấu hiệu nguy kịch, gọi 115 ngay.
            </p>
            <a
              href="tel:115"
              aria-label="Gọi Tổng đài Cấp cứu Quốc gia 115"
              style={{
                display: "inline-flex",
                alignItems: "center",
                minHeight: 48,
                padding: "0 24px",
                borderRadius: 12,
                background: "#be123c",
                color: "#ffffff",
                fontSize: 16,
                fontWeight: 800,
                textDecoration: "none",
              }}
            >
              Gọi 115
            </a>
          </div>
        </main>
      </body>
    </html>
  );
}
