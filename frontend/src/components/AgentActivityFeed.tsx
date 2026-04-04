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
  RestockSentinel: '📦 Restock Sentinel',
  GuardianSentinel: '🛡️ Guardian Sentinel',
  RetailAgent: '🤖 Retail Agent',
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
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [agentOnline, setAgentOnline] = useState(false)

  // Agent query state
  const [question, setQuestion] = useState('')
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
      const result = await api.post<any>('/ai/agent/query', {
        question,
        store_id: storeId,
      })
      setAgentResponse(result)
      // Refresh events to show this new insight
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
    // Poll for new events every 60 seconds
    const interval = setInterval(fetchEvents, 60000)
    return () => clearInterval(interval)
  }, [storeId])

  return (
    <div className="space-y-4">
      {/* Agent Query Box */}
      <div className="bg-slate-800/60 border border-violet-700/40 rounded-xl p-5 backdrop-blur-sm">
        <div className="flex items-center gap-2 mb-3">
          <div className={`w-2 h-2 rounded-full ${agentOnline ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Bot size={15} className="text-violet-400" />
            NorthStar Retail Agent
            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${
              agentOnline
                ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-700/40'
                : 'bg-slate-700 text-slate-500'
            }`}>
              {agentOnline ? 'LangGraph + Gemini' : 'Offline'}
            </span>
          </h3>
        </div>

        <div className="flex flex-col sm:flex-row gap-2">
          <input
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && askAgent()}
            placeholder="Ask the agent: 'What needs restocking?' or 'Any fraud alerts?'"
            className="flex-1 bg-slate-900/60 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500"
            disabled={!agentOnline}
          />
          <button
            onClick={askAgent}
            disabled={queryLoading || !question.trim() || !agentOnline}
            className="flex items-center justify-center gap-1.5 px-4 py-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white rounded-lg text-sm font-medium transition-colors shrink-0"
          >
            {queryLoading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
            {queryLoading ? 'Thinking…' : 'Ask Agent'}
          </button>
        </div>

        {/* Agent response */}
        {agentResponse && (
          <div className="mt-3 bg-slate-900/60 border border-slate-700 rounded-lg p-3">
            {agentResponse.error ? (
              <p className="text-red-400 text-sm">{agentResponse.error}</p>
            ) : (
              <>
                <p className="text-sm text-white leading-relaxed mb-2">{agentResponse.answer}</p>
                {agentResponse.tools_invoked?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    <span className="text-[10px] text-slate-500 mr-1">Tools used:</span>
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

      {/* Agent Events Feed */}
      <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-5 backdrop-blur-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Bot size={15} className="text-sky-400" /> Agent Activity
          </h3>
          <button onClick={fetchEvents} className="text-slate-500 hover:text-white transition-colors">
            <RefreshCw size={13} />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-6">
            <Loader2 size={18} className="animate-spin text-slate-500" />
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-6">
            <Bot size={24} className="text-slate-700 mx-auto mb-2" />
            <p className="text-slate-500 text-sm">No agent activity yet</p>
            <p className="text-slate-600 text-xs mt-1">
              {agentOnline
                ? 'Sentinels run every 5–10 min. Ask the agent a question above to generate events.'
                : 'Set GEMINI_API_KEY to activate autonomous agents.'}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {events.map(event => {
              const Icon = EVENT_ICONS[event.event_type] || Bot
              const styleClass = SEVERITY_STYLES[event.severity] || SEVERITY_STYLES.LOW
              return (
                <div key={event.id} className={`rounded-lg border px-3 py-2.5 ${styleClass}`}>
                  <div className="flex items-start gap-2">
                    <Icon size={13} className="mt-0.5 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider opacity-75">
                          {AGENT_LABELS[event.agent_name] || event.agent_name}
                        </span>
                        <span className="text-[10px] opacity-50">{formatTimeAgo(event.created_at)}</span>
                      </div>
                      <p className="text-xs leading-relaxed line-clamp-2">{event.summary}</p>
                      {event.reasoning && (
                        <p className="text-[10px] opacity-60 mt-1 font-mono truncate">{event.reasoning}</p>
                      )}
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
