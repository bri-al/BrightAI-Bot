'use client'

import { useState, useEffect } from 'react'
import { api } from '@/lib/api'

export default function BotControls({ addLog }: { addLog: (msg: string) => void }) {
  const [status, setStatus] = useState<any>({ is_trading: false, kill_switch: false })
  const [loading, setLoading] = useState('')

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api('/api/trade/status')
        setStatus(data || {})
      } catch (e) {
        console.error('Failed to load bot status:', e)
      }
    }
    load()
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [])

  const action = async (endpoint: string, msg: string) => {
    setLoading(endpoint)
    try {
      const result = await api(`/api/trade/${endpoint}`, { method: 'POST' })
      addLog(result?.message || msg)
      const data = await api('/api/trade/status')
      setStatus(data || {})
    } catch (e: any) {
      addLog(`Error: ${e?.message || e || 'unknown'}`)
      console.error('BotControls action error:', e)
    }
    setLoading('')
  }

  return (
    <>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-dark-400">Bot Status</span>
        <span className={`text-xs font-bold ${status.is_trading ? 'text-green-400' : 'text-dark-400'}`}>
          {status.is_trading ? 'RUNNING' : status.kill_switch ? 'KILLED' : 'STOPPED'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-1">
        <button
          onClick={() => action('start', 'Trading started')}
          disabled={loading !== '' || status.is_trading || status.kill_switch}
          className="btn btn-primary text-xs py-1.5"
        >
          {loading === 'start' ? '...' : 'Start'}
        </button>
        <button
          onClick={() => action('stop', 'Trading stopped')}
          disabled={loading !== '' || !status.is_trading}
          className="btn btn-secondary text-xs py-1.5"
        >
          {loading === 'stop' ? '...' : 'Stop'}
        </button>
      </div>

      <button
        onClick={() => action('kill', 'KILL SWITCH ACTIVATED')}
        disabled={loading !== '' || status.kill_switch}
        className="btn btn-danger w-full text-xs py-1.5"
      >
        {loading === 'kill' ? '...' : 'KILL SWITCH'}
      </button>

      {status.kill_switch && (
        <button
          onClick={() => action('kill/reset', 'Kill switch reset')}
          className="btn btn-warning w-full text-xs py-1.5"
        >
          Reset Kill Switch
        </button>
      )}

      <div className="text-xs text-dark-400">
        <div>Strategy: Adaptive</div>
        <div className="flex items-center gap-1">
          Broker: {status.broker?.name || '...'}
          <span className={`inline-block w-1.5 h-1.5 rounded-full ${status.broker?.connected ? 'bg-green-400' : 'bg-red-400'}`} />
        </div>
        {status.broker?.connected && status.broker?.account && (
          <div>Balance: ${status.broker.account.balance?.toFixed(2) ?? '...'}</div>
        )}
      </div>
    </>
  )
}
