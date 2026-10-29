"use client";

import {
  createElement,
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type FocusEvent,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import Image from "next/image";
import Link from "next/link";
import { useReducedMotion } from "framer-motion";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  MessageSquare,
  Pause,
  Play,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { HealthTopicDetailDialog } from "@/components/landing/HealthTopicDetailDialog";
import { fallbackIconForTopic, photoForTopic } from "@/components/landing/health-topic-photos";
import { LANDING_ANCHORS } from "@/components/landing/landing-anchors";
import { PhotoCreditDisclosure } from "@/components/landing/photo-credits";
import {
  advancePhase,
  approachVelocity,
  circularItemX,
  impulseForDistance,
  positiveModulo,
} from "@/components/landing/topic-stream-motion";
import { patientEntryHref } from "@/lib/auth-routing";
import { cn } from "@/lib/utils";
import { useHealthTopics } from "@/queries/useHealthTopics";
import type { HealthTopicSummaryDTO } from "@/services/health.service";
import { useAuthStore } from "@/store/useAuthStore";

/** Tốc độ trôi khi không ai chạm vào: đủ để thấy dòng sống, đủ chậm để đọc kịp. */
const CRUISE_SPEED_PX_PER_SECOND = 26;
/** Hằng số thời gian của quán tính: dừng dần dưới con trỏ, tăng tốc dần khi rời đi. */
const SETTLE_SECONDS = 0.55;
const REST_SPEED_PX_PER_SECOND = 0.4;
const MAX_FLING_PX_PER_SECOND = 2_400;
const DRAG_THRESHOLD_PX = 6;
const STREAM_GAP_PX = 16;
const MAX_FRAME_DELTA_MS = 32;

interface StreamLayout {
  items: HTMLElement[];
  starts: number[];
  widths: number[];
  loopLength: number;
  viewportWidth: number;
  circular: boolean;
}

interface DragState {
  pointerId: number;
  startX: number;
  startY: number;
  startPhase: number;
  lastX: number;
  lastTime: number;
  velocity: number;
  engaged: boolean;
}

function formatUpdatedDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

/** "WHO - Tổ chức Y tế Thế giới" -> "WHO": nhãn trên ảnh chỉ cần tên nguồn, bản đầy đủ nằm ở `title`. */
function shortSourceName(source: string): string {
  return source.split(" - ")[0].trim() || source;
}

/** Điểm vào Triage kèm chủ đề người dùng vừa đọc; khách chưa đăng nhập đi qua login trước. */
export function triageHrefForTopic(slug: string, isAuthenticated: boolean): string {
  return patientEntryHref(`/triage?health_topic=${encodeURIComponent(slug)}`, isAuthenticated);
}

function StreamSkeleton() {
  return (
    <div className="flex gap-4 overflow-hidden" aria-hidden="true">
      {[0, 1, 2, 3, 4].map((key) => (
        <div
          key={key}
          className="skeleton-sweep relative h-[22rem] w-60 shrink-0 overflow-hidden rounded-2xl bg-slate-200 sm:h-[26rem] sm:w-72 dark:bg-slate-800"
        />
      ))}
    </div>
  );
}

interface TopicCardProps {
  topic: HealthTopicSummaryDTO;
  isAuthenticated: boolean;
  circular: boolean;
  onOpenDetail: (slug: string) => void;
}

function TopicCard({ topic, isAuthenticated, circular, onOpenDetail }: TopicCardProps) {
  const photo = photoForTopic(topic.slug);
  const headingId = `health-topic-${topic.slug}`;

  return (
    <article
      aria-labelledby={headingId}
      data-flow-item="true"
      className={cn(
        "group/card h-[22rem] w-60 shrink-0 select-none sm:h-[26rem] sm:w-72",
        circular ? "absolute left-0 top-0" : "relative snap-start",
      )}
    >
      <div className="absolute inset-0 overflow-hidden rounded-2xl bg-slate-900 shadow-[0_18px_40px_-24px_rgba(15,23,42,0.55)]">
        {photo ? (
          <Image
            src={photo.src}
            alt={photo.alt}
            fill
            sizes="(min-width: 640px) 288px, 240px"
            draggable={false}
            style={photo.focus ? { objectPosition: photo.focus } : undefined}
            className="object-cover transition-transform duration-[900ms] ease-[cubic-bezier(0.16,1,0.3,1)] group-hover/card:scale-[1.05] group-focus-within/card:scale-[1.05] motion-reduce:transition-none motion-reduce:group-hover/card:scale-100 motion-reduce:group-focus-within/card:scale-100"
          />
        ) : (
          <div className="absolute inset-0 flex items-start justify-center bg-gradient-to-b from-teal-700 to-slate-900 pt-16">
            {createElement(fallbackIconForTopic(topic.slug), {
              className: "size-20 text-teal-100/80",
              strokeWidth: 1.5,
              "aria-hidden": true,
            })}
          </div>
        )}
        <div
          aria-hidden="true"
          className="absolute inset-0 bg-gradient-to-t from-slate-950/95 via-slate-950/45 to-slate-950/0"
        />
        <div
          aria-hidden="true"
          className="absolute inset-0 bg-slate-950/35 opacity-0 transition-opacity duration-300 group-hover/card:opacity-100 group-focus-within/card:opacity-100"
        />
      </div>

      {topic.ai_assisted && (
        <span
          title="Phần tóm tắt đã được AI diễn giải sẵn một lần từ nội dung của nguồn y tế được trích dẫn"
          className="absolute left-4 top-4 z-20 inline-flex items-center gap-1.5 rounded-full bg-slate-950/65 px-2.5 py-1 text-sm font-medium text-white"
        >
          <Sparkles className="size-3.5 text-teal-200" aria-hidden="true" />
          AI diễn giải
        </span>
      )}

      <div className="absolute inset-x-0 bottom-0 p-4 sm:p-6">
        <p className="mb-2 flex h-8 w-fit max-w-full items-center rounded-full bg-white/15 px-2 text-sm font-semibold text-white" title={topic.source}>
          <span className="truncate">Nguồn: {shortSourceName(topic.source)}</span>
        </p>
        <h3 id={headingId} className="text-xl font-bold leading-snug tracking-tight text-white text-balance">
          <button
            type="button"
            onClick={() => onOpenDetail(topic.slug)}
            className="text-left after:absolute after:inset-0 after:z-10 after:rounded-2xl focus-visible:outline-none focus-visible:after:ring-4 focus-visible:after:ring-inset focus-visible:after:ring-teal-300"
          >
            {topic.name}
          </button>
        </h3>
        <div className="grid grid-rows-[0fr] opacity-0 transition-[grid-template-rows,opacity] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] group-hover/card:grid-rows-[1fr] group-hover/card:opacity-100 group-focus-within/card:grid-rows-[1fr] group-focus-within/card:opacity-100 motion-reduce:transition-none">
          <div className="overflow-hidden">
            <p className="line-clamp-3 pt-2 text-sm leading-6 text-white/85">{topic.summary}</p>
            {topic.symptoms.length > 0 && (
              <p className="pt-2 text-sm leading-6 text-teal-100">
                {topic.symptoms.slice(0, 3).join(" · ")}
              </p>
            )}
            <p className="pt-2 text-sm text-white/70">Cập nhật {formatUpdatedDate(topic.last_updated)}</p>
            <Link
              href={triageHrefForTopic(topic.slug, isAuthenticated)}
              className="relative z-20 mt-4 inline-flex min-h-11 items-center gap-2 rounded-lg bg-white px-4 text-sm font-bold text-teal-900 transition-colors hover:bg-teal-50 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-teal-300"
            >
              <MessageSquare className="size-4" aria-hidden="true" />
              Kiểm tra triệu chứng
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </div>
    </article>
  );
}

function PhotoCredits({ topics }: { topics: HealthTopicSummaryDTO[] }) {
  const photos = topics.flatMap((topic) => {
    const photo = photoForTopic(topic.slug);
    return photo ? [{ key: topic.slug, label: topic.name, credit: photo.credit }] : [];
  });

  return <PhotoCreditDisclosure summary="Nguồn ảnh: Wikimedia Commons" photos={photos} centered className="mt-6" />;
}

/**
 * Lớp giáo dục sức khỏe trên trang chủ: một dòng ảnh trôi liên tục có quán
 * tính. Dòng chậm dần rồi dừng dưới con trỏ, tăng tốc lại khi con trỏ rời đi,
 * kéo/vuốt được và trôi theo đà khi thả tay. Chuyển động chỉ thay đổi cách
 * trình bày đúng danh sách backend trả về; không xếp hạng mức độ nguy hiểm hay
 * tự suy diễn nội dung lâm sàng.
 */
export function HealthTopicsSection() {
  const { data: topics, isLoading, isError } = useHealthTopics();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const reducedMotion = Boolean(useReducedMotion());
  const sectionRef = useRef<HTMLElement>(null);
  const railRef = useRef<HTMLDivElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const layoutRef = useRef<StreamLayout | null>(null);
  const phaseRef = useRef(0);
  const velocityRef = useRef(0);
  const targetRef = useRef(0);
  const frozenRef = useRef(true);
  const dragRef = useRef<DragState | null>(null);
  const suppressClickRef = useRef(false);
  const kickRef = useRef<() => void>(() => {});
  const [openSlug, setOpenSlug] = useState<string | null>(null);
  const [userPaused, setUserPaused] = useState(false);
  const [railHovered, setRailHovered] = useState(false);
  const [focusWithin, setFocusWithin] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [circularFlow, setCircularFlow] = useState(false);
  const [inView, setInView] = useState(() => typeof IntersectionObserver !== "function");
  const [documentVisible, setDocumentVisible] = useState(
    () => typeof document === "undefined" || document.visibilityState === "visible",
  );

  const count = topics?.length ?? 0;
  // Ngoài màn hình hoặc tab ẩn: đứng yên ngay, không tốn khung hình nào.
  const frozen = reducedMotion || !inView || !documentVisible;
  const flowPaused = frozen || userPaused || railHovered || focusWithin || openSlug !== null;

  const positionStreamItems = useCallback(() => {
    const layout = layoutRef.current;
    if (!layout?.circular) return;

    layout.items.forEach((item, index) => {
      const x = circularItemX(layout.starts[index], layout.widths[index], phaseRef.current, layout.loopLength);
      item.style.transform = `translate3d(${x.toFixed(2)}px, 0, 0)`;
    });
  }, []);

  useEffect(() => {
    const element = sectionRef.current;
    if (!element || typeof IntersectionObserver !== "function") return;
    const observer = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), {
      threshold: 0.15,
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const handleVisibilityChange = () => setDocumentVisible(document.visibilityState === "visible");
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, []);

  useLayoutEffect(() => {
    const rail = railRef.current;
    const track = trackRef.current;
    if (!rail || !track || count < 2) {
      layoutRef.current = null;
      setCircularFlow(false);
      return;
    }

    let disposed = false;
    const measure = () => {
      if (disposed) return;

      const items = Array.from(track.querySelectorAll<HTMLElement>("[data-flow-item='true']"));
      const widths = items.map((item) => item.getBoundingClientRect().width);
      const starts: number[] = [];
      let cursor = 0;
      widths.forEach((width) => {
        starts.push(cursor);
        cursor += width + STREAM_GAP_PX;
      });

      const viewportWidth = rail.clientWidth;
      const maxItemWidth = widths.length > 0 ? Math.max(...widths) : 0;
      const circular =
        !reducedMotion
        && viewportWidth > 0
        && widths.every((width) => width > 0)
        && cursor >= viewportWidth + maxItemWidth;

      layoutRef.current = { items, starts, widths, loopLength: cursor, viewportWidth, circular };
      setCircularFlow(circular);

      if (circular) {
        phaseRef.current = positiveModulo(phaseRef.current, cursor);
        positionStreamItems();
      } else {
        phaseRef.current = 0;
        velocityRef.current = 0;
        items.forEach((item) => item.style.removeProperty("transform"));
      }
    };

    measure();

    const resizeObserver = typeof ResizeObserver === "function" ? new ResizeObserver(measure) : null;
    resizeObserver?.observe(rail);
    if (!resizeObserver) window.addEventListener("resize", measure);
    void document.fonts?.ready.then(measure);

    return () => {
      disposed = true;
      resizeObserver?.disconnect();
      if (!resizeObserver) window.removeEventListener("resize", measure);
    };
  }, [count, positionStreamItems, reducedMotion]);

  // Một vòng rAF duy nhất, chỉ chạy khi dòng còn chuyển động: tích phân vận
  // tốc về đích rồi tự dừng khi đã nghỉ hẳn. Mọi thứ khác chỉ cần "đánh thức" nó.
  useEffect(() => {
    if (!circularFlow) return;

    let frame = 0;
    let lastTimestamp: number | null = null;
    const step = (timestamp: number) => {
      const layout = layoutRef.current;
      if (!layout?.circular || frozenRef.current) {
        velocityRef.current = 0;
        frame = 0;
        return;
      }

      const elapsed = lastTimestamp === null ? 0 : Math.min(timestamp - lastTimestamp, MAX_FRAME_DELTA_MS);
      lastTimestamp = timestamp;
      const drag = dragRef.current;
      if (!drag?.engaged) {
        velocityRef.current = approachVelocity(velocityRef.current, targetRef.current, elapsed, SETTLE_SECONDS);
        phaseRef.current = advancePhase(phaseRef.current, velocityRef.current, elapsed, layout.loopLength);
        positionStreamItems();
      }

      const atRest =
        !drag?.engaged
        && targetRef.current === 0
        && Math.abs(velocityRef.current) < REST_SPEED_PX_PER_SECOND;
      if (atRest) {
        velocityRef.current = 0;
        frame = 0;
        lastTimestamp = null;
        return;
      }
      frame = window.requestAnimationFrame(step);
    };

    kickRef.current = () => {
      if (frame !== 0 || frozenRef.current) return;
      lastTimestamp = null;
      frame = window.requestAnimationFrame(step);
    };
    kickRef.current();

    return () => {
      window.cancelAnimationFrame(frame);
      frame = 0;
      kickRef.current = () => {};
    };
  }, [circularFlow, positionStreamItems]);

  useEffect(() => {
    targetRef.current = flowPaused ? 0 : CRUISE_SPEED_PX_PER_SECOND;
    frozenRef.current = frozen;
    if (frozen) velocityRef.current = 0;
    kickRef.current();
  }, [flowPaused, frozen]);

  const cardStep = () => {
    const layout = layoutRef.current;
    const width = layout?.widths[0] ?? railRef.current?.querySelector<HTMLElement>("[data-flow-item='true']")?.offsetWidth ?? 0;
    return width + STREAM_GAP_PX;
  };

  /** Đẩy dòng đúng một thẻ bằng một cú hích vận tốc, rồi để quán tính đưa nó về nhịp cũ. */
  const nudge = (direction: 1 | -1) => {
    const distance = cardStep();
    if (layoutRef.current?.circular && !frozenRef.current) {
      velocityRef.current += direction * impulseForDistance(distance, SETTLE_SECONDS);
      kickRef.current();
      return;
    }
    railRef.current?.scrollBy?.({ left: direction * distance, behavior: reducedMotion ? "auto" : "smooth" });
  };

  const centerFocusedItem = (item: HTMLElement) => {
    const layout = layoutRef.current;
    if (!layout?.circular) return;
    const index = layout.items.indexOf(item);
    if (index < 0) return;

    const targetX = Math.max(0, (layout.viewportWidth - layout.widths[index]) / 2);
    phaseRef.current = positiveModulo(layout.starts[index] - targetX, layout.loopLength);
    velocityRef.current = 0;
    positionStreamItems();
  };

  const handleFocusCapture = (event: FocusEvent<HTMLDivElement>) => {
    setFocusWithin(true);
    const item = (event.target as HTMLElement).closest<HTMLElement>("[data-flow-item='true']");
    if (item) centerFocusedItem(item);
  };

  const handleBlurCapture = (event: FocusEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setFocusWithin(false);
  };

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    suppressClickRef.current = false;
    if (!layoutRef.current?.circular || event.button !== 0) return;
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      startPhase: phaseRef.current,
      lastX: event.clientX,
      lastTime: event.timeStamp,
      velocity: 0,
      engaged: false,
    };
  };

  const handlePointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    const layout = layoutRef.current;
    if (!drag || drag.pointerId !== event.pointerId || !layout?.circular) return;

    const dx = event.clientX - drag.startX;
    if (!drag.engaged) {
      if (Math.abs(dx) < DRAG_THRESHOLD_PX) return;
      // Cử chỉ chủ yếu theo chiều dọc là người dùng đang cuộn trang.
      if (Math.abs(event.clientY - drag.startY) > Math.abs(dx)) {
        dragRef.current = null;
        return;
      }
      drag.engaged = true;
      event.currentTarget.setPointerCapture?.(event.pointerId);
      velocityRef.current = 0;
      setDragging(true);
      kickRef.current();
    }

    const elapsedSeconds = Math.max(event.timeStamp - drag.lastTime, 1) / 1_000;
    const instantVelocity = -(event.clientX - drag.lastX) / elapsedSeconds;
    drag.velocity = drag.velocity * 0.6 + instantVelocity * 0.4;
    drag.lastX = event.clientX;
    drag.lastTime = event.timeStamp;
    phaseRef.current = positiveModulo(drag.startPhase - dx, layout.loopLength);
    positionStreamItems();
  };

  const endDrag = (event: ReactPointerEvent<HTMLDivElement>, fling: boolean) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    dragRef.current = null;
    if (!drag.engaged) return;

    suppressClickRef.current = fling;
    velocityRef.current = fling
      ? Math.max(-MAX_FLING_PX_PER_SECOND, Math.min(MAX_FLING_PX_PER_SECOND, drag.velocity))
      : 0;
    setDragging(false);
    kickRef.current();
  };

  // Một lần kéo kết thúc trên một thẻ không được tính là bấm mở thẻ đó.
  const handleClickCapture = (event: ReactMouseEvent<HTMLDivElement>) => {
    if (!suppressClickRef.current) return;
    suppressClickRef.current = false;
    event.preventDefault();
    event.stopPropagation();
  };

  return (
    <section
      ref={sectionRef}
      id={LANDING_ANCHORS.topics}
      aria-labelledby="health-topics-heading"
      className="relative w-full scroll-mt-24 overflow-hidden border-b border-border bg-card py-20 sm:py-24 lg:py-28"
    >
      <header className="mx-auto mb-10 flex max-w-7xl flex-col gap-6 px-4 sm:px-6 md:flex-row md:items-end md:justify-between lg:mb-12 lg:px-8">
        <div className="max-w-2xl">
          <h2
            id="health-topics-heading"
            className="text-[2rem] font-extrabold leading-[1.12] tracking-[-0.03em] text-foreground text-balance sm:text-5xl sm:leading-[1.08]"
          >
            Thông tin sức khỏe đáng chú ý
          </h2>
          <p className="mt-4 text-base leading-7 text-muted-foreground sm:text-lg sm:leading-8">
            Cập nhật các vấn đề sức khỏe đang được quan tâm và cách phòng ngừa.
          </p>
        </div>

        {!isLoading && !isError && count > 1 && (
          <div role="group" aria-label="Điều khiển dòng chủ đề" className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={() => nudge(-1)}
              aria-label="Xem chủ đề trước"
              className="flex size-12 items-center justify-center rounded-full border border-border bg-card text-foreground transition-colors hover:border-brand-edge hover:text-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            >
              <ArrowLeft className="size-5" aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={() => setUserPaused((current) => !current)}
              aria-pressed={userPaused}
              aria-label={userPaused ? "Cho dòng chủ đề trôi tiếp" : "Dừng dòng chủ đề"}
              className="flex size-12 items-center justify-center rounded-full border border-border bg-card text-foreground transition-colors hover:border-brand-edge hover:text-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            >
              {userPaused ? <Play className="size-5" aria-hidden="true" /> : <Pause className="size-5" aria-hidden="true" />}
            </button>
            <button
              type="button"
              onClick={() => nudge(1)}
              aria-label="Xem chủ đề tiếp theo"
              className="flex size-12 items-center justify-center rounded-full border border-border bg-card text-foreground transition-colors hover:border-brand-edge hover:text-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            >
              <ArrowRight className="size-5" aria-hidden="true" />
            </button>
          </div>
        )}
      </header>

      {isLoading ? (
        <div className="px-4 sm:px-6">
          <StreamSkeleton />
        </div>
      ) : isError ? (
        <div className="px-4">
          <div role="status" className="mx-auto flex max-w-3xl items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm font-medium text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
            <AlertCircle className="size-5 shrink-0" aria-hidden="true" />
            Không thể tải thông tin sức khỏe lúc này.
          </div>
        </div>
      ) : !topics || count === 0 ? (
        <div className="px-4">
          <div role="status" className="mx-auto flex max-w-3xl items-center gap-3 rounded-xl border border-slate-200 bg-white p-6 text-sm font-medium text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
            <BookOpen className="size-5 shrink-0" aria-hidden="true" />
            Hiện chưa có thông tin sức khỏe đáng chú ý.
          </div>
        </div>
      ) : (
        <div onFocusCapture={handleFocusCapture} onBlurCapture={handleBlurCapture}>
          <div
            ref={railRef}
            role="region"
            aria-label="Dòng chủ đề sức khỏe"
            data-testid="health-topic-stream"
            data-flow-state={flowPaused ? "paused" : "running"}
            data-circular={circularFlow ? "true" : "false"}
            onPointerEnter={(event) => event.pointerType === "mouse" && setRailHovered(true)}
            onPointerLeave={(event) => event.pointerType === "mouse" && setRailHovered(false)}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={(event) => endDrag(event, true)}
            onPointerCancel={(event) => endDrag(event, false)}
            onClickCapture={handleClickCapture}
            onDragStart={(event) => event.preventDefault()}
            className={cn(
              "health-topic-stream flow-rail",
              circularFlow ? (dragging ? "cursor-grabbing" : "cursor-grab") : "snap-x snap-mandatory overflow-x-auto scroll-px-4 sm:scroll-px-6",
            )}
          >
            <div
              ref={trackRef}
              className={cn(
                "relative",
                circularFlow ? "h-[22rem] w-full sm:h-[26rem]" : "flex w-max gap-4 px-4 sm:px-6",
              )}
            >
              {topics.map((topic) => (
                <TopicCard
                  key={topic.slug}
                  topic={topic}
                  isAuthenticated={isAuthenticated}
                  circular={circularFlow}
                  onOpenDetail={setOpenSlug}
                />
              ))}
            </div>
          </div>

          <div className="px-4">
            <PhotoCredits topics={topics} />
          </div>
        </div>
      )}

      <p className="mx-auto mt-6 flex max-w-7xl items-center justify-center gap-2 px-4 text-center text-sm leading-6 text-muted-foreground sm:px-6 lg:px-8">
        <ShieldCheck className="size-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
        Thông tin tham khảo, không thay thế cho thăm khám trực tiếp của nhân viên y tế.
      </p>

      <HealthTopicDetailDialog
        slug={openSlug}
        isAuthenticated={isAuthenticated}
        onClose={() => setOpenSlug(null)}
      />
    </section>
  );
}

export default HealthTopicsSection;
