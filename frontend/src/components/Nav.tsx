import { Link, useLocation } from 'react-router-dom'

export default function Nav({ theme, onToggleTheme }: { theme: 'dark' | 'light'; onToggleTheme: () => void }) {
  const { pathname } = useLocation()
  const isV2 = pathname.startsWith('/v2')
  return (
    <nav style={{
      background: 'var(--surface)',
      borderBottom: '1px solid var(--border)',
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      gap: 28,
      height: 48,
      position: 'sticky', top: 0, zIndex: 100,
    }}>
      <Link to={isV2 ? '/v2' : '/'} style={{
        fontWeight: 800, fontSize: 26, letterSpacing: '-1px',
        background: 'linear-gradient(90deg, var(--mindtrip) 0%, var(--wanderboat) 100%)',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        backgroundClip: 'text',
      }}>
        Compete
      </Link>
      <div style={{ display: 'flex', gap: 2, marginLeft: 'auto', alignItems: 'center' }}>
        {isV2 ? (
          <>
            <NavLink to="/v2" label="Reports" active={pathname === '/v2'} />
            <NavLink to="/trends" label="Trends" active={pathname === '/trends'} />
            <NavLink to="/studio" label="Queries" active={pathname === '/studio'} />
            <div style={{ width: 1, background: 'var(--border)', margin: '12px 4px' }} />
            <NavLink to="/" label="Classic" active={false} />
          </>
        ) : (
          <>
            <NavLink to="/" label="Reports" active={pathname === '/'} />
            <NavLink to="/trends" label="Trends" active={pathname === '/trends'} />
            <NavLink to="/studio" label="Queries" active={pathname === '/studio'} />
            <div style={{ width: 1, background: 'var(--border)', margin: '12px 4px' }} />
            <NavLink to="/v2" label="SBS View" active={false} />
          </>
        )}
        <div style={{ width: 1, background: 'var(--border)', margin: '12px 8px' }} />
        <button
          onClick={onToggleTheme}
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          style={{
            width: 32, height: 32, borderRadius: 6, fontSize: 15,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'var(--surface2)', border: '1px solid var(--border)',
            color: 'var(--muted)', transition: 'color 0.15s, background 0.15s',
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = 'var(--text)' }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'var(--muted)' }}
        >
          {theme === 'dark' ? '☀' : '☾'}
        </button>
      </div>
    </nav>
  )
}

function NavLink({ to, label, active }: { to: string; label: string; active: boolean }) {
  return (
    <Link to={to} style={{
      padding: '4px 12px', borderRadius: 6,
      background: active ? 'var(--surface2)' : 'transparent',
      color: active ? 'var(--text)' : 'var(--muted)',
      fontSize: 13, fontWeight: active ? 600 : 400,
    }}>
      {label}
    </Link>
  )
}
