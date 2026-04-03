import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { authStore } from '../store/auth'
import { Loader2, Mountain, Zap, Shield, Globe } from 'lucide-react'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      if (!res.ok) { setError('Invalid username or password'); return }
      const data = await res.json()
      authStore.login(data.access_token, data.refresh_token)
      navigate('/')
    } catch {
      setError('Network error — is the server running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-sky-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-sky-600/10 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-violet-600/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-sky-900/5 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-4xl relative z-10 flex gap-10 items-center">

        {/* Left — branding panel */}
        <div className="hidden lg:flex flex-col flex-1 pr-6">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 bg-sky-600 rounded-2xl flex items-center justify-center shadow-lg shadow-sky-900/40">
              <Mountain size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">NorthStar Outfitters</h1>
              <p className="text-xs text-sky-400 font-medium">Operations Platform</p>
            </div>
          </div>

          <h2 className="text-3xl font-bold text-white leading-snug mb-4">
            Retail operations<br />
            <span className="text-sky-400">at every altitude.</span>
          </h2>
          <p className="text-slate-400 text-sm leading-relaxed mb-8">
            Real-time POS, inventory management, and AI-driven insights across 48 stores in the US and UK — all in one platform.
          </p>

          <div className="space-y-3">
            {[
              { icon: Zap,    text: 'Live inventory with concurrent lock protection' },
              { icon: Shield, text: 'RS256 JWT authentication with role-based access' },
              { icon: Globe,  text: 'Multi-jurisdiction tax: New York, California, UK' },
            ].map(({ icon: Icon, text }) => (
              <div key={text} className="flex items-center gap-3 text-sm text-slate-300">
                <div className="w-7 h-7 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                  <Icon size={13} className="text-sky-400" />
                </div>
                {text}
              </div>
            ))}
          </div>

          <div className="mt-10 flex gap-6">
            {[['48', 'Stores'], ['2', 'Countries'], ['3', 'Roles']].map(([n, label]) => (
              <div key={label}>
                <p className="text-2xl font-bold text-white">{n}</p>
                <p className="text-xs text-slate-400">{label}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Right — login card */}
        <div className="w-full max-w-sm mx-auto lg:mx-0">
          {/* Mobile logo */}
          <div className="text-center mb-6 lg:hidden">
            <div className="inline-flex items-center justify-center w-14 h-14 bg-sky-600 rounded-2xl mb-3 shadow-lg shadow-sky-900/40">
              <Mountain size={26} className="text-white" />
            </div>
            <h1 className="text-xl font-bold text-white">NorthStar Outfitters</h1>
            <p className="text-slate-400 text-sm mt-0.5">Operations Platform</p>
          </div>

          <div className="bg-slate-800/80 backdrop-blur-sm border border-slate-700 rounded-2xl p-8 shadow-2xl">
            <h2 className="text-lg font-semibold text-white mb-1">Sign in to your account</h2>
            <p className="text-xs text-slate-400 mb-6">Enter your credentials to access the platform</p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Username</label>
                <input
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  placeholder="e.g. manager"
                  required
                  className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500 transition-colors"
                />
              </div>
              {error && (
                <div className="bg-red-900/40 border border-red-700 text-red-300 text-xs px-3 py-2.5 rounded-lg">
                  {error}
                </div>
              )}
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-sky-600 hover:bg-sky-500 disabled:opacity-60 text-white font-semibold rounded-lg py-2.5 text-sm transition-colors flex items-center justify-center gap-2 shadow-lg shadow-sky-900/30"
              >
                {loading && <Loader2 size={16} className="animate-spin" />}
                {loading ? 'Signing in...' : 'Sign in'}
              </button>
            </form>

            <div className="mt-6 pt-5 border-t border-slate-700">
              <p className="text-xs text-slate-500 mb-2.5">Demo credentials — click to fill</p>
              <div className="space-y-1">
                {[
                  ['admin',   'Regional Admin',   'sky'],
                  ['manager', 'Store Manager',    'violet'],
                  ['assoc',   'Sales Associate',  'emerald'],
                ].map(([user, role, color]) => (
                  <button
                    key={user}
                    onClick={() => { setUsername(user); setPassword('password123') }}
                    className="w-full text-left text-xs px-3 py-2 rounded-lg hover:bg-slate-700/80 text-slate-400 hover:text-slate-200 transition-colors flex items-center gap-2"
                  >
                    <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                      color === 'sky' ? 'bg-sky-400' : color === 'violet' ? 'bg-violet-400' : 'bg-emerald-400'
                    }`} />
                    <span className="font-mono font-medium text-white">{user}</span>
                    <span className="text-slate-500">— {role}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
