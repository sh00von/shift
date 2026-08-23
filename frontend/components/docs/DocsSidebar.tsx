"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { DOCS_NAV } from "@/lib/docs.config";
import { docHref } from "@/lib/docs-href";
import { cn } from "@/lib/utils";

export function DocsSidebar() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col gap-7 px-4 py-6 text-sm">
      {DOCS_NAV.map((section) => (
        <div key={section.title} className="space-y-1.5">
          <div className="gb-section-title px-2.5 pb-1">{section.title}</div>
          <ul className="space-y-0.5">
            {section.pages.map((page) => {
              const href = docHref(page.slug);
              const active = pathname === href;
              return (
                <li key={href}>
                  <Link
                    href={href}
                    className={cn(
                      "relative block rounded-md py-1.5 pr-2 pl-3 leading-snug transition-colors",
                      active
                        ? "bg-accent font-semibold text-foreground"
                        : "text-slate-500 hover:bg-muted hover:text-slate-900"
                    )}
                  >
                    {active && (
                      <span className="absolute top-1/2 left-0 h-4 w-0.5 -translate-y-1/2 rounded-full bg-primary" />
                    )}
                    {page.title}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
