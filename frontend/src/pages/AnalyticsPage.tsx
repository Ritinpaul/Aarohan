import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid, PieChart, Pie, Cell, Legend } from 'recharts'
import { Download, FileText, TrendingUp, AlertTriangle, Sparkles } from 'lucide-react'
import axios from 'axios'

const COLORS = ['var(--lime-500)', 'var(--green-500)', '#3b82f6', '#f59e0b', '#ef4444']

const issueData = [
    { name: 'Missing ABHA Identifier', count: 18 },
    { name: 'No Insurance Reference', count: 14 },
    { name: 'Invalid Date Format', count: 11 },
    { name: 'Missing Diagnosis ICD Code', count: 9 },
    { name: 'No Facility Name', count: 7 },
    { name: 'Missing Patient Gender', count: 6 },
    { name: 'Claim Total Absent', count: 5 },
    { name: 'Missing Encounter Dates', count: 4 },
]

const docTypes = [
    { name: 'PDF', value: 64 },
    { name: 'CSV', value: 18 },
    { name: 'HL7v2', value: 11 },
    { name: 'XML', value: 7 },
]

const tierData = [
    { name: 'Tier 1', value: 35 },
    { name: 'Tier 2', value: 45 },
    { name: 'Tier 3', value: 20 },
]

export default function AnalyticsPage() {
    const [, setStats] = useState<any>(null)

    useEffect(() => {
        axios.get('/api/v1/pipeline/audit?n=50').then(res => {
            setStats(res.data.stats || { total: 127, success_rate: 0.874, avg_score_lift: 22.3, avg_processing_ms: 458 })
        }).catch(() => {
            setStats({ total: 127, success_rate: 0.874, avg_score_lift: 22.3, avg_processing_ms: 458 })
        })
    }, [])

    // Generate trend data
    const trendData = Array.from({ length: 14 }, (_, i) => ({
        day: `Day ${i + 1}`,
        before: 25 + Math.random() * 30,
        after: 55 + Math.random() * 35,
    }))

    const scoreDistribution = [
        { range: '0-20', count: 3 },
        { range: '20-40', count: 8 },
        { range: '40-60', count: 22 },
        { range: '60-80', count: 45 },
        { range: '80-100', count: 18 },
    ]

    const kpis = [
        { label: 'Avg Compliance Score', value: '72.4%', sub: '+4.2% this week', icon: TrendingUp, color: 'var(--lime-600)' },
        { label: 'Documents This Week', value: '34', sub: '↑ 12% vs last week', icon: FileText, color: 'var(--green-600)' },
        { label: 'Most Common Issue', value: 'Missing ABHA', sub: '18 occurrences', icon: AlertTriangle, color: 'var(--warning)' },
        { label: 'Auto-Heal Success', value: '89.2%', sub: '112 of 127 fixed', icon: Sparkles, color: 'var(--green-700)' },
    ]

    return (
        <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '2rem 1.5rem' }}>
            {/* Header */}
            <div style={{ marginBottom: '2rem' }}>
                <h1 className="text-section-title" style={{ marginBottom: '0.5rem' }}>Compliance Analytics</h1>
                <p style={{ color: 'var(--gray-500)', fontSize: '0.9375rem' }}>Deep insights into document processing, compliance trends, and validation patterns.</p>
            </div>

            {/* KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1.25rem', marginBottom: '2rem' }}>
                {kpis.map(({ label, value, sub, icon: Icon, color }, i) => (
                    <div key={i} className="card animate-fade-in-up" style={{ animationDelay: `${i * 80}ms` }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                            <div>
                                <p style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--gray-400)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>{label}</p>
                                <p className="text-kpi" style={{ color, marginBottom: '0.375rem' }}>{value}</p>
                                <p style={{ fontSize: '0.75rem', color: 'var(--gray-400)' }}>{sub}</p>
                            </div>
                            <div style={{ width: '44px', height: '44px', borderRadius: 'var(--radius-xl)', background: 'var(--lime-50)', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid var(--lime-100)' }}>
                                <Icon size={20} color={color} />
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Charts Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
                {/* 14-day Trend */}
                <div className="card animate-fade-in-up delay-200">
                    <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, marginBottom: '1.25rem' }}>14-Day Compliance Trend</h3>
                    <ResponsiveContainer width="100%" height={280}>
                        <LineChart data={trendData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--gray-100)" />
                            <XAxis dataKey="day" tick={{ fontSize: 10, fill: 'var(--gray-400)' }} />
                            <YAxis tick={{ fontSize: 10, fill: 'var(--gray-400)' }} domain={[0, 100]} />
                            <Tooltip contentStyle={{ borderRadius: '12px', border: '1px solid var(--gray-100)', fontSize: '0.8125rem', boxShadow: 'var(--shadow-lg)' }} />
                            <Line type="monotone" dataKey="before" stroke="var(--gray-300)" strokeWidth={2} name="Pre-Heal" dot={false} />
                            <Line type="monotone" dataKey="after" stroke="var(--lime-500)" strokeWidth={2.5} name="Post-Heal" dot={false} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>

                {/* Report Generator */}
                <div className="card animate-fade-in-up delay-300">
                    <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, marginBottom: '1.25rem' }}>Generate Report</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        {['Compliance Summary', 'NRCeS Validation Report', 'Monthly Processing Report'].map(r => (
                            <button key={r} className="btn btn-ghost" style={{
                                justifyContent: 'space-between', padding: '0.875rem 1rem',
                                border: '1px solid var(--gray-100)', borderRadius: 'var(--radius-xl)',
                                fontSize: '0.8125rem', textAlign: 'left',
                            }}>
                                <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <FileText size={14} color="var(--gray-400)" /> {r}
                                </span>
                                <Download size={14} color="var(--gray-400)" />
                            </button>
                        ))}
                    </div>
                    <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.25rem' }}>
                        <button className="btn btn-primary" style={{ flex: 1, fontSize: '0.8125rem' }}>
                            <Download size={14} /> Export PDF
                        </button>
                        <button className="btn btn-outline" style={{ flex: 1, fontSize: '0.8125rem' }}>
                            <Download size={14} /> Export CSV
                        </button>
                    </div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1.5rem' }}>
                {/* Score Distribution */}
                <div className="card animate-fade-in-up delay-300">
                    <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, marginBottom: '1.25rem' }}>Score Distribution</h3>
                    <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={scoreDistribution}>
                            <XAxis dataKey="range" tick={{ fontSize: 10, fill: 'var(--gray-400)' }} />
                            <YAxis tick={{ fontSize: 10, fill: 'var(--gray-400)' }} />
                            <Tooltip contentStyle={{ borderRadius: '12px', border: '1px solid var(--gray-100)', fontSize: '0.8125rem', boxShadow: 'var(--shadow-lg)' }} />
                            <Bar dataKey="count" fill="var(--lime-500)" radius={[6, 6, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                {/* Document Types Donut */}
                <div className="card animate-fade-in-up delay-400">
                    <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, marginBottom: '1.25rem' }}>Document Types</h3>
                    <ResponsiveContainer width="100%" height={220}>
                        <PieChart>
                            <Pie data={docTypes} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                                {docTypes.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                            </Pie>
                            <Tooltip contentStyle={{ borderRadius: '12px', fontSize: '0.8125rem' }} />
                            <Legend iconSize={10} wrapperStyle={{ fontSize: '0.75rem' }} />
                        </PieChart>
                    </ResponsiveContainer>
                </div>

                {/* Hospital Tiers */}
                <div className="card animate-fade-in-up delay-500">
                    <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, marginBottom: '1.25rem' }}>Hospital Tiers</h3>
                    <ResponsiveContainer width="100%" height={220}>
                        <PieChart>
                            <Pie data={tierData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                                {tierData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                            </Pie>
                            <Tooltip contentStyle={{ borderRadius: '12px', fontSize: '0.8125rem' }} />
                            <Legend iconSize={10} wrapperStyle={{ fontSize: '0.75rem' }} />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Bottom: Top Issues */}
            <div className="card animate-fade-in-up delay-500" style={{ marginTop: '1.5rem' }}>
                <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 700, marginBottom: '1.25rem' }}>Top Validation Issues</h3>
                <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={issueData} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--gray-100)" />
                        <XAxis type="number" tick={{ fontSize: 10, fill: 'var(--gray-400)' }} />
                        <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: 'var(--gray-500)' }} width={180} />
                        <Tooltip contentStyle={{ borderRadius: '12px', border: '1px solid var(--gray-100)', fontSize: '0.8125rem', boxShadow: 'var(--shadow-lg)' }} />
                        <Bar dataKey="count" fill="var(--lime-500)" radius={[0, 6, 6, 0]} barSize={18} />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    )
}
