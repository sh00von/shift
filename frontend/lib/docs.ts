// Server-side helpers for reading documentation markdown from content/docs.
// Used only in Server Components (imports node:fs).
import fs from "node:fs";
import path from "node:path";
import { DOCS_FLAT, DocPage } from "./docs.config";
export { docHref } from "./docs-href";

const DOCS_DIR = path.join(process.cwd(), "content", "docs");

/** Map a slug ("" -> index, "methods/robust" -> methods/robust.md) to a file. */
function slugToFile(slug: string): string {
  const rel = slug === "" ? "index" : slug;
  return path.join(DOCS_DIR, `${rel}.md`);
}

/** Read raw markdown for a slug, or null if the file does not exist. */
export function readDoc(slug: string): string | null {
  const file = slugToFile(slug);
  try {
    return fs.readFileSync(file, "utf8");
  } catch {
    return null;
  }
}

/** The page metadata (title) for a slug, if it is in the manifest. */
export function findPage(slug: string): DocPage | undefined {
  return DOCS_FLAT.find((p) => p.slug === slug);
}

/** Previous / next page in reading order, for footer navigation. */
export function neighbours(slug: string): { prev?: DocPage; next?: DocPage } {
  const i = DOCS_FLAT.findIndex((p) => p.slug === slug);
  if (i === -1) return {};
  return {
    prev: i > 0 ? DOCS_FLAT[i - 1] : undefined,
    next: i < DOCS_FLAT.length - 1 ? DOCS_FLAT[i + 1] : undefined,
  };
}

/** All non-empty slugs, split into path segments for the [...slug] route. */
export function allDocParams(): { slug: string[] }[] {
  return DOCS_FLAT.filter((p) => p.slug !== "").map((p) => ({
    slug: p.slug.split("/"),
  }));
}
