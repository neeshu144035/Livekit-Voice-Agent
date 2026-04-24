'use client';

import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import Link from 'next/link';
import {
    History, ArrowLeft, Phone, PhoneIncoming, PhoneOutgoing,
    Clock, DollarSign, Bot, MessageSquare, ChevronDown,
    Search, Filter, RefreshCw, Loader2, X, Sparkles,
    ArrowUpRight, ArrowDownLeft, Globe, Mic, Volume2,
    Cpu, Zap, AlertCircle, CheckCircle, XCircle, Timer,
    ChevronRight, ChevronLeft, Eye, Home, BookOpen, BarChart3,
    Key, Settings
} from 'lucide-react';

const API_URL = '/api/';

interface CallRecord {
    id: number;
    call_id: string;
    agent_id: number;
    agent_name: string;
    room_name: string;
    call_type: string;
    direction: string;
    status: string;
    from_number: string | null;
    to_number: string | null;
    started_at: string | null;
    ended_at: string | null;
    duration_seconds: number | null;
    cost_usd: number;
    llm_cost: number;
    stt_cost: number;
    tts_cost: number;
    llm_tokens_in: number;
    llm_tokens_out: number;
    llm_model_used: string | null;
    stt_duration_ms: number;
    tts_characters: number;
    tts_provider?: string | null;
    tts_model_used?: string | null;
    tts_fallback_used?: boolean;
    tts_original_model?: string | null;
    tts_actual_model?: string | null;
    transcript_count: number;
    transcript_summary: string | null;
    error_message: string | null;
    created_at: string | null;
}

interface TranscriptEntry {
    role: string;
    content: string;
    timestamp: string | null;
    is_final: boolean;
    confidence: number | null;
    latency: {
        stt_ms: number | null;
        llm_ms: number | null;
        tts_ms: number | null;
    };
}

interface CallDetails {
    call: {
        call_id: string;
        agent_id: number;
        agent_name: string;
        room_name: string;
        call_type: string;
        direction: string;
        status: string;
        from_number: string | null;
        to_number: string | null;
        started_at: string | null;
        ended_at: string | null;
        duration_seconds: number | null;
        recording_url: string | null;
        error_message: string | null;
    };
    costs: {
        total_usd: number;
        llm_cost: number;
        stt_cost: number;
        tts_cost: number;
    };
    usage: {
        llm_model: string | null;
        llm_tokens_in: number;
        llm_tokens_out: number;
        stt_duration_ms: number;
        stt_duration_formatted: string;
        tts_characters: number;
        tts_provider?: string | null;
        tts_model?: string | null;
        tts_cost_source?: string | null;
    };
    latency: {
        stt_avg_ms: number | null;
        llm_avg_ms: number | null;
        tts_avg_ms: number | null;
        stt_p95_ms: number | null;
        llm_p95_ms: number | null;
    };
    transcript: TranscriptEntry[];
    metadata: Record<string, any>;
}

interface CallHistoryResponse {
    calls: CallRecord[];
    total: number;
    page: number;
    limit: number;
    total_pages: number;
}

function formatDuration(seconds: number | null): string {
    if (!seconds) return '—';
    const min = Math.floor(seconds / 60);
    const sec = seconds % 60;
    if (min === 0) return `${sec}s`;
    return `${min}m ${sec}s`;
}

function formatCost(cost: number): string {
    if (cost === 0) return '$0.00';
    if (cost < 0.01) return `$${cost.toFixed(4)}`;
    return `$${cost.toFixed(2)}`;
}

function formatDate(dateStr: string | null): string {
    if (!dateStr) return '—';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function formatTime(dateStr: string | null): string {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
    });
}

