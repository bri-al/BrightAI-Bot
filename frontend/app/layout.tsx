import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AI Trading Platform',
  description: 'Automated AI Trading System',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
