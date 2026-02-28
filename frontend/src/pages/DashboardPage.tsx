import { useEffect, useState } from 'react'
import { FileText, TrendingUp, ShieldCheck, Activity, ArrowRight, Clock } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid } from 'recharts'
import axios from 'axios'

interface AuditEntry {
    id: string; run_id: string; timestamp: string; source_file: string;
    format: string; success: boolean; score_before: number; score_after: number;
    score_delta: number; total_ms: number; error: string | null;
}

interface EvalReport {
    filename: string;
    timestamp: string;
    total_documents: number;
    success_rate: number;
    avg_score_before: number;
    avg_score_after: number;
    avg_lift: number;
}

interface Stats {
    total: number; success: number; failed: number; success_rate: number;
    avg_score_lift: number; avg_processing_ms: number; formats: Record<string, number>;
}

// Generate demo data when no real runs exist
function getDemoData() {
    const files = [
        'discharge_summary_01.pdf', 'ecg_report_042.pdf', 'lab_results.csv',
        'prescription_3321.pdf', 'ophthalmology_report.pdf', 'radiology_ct.pdf',
        'cardiology_echo.pdf', 'patient_intake_form.xml',
    ]
    const runs: AuditEntry[] = files.map((f, i) => ({
        id: `demo-${i}`, run_id: `run-${i}`, source_file: f,
        timestamp: new Date(Date.now() - i * 3600000 * 3).toISOString(),
        format: f.endsWith('.csv') ? 'csv' : f.endsWith('.xml') ? 'xml' : 'pdf',
        success: Math.random() > 0.15,
        score_before: 20 + Math.random() * 40,
        score_after: 55 + Math.random() * 40,
        score_delta: 15 + Math.random() * 25,
        total_ms: 200 + Math.random() * 800,
        error: null,
    }))
    const stats: Stats = {
        total: runs.length, success: runs.filter(r => r.success).length,
        failed: runs.filter(r => !r.success).length,
        success_rate: 0.875, avg_score_lift: 22.3, avg_processing_ms: 458,
        formats: { pdf: 6, csv: 1, xml: 1 },
    }
    return { runs, stats }
}

