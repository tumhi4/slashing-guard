import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'SlashingGuard | Autonomous Ethereum PoS Validator Slashing Insurance',
  description: 'Parametric validator slashing insurance protocol powered by GenLayer AI Consensus and Ethereum Beacon Chain telemetry.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen antialiased selection:bg-indigo-500 selection:text-white">
        {children}
      </body>
    </html>
  )
}
