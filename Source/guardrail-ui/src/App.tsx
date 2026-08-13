import { useState } from 'react'
import { Shield, ScrollText, FlaskConical, Activity, LogOut } from 'lucide-react'
import { cn } from '@/lib/utils'
import { RulesEditor } from '@/components/RulesEditor'
import { Login } from '@/components/Login'
import { isAuthenticated, logout } from '@/lib/api'

type View = 'rules' | 'audit' | 'test' | 'health'

const navItems = [
  { id: 'rules' as View, label: 'Rules Editor', icon: Shield, available: true },
  { id: 'audit' as View, label: 'Audit Log', icon: ScrollText, available: false },
  { id: 'test' as View, label: 'Test Harness', icon: FlaskConical, available: false },
  { id: 'health' as View, label: 'Layer Health', icon: Activity, available: false },
]

export default function App() {
  const [authed, setAuthed] = useState(isAuthenticated())
  const [view, setView] = useState<View>('rules')

  if (!authed) return <Login onSuccess={() => setAuthed(true)} />

  const handleLogout = () => {
    logout()
    setAuthed(false)
  }

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <aside className="w-60 shrink-0 border-r bg-card flex flex-col">
        <div className="h-14 flex items-center gap-2.5 px-5 border-b">
          <Shield className="h-5 w-5 text-emerald-600 shrink-0" />
          <span className="font-semibold text-sm tracking-tight">Guardrail Admin</span>
        </div>

        <nav className="flex-1 py-3 px-2 space-y-0.5">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => item.available && setView(item.id)}
              className={cn(
                'w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors',
                item.available
                  ? view === item.id
                    ? 'bg-accent text-accent-foreground font-medium'
                    : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'
                  : 'text-muted-foreground/40 cursor-not-allowed',
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              <span className="flex-1 text-left">{item.label}</span>
              {!item.available && (
                <span className="text-[10px] bg-muted rounded px-1.5 py-0.5 font-medium tracking-wide">
                  Soon
                </span>
              )}
            </button>
          ))}
        </nav>

        <div className="px-2 py-3 border-t space-y-1">
          <p className="text-[11px] text-muted-foreground px-3 pb-1">
            guardrails.yaml · hot-reload
          </p>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm text-muted-foreground hover:bg-accent/60 hover:text-foreground transition-colors"
          >
            <LogOut className="h-4 w-4 shrink-0" />
            <span className="flex-1 text-left">Sign out</span>
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-hidden flex flex-col">
        {view === 'rules' && <RulesEditor />}
      </main>
    </div>
  )
}
