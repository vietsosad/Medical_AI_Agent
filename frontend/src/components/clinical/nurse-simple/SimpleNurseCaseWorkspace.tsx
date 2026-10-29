"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { toast } from "sonner";

import { AttentionBanner } from "@/components/clinical/nurse-simple/case/AttentionBanner";
import { CaseHeader } from "@/components/clinical/nurse-simple/case/CaseHeader";
import { CaseLoadError, CaseSkeleton } from "@/components/clinical/nurse-simple/case/CaseStates";
import { QUEUE_HREF, contactLines } from "@/components/clinical/nurse-simple/case/case-format";
import { riseIn } from "@/components/clinical/nurse-simple/case/case-motion";
import { DecisionDesk, type DeskView } from "@/components/clinical/nurse-simple/case/DecisionDesk";
import {
  isOwnedByOther,
  ownershipOf,
  type ClaimAction,
  type ClaimActionOptions,
} from "@/components/clinical/nurse-simple/case/ownership";
import { ProtocolCriteria } from "@/components/clinical/nurse-simple/case/ProtocolCriteria";
import { SbarSummary } from "@/components/clinical/nurse-simple/case/SbarSummary";
import { TranscriptCard } from "@/components/clinical/nurse-simple/case/TranscriptCard";
import { useMediaQuery } from "@/components/clinical/nurse-simple/case/use-media-query";
import { esiTheme } from "@/components/clinical/nurse-simple/esi-theme";
import { SimpleCaseChatDock } from "@/components/clinical/nurse-simple/SimpleCaseChatDock";
import { SimpleCaseChatPanel } from "@/components/clinical/nurse-simple/SimpleCaseChatPanel";
import type { DecidedSummary } from "@/components/clinical/nurse-simple/SimpleDecisionForm";
import { SimplePatientContactPanel } from "@/components/clinical/nurse-simple/SimplePatientContactPanel";
import { useClaimSimpleCase, useSimpleNurseCase } from "@/queries/useSimpleNurseQueries";
import { SimpleNurseApiError } from "@/services/simple-nurse.service";
import { useAuthStore } from "@/store/useAuthStore";

/**
 * Hồ sơ ca và bàn quyết định của một ca Triage Agent.
 *
 * Bố cục theo trạm rà soát lâm sàng, đọc từ trái sang phải:
 * - cột trái: gọi cho ai (liên lạc, hồ sơ sức khỏe) và kênh nhắn người bệnh;
 * - cột giữa: tài liệu để đối chiếu (SBAR, tiêu chí phác đồ, hội thoại gốc);
 * - cột phải: bàn quyết định ghim theo màn hình, chốt ESI sau cùng.
 * Khung nhìn chưa đủ rộng cho ba cột thì cột trái gộp lên đầu cột đọc và kênh
 * nhắn tin chuyển thành khung nổi; màn hẹp hơn nữa thì xếp một cột theo đúng
 * thứ tự đó.
 */

/** Đủ chỗ cho ba cột (breakpoint 2xl của Tailwind). */
const WIDE_LAYOUT_QUERY = "(min-width: 96rem)";
/** Thời gian giữ lời xác nhận sau khi chốt, trước khi quay về hàng đợi. */
const CONFIRMATION_HOLD_MS = 1500;

const ACTION_ERROR_TITLE: Record<ClaimAction, string> = {
  CLAIM: "Chưa nhận được ca",
  RELEASE: "Chưa trả được ca về hàng đợi",
  PARK: "Chưa tạm gác được ca",
  RESTORE: "Chưa đẩy được ca lại hàng đợi",
};

/** 409 CASE_VERSION_CONFLICT từ `_assert_version` (routes_nurse_simple.py).
 * Đọc mã lỗi máy chủ; câu chữ chỉ là lối dự phòng cho lỗi không qua service. */
function isVersionConflict(error: Error): boolean {
  if (error instanceof SimpleNurseApiError) return error.code === "CASE_VERSION_CONFLICT";
  return /cập nhật bởi người khác/i.test(error.message);
}

