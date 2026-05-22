import { Link, useLocation } from 'react-router-dom'

export default function Nav() {
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
      <Link to={isV2 ? '/v2' : '/'} style={{ fontWeight: 700, fontSize: 14, letterSpacing: '-0.3px', display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ color: 'var(--mindtrip)' }}>Mindtrip</span>
        <span style={{ color: 'var(--muted)', fontSize: 12 }}>vs</span>
        <span style={{ color: 'var(--wanderboat)' }}>Wanderboat</span>
      </Link>
      <div style={{ display: 'flex', gap: 2, marginLeft: 'auto' }}>
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
