import { useState, useRef, useEffect } from 'react'
import { Send, Sparkles, FileText, AlertTriangle, ShieldCheck, Clock, User, Bot } from 'lucide-react'

interface ChatMessage {
    role: 'user' | 'assistant'
    content: string
    type?: 'text' | 'summary' | 'codes' | 'issues'
    data?: any
    timestamp: Date
}

const quickActions = [
    { label: 'Summarize last report', icon: FileText },
    { label: 'Show compliance issues', icon: AlertTriangle },
    { label: 'What is NRCeS?', icon: ShieldCheck },
    { label: 'Explain FHIR bundles', icon: Sparkles },
]

// Rule-based responses (no external LLM needed)
function getAssistantResponse(message: string): ChatMessage {
    const lower = message.toLowerCase()

    if (lower.includes('summarize') || lower.includes('summary')) {
        return {
            role: 'assistant', type: 'summary', timestamp: new Date(),
            content: 'Here is the clinical summary from the most recent pipeline run:',
            data: {
                patient: 'Anonymous (Age: 48, Gender: Female)',
                diagnosis: 'Global LV Hypokinesia with LVEF 20-25%, Seasonal Asthma',
                admission: '08-Sep-2022', discharge: '22-Dec-2023',
                facility: 'Department of General Medicine',
                compliance: '63.8 / 100',
                issues: ['Missing ABHA Identifier', 'Missing Insurance Reference'],
            }
        }
    }

    if (lower.includes('compliance') || lower.includes('issues') || lower.includes('validation')) {
        return {
            role: 'assistant', type: 'issues', timestamp: new Date(),
            content: 'The most common NRCeS validation issues I see are:',
            data: [
                { severity: 'ERROR', issue: 'Missing ABHA Identifier', resource: 'Patient', fix: 'Add a valid ABHA number or placeholder (00-0000-0000-0000)' },
                { severity: 'ERROR', issue: 'Missing Insurance Reference', resource: 'Claim.insurance', fix: 'Link a Coverage resource with subscriber details' },
                { severity: 'WARNING', issue: 'Missing Claim Total', resource: 'Claim.total', fix: 'Add a Money value for the total claim amount' },
                { severity: 'INFO', issue: 'No Medication Codes', resource: 'MedicationRequest', fix: 'Map medications to SNOMED CT or RxNorm codes' },
            ]
        }
    }

    if (lower.includes('icd') || lower.includes('codes') || lower.includes('mapping')) {
        return {
            role: 'assistant', type: 'codes', timestamp: new Date(),
            content: 'Here are the ICD-10 codes that were mapped from the clinical data:',
            data: [
                { code: 'I25.5', description: 'Ischemic cardiomyopathy', confidence: '92%' },
                { code: 'I50.9', description: 'Heart failure, unspecified', confidence: '88%' },
                { code: 'J45.20', description: 'Mild intermittent asthma', confidence: '76%' },
            ]
        }
    }

    if (lower.includes('nrces') || lower.includes('profile')) {
        return {
            role: 'assistant', type: 'text', timestamp: new Date(),
            content: '**NRCeS (National Resource Centre for EHR Standards)** defines the FHIR profiles that Indian healthcare systems must follow for interoperability.\n\n' +
                'Key profiles include:\n' +
                '• **ClaimBundle** — For insurance claim submissions via NHCX\n' +
                '• **OPConsultRecord** — For outpatient consultation records\n' +
                '• **DischargeSummaryRecord** — For discharge summaries\n' +
                '• **DiagnosticReportRecord** — For lab and diagnostic reports\n\n' +
                'Aarohan validates against these profiles using the **NRCeS Profile Matrix**, checking for required resources, mandatory fields, and value set bindings.'
        }
    }

    if (lower.includes('fhir') || lower.includes('bundle')) {
        return {
            role: 'assistant', type: 'text', timestamp: new Date(),
            content: '**FHIR Bundles** are the standard container format for exchanging healthcare data in the NHCX ecosystem.\n\n' +
                'A typical ClaimBundle contains:\n' +
                '• **Patient** — Demographics, ABHA ID\n' +
                '• **Organization** — Hospital/facility details\n' +
                '• **Encounter** — Admission/discharge dates, type\n' +
                '• **Condition** — Diagnoses with ICD-10 codes\n' +
                '• **Claim** — Insurance claim with billing details\n' +
                '• **Coverage** — Insurance coverage info\n\n' +
                'Aarohan transforms legacy data into these FHIR R4 resources, validates them, and signs the bundle with JWS RS256 for tamper-proof submission.'
        }
    }

    return {
        role: 'assistant', type: 'text', timestamp: new Date(),
        content: 'I can help you with:\n\n' +
            '• **Summarize reports** — Get clinical summaries of processed documents\n' +
            '• **Compliance issues** — View validation errors and how to fix them\n' +
            '• **ICD-10 codes** — See mapped diagnosis codes\n' +
            '• **NRCeS profiles** — Learn about compliance requirements\n' +
            '• **FHIR bundles** — Understand the output format\n\n' +
            'Try asking "What are the compliance issues?" or "Summarize the last report".'
    }
}

