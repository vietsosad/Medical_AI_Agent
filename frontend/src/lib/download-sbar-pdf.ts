import { axiosClient } from "@/lib/api/axios.client";

export async function downloadSbarPdf(sessionId: string): Promise<void> {
  const response = await axiosClient.get<Blob>(
    `/api/v1/triage/session/${sessionId}/pdf`,
    { responseType: "blob" },
  );
  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement("a");

  try {
    link.href = url;
    link.download = `Phieu_SBAR_${sessionId.slice(-8)}.pdf`;
    document.body.appendChild(link);
    link.click();
  } finally {
    link.remove();
    window.URL.revokeObjectURL(url);
  }
}
