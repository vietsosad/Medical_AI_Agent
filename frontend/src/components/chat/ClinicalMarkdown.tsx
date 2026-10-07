import ReactMarkdown, { type Components, type UrlTransform } from "react-markdown";

import { cn } from "@/lib/utils";

interface ClinicalMarkdownProps {
  content: string;
  className?: string;
}

const safeUrlTransform: UrlTransform = (url, key) => {
  if (key !== "href") return null;
  const normalized = url.trim();
  return /^(https?:\/\/|tel:)/i.test(normalized) ? normalized : null;
};

const components: Components = {
  p: ({ children }) => <p>{children}</p>,
  strong: ({ children }) => <strong className="font-bold">{children}</strong>,
  em: ({ children }) => <em>{children}</em>,
  h1: ({ children }) => (
    <h3 className="text-lg font-bold leading-7 text-slate-950 dark:text-white">{children}</h3>
  ),
  h2: ({ children }) => (
    <h3 className="text-lg font-bold leading-7 text-slate-950 dark:text-white">{children}</h3>
  ),
  h3: ({ children }) => (
    <h3 className="text-lg font-bold leading-7 text-slate-950 dark:text-white">{children}</h3>
  ),
  h4: ({ children }) => <h4 className="font-bold text-slate-950 dark:text-white">{children}</h4>,
  h5: ({ children }) => <h5 className="font-bold text-slate-950 dark:text-white">{children}</h5>,
  h6: ({ children }) => <h6 className="font-bold text-slate-950 dark:text-white">{children}</h6>,
  ul: ({ children }) => (
    <ul className="list-disc space-y-2 pl-6 marker:text-slate-500">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal space-y-2 pl-6 marker:font-semibold marker:text-slate-600 dark:marker:text-slate-300">
      {children}
    </ol>
  ),
  li: ({ children }) => <li>{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-slate-300 pl-4 text-slate-700 dark:border-slate-700 dark:text-slate-300">
      {children}
    </blockquote>
  ),
  pre: ({ children }) => (
    <pre className="overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100 [&>code]:bg-transparent [&>code]:p-0">
      {children}
    </pre>
  ),
  code: ({ children, className }) => (
    <code
      className={cn(
        "rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[0.9em] text-slate-900 dark:bg-slate-800 dark:text-slate-100",
        className,
      )}
    >
      {children}
    </code>
  ),
  a: ({ children, href }) => {
    if (!href) return <span>{children}</span>;
    const isExternal = /^https?:\/\//i.test(href);
    return (
      <a
        href={href}
        target={isExternal ? "_blank" : undefined}
        rel={isExternal ? "noreferrer noopener" : undefined}
        className="font-semibold text-sky-700 underline decoration-sky-300 underline-offset-4 hover:text-sky-900 focus-visible:rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600 dark:text-sky-300 dark:hover:text-sky-100"
      >
        {children}
      </a>
    );
  },
};

/** Raw HTML and unsafe URL schemes are deliberately disabled for clinical output. */
export function ClinicalMarkdown({ content, className }: ClinicalMarkdownProps) {
  return (
    <div className={cn("space-y-3 break-words", className)}>
      <ReactMarkdown
        skipHtml
        allowedElements={[
          "p",
          "strong",
          "em",
          "h1",
          "h2",
          "h3",
          "h4",
          "h5",
          "h6",
          "ul",
          "ol",
          "li",
          "blockquote",
          "pre",
          "code",
          "a",
          "br",
          "hr",
        ]}
        components={components}
        urlTransform={safeUrlTransform}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
