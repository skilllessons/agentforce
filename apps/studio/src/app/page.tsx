import Link from 'next/link'
import { listVerticals } from '@/lib/api-client'

export default async function HomePage() {
  const { verticals } = await listVerticals()
  return (
    <div>
      <section className="mb-10">
        <h2 className="text-2xl font-semibold">Pick a vertical</h2>
        <p className="mt-1 text-slate-600">
          Each vertical exposes a REST endpoint, SSE stream, and webhook delivery.
        </p>
      </section>
      <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {verticals.map((v) => (
          <li key={v.id}>
            <Link
              href={`/agents/${v.id}`}
              className="block rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-forge-500 hover:shadow-md"
            >
              <div className="text-lg font-semibold capitalize">{v.id}</div>
              <div className="mt-2 text-xs text-slate-500">
                {v.tools.length} tools · {v.avgRunSeconds ? `~${v.avgRunSeconds}s` : 'avg run pending'}
              </div>
              <div className="mt-3 flex flex-wrap gap-1">
                {v.tools.map((t) => (
                  <span key={t} className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-700">
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
