"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type FocusEvent,
} from "react";
import Link from "next/link";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
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
  type LucideIcon,
} from "lucide-react";

import { HealthTopicArtwork, artworkIconForTopic } from "@/components/landing/HealthTopicArtwork";
import { HealthTopicArtworkLightbox } from "@/components/landing/HealthTopicArtworkLightbox";
import { HealthTopicDetailDialog } from "@/components/landing/HealthTopicDetailDialog";
import {
  advanceCircularPhase,
  circularItemX,
  positiveModulo,
} from "@/components/landing/topic-stream-motion";
import { patientEntryHref } from "@/lib/auth-routing";
import { cn } from "@/lib/utils";
import { useHealthTopics } from "@/queries/useHealthTopics";
import type { HealthTopicSummaryDTO } from "@/services/health.service";
import { useAuthStore } from "@/store/useAuthStore";

const ROTATION_MS = 7_000;
const STREAM_SPEED_PX_PER_SECOND = 16;
const STREAM_GAP_PX = 8;
const MAX_FRAME_DELTA_MS = 32;

interface StreamLayout {
  items: HTMLButtonElement[];
  starts: number[];
  widths: number[];
  loopLength: number;
  viewportWidth: number;
  circular: boolean;
}

function formatUpdatedDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

/** Điểm vào Triage kèm chủ đề người dùng vừa đọc; khách chưa đăng nhập đi qua login trước. */
export function triageHrefForTopic(slug: string, isAuthenticated: boolean): string {
  return patientEntryHref(`/triage?health_topic=${encodeURIComponent(slug)}`, isAuthenticated);
}

function topicIcon(topic: HealthTopicSummaryDTO): LucideIcon {
  return artworkIconForTopic(topic.slug, topic.name);
}

function SpotlightSkeleton() {
  return (
    <div className="mx-auto max-w-5xl overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="grid lg:grid-cols-[0.9fr_1.1fr]">
        <div className="skeleton-sweep relative min-h-72 overflow-hidden bg-teal-50 p-8 dark:bg-teal-950/30">
          <div className="mx-auto aspect-square max-w-72 animate-pulse rounded-full bg-teal-100 dark:bg-teal-900" />
        </div>
        <div className="p-6 sm:p-8">
          <div className="h-4 w-28 animate-pulse rounded bg-slate-100 dark:bg-slate-800" />
          <div className="mt-4 h-8 w-2/3 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
          <div className="mt-6 space-y-3">
            <div className="h-4 w-full animate-pulse rounded bg-slate-100 dark:bg-slate-800" />
            <div className="h-4 w-5/6 animate-pulse rounded bg-slate-100 dark:bg-slate-800" />
          </div>
          <div className="mt-8 grid grid-cols-3 gap-4">
            {[0, 1, 2].map((key) => (
              <div key={key} className="h-16 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />
            ))}
          </div>
          <div className="mt-8 h-12 w-48 animate-pulse rounded-lg bg-teal-100 dark:bg-teal-900" />
        </div>
      </div>
    </div>
  );
}

interface TopicPreviewProps {
  topic: HealthTopicSummaryDTO;
  side: "previous" | "next";
}

function TopicPreview({ topic, side }: TopicPreviewProps) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "pointer-events-none absolute top-8 hidden h-[28rem] w-64 overflow-hidden rounded-2xl border border-slate-200 bg-white/80 p-5 opacity-35 xl:block dark:border-slate-800 dark:bg-slate-900/80",
        side === "previous" ? "-left-32" : "-right-32",
      )}
    >
      <HealthTopicArtwork slug={topic.slug} name={topic.name} compact decorative />
      <p className="mt-4 text-xl font-bold text-slate-800 dark:text-slate-100">{topic.name}</p>
      <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-500 dark:text-slate-400">
        {topic.summary}
      </p>
    </div>
  );
}

interface SpotlightTopicProps {
  topic: HealthTopicSummaryDTO;
  isAuthenticated: boolean;
  reducedMotion: boolean;
  onOpenDetail: (slug: string) => void;
  onArtworkOpenChange: (open: boolean) => void;
}

