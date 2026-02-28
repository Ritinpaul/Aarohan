import { ShieldCheck, ArrowRight, FileUp, Zap, Brain, Lock, Sparkles, Play, Check, LayoutDashboard, Workflow, BarChart3, FileText, MessageSquare } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

const trustBadges = ['NRCeS Compliant', 'FHIR R4', 'ABDM Ready', 'JWS Signed']

const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/pipeline', label: 'Pipeline', icon: Workflow },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/reports', label: 'Reports', icon: FileText },
    { to: '/assistant', label: 'AI Assistant', icon: MessageSquare },
]

const stats = [
    { value: <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', flexWrap: 'nowrap' }}><span style={{ fontSize: '1.50rem' }}>63%</span><ArrowRight size={20} color="var(--lime-500)" strokeWidth={3} /><span style={{ fontSize: '1.75rem' }}>95%</span></div>, label: 'Avg Compliance Lift' },
    { value: '7-Stage', label: 'Processing Pipeline' },
    { value: '3-Layer', label: 'OCR & Parser Engine' },
    { value: '< 500ms', label: 'Average Processing Time' },
]

const features = [
    { icon: FileUp, title: 'Multimodal Parser', desc: 'Parse PDFs, CSVs, HL7v2, and XML — with 3-layer OCR for scanned documents.' },
    { icon: Brain, title: 'Context-Aware Intelligence', desc: 'Auto-detects hospital tier, geographic state, and applicable health schemes.' },
    { icon: ShieldCheck, title: 'NRCeS Profile Validator', desc: 'Validates FHIR bundles against NRCeS profile constraints in real-time.' },
    { icon: Sparkles, title: 'Resilience Healer', desc: 'Auto-fixes compliance gaps — ABHA placeholders, date normalization, code mapping.' },
    { icon: Lock, title: 'JWS Signing & Audit Trail', desc: 'RS256 signed bundles with full pipeline audit trail for compliance proof.' },
    { icon: Zap, title: 'AI Clinical Summarizer', desc: 'Chat-based assistant for document Q&A, ICD-10 lookups, and compliance reports.' },
]

const steps = [
    { num: '01', title: 'Upload', desc: 'Drop any legacy healthcare document — PDF, CSV, HL7v2, or XML.' },
    { num: '02', title: 'Intelligent Processing', desc: '7-stage pipeline parses, heals, maps codes, and generates FHIR bundles.' },
    { num: '03', title: 'NHCX-Ready Output', desc: 'Validated, signed FHIR R4 bundle ready for NHCX network submission.' },
]

export default function LandingPage() {
    const navigate = useNavigate()

    return (
        <div style={{ overflow: 'hidden', background: '#ffffff' }}>

            {/* ─── Sticky Nav ──────────────────────────────────────────── */}
            <header style={{
                position: 'sticky', top: 0, zIndex: 50,
                background: 'rgba(255,255,255,0.92)',
                backdropFilter: 'blur(20px)',
                WebkitBackdropFilter: 'blur(20px)',
                borderBottom: '1px solid var(--gray-100)',
            }}>
                <div style={{
                    maxWidth: '1200px', margin: '0 auto',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '0 2rem', height: '68px',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                        <div style={{
                            width: '36px', height: '36px', borderRadius: 'var(--radius-xl)',
                            background: 'linear-gradient(135deg, var(--brand-start), var(--brand-end))',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            boxShadow: '0 2px 8px rgba(132,204,22,0.25)',
                        }}>
                            <ShieldCheck size={18} color="white" />
                        </div>
                        <span style={{ fontFamily: 'var(--font-serif)', fontSize: '1.375rem', color: 'var(--gray-900)' }}>Aarohan</span>
                    </div>

                    <nav style={{ display: 'flex', gap: '0.25rem' }}>
                        {navItems.map(({ to, label, icon: Icon }) => (
                            <button
                                key={to}
                                onClick={() => navigate(to)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.375rem',
                                    padding: '0.5rem 1rem',
                                    fontSize: '0.8125rem',
                                    fontWeight: 500,
                                    color: 'var(--gray-500)',
                                    background: 'transparent',
                                    border: 'none',
                                    borderRadius: 'var(--radius-full)',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s ease',
                                }}
                            >
                                <Icon size={16} />
                                {label}
                            </button>
                        ))}
                    </nav>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span className="badge badge-success" style={{ fontSize: '0.65rem' }}>
                            <span className="status-dot status-dot-success" style={{ marginRight: '4px' }} />
                            System Online
                        </span>
                        <button className="btn btn-primary" onClick={() => navigate('/pipeline')}>
                            Get Started <ArrowRight size={14} />
                        </button>
                    </div>
                </div>
            </header>

            {/* ─── Hero ──────────────────────────────────────────────── */}
            <section style={{
                maxWidth: '1200px', margin: '0 auto',
                padding: '5rem 2rem 4rem',
                display: 'grid', gridTemplateColumns: '1fr 1fr',
                gap: '4rem', alignItems: 'center',
            }}>
                {/* Left */}
                <div>
                    <div className="animate-fade-in-up" style={{ marginBottom: '1.5rem' }}>
                        <span className="pill pill-green" style={{ fontSize: '0.8125rem' }}>
                            <Sparkles size={14} /> Built for India's 1.4 Billion Citizens
                        </span>
                    </div>

                    <h1 className="text-hero animate-fade-in-up delay-100" style={{ marginBottom: '1.5rem' }}>
                        Your Partner in Smarter{' '}
                        <span style={{
                            fontStyle: 'italic',
                            background: 'linear-gradient(135deg, var(--brand-start), var(--brand-end))',
                            WebkitBackgroundClip: 'text',
                            WebkitTextFillColor: 'transparent',
                            backgroundClip: 'text',
                        }}>Healthcare Compliance</span>
                    </h1>

                    <p className="animate-fade-in-up delay-200" style={{
                        fontSize: '1.125rem', color: 'var(--gray-500)',
                        maxWidth: '520px', lineHeight: 1.7, marginBottom: '2rem',
                    }}>
                        Transform legacy healthcare data into NHCX-compliant FHIR bundles — automatically.
                        From scanned PDFs to signed bundles in under 500ms.
                    </p>

                    <div className="animate-fade-in-up delay-300" style={{ display: 'flex', gap: '0.75rem', marginBottom: '2.5rem' }}>
                        <button className="btn btn-dark btn-lg" onClick={() => navigate('/pipeline')}>
                            Launch Pipeline <ArrowRight size={18} />
                        </button>
                        <button className="btn btn-outline btn-lg" onClick={() => navigate('/dashboard')}>
                            <Play size={16} fill="var(--gray-500)" /> Watch Demo
                        </button>
                    </div>

                    {/* Trust pills */}
                    <div className="animate-fade-in-up delay-400" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        {trustBadges.map(b => (
                            <span key={b} className="pill pill-outline" style={{ fontSize: '0.75rem' }}>
                                <Check size={12} color="var(--lime-500)" strokeWidth={3} /> {b}
                            </span>
                        ))}
                    </div>
                </div>

                {/* Right — Abstract green card stack */}
                <div className="animate-fade-in-up delay-200" style={{ position: 'relative', display: 'flex', justifyContent: 'center' }}>
                    {/* Background glow */}
                    <div style={{
                        position: 'absolute', top: '50%', left: '50%',
                        transform: 'translate(-50%,-50%)',
                        width: '400px', height: '400px', borderRadius: '50%',
                        background: 'radial-gradient(circle, rgba(132,204,22,0.12), transparent 70%)',
                        filter: 'blur(40px)',
                    }} />

                    {/* Main card */}
                    <div style={{
                        position: 'relative', zIndex: 2,
                        background: 'linear-gradient(160deg, #d4f7a8 0%, #b5f061 50%, #84cc16 100%)',
                        borderRadius: '24px', padding: '2rem',
                        width: '360px', minHeight: '380px',
                        boxShadow: '0 20px 60px -12px rgba(132,204,22,0.3)',
                        display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
                    }}>
                        <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
                                <ShieldCheck size={20} color="var(--green-900)" />
                                <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '0.875rem', color: 'var(--green-900)' }}>
                                    NHCX Compliance Score
                                </span>
                            </div>

                            <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
                                <div style={{
                                    fontFamily: 'var(--font-display)', fontWeight: 800,
                                    fontSize: '4rem', color: 'var(--green-900)',
                                    lineHeight: 1,
                                }}>
                                    95.4
                                </div>
                                <div style={{ fontSize: '0.875rem', color: 'var(--green-800)', fontWeight: 500, marginTop: '0.5rem' }}>
                                    out of 100 · Passed
                                </div>
                            </div>
                        </div>

                        <div style={{
                            background: 'rgba(255,255,255,0.5)', borderRadius: '16px',
                            padding: '1rem', backdropFilter: 'blur(10px)',
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--green-800)' }}>Structural</span>
                                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--green-900)' }}>98%</span>
                            </div>
                            <div style={{ height: '6px', borderRadius: '3px', background: 'rgba(255,255,255,0.6)', marginBottom: '0.75rem' }}>
                                <div style={{ width: '98%', height: '100%', borderRadius: '3px', background: 'var(--green-700)' }} />
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--green-800)' }}>Terminology</span>
                                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--green-900)' }}>92%</span>
                            </div>
                            <div style={{ height: '6px', borderRadius: '3px', background: 'rgba(255,255,255,0.6)' }}>
                                <div style={{ width: '92%', height: '100%', borderRadius: '3px', background: 'var(--green-700)' }} />
                            </div>
                        </div>
                    </div>

                    {/* Floating mini card — top right */}
                    <div className="animate-float" style={{
                        position: 'absolute', top: '-10px', right: '10px', zIndex: 3,
                        background: 'white', borderRadius: '16px', padding: '0.875rem 1.25rem',
                        boxShadow: '0 8px 30px rgba(0,0,0,0.08)', border: '1px solid var(--gray-100)',
                    }}>
                        <div style={{ fontSize: '0.6875rem', color: 'var(--gray-400)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Processing</div>
                        <div style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: '1.25rem', color: 'var(--lime-600)' }}>
                            &lt; 500ms
                        </div>
                    </div>

                    {/* Floating mini card — bottom left */}
                    <div className="animate-float delay-300" style={{
                        position: 'absolute', bottom: '20px', left: '-10px', zIndex: 3,
                        background: 'white', borderRadius: '16px', padding: '0.875rem 1.25rem',
                        boxShadow: '0 8px 30px rgba(0,0,0,0.08)', border: '1px solid var(--gray-100)',
                    }}>
                        <div style={{ fontSize: '0.6875rem', color: 'var(--gray-400)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Formats</div>
                        <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '0.8125rem', color: 'var(--gray-700)', display: 'flex', gap: '0.375rem', marginTop: '0.25rem' }}>
                            {['PDF', 'CSV', 'HL7', 'XML'].map(f => (
                                <span key={f} style={{
                                    padding: '0.2rem 0.5rem', borderRadius: '6px',
                                    background: 'var(--lime-50)', color: 'var(--lime-700)',
                                    fontSize: '0.6875rem', fontWeight: 700,
                                }}>{f}</span>
                            ))}
                        </div>
                    </div>
                </div>
            </section>

            {/* ─── Stats Banner ───────────────────────────────────────── */}
            <section style={{
                background: 'var(--gray-50)',
                borderTop: '1px solid var(--gray-100)',
                borderBottom: '1px solid var(--gray-100)',
            }}>
                <div style={{
                    display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
                    maxWidth: '1200px', margin: '0 auto',
                    padding: '2.5rem 2rem',
                }}>
                    {stats.map((s, i) => (
                        <div key={i} className="animate-fade-in-up" style={{
                            display: 'flex', flexDirection: 'column',
                            alignItems: 'center', justifyContent: 'center', textAlign: 'center',
                            padding: '0 1.5rem',
                            borderRight: i < 3 ? '1px solid var(--gray-200)' : 'none',
                            animationDelay: `${i * 100}ms`,
                        }}>
                            <div className="text-kpi gradient-text" style={{ marginBottom: '0.5rem' }}>{s.value}</div>
                            <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)', fontWeight: 500 }}>{s.label}</div>
                        </div>
                    ))}
                </div>
            </section>

            {/* ─── Features Section ─────────────────────────────────── */}
            <section id="features" style={{ maxWidth: '1200px', margin: '0 auto', padding: '6rem 2rem' }}>
                <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
                    <span className="pill pill-green" style={{ fontSize: '0.75rem' }}>Features</span>
                </div>
                <div style={{ textAlign: 'center', maxWidth: '800px', margin: '0 auto 4rem' }}>
                    <h2 style={{
                        fontFamily: 'var(--font-serif)', fontSize: 'clamp(1.75rem, 3.5vw, 2.5rem)',
                        lineHeight: 1.3, color: 'var(--gray-900)', marginBottom: '1rem',
                    }}>
                        Achieve <span style={{ fontWeight: 700, fontStyle: 'italic' }}>compliance clarity</span> and take control of your healthcare data with tools designed to simplify and{' '}
                        <span style={{ fontWeight: 700, fontStyle: 'italic' }}>automate everything</span>.
                    </h2>
                    <p style={{ color: 'var(--gray-400)', fontSize: '0.9375rem' }}>
                        Everything you need, nothing you don't.
                    </p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem' }}>
                    {features.map(({ icon: Icon, title, desc }, i) => (
                        <div key={i} className="card-green-soft animate-fade-in-up" style={{
                            animationDelay: `${i * 100}ms`,
                        }}>
                            <div style={{
                                width: '52px', height: '52px', borderRadius: 'var(--radius-xl)',
                                background: 'rgba(255,255,255,0.7)', backdropFilter: 'blur(8px)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                marginBottom: '1.25rem',
                                boxShadow: '0 2px 8px rgba(132,204,22,0.1)',
                            }}>
                                <Icon size={24} color="var(--lime-700)" />
                            </div>
                            <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1.1rem', marginBottom: '0.625rem', color: 'var(--green-900)' }}>
                                {title}
                            </h3>
                            <p style={{ color: 'var(--green-800)', fontSize: '0.875rem', lineHeight: 1.6, opacity: 0.8 }}>
                                {desc}
                            </p>
                        </div>
                    ))}
                </div>
            </section>

            {/* ─── How It Works ───────────────────────────────────────── */}
            <section id="how-it-works" style={{
                background: 'var(--gray-50)', borderTop: '1px solid var(--gray-100)',
                padding: '6rem 2rem',
            }}>
                <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4rem', alignItems: 'center' }}>

                        {/* Left — Info Card */}
                        <div className="animate-fade-in-up">
                            <div style={{
                                background: 'linear-gradient(160deg, #1a2e05 0%, #14532d 50%, #166534 100%)',
                                borderRadius: '28px', padding: '2.5rem',
                                color: 'white', position: 'relative', overflow: 'hidden',
                                boxShadow: '0 25px 60px -12px rgba(0,0,0,0.3)',
                            }}>
                                {/* Background pattern */}
                                <div style={{
                                    position: 'absolute', top: '-20%', right: '-10%',
                                    width: '300px', height: '300px', borderRadius: '50%',
                                    background: 'radial-gradient(circle, rgba(132,204,22,0.15), transparent 70%)',
                                }} />

                                <div style={{ position: 'relative', zIndex: 1 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
                                        <ShieldCheck size={18} color="var(--lime-400)" />
                                        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--lime-300)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                            Pipeline Status
                                        </span>
                                    </div>

                                    <div style={{
                                        fontFamily: 'var(--font-display)', fontWeight: 800,
                                        fontSize: '3rem', marginBottom: '0.5rem',
                                    }}>
                                        7 Stages
                                    </div>
                                    <div style={{ fontSize: '1rem', color: 'rgba(255,255,255,0.6)', marginBottom: '2rem' }}>
                                        Complete processing pipeline
                                    </div>

                                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                                        {['Parse', 'Context', 'Score', 'Heal', 'Bundle', 'Validate', 'Sign'].map((s, i) => (
                                            <span key={s} style={{
                                                padding: '0.375rem 0.75rem', borderRadius: 'var(--radius-full)',
                                                background: i < 5 ? 'rgba(132,204,22,0.2)' : 'rgba(255,255,255,0.1)',
                                                color: i < 5 ? 'var(--lime-300)' : 'rgba(255,255,255,0.5)',
                                                fontSize: '0.6875rem', fontWeight: 600,
                                            }}>{s}</span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Right — Steps */}
                        <div>
                            <h2 className="text-section-title animate-fade-in-up" style={{ marginBottom: '1rem' }}>
                                Transform Your Data in 3 Easy Steps
                            </h2>
                            <p className="animate-fade-in-up delay-100" style={{ color: 'var(--gray-500)', fontSize: '1rem', marginBottom: '2.5rem', lineHeight: 1.7 }}>
                                Three steps from legacy chaos to NHCX compliance.
                            </p>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                                {steps.map((step, i) => (
                                    <div key={i} className="animate-fade-in-up" style={{
                                        display: 'flex', gap: '1rem', alignItems: 'flex-start',
                                        animationDelay: `${(i + 2) * 100}ms`,
                                    }}>
                                        <div style={{
                                            width: '44px', height: '44px', borderRadius: '50%',
                                            background: 'linear-gradient(135deg, var(--lime-100), var(--lime-50))',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            fontFamily: 'var(--font-display)', fontWeight: 800,
                                            fontSize: '0.875rem', color: 'var(--lime-700)',
                                            flexShrink: 0, border: '2px solid var(--lime-200)',
                                        }}>
                                            {step.num}
                                        </div>
                                        <div>
                                            <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1.125rem', marginBottom: '0.375rem', color: 'var(--gray-900)' }}>
                                                {step.title}
                                            </h3>
                                            <p style={{ color: 'var(--gray-500)', fontSize: '0.875rem', lineHeight: 1.6 }}>
                                                {step.desc}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* ─── CTA Footer ─────────────────────────────────────────── */}
            <section style={{
                background: 'linear-gradient(160deg, #1a2e05 0%, #14532d 50%, #166534 100%)',
                padding: '5rem 2rem',
                textAlign: 'center',
                position: 'relative', overflow: 'hidden',
            }}>
                <div style={{
                    position: 'absolute', top: '50%', left: '50%',
                    transform: 'translate(-50%,-50%)',
                    width: '600px', height: '600px', borderRadius: '50%',
                    background: 'radial-gradient(circle, rgba(132,204,22,0.1), transparent 70%)',
                }} />
                <div style={{ position: 'relative', zIndex: 1 }}>
                    <h2 style={{ fontFamily: 'var(--font-serif)', fontWeight: 400, fontSize: '2.5rem', color: 'white', marginBottom: '1rem' }}>
                        Ready to transform your healthcare data?
                    </h2>
                    <p style={{ color: 'rgba(255,255,255,0.55)', fontSize: '1.1rem', maxWidth: '600px', margin: '0 auto 2.5rem' }}>
                        Join hospitals and insurers across India in building a compliant, interoperable healthcare ecosystem.
                    </p>
                    <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem' }}>
                        <button className="btn btn-primary btn-lg" onClick={() => navigate('/pipeline')}>
                            Get Started Now <ArrowRight size={18} />
                        </button>
                        <button className="btn btn-lg" style={{
                            background: 'rgba(255,255,255,0.1)', color: 'white',
                            border: '1px solid rgba(255,255,255,0.2)',
                        }} onClick={() => navigate('/dashboard')}>
                            View Dashboard
                        </button>
                    </div>
                    <p style={{ fontSize: '0.8125rem', color: 'rgba(255,255,255,0.35)', marginTop: '1.5rem' }}>
                        Try it free. Upgrade anytime.
                    </p>
                </div>
            </section>

            {/* ─── Footer ─────────────────────────────────────────────── */}
            <footer style={{
                background: 'var(--gray-950)',
                padding: '2.5rem 2rem',
                textAlign: 'center',
                color: 'var(--gray-500)',
                fontSize: '0.8125rem',
            }}>
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <ShieldCheck size={16} color="var(--lime-500)" />
                    <span style={{ fontFamily: 'var(--font-serif)', fontWeight: 400, color: 'var(--gray-300)', fontSize: '1.125rem' }}>Aarohan</span>
                </div>
                NHCX Compliance Intelligence Platform · Built for India's Healthcare Future
            </footer>
        </div>
    )
}
