import { notFound } from "next/navigation";

import { ConceptUnit } from "@/components/concept-unit";
import { fetchConcept } from "@/lib/concepts-server";

type Params = Promise<{ slug: string }>;

export default async function ConceptDetailPage({
  params,
}: {
  params: Params;
}) {
  const { slug } = await params;
  try {
    const concept = await fetchConcept(slug);
    return (
      <div className="mx-auto max-w-3xl py-6">
        <ConceptUnit concept={concept} />
      </div>
    );
  } catch {
    notFound();
  }
}