export default function DashboardPage() {
    const navigate = useNavigate()
    const [runs, setRuns] = useState<AuditEntry[]>([])
    const [stats, setStats] = useState<Stats | null>(null)
    const [reports, setReports] = useState<EvalReport[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        axios.get('/api/v1/pipeline/audit?n=20')
            .then(res => {
                const data = res.data
                if (data.recent_runs && data.recent_runs.length > 0) {
                    setRuns(data.recent_runs)
                    setStats(data.stats)
                } else {
                    const demo = getDemoData()
                    setRuns(demo.runs)
                    setStats(demo.stats)
                }
            })
            .catch(() => {
                const demo = getDemoData()
                setRuns(demo.runs)
                setStats(demo.stats)
            })
            .finally(() => setLoading(false))

        axios.get('/api/v1/pipeline/eval_reports')
            .then(res => setReports(res.data))
            .catch(err => console.error("Failed to load reports:", err))
    }, [])

    const handleDownloadReport = (filename: string) => {
        navigate(`/reports/${filename}`)
    }

    // Chart data
    const trendData = runs.slice().reverse().map((r, i) => ({
        name: `Run ${i + 1}`,
        before: Math.round(r.score_before),
        after: Math.round(r.score_after),
    }))

    const issueData = [
        { name: 'Missing ABHA', count: 12 },
        { name: 'No Insurance Ref', count: 9 },
        { name: 'Invalid Date Format', count: 7 },
        { name: 'Missing Diagnosis Code', count: 6 },
        { name: 'No Facility Name', count: 4 },
    ]

    const kpis = [
        { label: 'Documents Processed', value: stats?.total || 0, icon: FileText, color: 'var(--emerald-600)' },
        { label: 'Avg Compliance Score', value: `${stats ? Math.round((stats.avg_score_lift || 0) + 50) : 72}%`, icon: TrendingUp, color: 'var(--teal-600)' },
        { label: 'NRCeS Pass Rate', value: `${stats ? Math.round(stats.success_rate * 100) : 87}%`, icon: ShieldCheck, color: '#059669' },
        { label: 'Avg Processing Time', value: `${stats ? Math.round(stats.avg_processing_ms) : 458}ms`, icon: Activity, color: '#0d9488' },
    ]

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh' }}>
                <div className="animate-float" style={{ textAlign: 'center', color: 'var(--gray-400)' }}>
                    <Activity size={32} style={{ marginBottom: '1rem' }} />
                    <p>Loading dashboard...</p>
                </div>
            </div>
        )
    }

    return (
        <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '2rem 1.5rem' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '2rem' }}>
                <div>
                    <p style={{ color: 'var(--gray-400)', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                        {new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                    </p>
                    <h1 className="text-section-title">Welcome back 👋</h1>
                </div>
                <button className="btn btn-primary" onClick={() => navigate('/pipeline')}>
                    <FileText size={16} /> New Pipeline Run <ArrowRight size={16} />
                </button>
            </div>

            {/* KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.25rem', marginBottom: '2rem' }}>
                {kpis.map(({ label, value, icon: Icon, color }, i) => (
                    <div key={i} className="card animate-fade-in-up" style={{ animationDelay: `${i * 80}ms` }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                            <div>
                                <p style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--gray-400)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>{label}</p>
                                <p className="text-kpi" style={{ color }}>{value}</p>
                            </div>
                            <div style={{
                                width: '42px', height: '42px', borderRadius: 'var(--radius-lg)',
                                background: `${color}12`, display: 'flex', alignItems: 'center', justifyContent: 'center',
                            }}>
                                <Icon size={20} color={color} />
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Main Grid: Table + Charts */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
                {/* Recent Activity Table */}
                <div className="card animate-fade-in-up delay-200" style={{ gridColumn: 'span 2' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
                        <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1.1rem' }}>Recent Pipeline Runs</h3>
                        <button className="btn btn-ghost" style={{ fontSize: '0.8125rem' }} onClick={() => navigate('/pipeline')}>
                            View All <ArrowRight size={14} />
                        </button>
                    </div>
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--gray-100)' }}>
                                    {['File Name', 'Type', 'Score Before', 'Score After', 'Lift', 'Status', 'Time'].map(h => (
                                        <th key={h} style={{ textAlign: 'left', padding: '0.75rem 1rem', color: 'var(--gray-400)', fontWeight: 600, fontSize: '0.6875rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {runs.slice(-8).reverse().map((r, i) => (
                                    <tr key={r.id} style={{ borderBottom: '1px solid var(--gray-50)' }}>
                                        <td style={{ padding: '0.75rem 1rem', fontWeight: 500, color: 'var(--gray-800)' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <FileText size={14} color="var(--gray-400)" />
                                                {r.source_file || `document_${i}.pdf`}
                                            </div>
                                        </td>
                                        <td style={{ padding: '0.75rem 1rem' }}>
                                            <span className="badge badge-neutral">{(r.format || 'pdf').toUpperCase()}</span>
                                        </td>
                                        <td style={{ padding: '0.75rem 1rem', color: 'var(--gray-500)' }}>{r.score_before?.toFixed(1) || '—'}</td>
                                        <td style={{ padding: '0.75rem 1rem', fontWeight: 600, color: 'var(--emerald-700)' }}>{r.score_after?.toFixed(1) || '—'}</td>
                                        <td style={{ padding: '0.75rem 1rem' }}>
                                            <span style={{ color: 'var(--emerald-600)', fontWeight: 600 }}>+{r.score_delta?.toFixed(1) || '0'}</span>
                                        </td>
                                        <td style={{ padding: '0.75rem 1rem' }}>
                                            <span className={r.success ? 'badge badge-success' : 'badge badge-danger'}>
                                                {r.success ? 'Passed' : 'Failed'}
                                            </span>
                                        </td>
                                        <td style={{ padding: '0.75rem 1rem', color: 'var(--gray-400)' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                                <Clock size={12} /> {r.total_ms?.toFixed(0) || '—'}ms
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Compliance Trend Chart */}
                <div className="card animate-fade-in-up delay-300">
                    <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1.1rem', marginBottom: '1.25rem' }}>Compliance Score Trend</h3>
                    <ResponsiveContainer width="100%" height={250}>
                        <LineChart data={trendData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--gray-100)" />
                            <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--gray-400)' }} />
                            <YAxis tick={{ fontSize: 11, fill: 'var(--gray-400)' }} domain={[0, 100]} />
                            <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid var(--gray-100)', fontSize: '0.8125rem' }} />
                            <Line type="monotone" dataKey="before" stroke="var(--gray-300)" strokeWidth={2} dot={{ r: 3 }} name="Before Heal" />
                            <Line type="monotone" dataKey="after" stroke="var(--emerald-500)" strokeWidth={2.5} dot={{ r: 4, fill: 'var(--emerald-500)' }} name="After Heal" />
                        </LineChart>
                    </ResponsiveContainer>
                </div>

                {/* Top Issues Chart */}
                <div className="card animate-fade-in-up delay-400">
                    <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1.1rem', marginBottom: '1.25rem' }}>Top Validation Issues</h3>
                    <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={issueData} layout="vertical">
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--gray-100)" />
                            <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--gray-400)' }} />
                            <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: 'var(--gray-500)' }} width={130} />
                            <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid var(--gray-100)', fontSize: '0.8125rem' }} />
                            <Bar dataKey="count" fill="var(--emerald-500)" radius={[0, 4, 4, 0]} barSize={20} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* System Reports Table */}
            <div className="card animate-fade-in-up delay-500" style={{ marginTop: '2rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1.1rem' }}>Available System Reports</h3>
                    <button className="btn btn-ghost" style={{ fontSize: '0.8125rem' }} onClick={() => navigate('/reports')}>
                        View All <ArrowRight size={14} />
                    </button>
                </div>

                {reports.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--gray-400)' }}>
                        <FileText size={32} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
                        <p>No reports generated yet.</p>
                    </div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--gray-100)', textAlign: 'left', color: 'var(--gray-400)', textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: '0.6875rem' }}>
                                    <th style={{ padding: '0.75rem 1rem' }}>Report Name</th>
                                    <th style={{ padding: '0.75rem 1rem' }}>Date</th>
                                    <th style={{ padding: '0.75rem 1rem' }}>Documents</th>
                                    <th style={{ padding: '0.75rem 1rem' }}>Success Rate</th>
                                    <th style={{ padding: '0.75rem 1rem' }}>Avg Lift</th>
                                    <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {reports.slice(0, 5).map((report) => (
                                    <tr key={report.filename} style={{ borderBottom: '1px solid var(--gray-50)' }}>
                                        <td style={{ padding: '0.75rem 1rem', fontWeight: 500, color: 'var(--gray-800)' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <FileText size={14} color="var(--blue-500)" />
                                                {report.filename}
                                            </div>
                                        </td>
                                        <td style={{ padding: '0.75rem 1rem', color: 'var(--gray-500)' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                                <Clock size={12} />
                                                {new Date(report.timestamp).toLocaleString()}
                                            </div>
                                        </td>
                                        <td style={{ padding: '0.75rem 1rem', color: 'var(--gray-600)' }}>{report.total_documents} files</td>
                                        <td style={{ padding: '0.75rem 1rem' }}>
                                            <span className={report.success_rate >= 90 ? 'badge badge-success' : 'badge badge-warning'}>
                                                {report.success_rate.toFixed(1)}%
                                            </span>
                                        </td>
                                        <td style={{ padding: '0.75rem 1rem', color: 'var(--emerald-600)', fontWeight: 600 }}>
                                            +{report.avg_lift.toFixed(1)}
                                        </td>
                                        <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                                            <button
                                                className="btn btn-ghost"
                                                onClick={() => handleDownloadReport(report.filename)}
                                                style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem' }}
                                            >
                                                Download
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    )
}
