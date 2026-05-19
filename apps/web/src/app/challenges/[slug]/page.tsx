type Params = Promise<{ slug: string }>;

export default async function ChallengeDetailPage({ params }: { params: Params }) {
  const { slug } = await params;
  return (
    <div className="space-y-4 py-8">
      <h1 className="text-3xl font-semibold capitalize">{slug.replace(/-/g, " ")}</h1>
      <p className="text-muted-foreground">
        Scenario, instructions, mentor chat, and submission form arrive in commits 5–8.
      </p>
    </div>
  );
}
