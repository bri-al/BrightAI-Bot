'use client'

import { useState, useEffect, useCallback } from 'react'
import Watchlist from '@/components/Watchlist'
import Chart from '@/components/Chart'
import TradePanel from '@/components/TradePanel'
import PositionsTable from '@/components/PositionsTable'
import PortfolioOverview from '@/components/PortfolioOverview'
import BotControls from '@/components/BotControls'
import { api } from '@/lib/api'

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT')
  const [logs, setLogs] = useState<string[]>(['System ready.'])
  const addLog = useCallback((msg: string) => {
    setLogs(prev => [...prev.slice(-99), `[${new Date().toLocaleTimeString()}] ${msg}`])
  }, [])

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/ws`
    let socket: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let mounted = true

    const connect = () => {
      socket = new WebSocket(wsUrl)
      socket.onopen = () => addLog('WebSocket connected')
      socket.onclose = () => {
        addLog('WebSocket disconnected')
        if (mounted) {
          reconnectTimer = setTimeout(connect, 3000)
        }
      }
      socket.onerror = () => {}
      socket.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data)
          if (msg.type === 'trade_executed' && msg.data) {
            addLog(`Trade: ${msg.data.action || '?'} ${msg.data.symbol || '?'} @ ${msg.data.price || '?'} [${msg.data.confidence || '?'}%]`)
          }
        } catch {}
      }
    }

    connect()

    return () => {
      mounted = false
      if (reconnectTimer) clearTimeout(reconnectTimer)
      if (socket) socket.close()
    }
  }, [addLog])

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: '●' },
    { id: 'trades', label: 'Trades', icon: '⇄' },
    { id: 'risk', label: 'Risk', icon: '⚠' },
  ]

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="w-56 bg-dark-800 border-r border-dark-700 flex flex-col flex-shrink-0">
        <div className="p-4 border-b border-dark-700">
          <h1 className="text-blue-400 font-bold text-sm tracking-wider">AI TRADING</h1>
          <span className="text-dark-400 text-xs">v1.0.0</span>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded text-sm transition ${
                activeTab === tab.id
                  ? 'bg-dark-700 text-white border-l-2 border-blue-400'
                  : 'text-dark-300 hover:text-white hover:bg-dark-700'
              }`}
            >
              <span className="text-xs w-4 text-center">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
        <div className="p-3 border-t border-dark-700 space-y-2">
          <BotControls addLog={addLog} />
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {activeTab === 'dashboard' && (
          <div className="flex-1 flex flex-col p-4 gap-4 overflow-y-auto">
            {/* Top bar: watchlist + chart */}
            <div className="flex gap-4 flex-1 min-h-0">
              <div className="w-56 flex-shrink-0">
                <Watchlist selected={selectedSymbol} onSelect={setSelectedSymbol} />
              </div>
              <div className="flex-1 flex flex-col gap-4 min-w-0">
                <div className="flex-1 min-h-0">
                  <Chart symbol={selectedSymbol} />
                </div>
                <PortfolioOverview />
              </div>
              <div className="w-72 flex-shrink-0">
                <TradePanel symbol={selectedSymbol} addLog={addLog} />
              </div>
            </div>

            {/* Bottom: positions + log */}
            <div className="flex gap-4">
              <div className="flex-1">
                <PositionsTable />
              </div>
              <div className="w-96">
                <div className="card">
                  <div className="card-header">Activity Log</div>
                  <div className="h-48 overflow-y-auto font-mono text-xs">
                    {logs.map((log, i) => (
                      <div key={i} className="log-entry text-dark-300">{log}</div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'trades' && (
          <div className="flex-1 p-4 overflow-y-auto">
            <h2 className="text-lg font-semibold mb-4">Trade History</h2>
            <TradesView />
          </div>
        )}

        {activeTab === 'risk' && (
          <div className="flex-1 p-4 overflow-y-auto">
            <h2 className="text-lg font-semibold mb-4">Risk Dashboard</h2>
            <RiskView />
          </div>
        )}
      </main>
    </div>
  )
}

function TradesView() {
  const [trades, setTrades] = useState<any[]>([])
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    const load = async () => {
      const data = await api(`/api/trades?status=${filter}`)
      setTrades(data || [])
    }
    load()
    const interval = setInterval(load, 10000)
    return () => clearInterval(interval)
  }, [filter])

  return (
    <div className="card">
      <div className="flex gap-2 mb-4">
        {['all', 'open', 'closed'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`btn ${filter === f ? 'btn-primary' : 'btn-secondary'} text-xs py-1 px-3`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Symbol</th>
            <th>Direction</th>
            <th>Entry</th>
            <th>Exit</th>
            <th>Size</th>
            <th>PnL</th>
            <th>Status</th>
            <th>Strategy</th>
            <th>Time</th>
          </tr>
        </thead>
        <tbody>
          {trades.length === 0 ? (
            <tr><td colSpan={10} className="text-dark-400 text-center py-8">No trades</td></tr>
          ) : trades.map((t: any) => (
            <tr key={t.id}>
              <td className="text-dark-400">{t.id}</td>
              <td className="font-medium">{t.symbol}</td>
              <td>
                <span className={`badge ${t.direction === 'long' ? 'badge-green' : 'badge-red'}`}>
                  {t.direction}
                </span>
              </td>
              <td>${t.entry_price?.toFixed(2)}</td>
              <td>{t.exit_price ? `$${t.exit_price.toFixed(2)}` : '-'}</td>
              <td>{t.size?.toFixed(4)}</td>
              <td className={t.pnl && t.pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                {t.pnl ? `$${t.pnl.toFixed(2)}` : '-'}
              </td>
              <td>
                <span className={`badge ${t.status === 'open' ? 'badge-yellow' : 'badge-blue'}`}>
                  {t.status}
                </span>
              </td>
              <td className="text-dark-400">{t.strategy || '-'}</td>
              <td className="text-dark-400 text-xs">
                {new Date(t.created_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RiskView() {
  const [risk, setRisk] = useState<any>({})

  useEffect(() => {
    const load = async () => {
      const data = await api('/api/portfolio')
      setRisk(data || {})
    }
    load()
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [])

  const items = [
    ['Current Equity', `$${(risk.equity || 0).toLocaleString()}`, 'text-green-400'],
    ['Drawdown', `${(risk.drawdown || 0).toFixed(2)}%`, Number(risk.drawdown) > 10 ? 'text-red-400' : Number(risk.drawdown) > 5 ? 'text-yellow-400' : 'text-green-400'],
    ['Open Positions', `${risk.open_positions || 0} / 5`, ''],
    ['Daily Trades', `${risk.daily_trades || 0} / 20`, ''],
    ['Daily P&L', `$${(risk.daily_pnl || 0).toFixed(2)}`, Number(risk.daily_pnl) >= 0 ? 'text-green-400' : 'text-red-400'],
    ['Total Trades', risk.total_trades || 0, ''],
    ['Kill Switch', risk.kill_switch ? 'ACTIVE' : 'Inactive', risk.kill_switch ? 'text-red-400 font-bold' : 'text-green-400'],
  ]

  return (
    <div className="grid grid-cols-2 gap-4">
      {items.map(([label, value, cls]) => (
        <div key={label} className="card">
          <div className="text-dark-400 text-xs uppercase tracking-wider mb-1">{label}</div>
          <div className={`text-2xl font-bold ${cls}`}>{value}</div>
        </div>
      ))}
      <div className="card col-span-2">
        <div className="card-header">Risk Limits</div>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div><span className="text-dark-400">Max Risk/Trade:</span> 2%</div>
          <div><span className="text-dark-400">Max Daily Loss:</span> 5%</div>
          <div><span className="text-dark-400">Max Drawdown:</span> 15%</div>
          <div><span className="text-dark-400">Min R/R Ratio:</span> 1:2</div>
          <div><span className="text-dark-400">Max Positions:</span> 5</div>
          <div><span className="text-dark-400">Max Daily Trades:</span> 20</div>
        </div>
      </div>
    </div>
  )
}
