import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { authStore } from '../store/auth'
import { Bot, AlertTriangle, Package, TrendingUp, Loader2, Zap, RefreshCw } from 'lucide-react'

const STORE_ID = 'b1000000-0000-0000-0000-000000000001'

interface AgentEvent {
  id: string
  agent_name: string
  event_type: string
  severity: 'URGENT' | 'HIGH' | 'MEDIUM' | 'LOW'
  store_id: string
  summary: string
  reasoning: string
  created_at: string
}

const SEVERITY_STYLES: Record<string, string> = {
  URGENT: 'bg-red-900/40 border-red-700/60 text-red-300',
  HIGH:   'bg-orange-900/40 border-orange-700/60 text-orange-300',
  MEDIUM: 'bg-amber-900/40 border-amber-700/60 text-amber-300',
  LOW:    'bg-sky-900/40 border-sky-700/60 text-sky-300',
}

const EVENT_ICONS: Record<string, any> = {
  RESTOCK_ALERT: Package,
  ANOMALY_FLAG:  AlertTriangle,
  INSIGHT:       TrendingUp,
}

const AGENT_LABELS: Record<string, string> = {
  RestockSentinel:  '📦 Restock Sentinel',
  GuardianSentinel: '🛡️ Guardian Sentinel',
  RetailAgent:      '🤖 Retail Agent',
}

function formatTimeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export default function AgentActivityFeed() {
  const user = authStore.getUser()
  const storeId = user?.store_id ?? STORE_ID
  const [events, setEvents]           = useState<AgentEvent[]>([])
  const [loading, setLoading]         = useState(true)
  const [agentOnline, setAgentOnline] = useState(false)
  const [question, setQuestion]       = useState('')
  const [queryLoading, setQueryLoading] = useState(false)
  const [agentResponse, setAgentResponse] = useState<any>(null)

  async function fetchEvents() {
    setLoading(true)
    try {
      const data = await api.get<{ events: AgentEvent[] }>(
        `/ai/agent/events?store_id=${storeId}&limit=10`
      )
      setEvents(data.events || [])
    } catch {
      setEvents([])
    } finally {
      setLoading(false)
    }
  }

  async function fetchStatus() {
    try {
      const status = await api.get<{ agent_online: boolean }>('/ai/agent/status')
      setAgentOnline(status.agent_online)
    } catch {
      setAgentOnline(false)
    }
  }

  async function askAgent() {
    if (!question.trim()) return
    setQueryLoading(true)
    setAgentResponse(null)
    try {
      const result = await api.post<any>('/ai/agent/query', { question, store_id: storeId })
      setAgentResponse(result)
      await fetchEvents()
    } catch (e: any) {
      setAgentResponse({ error: e.message })
    } finally {
      setQueryLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    fetchEvents()
    const interval = setInterval(fetchEvents, 60000)
    return () => clearInterval(interval)
  }, [storeId])

  return (
    <div className="space-y-3">

      {/* Agent Query Box */}
      <div className={`border rounded-xl p-4 backdrop-blur-sm transition-colors ${
        agentOnline
          ? 'bg-slate-800/70 border-violet-700/40'
          : 'bg-slate-800/40 border-slate-700/50'
      }`}>
        {/* Header */}
        <div className="flex items-center gap-2 mb-3">
          <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${
            agentOnline ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'
          }`} />
          <h3 className={`text-sm font-semibold flex items-center gap-2 ${
            agentOnline ? 'text-white' : 'text-slate-500'
          }`}>
            <Bot size={14} className={agentOnline ? 'text-violet-400' : 'text-slate-600'} />
            NorthStar Retail Agent
            {agentOnline && (
              <span className="text-[9px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider bg-emerald-900/60 text-emerald-300 border border-emerald-700/40">
                LangGraph + Gemini
              </span>
            )}
          </h3>
        </div>

        {/* Input (online) or explanation (offline) */}
        {agentOnline ? (
          <div className="space-y-2">
            <div className="flex gap-2">
              <input
                value={question}
                onChange={e => setQuestion(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && askAgent()}
                placeholder="Ask: 'What needs restocking?' or 'Any suspicious orders?'"
                className="flex-1 bg-slate-900/70 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500 min-w-0"
              />
              <button
                onClick={askAgent}
                disabled={queryLoading || !question.trim()}
                className="flex items-center justify-center gap-1.5 px-3 py-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white rounded-lg text-sm font-medium transition-all active:scale-95 shrink-0"
              >
                {queryLoading ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
                {queryLoading ? 'Thinking…' : 'Ask'}
              </button>
            </div>

            {agentResponse && (
              <div className="bg-slate-900/60 border border-slate-700 rounded-lg p-3">
                {agentResponse.error ? (
                  <p className="text-red-400 text-xs">{agentResponse.error}</p>
                ) : (
                  <>
                    <p className="text-sm text-white leading-relaxed">{agentResponse.answer}</p>
                    {agentResponse.tools_invoked?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2 pt-2 border-t border-slate-700">
                        <span className="text-[10px] text-slate-500">Tools used:</span>
                        {agentResponse.tools_invoked.map((t: any, i: number) => (
                          <span key={i} className="text-[10px] px-1.5 py-0.5 bg-violet-900/40 text-violet-300 rounded font-mono border border-violet-700/30">
                            {t.tool}
                          </span>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-start gap-2 px-3 py-2.5 bg-slate-900/40 rounded-lg border border-slate-700/50">
            <Bot size={13} className="text-slate-600 shrink-0 mt-0.5" />
            <p className="text-xs text-slate-500 leading-relaxed">
              Add <span className="font-mono text-slate-400 bg-slate-800 px-1 rounded">GEMINI_API_KEY</span> to Railway env variables to activate the AI agent.
            </p>
          </div>
        )}
      </div>

      {/* Agent Events Feed */}
      <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-4 backdrop-blur-sm">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Bot size={14} className="text-sky-400" />
            Agent Activity
          </h3>
          <button onClick={fetchEvents} className="text-slate-600 hover:text-white transition-colors p-1 rounded-lg hover:bg-slate-700">
            <RefreshCw size={12} />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-5">
            <Loader2 size={16} className="animate-spin text-slate-600" />
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-5">
            <Bot size={20} className="text-slate-700 mx-auto mb-1.5" />
            <p className="text-slate-600 text-xs">No agent activity yet</p>
            <p className="text-slate-700 text-[11px] mt-0.5">
              {agentOnline
                ? 'Sentinels scan every 5–10 min automatically.'
                : 'Activate with GEMINI_API_KEY in Railway.'}
            </p>
          </div>
        ) : (
          <div className="space-y-1.5">
            {events.map(event => {
              const Icon = EVENT_ICONS[event.event_type] || Bot
              const styleClass = SEVERITY_STYLES[event.severity] || SEVERITY_STYLES.LOW
              return (
                <div key={event.id} className={`rounded-lg border px-3 py-2 ${styleClass}`}>
                  <div className="flex items-start gap-2">
                    <Icon size={12} className="mt-0.5 shrink-0 opacity-80" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider opacity-70">
                          {AGENT_LABELS[event.agent_name] || event.agent_name}
                        </span>
                        <span className="text-[10px] opacity-40">{formatTimeAgo(event.created_at)}</span>
                      </div>
                      <p className="text-[11px] leading-relaxed line-clamp-2">{event.summary}</p>
                    </div>
                    <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded shrink-0 ${
                      event.severity === 'URGENT' ? 'bg-red-600 text-white' :
                      event.severity === 'HIGH'   ? 'bg-orange-600 text-white' :
                      event.severity === 'MEDIUM' ? 'bg-amber-600 text-white' :
                                                    'bg-slate-600 text-slate-300'
                    }`}>
                      {event.severity}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

    </div>
  )
}
