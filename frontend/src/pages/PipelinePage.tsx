import { useState } from 'react'
import { FileUp, Activity, BrainCircuit } from 'lucide-react'
import UploadTab from '../components/UploadTab'
import AssessTab from '../components/AssessTab'
import NetworkTab from '../components/NetworkTab'

export default function PipelinePage() {
    const [activeTab, setActiveTab] = useState<'upload' | 'assess' | 'results'>('upload')
    const [pipelineData, setPipelineData] = useState<any>(null)

    const handleUploadSuccess = (data: any) => {
        setPipelineData(data)
        setActiveTab('assess')
    }

    return (
        <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '2rem 1.5rem' }}>
            {/* Page Header */}
            <div style={{ marginBottom: '2rem' }}>
                <h1 className="text-section-title" style={{ marginBottom: '0.5rem' }}>
                    Intelligence Pipeline
                </h1>
                <p style={{ color: 'var(--gray-500)', fontSize: '0.9375rem' }}>
                    Upload, process, and transform healthcare documents into NHCX-compliant FHIR bundles.
                </p>
            </div>

            {/* Pipeline Container */}
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                {/* Sub-tabs */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '0 1.5rem',
                    gap: '2rem',
                    borderBottom: '1px solid var(--gray-100)',
                    background: 'var(--gray-50)',
                }}>
                    <TabBtn active={activeTab === 'upload'} onClick={() => setActiveTab('upload')} icon={<FileUp size={16} />} label="1. Ingest & Context" />
                    <TabBtn active={activeTab === 'assess'} onClick={() => setActiveTab('assess')} icon={<Activity size={16} />} label="2. Score & Heal" />
                    <TabBtn active={activeTab === 'results'} onClick={() => setActiveTab('results')} icon={<BrainCircuit size={16} />} label="3. Network & Compliance" />
                </div>

                {/* Content */}
                <div style={{ padding: '2rem' }}>
                    {activeTab === 'upload' && <UploadTab onUploadSuccess={handleUploadSuccess} />}
                    {activeTab === 'assess' && <AssessTab pipelineData={pipelineData} onNext={() => setActiveTab('results')} />}
                    {activeTab === 'results' && <NetworkTab pipelineData={pipelineData} />}
                </div>
            </div>
        </div>
    )
}

function TabBtn({ active, onClick, icon, label }: { active: boolean, onClick: () => void, icon: React.ReactNode, label: string }) {
    return (
        <button
            onClick={onClick}
            style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.375rem',
                padding: '0.875rem 0',
                fontSize: '0.8125rem',
                fontWeight: active ? 600 : 500,
                color: active ? 'var(--emerald-700)' : 'var(--gray-500)',
                background: 'transparent',
                border: 'none',
                borderBottom: active ? '2px solid var(--emerald-500)' : '2px solid transparent',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
            }}
        >
            {icon}
            {label}
        </button>
    )
}
