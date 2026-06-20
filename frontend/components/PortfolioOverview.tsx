'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

export default function PortfolioOverview() {
  const [portfolio, setPortfolio] = useState<any>({})

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api('/api/portfolio')
        setPortfolio(data || {})
      } catch (e) {
        console.error('Failed to load portfolio:', e)
      }
    }
    load()
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [])

  const stats = [
    { label: 'Balance', value: `$${(portfolio.equity || 0).toLocaleString()}`, color: 'text-green-400' },
    { label: 'Drawdown', value: `${(portfolio.drawdown || 0).toFixed(2)}%`, color: (portfolio.drawdown || 0) > 10 ? 'text-red-400' : (portfolio.drawdown || 0) > 5 ? 'text-yellow-400' : 'text-green-400' },
    { label: 'Open', value: `${portfolio.open_positions || 0}`, color: '' },
    { label: 'Daily P&L', value: `$${(portfolio.daily_pnl || 0).toFixed(2)}`, color: (portfolio.daily_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400' },
    { label: 'Win Rate', value: portfolio.total_trades && portfolio.winning_trades != null ? `${((portfolio.winning_trades / portfolio.total_trades) * 100).toFixed(1)}%` : '0%', color: '' },
    { label: 'Trades', value: `${portfolio.total_trades || 0}`, color: '' },
  ]

  return (
    <div className="grid grid-cols-6 gap-3">
      {stats.map(s => (
        <div key={s.label} className="card text-center py-3">
          <div className="text-dark-400 text-xs uppercase tracking-wider">{s.label}</div>
          <div className={`text-lg font-bold ${s.color}`}>{s.value}</div>
        </div>
      ))}
    </div>
  )
}
