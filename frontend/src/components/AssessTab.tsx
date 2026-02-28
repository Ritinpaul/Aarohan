import { AlertTriangle, CheckCircle, Info, ArrowRight, ShieldCheck } from 'lucide-react'

interface AssessTabProps {
    pipelineData: any
    onNext: () => void
}

export default function AssessTab({ pipelineData, onNext }: AssessTabProps) {
    if (!pipelineData) {
        return (
            <div className="py-20 text-center text-gray-500 text-sm">
                Please complete the Upload step first.
            </div>
        )
    }

    const scoreBefore = pipelineData.readiness_before || 0
    const scoreAfter = pipelineData.readiness_after || 0
    const delta = pipelineData.readiness_delta || 0
    const validation = pipelineData.validation || {}

    // Determine colors based on score
    const getScoreColor = (score: number) => {
        if (score >= 90) return 'text-nature-600'
        if (score >= 70) return 'text-amber-500'
        return 'text-red-500'
    }

    return (
        <div className="max-w-5xl mx-auto py-6 animate-in fade-in duration-500">

            {/* Top Metrics Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 block relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-4 opacity-5"><ShieldCheck className="w-16 h-16" /></div>
                    <p className="text-sm font-medium text-gray-500 mb-1">Pre-Heal Readiness</p>
                    <div className="flex items-baseline space-x-2">
                        <span className={`text-4xl font-bold ${getScoreColor(scoreBefore)}`}>{scoreBefore}</span>
                        <span className="text-sm text-gray-400">/ 100</span>
                    </div>
                </div>

                <div className="bg-gradient-to-br from-nature-500 to-teal-600 p-6 rounded-2xl shadow-md border border-nature-400 block relative overflow-hidden text-white">
                    <p className="text-sm font-medium text-white/80 mb-1">Post-Heal Score</p>
                    <div className="flex items-baseline space-x-2">
                        <span className="text-5xl font-extrabold">{scoreAfter}</span>
                        <span className="text-sm text-white/60">/ 100</span>
                    </div>
                    {delta > 0 && (
                        <div className="mt-2 text-sm font-medium bg-white/20 inline-block px-2 py-0.5 rounded-full">
                            +{delta} pt Lift applied by Resilience Healer
                        </div>
                    )}
                </div>

                <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 block">
                    <p className="text-sm font-medium text-gray-500 mb-1">NRCeS Validation Gate</p>
                    {validation.valid ? (
                        <div className="flex items-center text-nature-600 mt-2">
                            <CheckCircle className="w-8 h-8 mr-3" />
                            <div>
                                <p className="font-bold text-lg leading-tight">PASS</p>
                                <p className="text-xs text-nature-600/80">{validation.error_count} Errors • {validation.warning_count} Warnings</p>
                            </div>
                        </div>
                    ) : (
                        <div className="flex items-center text-red-600 mt-2">
                            <AlertTriangle className="w-8 h-8 mr-3" />
                            <div>
                                <p className="font-bold text-lg leading-tight">FAIL</p>
                                <p className="text-xs text-red-600/80">{validation.error_count} Blocks • {validation.warning_count} Warns</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">

                {/* Stages Pipeline View */}
                <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
                    <h3 className="text-lg font-semibold text-gray-900 mb-6">Execution Pipeline</h3>
                    <div className="space-y-4">
                        {(pipelineData.stages || []).map((stage: any, i: number) => (
                            <div key={i} className="flex items-center">
                                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${stage.success ? 'bg-nature-100 text-nature-600' : 'bg-red-100 text-red-600'}`}>
                                    {stage.success ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                                </div>
                                <div className="ml-4 flex-1">
                                    <div className="flex items-center justify-between">
                                        <p className="text-sm font-medium text-gray-900 capitalize">{stage.stage} Engine</p>
                                        <span className="text-xs text-gray-400">{stage.duration_ms} ms</span>
                                    </div>
                                    {stage.error && <p className="text-xs text-red-500 mt-1">{stage.error}</p>}
                                </div>
                            </div>
                        ))}
                    </div>
                    <div className="mt-8 pt-6 border-t border-gray-100">
                        <button
                            onClick={onNext}
                            className="w-full flex items-center justify-center px-4 py-2.5 bg-gray-900 hover:bg-gray-800 text-white font-medium rounded-xl transition-colors"
                        >
                            Continue to Network Sim <ArrowRight className="w-4 h-4 ml-2" />
                        </button>
                    </div>
                </div>

                {/* Validation Errors & Context */}
                <div className="space-y-6">
                    <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">Detected Context</h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="p-3 bg-gray-50 rounded-lg">
                                <p className="text-xs text-gray-500">Format Detected</p>
                                <p className="font-medium text-gray-900 uppercase">{pipelineData.format_detected}</p>
                            </div>
                            <div className="p-3 bg-gray-50 rounded-lg">
                                <p className="text-xs text-gray-500">Target Profile</p>
                                <p className="font-medium text-gray-900">{pipelineData.profile}</p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">NRCeS Validation Details</h3>
                        {validation.issues?.length > 0 ? (
                            <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
                                {validation.issues.map((issue: any, i: number) => (
                                    <div key={i} className={`p-3 rounded-lg border text-sm flex items-start ${issue.severity === 'error' ? 'bg-red-50 border-red-100 text-red-800' :
                                        issue.severity === 'warning' ? 'bg-amber-50 border-amber-100 text-amber-800' :
                                            'bg-blue-50 border-blue-100 text-blue-800'
                                        }`}>
                                        <div className="mt-0.5 mr-2 flex-shrink-0">
                                            {issue.severity === 'error' ? <AlertTriangle className="w-4 h-4" /> : <Info className="w-4 h-4" />}
                                        </div>
                                        <div>
                                            <p className="font-semibold">{issue.code}</p>
                                            <p className="opacity-90 mt-0.5">{issue.details}</p>
                                            {issue.expression && <code className="text-[10px] mt-1 block opacity-70 font-mono">{issue.expression}</code>}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="p-6 text-center border-2 border-dashed border-nature-200 rounded-xl bg-nature-50 text-nature-700 font-medium">
                                Zero issues found! 100% compliant.
                            </div>
                        )}
                    </div>
                </div>

            </div>
        </div>
    )
}
