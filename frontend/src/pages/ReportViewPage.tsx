import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Printer } from 'lucide-react'

export default function ReportViewPage() {
    const { filename } = useParams()
    const navigate = useNavigate()

    if (!filename) {
        return <div style={{ padding: '2rem' }}>Error: No filename provided</div>
    }

    const reportUrl = `/api/v1/pipeline/eval_reports/${filename}/summary`

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: 'var(--gray-50)' }}>
            {/* Header Bar */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '1rem 2rem',
                backgroundColor: 'white',
                borderBottom: '1px solid var(--gray-200)',
                flexShrink: 0
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <button
                        className="btn btn-ghost"
                        onClick={() => navigate(-1)}
                        style={{ padding: '0.5rem' }}
                    >
                        <ArrowLeft size={20} />
                    </button>
                    <div>
                        <h1 style={{ fontSize: '1.25rem', fontWeight: 600, margin: 0 }}>Report Viewer</h1>
                        <p style={{ fontSize: '0.875rem', color: 'var(--gray-500)', margin: 0 }}>{filename}</p>
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '0.75rem' }}>
                    <button
                        className="btn btn-outline"
                        onClick={() => {
                            const iframe = document.getElementById('report-iframe') as HTMLIFrameElement
                            if (iframe?.contentWindow) {
                                iframe.contentWindow.print()
                            }
                        }}
                    >
                        <Printer size={16} /> Print Report
                    </button>
                </div>
            </div>

            {/* Iframe Content */}
            <div style={{ flexGrow: 1, overflow: 'hidden' }}>
                <iframe
                    id="report-iframe"
                    src={reportUrl}
                    style={{ width: '100%', height: '100%', border: 'none' }}
                    title={`Report ${filename}`}
                />
            </div>
        </div>
    )
}
