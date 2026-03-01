import { NavLink, useNavigate } from 'react-router-dom'
import { ShieldCheck, LayoutDashboard, Workflow, BarChart3, FileText, MessageSquare, ArrowRight } from 'lucide-react'

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
            background: 'rgba(255,255,255,0.92)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            borderBottom: '1px solid var(--gray-100)',
        }}>
            <div style={{
                maxWidth: '1400px',
                margin: '0 auto',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0 2rem',
                height: '68px',
            }}>
                {/* Logo */}
                <button
                    onClick={() => navigate('/')}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.625rem',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        padding: 0,
                    }}
                >
                    <div style={{
                        width: '38px',
                        height: '38px',
                        borderRadius: 'var(--radius-xl)',
                        background: 'linear-gradient(135deg, var(--brand-start), var(--brand-end))',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: '0 2px 8px rgba(132, 204, 22, 0.25)',
                    }}>
                        <ShieldCheck size={20} color="white" />
                    </div>
                    <span style={{
                        fontFamily: 'var(--font-serif)',
                        fontWeight: 400,
                        fontSize: '1.375rem',
                        color: 'var(--gray-900)',
                        letterSpacing: '-0.01em',
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
                                padding: '0.5rem 1rem',
                                fontSize: '0.8125rem',
                                fontWeight: isActive ? 600 : 500,
                                color: isActive ? 'var(--lime-700)' : 'var(--gray-500)',
                                background: isActive ? 'var(--lime-50)' : 'transparent',
                                borderRadius: 'var(--radius-full)',
                                textDecoration: 'none',
                                transition: 'all 0.2s ease',
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
                    <button className="btn btn-primary btn-sm" onClick={() => navigate('/pipeline')}>
                        Get Started <ArrowRight size={14} />
                    </button>
                </div>
            </div>
        </header>
    )
}