function StatusBadge({ status }: { status: string }) {
    const styles: Record<string, { bg: string; text: string; icon: any }> = {
        'completed': { bg: 'bg-green-50 border-green-200', text: 'text-green-700', icon: CheckCircle },
        'in-progress': { bg: 'bg-blue-50 border-blue-200', text: 'text-blue-700', icon: Timer },
        'pending': { bg: 'bg-yellow-50 border-yellow-200', text: 'text-yellow-700', icon: Clock },
        'failed': { bg: 'bg-red-50 border-red-200', text: 'text-red-700', icon: XCircle },
        'error': { bg: 'bg-red-50 border-red-200', text: 'text-red-700', icon: AlertCircle },
        'dialing': { bg: 'bg-purple-50 border-purple-200', text: 'text-purple-700', icon: Phone },
        'initiating': { bg: 'bg-purple-50 border-purple-200', text: 'text-purple-700', icon: Phone },
    };
    const style = styles[status] || { bg: 'bg-gray-50 border-gray-200', text: 'text-gray-700', icon: Clock };
    const Icon = style.icon;
    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${style.bg} ${style.text}`}>
            <Icon className="w-3 h-3" />
            {status}
        </span>
    );
}

function DirectionBadge({ direction, callType }: { direction: string; callType: string }) {
    const normalizedDirection = (direction || '').toLowerCase();
    if (normalizedDirection === 'inbound') {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                <ArrowDownLeft className="w-3 h-3" />
                Inbound
            </span>
        );
    }
    if (callType === 'phone') {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                <ArrowUpRight className="w-3 h-3" />
                Outbound
            </span>
        );
    }
    return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-violet-50 text-violet-700 border border-violet-200">
            <Globe className="w-3 h-3" />
            Web Call
        </span>
    );
}

// ==================== Call Detail Panel ====================
function CallDetailPanel({ callId, onClose }: { callId: string; onClose: () => void }) {
    const [details, setDetails] = useState<CallDetails | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'transcript' | 'costs' | 'latency'>('transcript');

    useEffect(() => {
        const fetchDetails = async () => {
            setLoading(true);
            setError(null);
            try {
                const res = await axios.get(`${API_URL}call-history/${callId}/details`);
                setDetails(res.data);
            } catch (err: any) {
                setError(err.response?.data?.detail || 'Failed to load call details');
            } finally {
                setLoading(false);
            }
        };
        fetchDetails();
    }, [callId]);

    if (loading) {
        return (
            <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-50 flex items-center justify-center" onClick={onClose}>
                <div className="bg-white rounded-2xl shadow-2xl p-8" onClick={e => e.stopPropagation()}>
                    <Loader2 className="w-8 h-8 animate-spin text-violet-500 mx-auto" />
                    <p className="text-gray-500 mt-3 text-sm">Loading call details...</p>
                </div>
            </div>
        );
    }

    if (error || !details) {
        return (
            <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-50 flex items-center justify-center" onClick={onClose}>
                <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md" onClick={e => e.stopPropagation()}>
                    <AlertCircle className="w-8 h-8 text-red-500 mx-auto" />
                    <p className="text-red-600 mt-3 text-sm text-center">{error || 'Failed to load'}</p>
                    <button onClick={onClose} className="mt-4 px-4 py-2 bg-gray-100 rounded-lg text-sm w-full hover:bg-gray-200">Close</button>
                </div>
            </div>
        );
    }

    const { call, costs, usage, latency, transcript, metadata } = details;
    const normalizedCallDirection = (call.direction || '').toLowerCase();
    const ttsProvider = (usage.tts_provider || metadata?.tts_provider || 'deepgram').toLowerCase();
    const ttsModel = usage.tts_model || metadata?.tts_model || null;
    const ttsCostSource = usage.tts_cost_source || metadata?.tts_cost_source || null;
    const isXaiUnified = ttsProvider === 'xai';
    const ttsProviderLabel = ttsProvider === 'xai' ? 'xAI' : ttsProvider === 'elevenlabs' ? 'ElevenLabs' : 'Deepgram';

    return (
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-50 flex justify-end" onClick={onClose}>
            <div
                className="w-full max-w-2xl bg-white shadow-2xl overflow-y-auto animate-slide-in"
                onClick={e => e.stopPropagation()}
                style={{ animation: 'slideInRight 0.3s ease-out' }}
            >
                {/* Header */}
                <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 z-10">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${normalizedCallDirection === 'inbound' ? 'bg-emerald-100' : call.call_type === 'phone' ? 'bg-blue-100' : 'bg-violet-100'
                                }`}>
                                {normalizedCallDirection === 'inbound' ? (
                                    <PhoneIncoming className="w-5 h-5 text-emerald-600" />
                                ) : call.call_type === 'phone' ? (
                                    <PhoneOutgoing className="w-5 h-5 text-blue-600" />
                                ) : (
                                    <Globe className="w-5 h-5 text-violet-600" />
                                )}
                            </div>
                            <div>
                                <h2 className="text-lg font-semibold text-gray-900">
                                    {normalizedCallDirection === 'inbound' ? 'Inbound Call' : call.call_type === 'phone' ? 'Outbound Call' : 'Web Call'}
                                </h2>
                                <p className="text-xs text-gray-500 font-mono">{call.call_id}</p>
                            </div>
                        </div>
                        <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                            <X className="w-5 h-5 text-gray-400" />
                        </button>
                    </div>
                </div>

                {/* Call Info Cards */}
                <div className="px-6 py-4 space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                        <div className="bg-gray-50 rounded-xl p-3">
                            <p className="text-xs text-gray-500 mb-1">Agent</p>
                            <p className="text-sm font-medium text-gray-900 flex items-center gap-1.5">
                                <Bot className="w-4 h-4 text-violet-500" />
                                {call.agent_name}
                            </p>
                        </div>
                        <div className="bg-gray-50 rounded-xl p-3">
                            <p className="text-xs text-gray-500 mb-1">Duration</p>
                            <p className="text-sm font-medium text-gray-900 flex items-center gap-1.5">
                                <Clock className="w-4 h-4 text-blue-500" />
                                {formatDuration(call.duration_seconds)}
                            </p>
                        </div>
                        <div className="bg-gray-50 rounded-xl p-3">
                            <p className="text-xs text-gray-500 mb-1">Status</p>
                            <StatusBadge status={call.status} />
                        </div>
                        <div className="bg-gray-50 rounded-xl p-3">
                            <p className="text-xs text-gray-500 mb-1">Total Cost</p>
                            <p className="text-sm font-semibold text-green-600 flex items-center gap-1.5">
                                <DollarSign className="w-4 h-4" />
                                {formatCost(costs.total_usd)}
                            </p>
                        </div>
                    </div>

                    {/* Phone Numbers */}
                    {(call.from_number || call.to_number) && (
                        <div className="bg-gray-50 rounded-xl p-3">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-xs text-gray-500">From</p>
                                    <p className="text-sm font-medium text-gray-900">{call.from_number || '—'}</p>
                                </div>
                                <ChevronRight className="w-4 h-4 text-gray-400" />
                                <div className="text-right">
                                    <p className="text-xs text-gray-500">To</p>
                                    <p className="text-sm font-medium text-gray-900">{call.to_number || '—'}</p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Time */}
                    <div className="bg-gray-50 rounded-xl p-3">
                        <div className="flex items-center justify-between text-sm">
                            <div>
                                <p className="text-xs text-gray-500">Started</p>
                                <p className="font-medium text-gray-900">{formatDate(call.started_at)}</p>
                            </div>
                            <div className="text-right">
                                <p className="text-xs text-gray-500">Ended</p>
                                <p className="font-medium text-gray-900">{formatDate(call.ended_at)}</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Tabs */}
                <div className="px-6 border-b border-gray-200">
                    <div className="flex gap-1">
                        {[
                            { key: 'transcript', label: 'Transcript', icon: MessageSquare, count: transcript.length },
                            { key: 'costs', label: 'Costs & Usage', icon: DollarSign },
                            { key: 'latency', label: 'Performance', icon: Zap },
                        ].map(tab => (
                            <button
                                key={tab.key}
                                onClick={() => setActiveTab(tab.key as any)}
                                className={`flex items-center gap-1.5 px-3 py-2.5 text-sm font-medium border-b-2 transition-colors ${activeTab === tab.key
                                    ? 'border-violet-500 text-violet-700'
                                    : 'border-transparent text-gray-500 hover:text-gray-700'
                                    }`}
                            >
                                <tab.icon className="w-4 h-4" />
                                {tab.label}
                                {tab.count !== undefined && (
                                    <span className="ml-1 px-1.5 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">{tab.count}</span>
                                )}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Tab Content */}
                <div className="px-6 py-4">
                    {activeTab === 'transcript' && (
                        <div className="space-y-3">
                            {transcript.length === 0 ? (
                                <div className="text-center py-8">
                                    <MessageSquare className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                                    <p className="text-gray-500 text-sm">No transcript available</p>
                                    <p className="text-gray-400 text-xs mt-1">Transcripts are stored when a call is made</p>
                                </div>
                            ) : (
                                transcript.map((entry, i) => (
                                    <div
                                        key={i}
                                        className={`flex gap-3 ${entry.role === 'agent' ? '' : 'flex-row-reverse'}`}
                                    >
                                        <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${entry.role === 'agent' ? 'bg-violet-100' : 'bg-blue-100'
                                            }`}>
                                            {entry.role === 'agent' ? (
                                                <Bot className="w-3.5 h-3.5 text-violet-600" />
                                            ) : (
                                                <Mic className="w-3.5 h-3.5 text-blue-600" />
                                            )}
                                        </div>
                                        <div className={`max-w-[80%] ${entry.role === 'agent' ? '' : 'text-right'}`}>
                                            <div className={`inline-block px-3 py-2 rounded-2xl text-sm ${entry.role === 'agent'
                                                ? 'bg-gray-100 text-gray-800 rounded-tl-sm'
                                                : 'bg-violet-500 text-white rounded-tr-sm'
                                                }`}>
                                                {entry.content}
                                            </div>
                                            <div className="flex items-center gap-2 mt-0.5 px-1">
                                                <span className="text-[10px] text-gray-400">
                                                    {formatTime(entry.timestamp)}
                                                </span>
                                                {entry.latency?.stt_ms && (
                                                    <span className="text-[10px] text-gray-400">STT: {entry.latency.stt_ms}ms</span>
                                                )}
                                                {entry.latency?.llm_ms && (
                                                    <span className="text-[10px] text-gray-400">LLM: {entry.latency.llm_ms}ms</span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    )}

                    {activeTab === 'costs' && (
                        <div className="space-y-4">
                            {/* Cost Breakdown */}
                            <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-4 border border-green-100">
                                <h4 className="text-sm font-semibold text-green-800 mb-3 flex items-center gap-2">
                                    <DollarSign className="w-4 h-4" />
                                    Cost Breakdown
                                </h4>
                                <div className="space-y-2">
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm text-gray-600 flex items-center gap-2">
                                            <Cpu className="w-3.5 h-3.5 text-purple-500" />
                                            {isXaiUnified ? `Unified Voice Model (${usage.llm_model || ttsModel || 'xAI'})` : `LLM (${usage.llm_model || 'Unknown'})`}
                                        </span>
                                        <span className="text-sm font-medium text-gray-900">{formatCost(costs.llm_cost)}</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm text-gray-600 flex items-center gap-2">
                                            <Mic className="w-3.5 h-3.5 text-blue-500" />
                                            {isXaiUnified ? 'Input Speech (included in xAI session)' : 'Deepgram STT'}
                                        </span>
                                        <span className="text-sm font-medium text-gray-900">{formatCost(costs.stt_cost)}</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm text-gray-600 flex items-center gap-2">
                                            <Volume2 className="w-3.5 h-3.5 text-teal-500" />
                                            {isXaiUnified ? `xAI Voice Session${ttsModel ? ` (${ttsModel})` : ''}` : `${ttsProviderLabel} TTS${ttsModel ? ` (${ttsModel})` : ''}`}
                                        </span>
                                        <span className="text-sm font-medium text-gray-900">{formatCost(costs.tts_cost)}</span>
                                    </div>
                                    {ttsCostSource && (
                                        <div className="flex justify-end">
                                            <span className="text-[10px] text-gray-400">Source: {ttsCostSource}</span>
                                        </div>
                                    )}
                                    <div className="border-t border-green-200 pt-2 mt-2 flex justify-between items-center">
                                        <span className="text-sm font-semibold text-green-800">Total</span>
                                        <span className="text-base font-bold text-green-800">{formatCost(costs.total_usd)}</span>
                                    </div>
                                </div>
                            </div>

                            {/* Usage Details */}
                            <div className="bg-gray-50 rounded-xl p-4">
                                <h4 className="text-sm font-semibold text-gray-800 mb-3">Usage Metrics</h4>
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="bg-white rounded-lg p-3 border border-gray-100">
                                        <p className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">LLM Input Tokens</p>
                                        <p className="text-lg font-bold text-purple-600">{usage.llm_tokens_in.toLocaleString()}</p>
                                    </div>
                                    <div className="bg-white rounded-lg p-3 border border-gray-100">
                                        <p className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">LLM Output Tokens</p>
                                        <p className="text-lg font-bold text-purple-600">{usage.llm_tokens_out.toLocaleString()}</p>
                                    </div>
                                    <div className="bg-white rounded-lg p-3 border border-gray-100">
                                        <p className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">STT Duration</p>
                                        <p className="text-lg font-bold text-blue-600">{usage.stt_duration_formatted}</p>
                                    </div>
                                    <div className="bg-white rounded-lg p-3 border border-gray-100">
                                        <p className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">TTS Characters</p>
                                        <p className="text-lg font-bold text-teal-600">{usage.tts_characters.toLocaleString()}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'latency' && (
                        <div className="space-y-4">
                            <div className="bg-gray-50 rounded-xl p-4">
                                <h4 className="text-sm font-semibold text-gray-800 mb-3 flex items-center gap-2">
                                    <Zap className="w-4 h-4 text-yellow-500" />
                                    Average Latency
                                </h4>
                                <div className="space-y-3">
                                    {[ 
                                        { label: isXaiUnified ? 'Input Speech' : 'STT (Deepgram)', value: latency.stt_avg_ms, p95: latency.stt_p95_ms, color: 'blue', icon: Mic },
                                        { label: 'LLM', value: latency.llm_avg_ms, p95: latency.llm_p95_ms, color: 'purple', icon: Cpu },
                                        { label: isXaiUnified ? 'Voice Output (xAI)' : `TTS (${ttsProviderLabel})`, value: latency.tts_avg_ms, p95: null, color: 'teal', icon: Volume2 },
                                    ].map(item => (
                                        <div key={item.label} className="bg-white rounded-lg p-3 border border-gray-100">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-sm text-gray-600 flex items-center gap-2">
                                                    <item.icon className={`w-3.5 h-3.5 text-${item.color}-500`} />
                                                    {item.label}
                                                </span>
                                                <span className="text-sm font-bold text-gray-900">
                                                    {item.value ? `${item.value}ms` : '—'}
                                                </span>
                                            </div>
                                            {item.value && (
                                                <div className="w-full bg-gray-100 rounded-full h-1.5">
                                                    <div
                                                        className={`bg-${item.color}-500 rounded-full h-1.5`}
                                                        style={{ width: `${Math.min((item.value / 1000) * 100, 100)}%` }}
                                                    />
                                                </div>
                                            )}
                                            {item.p95 && (
                                                <p className="text-[10px] text-gray-400 mt-1">P95: {item.p95}ms</p>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Metadata */}
                            {metadata && Object.keys(metadata).length > 0 && (
                                <div className="bg-gray-50 rounded-xl p-4">
                                    <h4 className="text-sm font-semibold text-gray-800 mb-2">Metadata</h4>
                                    <pre className="text-xs text-gray-600 bg-white rounded-lg p-3 border border-gray-100 overflow-x-auto">
                                        {JSON.stringify(metadata, null, 2)}
                                    </pre>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}


// ==================== Main Page ====================
export default function CallHistoryPage() {
    const [calls, setCalls] = useState<CallRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [selectedCallId, setSelectedCallId] = useState<string | null>(null);
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [total, setTotal] = useState(0);
    const [searchQuery, setSearchQuery] = useState('');

    // Filters
    const [directionFilter, setDirectionFilter] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [callTypeFilter, setCallTypeFilter] = useState('');

    const fetchCalls = useCallback(async () => {
        try {
            const params = new URLSearchParams({ page: String(page), limit: '30' });
            if (directionFilter) params.set('direction', directionFilter);
            if (statusFilter) params.set('status', statusFilter);
            if (callTypeFilter) params.set('call_type', callTypeFilter);

            const res = await axios.get<CallHistoryResponse>(`${API_URL}call-history?${params}`);
            setCalls(res.data.calls);
            setTotalPages(res.data.total_pages);
            setTotal(res.data.total);
        } catch (err) {
            console.error('Error fetching call history:', err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [page, directionFilter, statusFilter, callTypeFilter]);

    useEffect(() => {
        setLoading(true);
        fetchCalls();
    }, [fetchCalls]);

    useEffect(() => {
        const interval = setInterval(fetchCalls, 15000);
        return () => clearInterval(interval);
    }, [fetchCalls]);

    const handleRefresh = () => {
        setRefreshing(true);
        fetchCalls();
    };

    // Filter calls by search
    const filteredCalls = calls.filter(call => {
        if (!searchQuery) return true;
        const q = searchQuery.toLowerCase();
        return (
            call.call_id.toLowerCase().includes(q) ||
            call.agent_name.toLowerCase().includes(q) ||
            (call.from_number && call.from_number.includes(q)) ||
            (call.to_number && call.to_number.includes(q))
        );
    });

    // Summary stats
    const totalCost = calls.reduce((sum, c) => sum + (c.cost_usd || 0), 0);
    const totalDuration = calls.reduce((sum, c) => sum + (c.duration_seconds || 0), 0);
    const inboundCount = calls.filter(c => (c.direction || '').toLowerCase() === 'inbound').length;
    const outboundCount = calls.filter(c => (c.direction || '').toLowerCase() === 'outbound').length;

    return (
        <div className="min-h-screen bg-gray-50" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
            {/* Main - with margin for fixed sidebar */}
            <main className="flex flex-col h-screen overflow-y-auto">
                {/* Header */}
                <header className="bg-white border-b border-gray-200 px-6 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl flex items-center justify-center">
                                <History className="w-5 h-5 text-white" />
                            </div>
                            <div>
                                <h1 className="text-xl font-semibold text-gray-900">Call History</h1>
                                <p className="text-xs text-gray-500">{total} total calls</p>
                            </div>
                        </div>
                        <button
                            onClick={handleRefresh}
                            disabled={refreshing}
                            className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition-colors"
                        >
                            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                            Refresh
                        </button>
                    </div>
                </header>

                {/* Summary Cards */}
                <div className="px-6 py-4 grid grid-cols-4 gap-4">
                    <div className="bg-white rounded-xl border border-gray-200 p-4">
                        <div className="flex items-center gap-2 mb-2">
                            <div className="w-8 h-8 bg-violet-100 rounded-lg flex items-center justify-center">
                                <Phone className="w-4 h-4 text-violet-600" />
                            </div>
                            <span className="text-xs text-gray-500 font-medium">Total Calls</span>
                        </div>
                        <p className="text-2xl font-bold text-gray-900">{total}</p>
                    </div>
                    <div className="bg-white rounded-xl border border-gray-200 p-4">
                        <div className="flex items-center gap-2 mb-2">
                            <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center">
                                <PhoneIncoming className="w-4 h-4 text-emerald-600" />
                            </div>
                            <span className="text-xs text-gray-500 font-medium">Inbound</span>
                        </div>
                        <p className="text-2xl font-bold text-gray-900">{inboundCount}</p>
                    </div>
                    <div className="bg-white rounded-xl border border-gray-200 p-4">
                        <div className="flex items-center gap-2 mb-2">
                            <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                                <Clock className="w-4 h-4 text-blue-600" />
                            </div>
                            <span className="text-xs text-gray-500 font-medium">Total Duration</span>
                        </div>
                        <p className="text-2xl font-bold text-gray-900">{formatDuration(totalDuration)}</p>
                    </div>
                    <div className="bg-white rounded-xl border border-gray-200 p-4">
                        <div className="flex items-center gap-2 mb-2">
                            <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                                <DollarSign className="w-4 h-4 text-green-600" />
                            </div>
                            <span className="text-xs text-gray-500 font-medium">Total Cost</span>
                        </div>
                        <p className="text-2xl font-bold text-green-600">{formatCost(totalCost)}</p>
                    </div>
                </div>

                {/* Filters */}
                <div className="px-6 flex items-center gap-3 mb-4">
                    <div className="relative flex-1 max-w-sm">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search by ID, agent, or number..."
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-violet-400 transition-colors"
                        />
                    </div>
                    <select
                        value={directionFilter}
                        onChange={e => { setDirectionFilter(e.target.value); setPage(1); }}
                        className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:border-violet-400"
                    >
                        <option value="">All Directions</option>
                        <option value="inbound">Inbound</option>
                        <option value="outbound">Outbound</option>
                    </select>
                    <select
                        value={statusFilter}
                        onChange={e => { setStatusFilter(e.target.value); setPage(1); }}
                        className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:border-violet-400"
                    >
                        <option value="">All Statuses</option>
                        <option value="completed">Completed</option>
                        <option value="in-progress">In Progress</option>
                        <option value="failed">Failed</option>
                        <option value="pending">Pending</option>
                    </select>
                    <select
                        value={callTypeFilter}
                        onChange={e => { setCallTypeFilter(e.target.value); setPage(1); }}
                        className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:border-violet-400"
                    >
                        <option value="">All Types</option>
                        <option value="phone">Phone</option>
                        <option value="web">Web</option>
                    </select>
                </div>

                {/* Table */}
                <div className="flex-1 px-6 pb-6 overflow-auto">
                    {loading ? (
                        <div className="flex items-center justify-center h-64">
                            <Loader2 className="w-8 h-8 animate-spin text-violet-400" />
                        </div>
                    ) : filteredCalls.length === 0 ? (
                        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                            <History className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                            <p className="text-gray-500 text-sm">No calls found</p>
                            <p className="text-gray-400 text-xs mt-1">
                                {total === 0 ? 'Make your first call to see it here' : 'Try adjusting your filters'}
                            </p>
                        </div>
                    ) : (
                        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                            <table className="w-full">
                                <thead>
                                    <tr className="border-b border-gray-100 bg-gray-50/50">
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Call</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Agent</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Direction</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Duration</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cost</th>
                                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                                        <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider"></th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-50">
                                    {filteredCalls.map(call => (
                                        <tr
                                            key={call.call_id}
                                            className="hover:bg-violet-50/30 transition-colors cursor-pointer group"
                                            onClick={() => setSelectedCallId(call.call_id)}
                                        >
                                            <td className="px-4 py-3">
                                                <div>
                                                    <p className="text-sm text-gray-900 font-medium">
                                                        {call.from_number || call.to_number || call.call_id.slice(0, 20)}
                                                    </p>
                                                    <p className="text-[10px] text-gray-400 font-mono">{call.call_id.slice(0, 24)}</p>
                                                </div>
                                            </td>
                                            <td className="px-4 py-3">
                                                <div>
                                                    <span className="text-sm text-gray-700 flex items-center gap-1.5">
                                                        <Bot className="w-3.5 h-3.5 text-violet-400" />
                                                        {call.agent_name}
                                                    </span>
                                                    <p className="text-[10px] text-gray-400 mt-0.5">
                                                        TTS: {call.tts_provider === 'xai' ? 'xAI' : call.tts_provider === 'elevenlabs' ? 'ElevenLabs' : 'Deepgram'}
                                                        {call.tts_model_used ? ` • ${call.tts_model_used}` : ''}
                                                        {call.tts_fallback_used ? <span className="text-amber-600 ml-1">(fallback)</span> : ''}
                                                    </p>
                                                </div>
                                            </td>
                                            <td className="px-4 py-3">
                                                <DirectionBadge direction={call.direction} callType={call.call_type} />
                                            </td>
                                            <td className="px-4 py-3">
                                                <StatusBadge status={call.status} />
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className="text-sm text-gray-700">{formatDuration(call.duration_seconds)}</span>
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className="text-sm font-medium text-green-600">{formatCost(call.cost_usd)}</span>
                                            </td>
                                            <td className="px-4 py-3">
                                                <span className="text-sm text-gray-500">{formatDate(call.created_at)}</span>
                                            </td>
                                            <td className="px-4 py-3 text-right">
                                                <button className="p-1.5 rounded-lg text-gray-400 hover:bg-violet-100 hover:text-violet-600 transition-colors opacity-0 group-hover:opacity-100">
                                                    <Eye className="w-4 h-4" />
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>

                            {/* Pagination */}
                            {totalPages > 1 && (
                                <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100">
                                    <p className="text-sm text-gray-500">
                                        Page {page} of {totalPages} ({total} calls)
                                    </p>
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => setPage(Math.max(1, page - 1))}
                                            disabled={page === 1}
                                            className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
                                        >
                                            <ChevronLeft className="w-4 h-4" />
                                        </button>
                                        <button
                                            onClick={() => setPage(Math.min(totalPages, page + 1))}
                                            disabled={page === totalPages}
                                            className="p-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed"
                                        >
                                            <ChevronRight className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </main>

            {/* Call Detail Slide-in Panel */}
            {selectedCallId && (
                <CallDetailPanel callId={selectedCallId} onClose={() => setSelectedCallId(null)} />
            )}

            {/* Animation styles */}
            <style jsx global>{`
                @keyframes slideInRight {
                    from { transform: translateX(100%); }
                    to { transform: translateX(0); }
                }
            `}</style>
        </div>
    );
}
