import Link from "next/link";

export default function TracksPage() {
  return (
    <div className="space-y-6 py-8">
      <h1 className="text-3xl font-semibold">Tracks</h1>
      <p className="text-muted-foreground">One track for the MVP. More coming after validation.</p>
      <div className="grid gap-4">
        <Link
          href="/tracks/backend-production-python"
          className="rounded-lg border border-border p-6 hover:bg-muted"
        >
          <h2 className="font-semibold">Backend Production Developer</h2>
          <p className="text-sm text-muted-foreground">
            Python · FastAPI · PostgreSQL · Docker · pytest · Git · GitHub Actions
          </p>
        </Link>
      </div>
    </div>
  );
}
