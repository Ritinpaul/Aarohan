import { useState, useEffect } from 'react'
import { FileText, Download, Clock, CheckCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

interface EvalReport {
    filename: string;
    timestamp: string;
    total_documents: number;
    success_rate: number;
    avg_score_before: number;
    avg_score_after: number;
    avg_lift: number;
}

export default function ReportsPage() {
    const navigate = useNavigate()
    const [reports, setReports] = useState<EvalReport[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        axios.get('/api/v1/pipeline/eval_reports')
            .then(res => setReports(res.data))
            .catch(err => console.error("Failed to load reports:", err))
            .finally(() => setLoading(false))
    }, [])

    const handleDownload = (filename: string) => {
        navigate(`/reports/${filename}`)
    }

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
                <p style={{ color: 'var(--gray-400)' }}>Loading reports...</p>
            </div>
        )
    }

    return (
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem 1.5rem' }}>
            <div style={{ marginBottom: '2rem' }}>
                <h1 className="text-section-title" style={{ marginBottom: '0.5rem' }}>System Reports</h1>
                <p style={{ color: 'var(--gray-500)', fontSize: '0.9375rem' }}>
                    View and download evaluation pipeline reports containing detailed validation metrics.
                </p>
            </div>

            <div className="card animate-fade-in-up">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h3 style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: '1.125rem' }}>Evaluation History</h3>
                </div>

                {reports.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--gray-400)' }}>
                        <FileText size={32} style={{ margin: '0 auto 1rem', opacity: 0.5 }} />
                        <p>No reports generated yet.</p>
                    </div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid var(--gray-100)', textAlign: 'left', color: 'var(--gray-400)', textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: '0.75rem' }}>
                                    <th style={{ padding: '0.75rem 1rem' }}>Report Name</th>
                                    <th style={{ padding: '0.75rem 1rem' }}>Date</th>
                                    <th style={{ padding: '0.75rem 1rem' }}>Documents</th>
                                    <th style={{ padding: '0.75rem 1rem' }}>Success Rate</th>
                                    <th style={{ padding: '0.75rem 1rem' }}>Avg Lift</th>
                                    <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {reports.map((report) => (
                                    <tr key={report.filename} style={{ borderBottom: '1px solid var(--gray-50)' }}>
                                        <td style={{ padding: '1rem', fontWeight: 500, color: 'var(--gray-800)' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <FileText size={16} color="var(--blue-500)" />
                                                {report.filename}
                                            </div>
                                        </td>
                                        <td style={{ padding: '1rem', color: 'var(--gray-500)' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <Clock size={14} />
                                                {new Date(report.timestamp).toLocaleString()}
                                            </div>
                                        </td>
                                        <td style={{ padding: '1rem', color: 'var(--gray-600)' }}>{report.total_documents} files</td>
                                        <td style={{ padding: '1rem' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: report.success_rate > 90 ? 'var(--emerald-600)' : 'var(--warning-dark)' }}>
                                                <CheckCircle size={14} />
                                                {report.success_rate.toFixed(1)}%
                                            </div>
                                        </td>
                                        <td style={{ padding: '1rem', color: 'var(--emerald-600)', fontWeight: 500 }}>
                                            +{report.avg_lift.toFixed(1)} pts
                                        </td>
                                        <td style={{ padding: '1rem', textAlign: 'right' }}>
                                            <button
                                                className="btn btn-ghost"
                                                onClick={() => handleDownload(report.filename)}
                                                style={{ padding: '0.375rem 0.75rem', fontSize: '0.8125rem' }}
                                            >
                                                <Download size={14} /> Download Summary
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
