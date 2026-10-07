"use client";

import * as React from "react";
import * as SliderPrimitive from "@radix-ui/react-slider";
import { cn } from "@/lib/utils";

interface SliderProps
  extends React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root> {
  trackClassName?: string;
  rangeClassName?: string;
  thumbClassName?: string;
}

const Slider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  SliderProps
>(({ className, trackClassName, rangeClassName, thumbClassName, ...props }, ref) => (
  <SliderPrimitive.Root
    ref={ref}
    className={cn(
      "relative flex w-full touch-none select-none items-center py-2 cursor-pointer",
      className
    )}
    {...props}
  >
    <SliderPrimitive.Track
      className={cn(
        "relative h-3 w-full grow overflow-hidden rounded-full bg-zinc-800 border border-zinc-700/80",
        trackClassName
      )}
    >
      <SliderPrimitive.Range
        className={cn("absolute h-full bg-gradient-to-r from-emerald-500 via-amber-500 to-rose-500", rangeClassName)}
      />
    </SliderPrimitive.Track>
    <SliderPrimitive.Thumb
      className={cn(
        "block h-6 w-6 rounded-full border-2 border-white bg-zinc-950 shadow-[0_0_15px_rgba(0,0,0,0.8)] transition-transform duration-150 hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950 disabled:pointer-events-none disabled:opacity-50",
        thumbClassName
      )}
    />
  </SliderPrimitive.Root>
));
Slider.displayName = SliderPrimitive.Root.displayName;

export { Slider };