const recentFiles = [
    { name: 'Copy of 97.pdf', score: 63.8, date: 'Just now' },
    { name: 'discharge_01.pdf', score: 78.2, date: '2h ago' },
    { name: 'ecg_report.pdf', score: 55.4, date: '5h ago' },
    { name: 'lab_results.csv', score: 82.1, date: 'Yesterday' },
    { name: 'prescription.pdf', score: 41.5, date: '2 days ago' },
]

export default function AssistantPage() {
    const [messages, setMessages] = useState<ChatMessage[]>([
        {
            role: 'assistant', type: 'text', timestamp: new Date(),
            content: '👋 Hello! I\'m the **Aarohan Clinical Intelligence Assistant**. I can help you understand your processed documents, compliance scores, and FHIR mappings.\n\nWhat would you like to know?'
        }
    ])
    const [input, setInput] = useState('')
    const [isTyping, setIsTyping] = useState(false)
    const bottomRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    const sendMessage = (text?: string) => {
        const msg = text || input.trim()
        if (!msg) return

        const userMsg: ChatMessage = { role: 'user', content: msg, timestamp: new Date() }
        setMessages(prev => [...prev, userMsg])
        setInput('')
        setIsTyping(true)

        setTimeout(() => {
            const response = getAssistantResponse(msg)
            setMessages(prev => [...prev, response])
            setIsTyping(false)
        }, 600 + Math.random() * 800)
    }

    return (
        <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '2rem 1.5rem', display: 'grid', gridTemplateColumns: '1fr 300px', gap: '1.5rem', height: 'calc(100vh - 96px)' }}>

            {/* Main Chat */}
            <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                {/* Header */}
                <div style={{ marginBottom: '1.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                        <div style={{ width: '40px', height: '40px', borderRadius: 'var(--radius-lg)', background: 'linear-gradient(135deg, var(--emerald-500), var(--teal-500))', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <Sparkles size={20} color="white" />
                        </div>
                        <div>
                            <h1 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1.5rem' }}>Clinical Intelligence Assistant</h1>
                            <p style={{ color: 'var(--gray-400)', fontSize: '0.8125rem' }}>Ask questions about your processed documents, FHIR compliance, or get clinical summaries</p>
                        </div>
                    </div>
                </div>

                {/* Chat Messages */}
                <div className="card" style={{ flex: 1, overflow: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                    {messages.map((msg, i) => (
                        <div key={i} style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start', animation: 'fadeInUp 0.3s ease-out' }}>
                            <div style={{
                                width: '32px', height: '32px', borderRadius: '50%', flexShrink: 0,
                                background: msg.role === 'assistant' ? 'linear-gradient(135deg, var(--emerald-500), var(--teal-500))' : 'var(--gray-200)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                            }}>
                                {msg.role === 'assistant' ? <Bot size={16} color="white" /> : <User size={16} color="var(--gray-600)" />}
                            </div>
                            <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ fontSize: '0.6875rem', color: 'var(--gray-400)', marginBottom: '0.375rem' }}>
                                    {msg.role === 'assistant' ? 'Aarohan AI' : 'You'} · {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </div>

                                {/* Text content */}
                                <div style={{ fontSize: '0.875rem', color: 'var(--gray-700)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}
                                    dangerouslySetInnerHTML={{ __html: msg.content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br/>') }}
                                />

                                {/* Summary Card */}
                                {msg.type === 'summary' && msg.data && (
                                    <div style={{ marginTop: '0.75rem', padding: '1rem', background: 'var(--emerald-50)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--emerald-100)' }}>
                                        {Object.entries(msg.data as Record<string, any>).map(([k, v]) => (
                                            <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.375rem 0', borderBottom: '1px solid var(--emerald-100)', fontSize: '0.8125rem' }}>
                                                <span style={{ fontWeight: 600, color: 'var(--emerald-800)', textTransform: 'capitalize' }}>{k.replace(/_/g, ' ')}</span>
                                                <span style={{ color: 'var(--gray-600)', textAlign: 'right', maxWidth: '60%' }}>{Array.isArray(v) ? v.join(', ') : String(v)}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {/* Issues Table */}
                                {msg.type === 'issues' && msg.data && (
                                    <div style={{ marginTop: '0.75rem', overflow: 'auto' }}>
                                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
                                            <thead>
                                                <tr style={{ borderBottom: '2px solid var(--gray-100)' }}>
                                                    {['Severity', 'Issue', 'Resource', 'Fix'].map(h => (
                                                        <th key={h} style={{ textAlign: 'left', padding: '0.5rem', color: 'var(--gray-400)', fontSize: '0.6875rem', textTransform: 'uppercase' }}>{h}</th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {(msg.data as any[]).map((d, j) => (
                                                    <tr key={j} style={{ borderBottom: '1px solid var(--gray-50)' }}>
                                                        <td style={{ padding: '0.5rem' }}>
                                                            <span className={`badge ${d.severity === 'ERROR' ? 'badge-danger' : d.severity === 'WARNING' ? 'badge-warning' : 'badge-info'}`}>
                                                                {d.severity}
                                                            </span>
                                                        </td>
                                                        <td style={{ padding: '0.5rem', fontWeight: 500 }}>{d.issue}</td>
                                                        <td style={{ padding: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--gray-500)' }}>{d.resource}</td>
                                                        <td style={{ padding: '0.5rem', color: 'var(--gray-500)' }}>{d.fix}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}

                                {/* Codes Table */}
                                {msg.type === 'codes' && msg.data && (
                                    <div style={{ marginTop: '0.75rem', overflow: 'auto' }}>
                                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
                                            <thead>
                                                <tr style={{ borderBottom: '2px solid var(--gray-100)' }}>
                                                    {['ICD-10 Code', 'Description', 'Confidence'].map(h => (
                                                        <th key={h} style={{ textAlign: 'left', padding: '0.5rem', color: 'var(--gray-400)', fontSize: '0.6875rem', textTransform: 'uppercase' }}>{h}</th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {(msg.data as any[]).map((d, j) => (
                                                    <tr key={j} style={{ borderBottom: '1px solid var(--gray-50)' }}>
                                                        <td style={{ padding: '0.5rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--emerald-700)' }}>{d.code}</td>
                                                        <td style={{ padding: '0.5rem' }}>{d.description}</td>
                                                        <td style={{ padding: '0.5rem' }}>
                                                            <span className="badge badge-success">{d.confidence}</span>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {isTyping && (
                        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                            <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'linear-gradient(135deg, var(--emerald-500), var(--teal-500))', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <Bot size={16} color="white" />
                            </div>
                            <div style={{ display: 'flex', gap: '4px', padding: '0.75rem 1rem', background: 'var(--gray-50)', borderRadius: '12px' }}>
                                {[0, 1, 2].map(i => (
                                    <div key={i} style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--gray-300)', animation: `pulse-glow 1.4s infinite ${i * 0.2}s` }} />
                                ))}
                            </div>
                        </div>
                    )}
                    <div ref={bottomRef} />
                </div>

                {/* Quick Actions */}
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
                    {quickActions.map(({ label, icon: Icon }) => (
                        <button key={label} className="btn btn-ghost" onClick={() => sendMessage(label)} style={{
                            fontSize: '0.75rem', padding: '0.5rem 0.75rem', border: '1px solid var(--gray-100)',
                            borderRadius: 'var(--radius-full)', color: 'var(--gray-500)',
                        }}>
                            <Icon size={12} /> {label}
                        </button>
                    ))}
                </div>

                {/* Input */}
                <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.75rem' }}>
                    <input
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && sendMessage()}
                        placeholder="Ask about your documents, compliance, or FHIR mappings..."
                        style={{
                            flex: 1, padding: '0.875rem 1.25rem', borderRadius: 'var(--radius-xl)',
                            border: '1px solid var(--gray-200)', fontSize: '0.875rem',
                            outline: 'none', background: 'white', fontFamily: 'var(--font-sans)',
                        }}
                    />
                    <button className="btn btn-primary" onClick={() => sendMessage()} style={{ borderRadius: 'var(--radius-xl)' }}>
                        <Send size={18} />
                    </button>
                </div>
            </div>

            {/* Right Sidebar: Processing History */}
            <div>
                <div className="card" style={{ position: 'sticky', top: '80px' }}>
                    <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '0.9375rem', marginBottom: '1rem' }}>Processing History</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        {recentFiles.map((f, i) => (
                            <div key={i} style={{ padding: '0.75rem', background: 'var(--gray-50)', borderRadius: 'var(--radius-lg)', cursor: 'pointer', transition: 'all 0.15s ease' }}
                                onMouseEnter={e => (e.currentTarget.style.background = 'var(--emerald-50)')}
                                onMouseLeave={e => (e.currentTarget.style.background = 'var(--gray-50)')}
                                onClick={() => sendMessage(`Summarize ${f.name}`)}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                                    <FileText size={14} color="var(--gray-400)" />
                                    <span style={{ fontSize: '0.8125rem', fontWeight: 500, color: 'var(--gray-700)' }}>{f.name}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <span style={{ fontSize: '0.6875rem', color: 'var(--gray-400)' }}>
                                        <Clock size={10} style={{ verticalAlign: 'middle', marginRight: '2px' }} /> {f.date}
                                    </span>
                                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: f.score >= 70 ? 'var(--emerald-600)' : f.score >= 50 ? 'var(--warning)' : 'var(--danger)' }}>
                                        {f.score}%
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
}
