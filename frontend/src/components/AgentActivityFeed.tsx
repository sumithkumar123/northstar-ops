import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { authStore } from '../store/auth'
import {
  Bot,
  AlertTriangle,
  Package,
  TrendingUp,
  Loader2,
  Zap,
  RefreshCw,
  Sparkles,
  Brain,
  Clock3,
} from 'lucide-react'

const STORE_ID = 'b1000000-0000-0000-0000-000000000001'

interface AgentToolCall {
  tool?: string
  name?: string
  args?: Record<string, unknown>
}

interface AgentEventPayload {
  question?: string
  full_response?: string
  tools_used?: AgentToolCall[]
  reasoning_steps?: number
  model?: string | null
}

interface AgentEvent {
  id: string
  agent_name: string
  event_type: string
  severity: 'URGENT' | 'HIGH' | 'MEDIUM' | 'LOW'
  store_id: string
  summary: string
  reasoning: string
  created_at: string
  payload?: AgentEventPayload
}

const SAMPLE_QUESTIONS = [
  'What products need restocking before the weekend?',
  'Can another store transfer inventory to mine before I reorder?',
  'Are there any suspicious transactions in the last 7 days?',
]

const SEVERITY_STYLES: Record<string, string> = {
  URGENT: 'border-red-500/50 bg-red-500/10 text-red-200',
  HIGH: 'border-orange-500/50 bg-orange-500/10 text-orange-200',
  MEDIUM: 'border-amber-500/50 bg-amber-500/10 text-amber-200',
  LOW: 'border-sky-500/40 bg-sky-500/10 text-sky-200',
}

const EVENT_ICONS: Record<string, any> = {
  RESTOCK_ALERT: Package,
  ANOMALY_FLAG: AlertTriangle,
  INSIGHT: TrendingUp,
}

