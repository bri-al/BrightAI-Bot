'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

export default function PositionsTable() {
  const [positions, setPositions] = useState<any[]>([])

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api('/api/trades')
        if (data) {
          setPositions(data.filter((t: any) => t.status === 'open'))
        }
      } catch (e) {
        console.error('Failed to load positions:', e)
      }
    }
    load()
    const interval = setInterval(load, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="card">
      <div className="card-header">Open Positions ({positions.length})</div>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Direction</th>
            <th>Entry</th>
            <th>Size</th>
            <th>SL</th>
            <th>TP</th>
            <th>Strategy</th>
          </tr>
        </thead>
        <tbody>
          {positions.length === 0 ? (
            <tr><td colSpan={7} className="text-dark-400 text-center py-6">No open positions</td></tr>
          ) : positions.map((t: any) => (
            <tr key={t.id}>
              <td className="font-medium">{t.symbol}</td>
              <td>
                <span className={`badge ${t.direction === 'long' ? 'badge-green' : 'badge-red'}`}>
                  {t.direction}
                </span>
              </td>
              <td>${t.entry_price?.toFixed(2)}</td>
              <td>{t.size?.toFixed(4)}</td>
              <td className="text-red-400">${t.stop_loss?.toFixed(2)}</td>
              <td className="text-green-400">{t.take_profit ? `$${t.take_profit.toFixed(2)}` : '-'}</td>
              <td className="text-dark-400">{t.strategy || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
