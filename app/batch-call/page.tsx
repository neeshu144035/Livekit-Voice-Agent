'use client';

import Link from 'next/link';
import {
    Bot, BookOpen, Phone, PhoneCall, History, MessageSquare,
    BarChart3, Settings, Key, Sparkles, Plus, Calendar, Upload
} from 'lucide-react';
import { useToast } from '../../components/ToastProvider';

export default function BatchCallPage() {
    const { showToast } = useToast();

    return (
        <div className="min-h-screen bg-gray-50" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
            {/* Main Content */}
            <main className="min-w-0">
                <div className="p-4 md:p-8">
                    <div className="max-w-6xl mx-auto">
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
                            <div className="flex items-center gap-3">
                                <div className="w-8 sm:w-10 bg-purple-100 rounded-lg flex items-center justify-center">
                                    <PhoneCall className="w-4 sm:w-5 text-purple-600" />
                                </div>
                                <h1 className="text-xl sm:text-2xl font-semibold text-gray-900">Batch Call</h1>
                            </div>
                            <button
                                onClick={() => showToast('Create campaign - Coming soon!', 'info')}
                                className="flex items-center justify-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800"
                            >
                                <Plus className="w-4 h-4" />
                                New Campaign
                            </button>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 mb-8">
                            <div className="bg-white p-4 sm:p-6 rounded-xl border border-gray-200">
                                <h3 className="text-sm font-medium text-gray-500 mb-2">Total Calls</h3>
                                <p className="text-2xl sm:text-3xl font-semibold text-gray-900">0</p>
                            </div>
                            <div className="bg-white p-4 sm:p-6 rounded-xl border border-gray-200">
                                <h3 className="text-sm font-medium text-gray-500 mb-2">Completed</h3>
                                <p className="text-2xl sm:text-3xl font-semibold text-green-600">0</p>
                            </div>
                            <div className="bg-white p-4 sm:p-6 rounded-xl border border-gray-200">
                                <h3 className="text-sm font-medium text-gray-500 mb-2">Failed</h3>
                                <p className="text-2xl sm:text-3xl font-semibold text-red-600">0</p>
                            </div>
                        </div>

                        <div className="bg-white rounded-xl border border-gray-200 p-6 sm:p-12 text-center">
                            <div className="w-12 sm:w-16 h-12 sm:h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Calendar className="w-6 sm:w-8 text-gray-400" />
                            </div>
                            <h2 className="text-lg font-medium text-gray-900 mb-2">No Campaigns Yet</h2>
                            <p className="text-gray-500 mb-6">Launch bulk calling campaigns to reach multiple contacts</p>
                            <div className="flex flex-col sm:flex-row justify-center gap-3">
                                <button
                                    onClick={() => showToast('Import contacts - Coming soon!', 'info')}
                                    className="flex items-center justify-center gap-2 px-4 py-2 border border-gray-200 rounded-lg text-gray-700 hover:bg-gray-50"
                                >
                                    <Upload className="w-4 h-4" />
                                    Import Contacts
                                </button>
                                <button
                                    onClick={() => showToast('Create campaign - Coming soon!', 'info')}
                                    className="flex items-center justify-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800"
                                >
                                    <Plus className="w-4 h-4" />
                                    Create Campaign
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}