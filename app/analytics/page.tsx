'use client';

import { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import Link from 'next/link';
import {
    Bot, BookOpen, Phone, PhoneCall, History, MessageSquare,
    BarChart3, Settings, Key, Sparkles, ArrowLeft,
    TrendingUp, Users, Clock, DollarSign, RefreshCw, Loader2,
    PhoneIncoming, PhoneOutgoing, Globe
} from 'lucide-react';

const API_URL = '/api/';

interface AnalyticsData {
    period_days: number;
    // New format with phone/web separate
    phone?: {
        period: {
            total_calls: number;
            completed_calls: number;
            failed_calls: number;
            success_rate: number;
            total_duration_seconds: number;
            average_duration_seconds: number;
            total_cost_usd: number;
        };
        all_time: {
            total_calls: number;
            completed_calls: number;
            failed_calls: number;
            success_rate: number;
            total_duration_seconds: number;
            average_duration_seconds: number;
            total_cost_usd: number;
        };
    };
    web?: {
        period: {
            total_calls: number;
            completed_calls: number;
            failed_calls: number;
            success_rate: number;
            total_duration_seconds: number;
            average_duration_seconds: number;
            total_cost_usd: number;
        };
        all_time: {
            total_calls: number;
            completed_calls: number;
            failed_calls: number;
            success_rate: number;
            total_duration_seconds: number;
            average_duration_seconds: number;
            total_cost_usd: number;
        };
    };
    // Old format (direct fields) - fallback
    total_calls?: number;
    completed_calls?: number;
    failed_calls?: number;
    success_rate?: number;
    total_duration_seconds?: number;
    average_duration_seconds?: number;
    total_cost_usd?: number;
}

interface DailyStats {
    date: string;
    calls: number;
    duration: number;
    cost: number;
}

function formatDuration(seconds: number): string {
    if (!seconds) return '0s';
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

export default function AnalyticsPage() {
    const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
    const [dailyStats, setDailyStats] = useState<DailyStats[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [days, setDays] = useState(7);

    const fetchAnalytics = useCallback(async () => {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);

            const res = await axios.get<AnalyticsData>(`${API_URL}analytics?days=${days}`, {
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            const data = res.data;
            setAnalytics(data);

            // Use phone calls for the chart (new format) or old format as fallback
            const totalCalls = data.phone?.period?.total_calls ?? data.total_calls ?? 0;
            const totalDuration = data.phone?.period?.total_duration_seconds ?? data.total_duration_seconds ?? 0;
            const totalCost = data.phone?.period?.total_cost_usd ?? data.total_cost_usd ?? 0;

            // Generate daily stats based on the period
            const stats: DailyStats[] = [];
            const now = new Date();
            for (let i = days - 1; i >= 0; i--) {
                const date = new Date(now);
                date.setDate(date.getDate() - i);
                const dateStr = date.toISOString().split('T')[0];

                // Simulate daily distribution
                const dailyCalls = days > 0 ? Math.floor(totalCalls / days) : 0;
                stats.push({
                    date: dateStr,
                    calls: dailyCalls,
                    duration: days > 0 ? Math.floor(totalDuration / days) : 0,
                    cost: days > 0 ? totalCost / days : 0
                });
            }
            setDailyStats(stats);
        } catch (err: any) {
            if (axios.isCancel(err)) {
                console.log('Request cancelled');
            } else {
                console.error('Error fetching analytics:', err);
            }
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [days]);

    useEffect(() => {
        setLoading(true);
        fetchAnalytics();
    }, [fetchAnalytics]);

    const handleRefresh = () => {
        setRefreshing(true);
        fetchAnalytics();
    };

    const maxCalls = Math.max(...dailyStats.map(d => d.calls), 1);

    return (
        <div className="min-h-screen bg-gray-50" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
            {/* Main Content */}
            <main className="flex flex-col bg-gray-50 min-w-0">
                {/* Header */}
                <header className="bg-white border-b border-gray-200 px-4 md:px-6 py-3 md:py-4">
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 md:gap-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 md:gap-4">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                                        <BarChart3 className="w-5 h-5 text-green-600" />
                                    </div>
                                    <h1 className="text-lg md:text-xl font-semibold text-gray-900">Analytics</h1>
                                </div>
                            </div>
                        </div>

                        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3">
                            {/* Date Range Selector */}
                            <select
                                value={days}
                                onChange={(e) => setDays(Number(e.target.value))}
                                className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:border-green-400"
                            >
                                <option value={7}>Last 7 days</option>
                                <option value={14}>Last 14 days</option>
                                <option value={30}>Last 30 days</option>
                                <option value={90}>Last 90 days</option>
                            </select>
                            {/* Refresh Button */}
                            <button
                                onClick={handleRefresh}
                                disabled={refreshing}
                                className="flex items-center gap-2 px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition-colors"
                            >
                                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                                Refresh
                            </button>
                        </div>
                    </div>
                </header>

                {/* Content */}
                <div className="flex-1 p-6 overflow-auto">
                    <div className="max-w-6xl mx-auto">

                    {loading ? (
                        <div className="flex items-center justify-center h-64">
                            <Loader2 className="w-8 h-8 animate-spin text-green-400" />
                        </div>
                    ) : analytics && (analytics.phone?.all_time?.total_calls || analytics.web?.all_time?.total_calls || analytics.total_calls) ? (
                        <>
                            {/* Phone Calls Stats */}
                            <div className="mb-8">
                                <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                                    <Phone className="w-5 h-5" />
                                    Phone Calls (Inbound + Outbound)
                                </h2>
                                <div className="grid grid-cols-5 gap-6">
                                    <div className="bg-white p-6 rounded-xl border border-gray-200">
                                        <div className="flex items-center gap-3 mb-2">
                                            <div className="w-10 h-10 bg-violet-100 rounded-lg flex items-center justify-center">
                                                <Phone className="w-5 h-5 text-violet-600" />
                                            </div>
                                            <span className="text-sm text-gray-500">Total Calls</span>
                                        </div>
                                        <p className="text-3xl font-bold text-gray-900">{analytics.phone?.all_time?.total_calls ?? 0}</p>
                                        <div className="flex items-center gap-2 mt-2">
                                            <span className="text-xs text-green-600">
                                                {analytics.phone?.all_time?.completed_calls ?? 0} completed
                                            </span>
                                        </div>
                                    </div>
                                    <div className="bg-white p-6 rounded-xl border border-gray-200">
                                        <div className="flex items-center gap-3 mb-2">
                                            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                                                <Clock className="w-5 h-5 text-blue-600" />
                                            </div>
                                            <span className="text-sm text-gray-500">Avg Duration</span>
                                        </div>
                                        <p className="text-3xl font-bold text-gray-900">{formatDuration(analytics.phone?.all_time?.average_duration_seconds ?? 0)}</p>
                                    </div>
                                    <div className="bg-white p-6 rounded-xl border border-gray-200">
                                        <div className="flex items-center gap-3 mb-2">
                                            <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                                                <Clock className="w-5 h-5 text-orange-600" />
                                            </div>
                                            <span className="text-sm text-gray-500">Total Duration</span>
                                        </div>
                                        <p className="text-3xl font-bold text-gray-900">{formatDuration(analytics.phone?.all_time?.total_duration_seconds ?? 0)}</p>
                                    </div>
                                    <div className="bg-white p-6 rounded-xl border border-gray-200">
                                        <div className="flex items-center gap-3 mb-2">
                                            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                                                <TrendingUp className="w-5 h-5 text-green-600" />
                                            </div>
                                            <span className="text-sm text-gray-500">Success Rate</span>
                                        </div>
                                        <p className="text-3xl font-bold text-gray-900">{analytics.phone?.all_time?.success_rate ?? 0}%</p>
                                        <div className="flex items-center gap-2 mt-2">
                                            <span className="text-xs text-gray-500">
                                                {analytics.phone?.all_time?.failed_calls ?? 0} failed
                                            </span>
                                        </div>
                                    </div>
                                    <div className="bg-white p-6 rounded-xl border border-gray-200">
                                        <div className="flex items-center gap-3 mb-2">
                                            <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
                                                <DollarSign className="w-5 h-5 text-emerald-600" />
                                            </div>
                                            <span className="text-sm text-gray-500">Total Cost</span>
                                        </div>
                                        <p className="text-3xl font-bold text-gray-900">${analytics.phone?.all_time?.total_cost_usd?.toFixed(4) ?? '0.0000'}</p>
                                        <div className="flex items-center gap-2 mt-2">
                                            <span className="text-xs text-gray-500">
                                                ${((analytics.phone?.all_time?.total_cost_usd ?? 0) / (analytics.phone?.all_time?.total_calls ?? 1)).toFixed(4)}/call
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Web Calls Stats */}
                            <div className="mb-8">
                                <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                                    <Globe className="w-5 h-5" />
                                    Web Calls
                                </h2>
                                <div className="grid grid-cols-5 gap-6">
                                    <div className="bg-white p-6 rounded-xl border border-gray-200">
                                        <div className="flex items-center gap-3 mb-2">
                                            <div className="w-10 h-10 bg-violet-100 rounded-lg flex items-center justify-center">
                                                <Globe className="w-5 h-5 text-violet-600" />
                                            </div>
                                            <span className="text-sm text-gray-500">Total Calls</span>
                                        </div>
                                        <p className="text-3xl font-bold text-gray-900">{analytics.web?.all_time?.total_calls ?? 0}</p>
                                        <div className="flex items-center gap-2 mt-2">
                                            <span className="text-xs text-green-600">
                                                {analytics.web?.all_time?.completed_calls ?? 0} completed
                                            </span>
                                        </div>
                                    </div>
                                    <div className="bg-white p-6 rounded-xl border border-gray-200">
                                        <div className="flex items-center gap-3 mb-2">
                                            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                                                <Clock className="w-5 h-5 text-blue-600" />
                                            </div>
                                            <span className="text-sm text-gray-500">Avg Duration</span>
                                        </div>
                                        <p className="text-3xl font-bold text-gray-900">{formatDuration(analytics.web?.all_time?.average_duration_seconds ?? 0)}</p>
                                    </div>
                                    <div className="bg-white p-6 rounded-xl border border-gray-200">
                                        <div className="flex items-center gap-3 mb-2">
                                            <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                                                <Clock className="w-5 h-5 text-orange-600" />
                                            </div>
                                            <span className="text-sm text-gray-500">Total Duration</span>
                                        </div>
                                        <p className="text-3xl font-bold text-gray-900">{formatDuration(analytics.web?.all_time?.total_duration_seconds ?? 0)}</p>
                                    </div>
                                    <div className="bg-white p-6 rounded-xl border border-gray-200">
                                        <div className="flex items-center gap-3 mb-2">
                                            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                                                <TrendingUp className="w-5 h-5 text-green-600" />
                                            </div>
                                            <span className="text-sm text-gray-500">Success Rate</span>
                                        </div>
                                        <p className="text-3xl font-bold text-gray-900">{analytics.web?.all_time?.success_rate ?? 0}%</p>
                                        <div className="flex items-center gap-2 mt-2">
                                            <span className="text-xs text-gray-500">
                                                {analytics.web?.all_time?.failed_calls ?? 0} failed
                                            </span>
                                        </div>
                                    </div>
                                    <div className="bg-white p-6 rounded-xl border border-gray-200">
                                        <div className="flex items-center gap-3 mb-2">
                                            <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
                                                <DollarSign className="w-5 h-5 text-emerald-600" />
                                            </div>
                                            <span className="text-sm text-gray-500">Total Cost</span>
                                        </div>
                                        <p className="text-3xl font-bold text-gray-900">${analytics.web?.all_time?.total_cost_usd?.toFixed(4) ?? '0.0000'}</p>
                                        <div className="flex items-center gap-2 mt-2">
                                            <span className="text-xs text-gray-500">
                                                ${((analytics.web?.all_time?.total_cost_usd ?? 0) / (analytics.web?.all_time?.total_calls ?? 1)).toFixed(4)}/call
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Daily Calls Chart */}
                            <div className="bg-white rounded-xl border border-gray-200 p-6 mb-8">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4">Daily Calls</h3>
                                <div className="h-64 flex items-end gap-2">
                                    {dailyStats.map((day, i) => (
                                        <div key={i} className="flex-1 flex flex-col items-center">
                                            <div
                                                className="w-full bg-gradient-to-t from-green-500 to-green-400 rounded-t-md transition-all hover:from-green-600 hover:to-green-500"
                                                style={{ height: `${(day.calls / maxCalls) * 100}%`, minHeight: day.calls > 0 ? '4px' : '0' }}
                                                title={`${day.calls} calls`}
                                            />
                                            <span className="text-[10px] text-gray-400 mt-2">
                                                {new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                        </>
                    ) : (
                        /* Empty State */
                        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                            <BarChart3 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                            <p className="text-gray-500 text-lg font-medium">No calls recorded yet</p>
                            <p className="text-gray-400 mt-2">Start making calls to see performance metrics</p>
                            <Link
                                href="/"
                                className="inline-flex items-center gap-2 mt-6 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
                            >
                                <Bot className="w-4 h-4" />
                                Create an Agent
                            </Link>
                        </div>
                    )}
                </div>
            </div>
        </main>
    </div>
);
}
