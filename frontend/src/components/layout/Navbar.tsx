import { NavLink, useNavigate } from 'react-router-dom'
import { ShieldCheck, LayoutDashboard, Workflow, BarChart3, FileText, MessageSquare } from 'lucide-react'

const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/pipeline', label: 'Pipeline', icon: Workflow },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/reports', label: 'Reports', icon: FileText },
    { to: '/assistant', label: 'AI Assistant', icon: MessageSquare },
]

export default function Navbar() {
    const navigate = useNavigate()

    return (
        <header style={{
            position: 'sticky',
            top: 0,
            zIndex: 50,
            background: 'rgba(255,255,255,0.85)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            borderBottom: '1px solid var(--gray-100)',
            boxShadow: 'var(--shadow-sm)',
        }}>
            <div style={{
                maxWidth: '1400px',
                margin: '0 auto',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0 1.5rem',
                height: '64px',
            }}>
                {/* Logo */}
                <button
                    onClick={() => navigate('/')}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        padding: 0,
                    }}
                >
                    <div style={{
                        width: '36px',
                        height: '36px',
                        borderRadius: 'var(--radius-lg)',
                        background: 'linear-gradient(135deg, var(--emerald-600), var(--teal-500))',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                    }}>
                        <ShieldCheck size={20} color="white" />
                    </div>
                    <span style={{
                        fontFamily: 'var(--font-display)',
                        fontWeight: 700,
                        fontSize: '1.25rem',
                        color: 'var(--gray-900)',
                    }}>
                        Aarohan
                    </span>
                </button>

                {/* Nav Links */}
                <nav style={{ display: 'flex', gap: '0.25rem' }}>
                    {navItems.map(({ to, label, icon: Icon }) => (
                        <NavLink
                            key={to}
                            to={to}
                            style={({ isActive }) => ({
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.375rem',
                                padding: '0.5rem 0.875rem',
                                fontSize: '0.8125rem',
                                fontWeight: isActive ? 600 : 500,
                                color: isActive ? 'var(--emerald-700)' : 'var(--gray-500)',
                                background: isActive ? 'var(--emerald-50)' : 'transparent',
                                borderRadius: 'var(--radius-lg)',
                                textDecoration: 'none',
                                transition: 'all 0.15s ease',
                            })}
                        >
                            <Icon size={16} />
                            {label}
                        </NavLink>
                    ))}
                </nav>

                {/* Right Side */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span className="badge badge-success" style={{ fontSize: '0.65rem' }}>
                        <span className="status-dot status-dot-success" style={{ marginRight: '4px' }} />
                        System Online
                    </span>
                </div>
            </div>
        </header>
    )
}
