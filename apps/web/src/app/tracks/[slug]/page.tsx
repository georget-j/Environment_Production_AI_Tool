type Params = Promise<{ slug: string }>;

export default async function TrackDetailPage({ params }: { params: Params }) {
  const { slug } = await params;
  return (
    <div className="space-y-4 py-8">
      <h1 className="text-3xl font-semibold capitalize">{slug.replace(/-/g, " ")}</h1>
      <p className="text-muted-foreground">
        Challenge list will be wired to the API in commit 5.
      </p>
    </div>
  );
}
