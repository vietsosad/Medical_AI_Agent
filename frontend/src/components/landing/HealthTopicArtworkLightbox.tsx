"use client";

import { useRef } from "react";
import { Maximize2, X } from "lucide-react";

import { HealthTopicArtwork } from "@/components/landing/HealthTopicArtwork";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

interface HealthTopicArtworkLightboxProps {
  slug: string;
  name: string;
  className?: string;
  onOpenChange?: (open: boolean) => void;
}

export function HealthTopicArtworkLightbox({
  slug,
  name,
  className,
  onOpenChange,
}: HealthTopicArtworkLightboxProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  return (
    <Dialog onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <button
          type="button"
          aria-label={`Phóng to minh họa ${name}`}
          className={cn(
            "group relative flex h-full w-full cursor-zoom-in items-center justify-center rounded-xl",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 focus-visible:ring-offset-4 focus-visible:ring-offset-teal-50",
            "dark:focus-visible:ring-teal-300 dark:focus-visible:ring-offset-teal-950",
            className,
          )}
        >
          <HealthTopicArtwork
            slug={slug}
            name={name}
            decorative
            className="relative z-10 max-w-md transition-transform duration-500 ease-out group-hover:scale-[1.025] motion-reduce:transition-none motion-reduce:group-hover:scale-100"
          />
          <span className="absolute bottom-3 right-3 z-20 inline-flex min-h-10 items-center gap-2 rounded-lg border border-white/80 bg-white/95 px-3 text-sm font-bold text-slate-800 shadow-sm transition-colors group-hover:border-teal-200 group-hover:text-teal-800 dark:border-slate-700 dark:bg-slate-900/95 dark:text-slate-100 dark:group-hover:border-teal-700 dark:group-hover:text-teal-200">
            <Maximize2 className="size-4" aria-hidden="true" />
            Phóng to
          </span>
        </button>
      </DialogTrigger>

      <DialogContent
        hideCloseButton
        overlayClassName="bg-slate-950/90 backdrop-blur-sm motion-reduce:animate-none"
        onOpenAutoFocus={(event) => {
          event.preventDefault();
          closeButtonRef.current?.focus();
        }}
        className="!inset-0 !left-0 !top-0 !flex !h-dvh !w-screen !max-w-none !translate-x-0 !translate-y-0 flex-col gap-0 overflow-hidden !rounded-none border-0 bg-slate-950 p-0 text-white shadow-none motion-reduce:animate-none"
      >
        <DialogHeader className="flex-row items-center justify-between space-y-0 border-b border-white/10 px-4 py-3 text-left sm:px-6">
          <div className="min-w-0 pr-4">
            <DialogTitle className="truncate text-lg font-bold text-white sm:text-xl">
              Minh họa y khoa: {name}
            </DialogTitle>
            <DialogDescription className="mt-1 text-sm text-slate-300">
              Ảnh minh họa giúp nhận biết chủ đề, không dùng để tự chẩn đoán.
            </DialogDescription>
          </div>
          <DialogClose asChild>
            <button
              ref={closeButtonRef}
              type="button"
              aria-label="Đóng ảnh phóng to"
              className="flex size-12 shrink-0 items-center justify-center rounded-xl border border-white/20 bg-white/10 text-white transition-colors hover:bg-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-300 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950"
            >
              <X className="size-6" aria-hidden="true" />
            </button>
          </DialogClose>
        </DialogHeader>

        <div className="flex min-h-0 flex-1 items-center justify-center overflow-auto p-4 sm:p-8">
          <div className="flex w-full max-w-6xl items-center justify-center rounded-2xl border border-white/10 bg-slate-50 p-3 sm:p-8 dark:bg-slate-900">
            <HealthTopicArtwork
              slug={slug}
              name={name}
              className="mx-auto h-auto max-h-[calc(100dvh-11rem)] w-full max-w-6xl"
            />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
