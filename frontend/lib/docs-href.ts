// Pure helper safe to import from Client Components (no node:fs).

/** The href for a doc slug ("" -> /docs, "methods/robust" -> /docs/methods/robust). */
export function docHref(slug: string): string {
  return slug === "" ? "/docs" : `/docs/${slug}`;
}
