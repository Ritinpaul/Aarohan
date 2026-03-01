import { useState, useRef } from 'react'
import { UploadCloud, FileType, Loader2, Building2, Activity } from 'lucide-react'
import axios from 'axios'

interface UploadTabProps {
    onUploadSuccess: (data: any) => void
}

export default function UploadTab({ onUploadSuccess }: UploadTabProps) {
    const [file, setFile] = useState<File | null>(null)
    const [isUploading, setIsUploading] = useState(false)
    const [error, setError] = useState('')
    const fileInputRef = useRef<HTMLInputElement>(null)

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0])
            setError('')
        }
    }

    const handleUpload = async () => {
        if (!file) return
        setIsUploading(true)
        setError('')

        const formData = new FormData()
        formData.append('file', file)
        formData.append('profile', 'ClaimBundle')
        formData.append('network', 'nhcx')
        formData.append('sign', 'true')

        try {
            // Complete pipeline run
            const res = await axios.post('/api/v1/pipeline/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })
            onUploadSuccess(res.data)
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || 'Upload failed')
        } finally {
            setIsUploading(false)
        }
    }

    return (
        <div className="max-w-3xl mx-auto py-8">
            <div className="text-center mb-8">
                <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.75rem' }} className="text-gray-900">Ingest Legacy Clinical Data</h2>
                <p className="text-gray-500 mt-2">Upload unstructured or legacy formats. The engine will automatically detect context and extract structured FHIR data.</p>
            </div>

            <div
                className="border-2 border-dashed border-gray-200 rounded-3xl p-12 text-center hover:border-lime-400 hover:bg-lime-50/50 transition-all duration-300 bg-white cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
                style={{ borderRadius: '24px' }}
            >
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full mb-4"
                    style={{ background: 'var(--lime-100)' }}>
                    <UploadCloud className="w-8 h-8" style={{ color: 'var(--lime-600)' }} />
                </div>
                <h3 className="text-lg font-medium text-gray-900">Drop your file here, or browse</h3>
                <p className="text-sm text-gray-500 mt-2">Supports PDF (Diagnostic/Discharge), CSV, HL7v2, XML</p>

                <input
                    type="file"
                    className="hidden"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    accept=".pdf,.csv,.hl7,.xml"
                />
            </div>

            {file && (
                <div className="mt-6 flex items-center justify-between p-4 bg-white rounded-2xl shadow-sm border border-gray-100">
                    <div className="flex items-center space-x-4">
                        <div className="p-2 rounded-lg" style={{ background: 'var(--lime-50)' }}>
                            <FileType className="w-6 h-6" style={{ color: 'var(--lime-600)' }} />
                        </div>
                        <div>
                            <p className="font-medium text-gray-900">{file.name}</p>
                            <p className="text-sm text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
                        </div>
                    </div>
                    <button
                        onClick={handleUpload}
                        disabled={isUploading}
                        className="px-6 py-2.5 text-white font-medium rounded-full transition-all duration-300 disabled:opacity-50 flex items-center shadow-sm"
                        style={{ background: 'linear-gradient(135deg, var(--brand-start), var(--brand-end))' }}
                    >
                        {isUploading ? (
                            <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Processing...</>
                        ) : (
                            'Run Intelligence Pipeline'
                        )}
                    </button>
                </div>
            )}

            {error && (
                <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100 text-sm">
                    {error}
                </div>
            )}

            {/* Feature Highlights */}
            <div className="grid grid-cols-2 gap-6 mt-12">
                <div style={{ background: 'linear-gradient(160deg, #e8fccf, #d4f7a8)', borderRadius: '20px', padding: '1.5rem', border: '1px solid rgba(132,204,22,0.15)' }}>
                    <Building2 className="w-6 h-6 mb-3" style={{ color: 'var(--lime-700)' }} />
                    <h4 className="font-semibold text-gray-900">Auto Context Detection</h4>
                    <p className="text-sm mt-1" style={{ color: 'var(--green-800)', opacity: 0.8 }}>Automatically detects hospital tier, geographic state, and applicable health schemes (PMJAY, CGHS).</p>
                </div>
                <div style={{ background: 'linear-gradient(160deg, #e8fccf, #d4f7a8)', borderRadius: '20px', padding: '1.5rem', border: '1px solid rgba(132,204,22,0.15)' }}>
                    <Activity className="w-6 h-6 mb-3" style={{ color: 'var(--lime-700)' }} />
                    <h4 className="font-semibold text-gray-900">Multimodal Parsing</h4>
                    <p className="text-sm mt-1" style={{ color: 'var(--green-800)', opacity: 0.8 }}>Extracts from unstructured clinical narratives, OCRs PDFs, and maps legacy codes natively.</p>
                </div>
            </div>
        </div>
    )
}
