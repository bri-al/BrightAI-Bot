'use client'

import { useEffect, useRef, useState } from 'react'
import { api } from '@/lib/api'

export default function Chart({ symbol }: { symbol: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const seriesRef = useRef<any>(null)
  const markersRef = useRef<any>(null)
  const [analysis, setAnalysis] = useState<any>(null)
  const [signal, setSignal] = useState<any>(null)

  useEffect(() => {
    let chart: any = null
    let cancelled = false

    const init = async () => {
      if (!containerRef.current) return

      const { createChart, ColorType } = await import('lightweight-charts')

      if (cancelled) return

      chart = createChart(containerRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: '#161b22' },
          textColor: '#8b949e',
        },
        grid: {
          vertLines: { color: '#21262d' },
          horzLines: { color: '#21262d' },
        },
        timeScale: {
          borderColor: '#30363d',
          timeVisible: true,
        },
        crosshair: {
          vertLine: { color: '#58a6ff', style: 2 },
          horzLine: { color: '#58a6ff', style: 2 },
        },
        width: containerRef.current.clientWidth,
        height: containerRef.current.clientHeight,
      })

      const candleSeries = chart.addCandlestickSeries({
        upColor: '#3fb950',
        downColor: '#f85149',
        borderDownColor: '#f85149',
        borderUpColor: '#3fb950',
        wickDownColor: '#f85149',
        wickUpColor: '#3fb950',
      })

      chartRef.current = chart
      seriesRef.current = candleSeries
      await loadData(symbol, candleSeries)
      await loadAnalysis(symbol)
    }

    init()

    const handleResize = () => {
      if (chartRef.current && containerRef.current) {
        chartRef.current.resize(containerRef.current.clientWidth, containerRef.current.clientHeight)
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      cancelled = true
      window.removeEventListener('resize', handleResize)
      if (chart) chart.remove()
    }
  }, [symbol])

  const loadData = async (sym: string, series: any) => {
    try {
      const data = await api(`/api/market/candles/${sym}?limit=100`)
      if (!data || !data.candles) return
      series.setData(data.candles)
    } catch (e) {
      console.error('Failed to load chart data:', e)
    }
  }

  const loadAnalysis = async (sym: string) => {
    try {
      const data = await api(`/api/analysis/${sym}`)
      if (data?.error) return
      setAnalysis(data)

      const sig = await api(`/api/signal/${sym}`)
      setSignal(sig)
    } catch (e) {
      console.error('Failed to load analysis:', e)
    }
  }

  return (
    <div className="card h-full flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <div className="card-header mb-0">{symbol}</div>
        {analysis && (
          <div className="flex gap-4 text-xs">
            <span className="text-dark-400">
              Price: <span className="text-white font-bold">${analysis.current_price?.toFixed(2)}</span>
            </span>
          </div>
        )}
      </div>
      <div ref={containerRef} className="flex-1" style={{ minHeight: 0 }} />
      {analysis && (
        <div className="flex gap-4 mt-2 text-xs text-dark-400">
          <span>Trend: <span className="text-white">{analysis.trend}</span></span>
          <span>RSI: <span className="text-white">{analysis.rsi}</span></span>
          <span>Bias: <span className={analysis.bias === 'long' ? 'text-green-400' : analysis.bias === 'short' ? 'text-red-400' : 'text-yellow-400'}>{analysis.bias}</span></span>
          <span>Vol: <span className="text-white">{analysis.volatility_level}</span></span>
        </div>
      )}
    </div>
  )
}
