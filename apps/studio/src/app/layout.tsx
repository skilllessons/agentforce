import type { ReactNode } from 'react'
import './globals.css'

export const metadata = {
  title: 'AgentForge Studio',
  description: 'Launch domain-specific deep research agents',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-forge-50 text-slate-900">
        <header className="border-b border-slate-200 bg-white px-6 py-4">
          <div className="mx-auto flex max-w-7xl items-center justify-between">
            <h1 className="text-xl font-semibold text-forge-500">AgentForge</h1>
            <nav className="text-sm">
              <a className="text-slate-600 hover:text-forge-500" href="/">Studio</a>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
      </body>
    </html>
  )
}
