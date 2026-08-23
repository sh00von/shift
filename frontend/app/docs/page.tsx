import { notFound } from "next/navigation";
import { DocArticle } from "@/components/docs/DocArticle";
import { readDoc } from "@/lib/docs";

export default function DocsIndexPage() {
  const md = readDoc("");
  if (md === null) notFound();
  return <DocArticle slug="" markdown={md} />;
}