export function SimpleNurseCaseWorkspace({
  sessionId,
  openChat = false,
}: {
  sessionId: string;
  /** `?openChat=1` từ hộp thư "Tin nhắn mới" (SimpleClinicalInbox.tsx). */
  openChat?: boolean;
}) {
  const { data, isError, error, refetch } = useSimpleNurseCase(sessionId);
  const currentUserId = useAuthStore((state) => state.user?.id);
  const claim = useClaimSimpleCase(sessionId);
  const router = useRouter();
  const wide = useMediaQuery(WIDE_LAYOUT_QUERY);
  const [decided, setDecided] = useState<DecidedSummary | null>(null);
  const leftForQueue = useRef(false);

  const backToQueue = useCallback(() => {
    if (leftForQueue.current) return;
    leftForQueue.current = true;
    router.push(QUEUE_HREF);
  }, [router]);

  // Chốt xong: giữ lời xác nhận một nhịp ngắn rồi mới về hàng đợi, như trước.
  useEffect(() => {
    if (!decided) return;
    const timer = window.setTimeout(backToQueue, CONFIRMATION_HOLD_MS);
    return () => window.clearTimeout(timer);
  }, [decided, backToQueue]);

  if (!data) {
    // Lỗi khi đã có dữ liệu (một nhịp làm mới hỏng) không được xoá hồ sơ đang
    // đọc khỏi màn hình -- chỉ báo lỗi toàn trang khi chưa từng tải được.
    return isError ? (
      <CaseLoadError
        message={error instanceof Error ? error.message : "Vui lòng thử lại."}
        onRetry={() => void refetch()}
      />
    ) : (
      <CaseSkeleton />
    );
  }

  const ownership = ownershipOf(data, currentUserId);
  const isClosed = ownership === "closed";
  const canDecide = ownership === "mine" || ownership === "parked-mine";
  const showChat = !isOwnedByOther(data, currentUserId);
  const pendingAction = claim.isPending ? (claim.variables?.action ?? null) : null;
  const citations = data.sbar?.citations ?? [];
  const deskView: DeskView = decided ? "confirmation" : canDecide ? "form" : isClosed ? "closed" : "locked";

  const reportError = (title: string, actionError: Error) => {
    if (isVersionConflict(actionError)) {
      toast.error("Ca vừa được cập nhật ở nơi khác", {
        description: "Dữ liệu mới nhất đã được tải lại. Hãy xem lại ca trước khi thao tác tiếp.",
      });
    } else {
      toast.error(title, { description: actionError.message });
    }
    void refetch();
  };

  const runClaimAction = (action: ClaimAction, options: ClaimActionOptions = {}) => {
    claim.mutate(
      { version: data.case_version, action, ...(options.reason ? { reason: options.reason } : {}) },
      {
        onSuccess: () => {
          options.onSuccess?.();
          if (action === "RELEASE") {
            toast.success("Đã trả ca về hàng đợi");
            router.push(QUEUE_HREF);
          } else if (action === "PARK") {
            toast.success("Đã tạm gác ca", {
              description: "Ca chuyển sang mục Tạm gác lại. Bạn vẫn chốt được ESI khi đã đủ thông tin.",
            });
          } else if (action === "RESTORE") {
            toast.success("Ca đã trở lại hàng đợi");
          }
        },
        onError: (actionError) => reportError(ACTION_ERROR_TITLE[action], actionError),
      },
    );
  };

  const handleDecided = (summary: DecidedSummary) => {
    setDecided(summary);
    toast.success(`Đã chốt ESI ${summary.finalEsi} · ${esiTheme(summary.finalEsi).label}`, {
      description: "Người bệnh sẽ thấy mức này trong phiên của họ.",
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <CaseHeader
        data={data}
        ownership={ownership}
        canDecide={canDecide && !decided}
        actionsLocked={decided !== null}
        pendingAction={pendingAction}
        onClaimAction={runClaimAction}
        refreshFailed={isError}
      />

      {data.attention_required && (
        <AttentionBanner data={data} callTarget={contactLines(data.patient)[0] ?? null} closed={isClosed} />
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem] 2xl:grid-cols-[16rem_minmax(0,1fr)_22rem]">
        {/* Ở 2xl khung này "tan" (display: contents) để cột liên lạc và cột đọc
            thành hai cột riêng của lưới; dưới 2xl nó là một cột đọc liền mạch. */}
        <div className="flex min-w-0 flex-col gap-6 2xl:contents">
          <div className="@container flex min-w-0 flex-col gap-6 2xl:col-start-1 2xl:row-start-1">
            <SimplePatientContactPanel patient={data.patient} delay={0.05} className="@lg:grid-cols-2" />
            {wide && showChat && (
              <motion.div {...riseIn(0.15)} className="sticky top-6">
                <SimpleCaseChatPanel sessionId={sessionId} readOnly={isClosed} autoFocus={openChat} />
              </motion.div>
            )}
          </div>

          <div className="flex min-w-0 flex-col gap-6 2xl:col-start-2 2xl:row-start-1">
            <SbarSummary sbar={data.sbar} delay={0.1} />
            {citations.length > 0 && <ProtocolCriteria citations={citations} delay={0.15} />}
            <TranscriptCard messages={data.messages} delay={0.2} />
          </div>
        </div>

        <DecisionDesk
          data={data}
          sessionId={sessionId}
          view={deskView}
          ownership={ownership}
          decided={decided}
          holdSeconds={CONFIRMATION_HOLD_MS / 1000}
          onDecided={handleDecided}
          onDecisionError={(decisionError) => reportError("Chưa lưu được quyết định", decisionError)}
          onLeaveNow={backToQueue}
          delay={0.15}
          className="xl:col-start-2 xl:row-start-1 2xl:col-start-3"
        />
      </div>

      {!wide && showChat && <SimpleCaseChatDock sessionId={sessionId} initialOpen={openChat} readOnly={isClosed} />}
    </div>
  );
}
