import Link from 'next/link'
import { listVerticals } from '@/lib/api-client'

export default async function HomePage() {
  const { verticals } = await listVerticals()
  return (
    <div className="mx-auto h-full max-w-7xl overflow-y-auto px-6 py-8">
      <section className="mb-10">
        <h2 className="font-serif text-3xl font-medium tracking-tight">Pick a vertical</h2>
        <p className="mt-1 text-muted-foreground">
          Each vertical exposes a REST endpoint, live status, and webhook delivery.
        </p>
      </section>
      <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {verticals.map((v) => (
          <li key={v.id}>
            <Link
              href={`/agents/${v.id}`}
              className="block rounded-xl border border-border bg-card p-5 transition-colors hover:border-primary hover:bg-accent"
            >
              <div className="text-lg font-semibold capitalize">{v.id}</div>
              <div className="mt-2 text-xs text-muted-foreground">
                {v.tools.length} tools · {v.avgRunSeconds ? `~${v.avgRunSeconds}s` : 'avg run pending'}
              </div>
              <div className="mt-3 flex flex-wrap gap-1">
                {v.tools.map((t) => (
                  <span key={t} className="rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground">
                    {t}
                  </span>
                ))}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
