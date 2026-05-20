import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="space-y-16 py-12">
      <section className="space-y-6 text-center">
        <h1 className="mx-auto max-w-3xl text-balance text-5xl font-semibold tracking-tight">
          The missing bridge between coding tutorials and your first production engineering job.
        </h1>
        <p className="mx-auto max-w-2xl text-lg text-muted-foreground">
          Edit realistic broken Python services in your browser, get guided by an AI senior
          engineer, watch the tests turn green, and graduate with portfolio-ready proof of work.
        </p>
        <div className="flex items-center justify-center gap-3">
          <Link href="/login">
            <Button size="lg">Start the Backend Production track</Button>
          </Link>
          <Link href="/tracks">
            <Button size="lg" variant="outline">
              See the curriculum
            </Button>
          </Link>
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-3">
        <Feature title="Realistic production code">
          Broken FastAPI services, real pytest suites, in-browser execution. Not toy exercises.
        </Feature>
        <Feature title="AI senior engineer">
          Socratic mentoring, structured code reviews, and error explanations. The AI guides; tests
          decide pass/fail.
        </Feature>
        <Feature title="Portfolio proof">
          Every challenge ends with a green test suite and an AI code review you can show to a
          hiring manager.
        </Feature>
      </section>
    </div>
  );
}

function Feature({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border p-6">
      <h3 className="mb-2 font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground">{children}</p>
    </div>
  );
}
