import Link from "next/link";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { Markdown } from "./Markdown";
import { neighbours, findPage, docHref } from "@/lib/docs";

/** Renders one documentation page: eyebrow, markdown body, and prev/next footer. */
export function DocArticle({ slug, markdown }: { slug: string; markdown: string }) {
  const { prev, next } = neighbours(slug);
  const page = findPage(slug);

  const isOverview = slug === "";

  return (
    <article>
      {isOverview ? (
        <div className="mb-6 flex items-center gap-3">
          <img
            src="/logo.png"
            alt="SHIFT"
            className="h-14 w-14 rounded-xl object-cover shadow-sm"
          />
          <div className="leading-tight">
            <div className="text-lg font-bold tracking-tight text-slate-900">SHIFT</div>
            <div className="text-xs text-slate-500">
              Shoreline Intelligence, Forecasting &amp; Trends
            </div>
          </div>
        </div>
      ) : (
        page && <p className="gb-section-title mb-3">Documentation</p>
      )}
      <Markdown>{markdown}</Markdown>

      <nav className="mt-14 grid grid-cols-1 gap-3 border-t border-slate-200 pt-6 sm:grid-cols-2">
        {prev ? (
          <Link
            href={docHref(prev.slug)}
            className="group flex flex-col rounded-xl border border-slate-200 px-4 py-3 transition-colors hover:border-slate-900"
          >
            <span className="flex items-center gap-1 text-[11px] font-medium text-slate-400">
              <ArrowLeft className="h-3 w-3" /> Previous
            </span>
            <span className="mt-0.5 text-sm font-semibold text-slate-700 group-hover:text-slate-950">
              {prev.title}
            </span>
          </Link>
        ) : (
          <span className="hidden sm:block" />
        )}
        {next ? (
          <Link
            href={docHref(next.slug)}
            className="group flex flex-col items-end rounded-xl border border-slate-200 px-4 py-3 text-right transition-colors hover:border-slate-900 sm:col-start-2"
          >
            <span className="flex items-center gap-1 text-[11px] font-medium text-slate-400">
              Next <ArrowRight className="h-3 w-3" />
            </span>
            <span className="mt-0.5 text-sm font-semibold text-slate-700 group-hover:text-slate-950">
              {next.title}
            </span>
          </Link>
        ) : null}
      </nav>
    </article>
  );
}