const AGENT_LABELS: Record<string, string> = {
  RestockSentinel: 'Restock Sentinel',
  GuardianSentinel: 'Guardian Sentinel',
  RetailAgent: 'Retail Agent',
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

function getToolName(tool?: AgentToolCall) {
  return tool?.tool || tool?.name || 'unknown_tool'
}

export default function AgentActivityFeed() {
  const user = authStore.getUser()
  const storeId = user?.store_id ?? STORE_ID
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [agentOnline, setAgentOnline] = useState(false)
  const [agentStatusMessage, setAgentStatusMessage] = useState('')
  const [question, setQuestion] = useState('')
  const [queryLoading, setQueryLoading] = useState(false)
  const [agentResponse, setAgentResponse] = useState<any>(null)

  async function fetchEvents() {
    setLoading(true)
    try {
      const data = await api.get<{ events: AgentEvent[] }>(`/ai/agent/events?store_id=${storeId}&limit=10`)
      setEvents(data.events || [])
    } catch {
      setEvents([])
    } finally {
      setLoading(false)
    }
  }

  async function fetchStatus() {
    try {
      const status = await api.get<{
        agent_online: boolean
        message?: string
        init_error?: string
        model?: string
      }>('/ai/agent/status')
      setAgentOnline(status.agent_online)
      setAgentStatusMessage(
        status.agent_online
          ? (status.model ? `Connected to ${status.model}` : 'Agent is online')
          : (status.init_error || status.message || 'Agent is offline')
      )
    } catch {
      setAgentOnline(false)
      setAgentStatusMessage('Unable to reach AI service')
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
    const interval = setInterval(fetchEvents, 30000)
    return () => clearInterval(interval)
  }, [storeId])

  return (
    <div className="space-y-4">
      <div className={`rounded-[28px] border p-4 shadow-2xl transition-colors ${
        agentOnline
          ? 'border-cyan-500/30 bg-slate-900/85'
          : 'border-slate-700/60 bg-slate-900/60'
      }`}>
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${agentOnline ? 'bg-emerald-400' : 'bg-slate-500'}`} />
              <p className="text-[11px] font-semibold uppercase tracking-[0.25em] text-cyan-300/80">
                Agent Command
              </p>
            </div>
            <h2 className="display-font text-2xl text-white">NorthStar Retail Agent</h2>
            <p className="max-w-md text-xs leading-relaxed text-slate-400">
              Ask for restocks, transfers, anomalies, or a business summary. The agent decides
              which retail tools to call and logs its work below.
            </p>
          </div>
          <div className="rounded-full border border-emerald-500/25 bg-emerald-500/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-300">
            LangGraph + Gemini
          </div>
        </div>

        <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/80 p-3">
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && askAgent()}
              placeholder="Ask a manager-style question..."
              className="min-w-0 flex-1 rounded-2xl border border-slate-700 bg-slate-900/70 px-4 py-3 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
            />
            <button
              onClick={askAgent}
              disabled={queryLoading || !question.trim()}
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-500 px-4 py-3 text-sm font-semibold text-slate-950 transition-transform hover:scale-[1.01] disabled:opacity-40"
            >
              {queryLoading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
              {queryLoading ? 'Thinking...' : 'Ask'}
            </button>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {SAMPLE_QUESTIONS.map(sample => (
              <button
                key={sample}
                onClick={() => setQuestion(sample)}
                className="rounded-full border border-slate-700 bg-slate-900/60 px-3 py-1.5 text-[11px] text-slate-300 transition-colors hover:border-cyan-500/40 hover:text-white"
              >
                {sample}
              </button>
            ))}
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-slate-800 pt-3 text-[11px] text-slate-500">
            <span className="inline-flex items-center gap-1.5">
              <Brain size={12} className="text-cyan-400" />
              {agentStatusMessage}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Clock3 size={12} className="text-violet-400" />
              Autonomous scans every 5-10 min
            </span>
          </div>

          {agentResponse && (
            <div className="mt-3 rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
              {agentResponse.error ? (
                <p className="text-sm text-red-400">{agentResponse.error}</p>
              ) : (
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.2em] text-slate-500">
                    <span>Latest Response</span>
                    {agentResponse.model && (
                      <span className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-2 py-0.5 text-[10px] text-cyan-300">
                        {agentResponse.model}
                      </span>
                    )}
                    {agentResponse.reasoning_steps && (
                      <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[10px] text-slate-400">
                        {agentResponse.reasoning_steps} steps
                      </span>
                    )}
                  </div>
                  <p className="whitespace-pre-wrap text-sm leading-7 text-white">
                    {typeof agentResponse.answer === 'string'
                      ? agentResponse.answer
                      : JSON.stringify(agentResponse.answer, null, 2)}
                  </p>
                  {agentResponse.tools_invoked?.length > 0 && (
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-3">
                      <p className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">
                        <Sparkles size={12} className="text-cyan-400" />
                        Tool Trace
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {agentResponse.tools_invoked.map((tool: AgentToolCall, index: number) => (
                          <span
                            key={`${getToolName(tool)}-${index}`}
                            className="rounded-full border border-cyan-500/25 bg-cyan-500/10 px-2.5 py-1 font-mono text-[11px] text-cyan-200"
                          >
                            {getToolName(tool)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="rounded-[28px] border border-slate-800 bg-slate-900/75 p-4 shadow-2xl">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.25em] text-sky-300/80">
              Audit Trail
            </p>
            <h3 className="display-font text-2xl text-white">Agent Activity</h3>
            <p className="mt-1 text-xs text-slate-500">
              Every decision here is logged with the question, tools used, and severity.
            </p>
          </div>
          <button
            onClick={fetchEvents}
            className="rounded-full border border-slate-700 p-2 text-slate-400 transition-colors hover:border-cyan-500/40 hover:text-white"
            aria-label="Refresh agent activity"
          >
            <RefreshCw size={14} />
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 size={18} className="animate-spin text-slate-600" />
          </div>
        ) : events.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-950/50 px-4 py-10 text-center">
            <Bot size={22} className="mx-auto mb-2 text-slate-700" />
            <p className="text-sm text-slate-400">No agent activity yet</p>
            <p className="mt-1 text-xs text-slate-600">
              Ask a store question or wait for the sentinels to scan automatically.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {events.map(event => {
              const Icon = EVENT_ICONS[event.event_type] || Bot
              const styleClass = SEVERITY_STYLES[event.severity] || SEVERITY_STYLES.LOW
              const tools = event.payload?.tools_used || []

              return (
                <div key={event.id} className={`rounded-2xl border p-4 ${styleClass}`}>
                  <div className="flex items-start gap-3">
                    <div className="rounded-xl bg-slate-950/40 p-2">
                      <Icon size={14} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[11px] font-bold uppercase tracking-[0.2em]">
                          {AGENT_LABELS[event.agent_name] || event.agent_name}
                        </span>
                        <span className="text-[11px] opacity-60">{formatTimeAgo(event.created_at)}</span>
                        <span className="ml-auto rounded-full border border-white/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.2em]">
                          {event.severity}
                        </span>
                      </div>

                      {event.payload?.question && (
                        <p className="mt-2 text-[11px] leading-5 text-slate-300/90">
                          <span className="font-semibold text-white">Question:</span> {event.payload.question}
                        </p>
                      )}

                      <p className="mt-2 text-sm leading-6 text-white/95">{event.summary}</p>

                      {tools.length > 0 && (
                        <div className="mt-3">
                          <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-300/70">
                            Tools used
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {tools.map((tool, index) => (
                              <span
                                key={`${getToolName(tool)}-${index}`}
                                className="rounded-full border border-white/10 bg-slate-950/35 px-2.5 py-1 font-mono text-[11px] text-white/90"
                              >
                                {getToolName(tool)}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {event.reasoning && (
                        <p className="mt-3 text-[11px] leading-5 text-slate-300/80">
                          <span className="font-semibold text-white/90">Why:</span> {event.reasoning}
                        </p>
                      )}
                    </div>
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