function SpotlightTopic({
  topic,
  isAuthenticated,
  reducedMotion,
  onOpenDetail,
  onArtworkOpenChange,
}: SpotlightTopicProps) {
  return (
    <motion.article
      id="active-health-topic"
      data-testid="active-health-topic"
      aria-labelledby={`health-topic-${topic.slug}`}
      initial={reducedMotion ? false : { opacity: 0, x: 18 }}
      animate={{ opacity: 1, x: 0 }}
      exit={reducedMotion ? undefined : { opacity: 0, x: -18 }}
      transition={{ duration: reducedMotion ? 0 : 0.55, ease: [0.16, 1, 0.3, 1] }}
      className="relative z-10 mx-auto max-w-5xl overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="grid lg:grid-cols-[0.9fr_1.1fr]">
        <div className="relative flex min-h-72 items-center justify-center overflow-hidden bg-teal-50 p-3 dark:bg-teal-950/30 sm:p-5 lg:min-h-[30rem]">
          <span className="absolute left-6 top-6 size-3 rounded-full bg-teal-500/70" aria-hidden="true" />
          <span className="absolute bottom-8 right-8 size-16 rounded-full border border-sky-200 dark:border-sky-900" aria-hidden="true" />
          <HealthTopicArtworkLightbox
            slug={topic.slug}
            name={topic.name}
            onOpenChange={onArtworkOpenChange}
            className="relative z-10 min-h-64 w-full lg:min-h-[28rem]"
          />
        </div>

        <div className="flex flex-col p-6 sm:p-8 lg:p-10">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm font-bold uppercase tracking-[0.12em] text-teal-700 dark:text-teal-300">
              Chủ đề đang xem
            </span>
            {topic.ai_assisted && (
              <span
                title="Phần tóm tắt đã được AI diễn giải sẵn một lần từ nội dung của nguồn y tế được trích dẫn"
                className="inline-flex items-center gap-2 rounded-full bg-sky-50 px-3 py-2 text-sm font-semibold text-sky-800 dark:bg-sky-950 dark:text-sky-200"
              >
                <Sparkles className="size-4" aria-hidden="true" />
                AI diễn giải
              </span>
            )}
          </div>

          <h3
            id={`health-topic-${topic.slug}`}
            className="mt-4 text-3xl font-bold tracking-tight text-slate-950 dark:text-white sm:text-4xl"
          >
            {topic.name}
          </h3>
          <p className="mt-4 text-base leading-7 text-slate-600 dark:text-slate-300">
            {topic.summary}
          </p>

          {topic.symptoms.length > 0 && (
            <div className="mt-8">
              <p className="text-sm font-bold uppercase tracking-[0.08em] text-slate-500 dark:text-slate-400">
                Dấu hiệu thường gặp
              </p>
              <ul className="mt-4 grid gap-4 sm:grid-cols-3">
                {topic.symptoms.slice(0, 3).map((symptom) => (
                  <li key={symptom} className="flex items-start gap-3 text-sm leading-6 text-slate-700 dark:text-slate-200">
                    <span className="mt-2 size-2 shrink-0 rounded-full bg-teal-500" aria-hidden="true" />
                    <span>{symptom}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="mt-8 flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-slate-100 pt-6 text-sm text-slate-500 dark:border-slate-800 dark:text-slate-400">
            <span className="font-semibold" title={topic.source}>Nguồn: {topic.source}</span>
            <span aria-hidden="true">·</span>
            <span>Cập nhật {formatUpdatedDate(topic.last_updated)}</span>
          </p>

          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
            <Link
              href={triageHrefForTopic(topic.slug, isAuthenticated)}
              className="group flex min-h-12 shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-lg bg-teal-600 px-5 text-base font-bold text-white transition-colors hover:bg-teal-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2"
            >
              <MessageSquare className="size-5 shrink-0" aria-hidden="true" />
              Kiểm tra triệu chứng
              <ArrowRight className="size-5 transition-transform group-hover:translate-x-1 motion-reduce:transition-none" aria-hidden="true" />
            </Link>
            <button
              type="button"
              onClick={() => onOpenDetail(topic.slug)}
              className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg px-4 text-base font-semibold text-slate-700 underline-offset-4 transition-colors hover:bg-slate-50 hover:text-teal-700 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 sm:whitespace-nowrap dark:text-slate-200 dark:hover:bg-slate-800 dark:hover:text-teal-300"
            >
              <BookOpen className="size-5" aria-hidden="true" />
              Xem hướng dẫn đầy đủ
            </button>
          </div>
        </div>
      </div>
    </motion.article>
  );
}

/**
 * Lớp giáo dục sức khỏe trên trang chủ. Chuyển động chỉ thay đổi cách trình bày
 * đúng danh sách backend trả về; không xếp hạng mức độ nguy hiểm hay tự suy diễn
 * nội dung lâm sàng.
 */
export function HealthTopicsSection() {
  const { data: topics, isLoading, isError } = useHealthTopics();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const reducedMotion = Boolean(useReducedMotion());
  const sectionRef = useRef<HTMLElement>(null);
  const selectorRailRef = useRef<HTMLDivElement>(null);
  const selectorTrackRef = useRef<HTMLDivElement>(null);
  const streamLayoutRef = useRef<StreamLayout | null>(null);
  const streamPhaseRef = useRef(0);
  const [openSlug, setOpenSlug] = useState<string | null>(null);
  const [artworkOpen, setArtworkOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [userPaused, setUserPaused] = useState(false);
  const [stageHovered, setStageHovered] = useState(false);
  const [railHovered, setRailHovered] = useState(false);
  const [focusWithin, setFocusWithin] = useState(false);
  const [pointerActive, setPointerActive] = useState(false);
  const [circularFlow, setCircularFlow] = useState(false);
  const [inView, setInView] = useState(() => typeof IntersectionObserver !== "function");
  const [documentVisible, setDocumentVisible] = useState(
    () => typeof document === "undefined" || document.visibilityState === "visible",
  );

  const count = topics?.length ?? 0;
  const safeIndex = count > 0 ? activeIndex % count : 0;
  const activeTopic = topics?.[safeIndex];
  const previousTopic = count > 1 ? topics?.[(safeIndex - 1 + count) % count] : undefined;
  const nextTopic = count > 1 ? topics?.[(safeIndex + 1) % count] : undefined;
  const commonPaused =
    userPaused || reducedMotion || !inView || !documentVisible || openSlug !== null || artworkOpen;
  const rotationPaused = commonPaused || stageHovered || focusWithin;
  const flowPaused = commonPaused || railHovered || focusWithin || pointerActive;

  const positionStreamItems = useCallback(() => {
    const layout = streamLayoutRef.current;
    if (!layout?.circular) return;

    layout.items.forEach((item, index) => {
      const x = circularItemX(
        layout.starts[index],
        layout.widths[index],
        streamPhaseRef.current,
        layout.loopLength,
      );
      item.style.transform = `translate3d(${x.toFixed(2)}px, 0, 0)`;
    });
  }, []);

  useEffect(() => {
    const element = sectionRef.current;
    if (!element || typeof IntersectionObserver !== "function") return;
    const observer = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), {
      threshold: 0.2,
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
    const rail = selectorRailRef.current;
    const track = selectorTrackRef.current;
    if (!rail || !track || count < 2) {
      streamLayoutRef.current = null;
      setCircularFlow(false);
      return;
    }

    let disposed = false;
    const measure = () => {
      if (disposed) return;

      const items = Array.from(
        track.querySelectorAll<HTMLButtonElement>("[data-flow-item='true']"),
      );
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

      streamLayoutRef.current = {
        items,
        starts,
        widths,
        loopLength: cursor,
        viewportWidth,
        circular,
      };
      rail.dataset.circular = circular ? "true" : "false";
      setCircularFlow(circular);

      if (circular) {
        streamPhaseRef.current = positiveModulo(streamPhaseRef.current, cursor);
        positionStreamItems();
      } else {
        streamPhaseRef.current = 0;
        items.forEach((item) => {
          item.style.removeProperty("transform");
        });
      }
    };

    measure();

    const resizeObserver = typeof ResizeObserver === "function"
      ? new ResizeObserver(measure)
      : null;
    resizeObserver?.observe(rail);
    if (!resizeObserver) window.addEventListener("resize", measure);

    void document.fonts?.ready.then(measure);

    return () => {
      disposed = true;
      resizeObserver?.disconnect();
      if (!resizeObserver) window.removeEventListener("resize", measure);
    };
  }, [count, positionStreamItems, reducedMotion]);

  const showNext = useCallback(() => {
    if (count < 2) return;
    setActiveIndex((current) => (current + 1) % count);
  }, [count]);

  const showPrevious = useCallback(() => {
    if (count < 2) return;
    setActiveIndex((current) => (current - 1 + count) % count);
  }, [count]);

  useEffect(() => {
    if (count < 2 || rotationPaused) return;
    const timer = window.setTimeout(showNext, ROTATION_MS);
    return () => window.clearTimeout(timer);
  }, [count, rotationPaused, safeIndex, showNext]);

  useEffect(() => {
    if (count < 2 || flowPaused || !circularFlow) return;

    let animationFrame = 0;
    let lastTimestamp: number | null = null;
    const flow = (timestamp: number) => {
      const elapsed = lastTimestamp === null
        ? 0
        : Math.min(timestamp - lastTimestamp, MAX_FRAME_DELTA_MS);
      lastTimestamp = timestamp;

      const layout = streamLayoutRef.current;
      if (layout?.circular) {
        streamPhaseRef.current = advanceCircularPhase(
          streamPhaseRef.current,
          elapsed,
          STREAM_SPEED_PX_PER_SECOND,
          layout.loopLength,
        );
        positionStreamItems();
      }

      animationFrame = window.requestAnimationFrame(flow);
    };

    animationFrame = window.requestAnimationFrame(flow);
    return () => window.cancelAnimationFrame(animationFrame);
  }, [circularFlow, count, flowPaused, positionStreamItems]);

  const centerFocusedStreamItem = useCallback((item: HTMLButtonElement) => {
    const layout = streamLayoutRef.current;
    if (!layout?.circular) return;

    const index = layout.items.indexOf(item);
    if (index < 0) return;

    const targetX = Math.max(0, (layout.viewportWidth - layout.widths[index]) / 2);
    streamPhaseRef.current = positiveModulo(
      layout.starts[index] - targetX,
      layout.loopLength,
    );
    positionStreamItems();
  }, [positionStreamItems]);

  const handleFocusCapture = (event: FocusEvent<HTMLDivElement>) => {
    setFocusWithin(true);
    const target = event.target as HTMLElement;
    const streamItem = target.closest<HTMLButtonElement>("[data-flow-item='true']");
    if (streamItem) centerFocusedStreamItem(streamItem);
  };
  const handleBlurCapture = (event: FocusEvent<HTMLDivElement>) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setFocusWithin(false);
  };

  return (
    <section
      ref={sectionRef}
      id="thong-tin-suc-khoe"
      aria-labelledby="health-topics-heading"
      className="relative w-full scroll-mt-20 overflow-hidden border-y border-slate-200 bg-slate-50 px-4 py-20 dark:border-slate-800 dark:bg-slate-950 sm:px-6 lg:px-8"
    >
      <div className="pointer-events-none absolute left-1/2 top-8 size-56 -translate-x-1/2 rounded-full bg-teal-100/60 blur-3xl dark:bg-teal-950/40" aria-hidden="true" />

      <div className="relative mx-auto max-w-7xl">
        <header className="mx-auto mb-10 max-w-3xl text-center">
          <p className="text-sm font-bold uppercase tracking-[0.14em] text-teal-700 dark:text-teal-300">
            Góc thông tin sức khỏe
          </p>
          <h2
            id="health-topics-heading"
            className="mt-3 font-heading text-3xl font-extrabold tracking-tight text-slate-950 dark:text-white sm:text-4xl lg:text-5xl"
          >
            Thông tin sức khỏe đáng chú ý
          </h2>
          <p className="mt-4 text-base font-medium leading-7 text-slate-600 dark:text-slate-300 sm:text-lg">
            Cập nhật các vấn đề sức khỏe đang được quan tâm và cách phòng ngừa.
          </p>
        </header>

        {isLoading ? (
          <SpotlightSkeleton />
        ) : isError ? (
          <div role="status" className="mx-auto flex max-w-3xl items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 p-6 text-sm font-medium text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
            <AlertCircle className="size-5 shrink-0" aria-hidden="true" />
            Không thể tải thông tin sức khỏe lúc này.
          </div>
        ) : !topics || !activeTopic ? (
          <div role="status" className="mx-auto flex max-w-3xl items-center gap-3 rounded-xl border border-slate-200 bg-white p-6 text-sm font-medium text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
            <BookOpen className="size-5 shrink-0" aria-hidden="true" />
            Hiện chưa có thông tin sức khỏe đáng chú ý.
          </div>
        ) : (
          <div
            onMouseEnter={() => setStageHovered(true)}
            onMouseLeave={() => setStageHovered(false)}
            onFocusCapture={handleFocusCapture}
            onBlurCapture={handleBlurCapture}
          >
            <div className="relative mx-auto max-w-6xl px-0 xl:px-20">
              {previousTopic && <TopicPreview topic={previousTopic} side="previous" />}
              {nextTopic && <TopicPreview topic={nextTopic} side="next" />}

              <AnimatePresence mode="wait" initial={false}>
                <SpotlightTopic
                  key={activeTopic.slug}
                  topic={activeTopic}
                  isAuthenticated={isAuthenticated}
                  reducedMotion={reducedMotion}
                  onOpenDetail={setOpenSlug}
                  onArtworkOpenChange={setArtworkOpen}
                />
              </AnimatePresence>

              {count > 1 && (
                <>
                  <button
                    type="button"
                    onClick={showPrevious}
                    aria-label="Xem chủ đề trước"
                    className="absolute left-2 top-72 z-20 flex size-12 -translate-y-1/2 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 shadow-[0_8px_24px_-16px_rgba(15,23,42,0.5)] transition-colors hover:border-teal-300 hover:text-teal-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 sm:top-1/2 xl:left-14"
                  >
                    <ArrowLeft className="size-5" aria-hidden="true" />
                  </button>
                  <button
                    type="button"
                    onClick={showNext}
                    aria-label="Xem chủ đề tiếp theo"
                    className="absolute right-2 top-72 z-20 flex size-12 -translate-y-1/2 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-700 shadow-[0_8px_24px_-16px_rgba(15,23,42,0.5)] transition-colors hover:border-teal-300 hover:text-teal-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 sm:top-1/2 xl:right-14"
                  >
                    <ArrowRight className="size-5" aria-hidden="true" />
                  </button>
                </>
              )}
            </div>

            {count > 1 && (
              <div className="mx-auto mt-6 max-w-5xl">
                <div
                  ref={selectorRailRef}
                  role="group"
                  aria-label="Dòng chủ đề sức khỏe tự trôi"
                  data-testid="health-topic-stream"
                  data-flow-state={flowPaused ? "paused" : "running"}
                  data-circular={circularFlow ? "true" : "false"}
                  onMouseEnter={() => setRailHovered(true)}
                  onMouseLeave={() => setRailHovered(false)}
                  onPointerDown={() => setPointerActive(true)}
                  onPointerUp={() => setPointerActive(false)}
                  onPointerLeave={() => setPointerActive(false)}
                  onPointerCancel={() => setPointerActive(false)}
                  className="health-topic-stream flow-rail overflow-x-auto pb-2"
                >
                  <div
                    ref={selectorTrackRef}
                    className={cn(
                      "health-topic-stream-track",
                      circularFlow
                        ? "relative h-12 w-full"
                        : "flex w-max min-w-full gap-2",
                    )}
                  >
                    {topics.map((topic, index) => {
                      const Icon = topicIcon(topic);
                      const selected = index === safeIndex;
                      return (
                        <button
                          key={topic.slug}
                          type="button"
                          aria-pressed={selected}
                          aria-controls="active-health-topic"
                          data-topic-index={index}
                          data-flow-item="true"
                          onClick={() => setActiveIndex(index)}
                          className={cn(
                            "flex min-h-12 shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-lg border px-4 text-sm font-semibold transition-colors",
                            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-2",
                            circularFlow && "absolute left-0 top-0 will-change-transform",
                            selected
                              ? "border-teal-500 bg-teal-50 text-teal-900 dark:border-teal-500 dark:bg-teal-950 dark:text-teal-100"
                              : "border-slate-200 bg-white text-slate-600 hover:border-teal-200 hover:text-teal-800 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:text-teal-300",
                          )}
                        >
                          <Icon className="size-5" aria-hidden="true" />
                          {topic.name}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-center gap-3">
                  <div
                    role="progressbar"
                    aria-label="Thời gian tới chủ đề tiếp theo"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuetext={rotationPaused ? "Đã tạm dừng" : "Đang tự chuyển"}
                    className="h-1.5 w-48 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
                  >
                    {rotationPaused ? (
                      <span className="block h-full w-1/3 rounded-full bg-teal-500" />
                    ) : (
                      <span key={activeTopic.slug} className="health-topic-progress block h-full rounded-full bg-teal-500" />
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => setUserPaused((current) => !current)}
                    aria-pressed={userPaused}
                    aria-label={userPaused ? "Tiếp tục tự chuyển chủ đề" : "Tạm dừng tự chuyển chủ đề"}
                    className="flex size-11 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 transition-colors hover:border-teal-300 hover:text-teal-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
                  >
                    {userPaused ? <Play className="size-5" aria-hidden="true" /> : <Pause className="size-5" aria-hidden="true" />}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        <p className="mx-auto mt-10 flex max-w-3xl items-start gap-3 rounded-xl border border-slate-200 bg-white p-4 text-sm leading-6 text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
          <ShieldCheck className="mt-0.5 size-5 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
          <span>
            Đây là thông tin sức khỏe mang tính tham khảo, không thay thế cho thăm khám và đánh giá trực tiếp của nhân viên y tế. Nếu bạn đang có triệu chứng, hãy dùng phần khám sàng lọc để được hướng dẫn phù hợp.
          </span>
        </p>
      </div>

      <HealthTopicDetailDialog
        slug={openSlug}
        isAuthenticated={isAuthenticated}
        onClose={() => setOpenSlug(null)}
      />
    </section>
  );
}

export default HealthTopicsSection;
