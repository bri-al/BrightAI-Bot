'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'AAPL', 'MSFT', 'GOOGL']
const ASSET_CLASS: Record<string, string> = {
  BTCUSDT: 'Crypto', ETHUSDT: 'Crypto', SOLUSDT: 'Crypto',
  EURUSD: 'Forex', GBPUSD: 'Forex', USDJPY: 'Forex', XAUUSD: 'Forex',
  AAPL: 'Stocks', MSFT: 'Stocks', GOOGL: 'Stocks',
}

export default function Watchlist({ selected, onSelect }: { selected: string; onSelect: (s: string) => void }) {
  const [prices, setPrices] = useState<Record<string, number>>({})

  useEffect(() => {
    const load = async () => {
      const results = await Promise.allSettled(
        SYMBOLS.map(sym => api(`/api/analysis/${sym}`))
      )
      const entries: Record<string, number> = {}
      results.forEach((r, i) => {
        if (r.status === 'fulfilled' && r.value?.current_price) {
          entries[SYMBOLS[i]] = r.value.current_price
        }
      })
      setPrices(entries)
    }
    load()
    const interval = setInterval(load, 15000)
    return () => clearInterval(interval)
  }, [])

  const grouped: Record<string, string[]> = { Crypto: [], Forex: [], Stocks: [] }
  SYMBOLS.forEach(s => {
    const cls = ASSET_CLASS[s]
    if (grouped[cls]) grouped[cls].push(s)
  })

  return (
    <div className="card h-full flex flex-col">
      <div className="card-header">Watchlist</div>
      <div className="flex-1 overflow-y-auto space-y-3">
        {Object.entries(grouped).map(([cls, symbols]) => (
          <div key={cls}>
            <div className="text-dark-400 text-xs uppercase tracking-wider mb-1 px-1">{cls}</div>
            {symbols.map(sym => (
              <button
                key={sym}
                onClick={() => onSelect(sym)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded text-sm transition ${
                  selected === sym ? 'bg-dark-700 border border-dark-600' : 'hover:bg-dark-700'
                }`}
              >
                <span className="font-medium">{sym}</span>
                <span className="text-blue-400 font-mono tabular-nums">
                  {prices[sym] ? `$${prices[sym].toFixed(2)}` : '...'}
                </span>
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
