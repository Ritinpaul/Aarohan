import { useState } from 'react'
import { Server, ShieldCheck, FileJson, Copy, Check, Lock, Loader2 } from 'lucide-react'
import axios from 'axios'

interface NetworkTabProps {
    pipelineData: any
}

export default function NetworkTab({ pipelineData }: NetworkTabProps) {
    const [copied, setCopied] = useState(false)
    const [payerRes, setPayerRes] = useState<any>(null)
    const [loading, setLoading] = useState(false)

    if (!pipelineData) {
        return (
            <div className="py-20 text-center text-gray-500 text-sm">
                Please complete the Upload step first.
            </div>
        )
    }

    // `bundle` is the full FHIR JSON; fall back to a minimal object if not sent
    const bundle = pipelineData.bundle || { id: pipelineData.run_id, type: 'collection', entry: [] }
    const { jws_digest, jws_token } = pipelineData

    const handleCopy = () => {
        navigator.clipboard.writeText(JSON.stringify(bundle, null, 2))
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
    }

    const simulatePayer = async (flow: 'eligibility' | 'preauth' | 'claim') => {
        setLoading(true)
        try {
            const res = await axios.post(`/api/v1/payer/${flow}`, {
                bundle: bundle,
                claim_amount: bundle.entry?.find((e: any) => e.resource?.resourceType === 'Claim')?.resource?.total?.value || 50000.0,
                subscriber_id: 'SUB-DEMO-001'
            })
            setPayerRes(res.data)
        } catch (err: any) {
            alert("Payer Simulation failed: " + (err.response?.data?.detail || err.message))
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="max-w-6xl mx-auto py-6 animate-in fade-in duration-500">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

                {/* Left Column: Network Operations */}
                <div className="lg:col-span-5 space-y-6">

                    {/* JWS Signing Result */}
                    <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-4 opacity-10 text-teal-600">
                            <Lock className="w-16 h-16" />
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                            <ShieldCheck className="w-5 h-5 text-teal-600 mr-2" />
                            JWS Signing (RS256)
                        </h3>

                        <div className="space-y-3">
                            <div>
                                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Bundle Digest (SHA-256)</p>
                                <code className="block p-3 bg-gray-50 text-xs text-gray-600 rounded-lg break-all border border-gray-100 font-mono">
                                    {jws_digest || 'No digest available'}
                                </code>
                            </div>
                            <div>
                                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Signed Header</p>
                                <code className="block p-3 bg-gray-50 text-xs text-gray-600 rounded-lg break-all border border-gray-100 font-mono">
                                    {jws_token ? jws_token.split('.')[0] : '{"alg":"RS256","typ":"JWT","kid":"aarohan-demo-key"}'}
                                </code>
                            </div>
                            <div className="pt-2 flex items-center text-sm font-medium text-teal-600">
                                <Check className="w-4 h-4 mr-1" /> Payload Signed Successfully
                            </div>
                        </div>
                    </div>

                    {/* Dummy Payer Integration */}
                    <div className="bg-gradient-to-br from-indigo-50 to-blue-50 rounded-2xl p-6 border border-indigo-100 shadow-sm">
                        <h3 className="text-lg font-semibold text-indigo-900 mb-2 flex items-center">
                            <Server className="w-5 h-5 text-indigo-600 mr-2" />
                            Payer Gateway Simulation
                        </h3>
                        <p className="text-sm text-indigo-700/80 mb-6">Test the NHCX routing logic and payer adjudication responses in real-time.</p>

                        <div className="space-y-3">
                            <button
                                onClick={() => simulatePayer('eligibility')}
                                disabled={loading}
                                className="w-full text-left px-4 py-3 bg-white hover:bg-indigo-50 border border-indigo-100 rounded-xl transition-colors font-medium text-indigo-900 flex justify-between items-center shadow-sm"
                            >
                                1. Check Coverage Eligibility <ArrowRight className="w-4 h-4 text-indigo-400" />
                            </button>
                            <button
                                onClick={() => simulatePayer('preauth')}
                                disabled={loading}
                                className="w-full text-left px-4 py-3 bg-white hover:bg-indigo-50 border border-indigo-100 rounded-xl transition-colors font-medium text-indigo-900 flex justify-between items-center shadow-sm"
                            >
                                2. Request Pre-Authorization <ArrowRight className="w-4 h-4 text-indigo-400" />
                            </button>
                            <button
                                onClick={() => simulatePayer('claim')}
                                disabled={loading}
                                className="w-full text-left px-4 py-3 bg-white hover:bg-indigo-50 border border-indigo-100 rounded-xl transition-colors font-medium text-indigo-900 flex justify-between items-center shadow-sm"
                            >
                                3. Submit Final Claim <ArrowRight className="w-4 h-4 text-indigo-400" />
                            </button>
                        </div>

                        {loading && (
                            <div className="mt-6 flex justify-center py-4 text-indigo-400">
                                <Loader2 className="w-6 h-6 animate-spin" />
                            </div>
                        )}

                        {payerRes && !loading && (
                            <div className="mt-6 p-4 bg-white rounded-xl border border-indigo-100 animate-in slide-in-from-bottom-2 duration-300">
                                <div className="flex justify-between items-center mb-3">
                                    <span className={`px-2.5 py-1 text-xs font-bold uppercase tracking-wider rounded-md ${payerRes.status === 'approved' ? 'bg-green-100 text-green-700' :
                                        payerRes.status === 'queued' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'
                                        }`}>
                                        {payerRes.status}
                                    </span>
                                    <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">{payerRes.flow}</span>
                                </div>

                                <p className="text-sm font-medium text-gray-900 mb-1">{payerRes.remarks}</p>
                                <div className="grid grid-cols-2 gap-2 mt-4 border-t border-gray-100 pt-3">
                                    <div>
                                        <p className="text-[10px] text-gray-400 uppercase tracking-wider">Scheme</p>
                                        <p className="text-sm font-semibold text-gray-700 capitalize">{payerRes.scheme_name}</p>
                                    </div>
                                    <div>
                                        <p className="text-[10px] text-gray-400 uppercase tracking-wider">Approved Amount</p>
                                        <p className="text-sm font-semibold text-gray-700">₹{payerRes.benefit_amount.toLocaleString()}</p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Right Column: FHIR JSON Viewer */}
                <div className="lg:col-span-7 bg-gray-900 rounded-2xl flex flex-col shadow-xl overflow-hidden border border-gray-800">
                    <div className="flex items-center justify-between px-4 py-3 bg-gray-800/80 border-b border-gray-700">
                        <div className="flex items-center text-gray-300 text-sm font-medium">
                            <FileJson className="w-4 h-4 mr-2 text-nature-400" />
                            Generated FHIR Bundle
                            <span className="ml-3 px-2 py-0.5 bg-gray-700 text-gray-300 rounded text-xs">
                                {pipelineData.profile}
                            </span>
                        </div>
                        <button
                            onClick={handleCopy}
                            className="text-gray-400 hover:text-white transition-colors p-1"
                            title="Copy to clipboard"
                        >
                            {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                        </button>
                    </div>
                    <div className="p-4 flex-1 overflow-auto bg-[#0d1117] relative custom-scrollbar max-h-[650px]">
                        <pre className="text-[13px] leading-relaxed text-gray-300 font-mono">
                            <code dangerouslySetInnerHTML={{
                                __html: syntaxHighlight(JSON.stringify(bundle, null, 2))
                            }} />
                        </pre>
                    </div>
                </div>

            </div>
        </div>
    )
}

function ArrowRight({ className }: { className?: string }) {
    return <ArrowRightIcon className={className || "w-4 h-4"} />
}
import { ArrowRight as ArrowRightIcon } from 'lucide-react'

// Simple JSON syntax highlighter for demo
function syntaxHighlight(json: string) {
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        let cls = 'text-blue-400'; // number
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'text-green-400'; // key
            } else {
                cls = 'text-amber-300'; // string
            }
        } else if (/true|false/.test(match)) {
            cls = 'text-purple-400'; // boolean
        } else if (/null/.test(match)) {
            cls = 'text-gray-500'; // null
        }
        return '<span class="' + cls + '">' + match + '</span>';
    });
}
