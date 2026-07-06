import Link from 'next/link'
import { listVerticals } from '@/lib/api-client'

export default async function HomePage() {
  const { verticals } = await listVerticals()
  return (
    <div className="mx-auto h-full max-w-7xl overflow-y-auto px-6 py-8">
      <section className="mb-10">
        <h2 className="text-2xl font-semibold text-slate-100">Pick a vertical</h2>
        <p className="mt-1 text-slate-400">
          Each vertical exposes a REST endpoint, live status, and webhook delivery.
        </p>
      </section>
      <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {verticals.map((v) => (
          <li key={v.id}>
            <Link
              href={`/agents/${v.id}`}
              className="block rounded-xl border border-white/10 bg-[#171717] p-5 transition hover:border-forge-500 hover:bg-[#1c1c1c]"
            >
              <div className="text-lg font-semibold capitalize text-slate-100">{v.id}</div>
              <div className="mt-2 text-xs text-slate-500">
                {v.tools.length} tools · {v.avgRunSeconds ? `~${v.avgRunSeconds}s` : 'avg run pending'}
              </div>
              <div className="mt-3 flex flex-wrap gap-1">
                {v.tools.map((t) => (
                  <span key={t} className="rounded-md bg-white/5 px-2 py-1 text-xs text-slate-400">
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
