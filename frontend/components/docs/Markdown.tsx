import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSlug from "rehype-slug";
import rehypeAutolinkHeadings from "rehype-autolink-headings";

/**
 * Renders a markdown string with the SHIFT docs typography.
 * GFM tables/strikethrough via remark-gfm; heading anchors via rehype-slug +
 * rehype-autolink-headings. Styling is scoped through the `shift-doc` class
 * (see the CSS in DocsLayout / globals) rather than @tailwindcss/typography so
 * we avoid another dependency.
 */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="shift-doc">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[
          rehypeSlug,
          [rehypeAutolinkHeadings, { behavior: "wrap" }],
        ]}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
