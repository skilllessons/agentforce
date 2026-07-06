import type { ReactNode } from 'react'
import './globals.css'

export const metadata = {
  title: 'AgentForge Studio',
  description: 'Launch domain-specific deep research agents',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#0d0d0d] text-slate-100">
        <header className="border-b border-white/10 bg-[#171717] px-6 py-4">
          <div className="mx-auto flex max-w-7xl items-center justify-between">
            <h1 className="text-xl font-semibold text-white">
              Agent<span className="text-forge-500">Forge</span>
            </h1>
            <nav className="text-sm">
              <a className="text-slate-400 hover:text-white" href="/">Studio</a>
            </nav>
          </div>
        </header>
        <main className="h-[calc(100vh-65px)] overflow-hidden">{children}</main>
      </body>
    </html>
  )
}
