import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { DocArticle } from "@/components/docs/DocArticle";
import { readDoc, findPage, allDocParams } from "@/lib/docs";

export function generateStaticParams() {
  return allDocParams();
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string[] }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const page = findPage(slug.join("/"));
  return { title: page ? `${page.title} — SHIFT Docs` : "SHIFT Docs" };
}

export default async function DocPage({
  params,
}: {
  params: Promise<{ slug: string[] }>;
}) {
  const { slug } = await params;
  const joined = slug.join("/");
  const md = readDoc(joined);
  if (md === null) notFound();
  return <DocArticle slug={joined} markdown={md} />;
}
