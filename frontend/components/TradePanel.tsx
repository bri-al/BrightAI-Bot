'use client'

import { useState, useEffect } from 'react'
import { api } from '@/lib/api'

export default function TradePanel({ symbol, addLog }: { symbol: string; addLog: (msg: string) => void }) {
  const [signal, setSignal] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadSignal()
    const interval = setInterval(loadSignal, 30000)
    return () => clearInterval(interval)
  }, [symbol])

  const loadSignal = async () => {
    try {
      const data = await api(`/api/signal/${symbol}`)
      setSignal(data)
    } catch (e) {
      console.error('Failed to load signal:', e)
    }
  }

  const handleExecute = async () => {
    setLoading(true)
    try {
      const result = await api(`/api/trade/execute/${symbol}`, { method: 'POST' })
      if (result?.action === 'FAILED' || result?.action === 'REJECTED') {
        addLog(`Trade rejected: ${result?.reason || 'unknown'}`)
      } else if (result?.action !== 'HOLD') {
        addLog(`Executed ${result?.action || '?'} ${symbol} @ ${result?.entry || '?'} [${result?.confidence || '?'}%]`)
      } else {
        addLog(`No trade signal for ${symbol}`)
      }
      loadSignal()
    } catch (e: any) {
      addLog(`Trade error: ${e?.message || e || 'unknown'}`)
    }
    setLoading(false)
  }

  const signalColor = signal?.action === 'BUY' ? 'text-green-400' : signal?.action === 'SELL' ? 'text-red-400' : 'text-yellow-400'
  const signalBg = signal?.action === 'BUY' ? 'bg-green-900/30 border-green-700' : signal?.action === 'SELL' ? 'bg-red-900/30 border-red-700' : 'bg-dark-700 border-dark-600'

  return (
    <div className="card h-full flex flex-col">
      <div className="card-header">Trade Panel - {symbol}</div>

      {/* Signal Display */}
      <div className={`p-4 rounded-lg border mb-4 ${signalBg}`}>
        <div className="text-center">
          <div className={`text-2xl font-bold ${signalColor}`}>
            {signal?.action || 'LOADING'}
          </div>
          {signal && (
            <>
              <div className="text-dark-400 text-xs mt-1">
                Confidence: <span className="text-white font-bold">{signal.confidence}%</span>
              </div>
              <div className="text-dark-400 text-xs">
                Regime: <span className="text-white">{signal.regime}</span>
              </div>
              <div className="text-dark-400 text-xs mt-2">{signal.reason}</div>
            </>
          )}
        </div>
      </div>

      {/* AI Explanation */}
      {signal && (
        <div className="mb-4">
          <div className="text-xs text-dark-400 uppercase tracking-wider mb-2">AI Analysis</div>
          <div className="text-xs text-dark-300 space-y-1">
            <p>Market regime: <span className="text-white">{signal.regime}</span> (strength: {signal.regime_strength}%)</p>
            <p>Current price: <span className="text-white">${signal.price?.toFixed(2)}</span></p>
            <p>Action: <span className={signalColor}>{signal.action}</span></p>
            <p>Reasoning: {signal.reason}</p>
          </div>
        </div>
      )}

      {/* Execute Button */}
      <div className="mt-auto space-y-2">
        <button
          onClick={handleExecute}
          disabled={loading}
          className="btn btn-primary w-full"
        >
          {loading ? 'Processing...' : `Execute ${signal?.action || 'HOLD'}`}
        </button>
        <div className="text-xs text-dark-400 text-center">
          Risk: 2% | R/R: 1:2 | Auto SL/TP
        </div>
      </div>
    </div>
  )
}
