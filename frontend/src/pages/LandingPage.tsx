import { ShieldCheck, ArrowRight, FileUp, Zap, Brain, Lock, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

const trustBadges = ['NRCeS Compliant', 'FHIR R4', 'ABDM Ready', 'JWS Signed']

const stats = [
    { value: <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', flexWrap: 'nowrap' }}><span style={{ fontSize: '1.50rem' }}>63%</span><ArrowRight size={20} color="var(--emerald-400)" strokeWidth={3} /><span style={{ fontSize: '1.75rem' }}>95%</span></div>, label: 'Avg Compliance Lift' },
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
        <div style={{ overflow: 'hidden' }}>
            {/* ─── Hero ──────────────────────────────────────────────── */}
            <section style={{
                position: 'relative',
                minHeight: '90vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'linear-gradient(160deg, var(--emerald-950) 0%, var(--emerald-800) 40%, #0d4f4f 100%)',
                overflow: 'hidden',
            }}>
                {/* Abstract bg shapes */}
                <div style={{ position: 'absolute', top: '-10%', right: '-5%', width: '600px', height: '600px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(16,185,129,0.15), transparent 70%)', filter: 'blur(60px)' }} />
                <div style={{ position: 'absolute', bottom: '-10%', left: '-5%', width: '500px', height: '500px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(45,212,191,0.12), transparent 70%)', filter: 'blur(60px)' }} />

                <div style={{ position: 'relative', zIndex: 1, maxWidth: '900px', textAlign: 'center', padding: '4rem 2rem' }}>
                    <div className="animate-fade-in-up" style={{ marginBottom: '1.5rem' }}>
                        <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.5rem 1rem',
                            background: 'rgba(16,185,129,0.15)',
                            border: '1px solid rgba(16,185,129,0.3)',
                            borderRadius: 'var(--radius-full)',
                            color: 'var(--emerald-300)',
                            fontSize: '0.8125rem',
                            fontWeight: 600,
                        }}>
                            <Sparkles size={14} /> Built for India's 1.4 Billion Citizens
                        </span>
                    </div>

                    <h1 className="text-hero animate-fade-in-up delay-100" style={{ color: 'white', marginBottom: '1.5rem' }}>
                        Transform Legacy Healthcare Data into{' '}
                        <span style={{ color: 'var(--emerald-400)' }}>NHCX-Ready</span>{' '}
                        FHIR Bundles
                    </h1>

                    <p className="animate-fade-in-up delay-200" style={{ fontSize: '1.2rem', color: 'rgba(255,255,255,0.7)', maxWidth: '700px', margin: '0 auto 2.5rem', lineHeight: 1.7 }}>
                        India's first AI-powered compliance intelligence platform for hospitals, insurers, and TPAs.
                        From scanned PDFs to signed FHIR bundles in under 500ms.
                    </p>

                    <div className="animate-fade-in-up delay-300" style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginBottom: '3rem' }}>
                        <button className="btn btn-primary btn-lg" onClick={() => navigate('/pipeline')}>
                            Launch Pipeline <ArrowRight size={18} />
                        </button>
                        <button className="btn btn-outline btn-lg" style={{ color: 'rgba(255,255,255,0.9)', borderColor: 'rgba(255,255,255,0.25)' }} onClick={() => navigate('/dashboard')}>
                            View Dashboard
                        </button>
                    </div>

                    {/* Trust Badges */}
                    <div className="animate-fade-in-up delay-400" style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                        {trustBadges.map(b => (
                            <span key={b} style={{
                                padding: '0.375rem 0.875rem',
                                borderRadius: 'var(--radius-full)',
                                background: 'rgba(255,255,255,0.08)',
                                border: '1px solid rgba(255,255,255,0.15)',
                                color: 'rgba(255,255,255,0.8)',
                                fontSize: '0.75rem',
                                fontWeight: 600,
                                letterSpacing: '0.02em',
                            }}>
                                ✓ {b}
                            </span>
                        ))}
                    </div>
                </div>
            </section>

            {/* ─── Stats Banner ───────────────────────────────────────── */}
            <section style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                maxWidth: '1200px',
                margin: '-3rem auto 0',
                position: 'relative',
                zIndex: 2,
                padding: '0 2rem',
            }}>
                {stats.map((s, i) => (
                    <div key={i} className="card animate-fade-in-up" style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        textAlign: 'center',
                        padding: '2rem 1.5rem',
                        margin: '0 0.5rem',
                        animationDelay: `${i * 100}ms`,
                    }}>
                        <div className="text-kpi gradient-text" style={{ marginBottom: '0.5rem' }}>{s.value}</div>
                        <div style={{ fontSize: '0.875rem', color: 'var(--gray-500)', fontWeight: 500 }}>{s.label}</div>
                    </div>
                ))}
            </section>

            {/* ─── How It Works ───────────────────────────────────────── */}
            <section style={{ maxWidth: '1200px', margin: '0 auto', padding: '6rem 2rem' }}>
                <h2 className="text-section-title" style={{ textAlign: 'center', marginBottom: '0.75rem' }}>
                    How It Works
                </h2>
                <p style={{ textAlign: 'center', color: 'var(--gray-500)', marginBottom: '4rem', fontSize: '1.1rem' }}>
                    Three steps from legacy chaos to NHCX compliance.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '2rem', position: 'relative' }}>
                    {steps.map((step, i) => (
                        <div key={i} className="card animate-fade-in-up" style={{
                            textAlign: 'center',
                            padding: '2.5rem 2rem',
                            position: 'relative',
                            animationDelay: `${i * 150}ms`,
                        }}>
                            <div style={{
                                width: '56px',
                                height: '56px',
                                borderRadius: 'var(--radius-xl)',
                                background: 'linear-gradient(135deg, var(--emerald-100), var(--emerald-50))',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                margin: '0 auto 1.25rem',
                                fontFamily: 'var(--font-display)',
                                fontWeight: 800,
                                fontSize: '1.25rem',
                                color: 'var(--emerald-700)',
                            }}>
                                {step.num}
                            </div>
                            <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1.25rem', marginBottom: '0.75rem', color: 'var(--gray-900)' }}>
                                {step.title}
                            </h3>
                            <p style={{ color: 'var(--gray-500)', fontSize: '0.9375rem', lineHeight: 1.6 }}>
                                {step.desc}
                            </p>
                        </div>
                    ))}
                </div>
            </section>

            {/* ─── Features Grid ──────────────────────────────────────── */}
            <section style={{ background: 'var(--gray-50)', padding: '6rem 2rem' }}>
                <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                    <h2 className="text-section-title" style={{ textAlign: 'center', marginBottom: '0.75rem' }}>
                        Platform Capabilities
                    </h2>
                    <p style={{ textAlign: 'center', color: 'var(--gray-500)', marginBottom: '4rem', fontSize: '1.1rem' }}>
                        Enterprise-grade intelligence for every stage of the compliance journey.
                    </p>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem' }}>
                        {features.map(({ icon: Icon, title, desc }, i) => (
                            <div key={i} className="card animate-fade-in-up" style={{
                                padding: '2rem',
                                animationDelay: `${i * 100}ms`,
                            }}>
                                <div style={{
                                    width: '48px',
                                    height: '48px',
                                    borderRadius: 'var(--radius-lg)',
                                    background: 'linear-gradient(135deg, var(--emerald-100), var(--emerald-50))',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    marginBottom: '1rem',
                                }}>
                                    <Icon size={22} color="var(--emerald-600)" />
                                </div>
                                <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1.1rem', marginBottom: '0.5rem', color: 'var(--gray-900)' }}>
                                    {title}
                                </h3>
                                <p style={{ color: 'var(--gray-500)', fontSize: '0.875rem', lineHeight: 1.6 }}>
                                    {desc}
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ─── CTA Footer ─────────────────────────────────────────── */}
            <section style={{
                background: 'linear-gradient(160deg, var(--emerald-950), var(--emerald-800))',
                padding: '5rem 2rem',
                textAlign: 'center',
            }}>
                <h2 style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: '2.25rem', color: 'white', marginBottom: '1rem' }}>
                    Ready to transform your healthcare data?
                </h2>
                <p style={{ color: 'rgba(255,255,255,0.65)', fontSize: '1.1rem', maxWidth: '600px', margin: '0 auto 2.5rem' }}>
                    Join hospitals and insurers across India in building a compliant, interoperable healthcare ecosystem.
                </p>
                <button className="btn btn-primary btn-lg" onClick={() => navigate('/pipeline')}>
                    Get Started Now <ArrowRight size={18} />
                </button>
            </section>

            {/* ─── Footer ─────────────────────────────────────────────── */}
            <footer style={{
                background: 'var(--gray-950)',
                padding: '2rem',
                textAlign: 'center',
                color: 'var(--gray-500)',
                fontSize: '0.8125rem',
            }}>
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <ShieldCheck size={16} color="var(--emerald-500)" />
                    <span style={{ fontWeight: 600, color: 'var(--gray-400)' }}>Aarohan</span>
                </div>
                NHCX Compliance Intelligence Platform · Built for India's Healthcare Future
            </footer>
        </div>
    )
}
