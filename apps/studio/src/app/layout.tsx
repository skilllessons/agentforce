import type { ReactNode } from 'react'
import { Inter, Source_Serif_4 } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const serif = Source_Serif_4({ subsets: ['latin'], variable: '--font-serif' })

export const metadata = {
  title: 'AgentForge Studio',
  description: 'Launch domain-specific deep research agents',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${serif.variable}`}>
      <body className="min-h-screen font-sans antialiased">
        <header className="flex h-14 items-center border-b border-border bg-card/60 px-5 backdrop-blur">
          <div className="mx-auto flex w-full max-w-7xl items-center justify-between">
            <h1 className="font-serif text-lg font-semibold tracking-tight">
              Agent<span className="text-primary">Forge</span>
            </h1>
            <nav className="text-sm text-muted-foreground">
              <a className="transition-colors hover:text-foreground" href="/">
                Studio
              </a>
            </nav>
          </div>
        </header>
        <main className="h-[calc(100vh-3.5rem)] overflow-hidden">{children}</main>
      </body>
    </html>
  )
}
