import type { CSSProperties, ReactNode } from "react";

import { cn } from "@/lib/utils";

/** Tiêu đề lớn của mỗi màn xác thực kèm đúng một dòng giải thích. */
export function AuthHeading({
  title,
  description,
  align = "start",
  className,
  style,
}: {
  title: string;
  description?: ReactNode;
  align?: "start" | "center";
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <header
      className={cn("flex flex-col gap-2", align === "center" && "items-center text-center", className)}
      style={style}
    >
      <h1 className="text-3xl font-extrabold leading-tight tracking-tight text-balance text-foreground">
        {title}
      </h1>
      {description ? (
        <p className="text-base leading-relaxed text-pretty text-muted-foreground">{description}</p>
      ) : null}
    </header>
  );
}
