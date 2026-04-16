'use client';

import Link from 'next/link';
import {
    Bot, BookOpen, Phone, PhoneCall, History, MessageSquare,
    BarChart3, Settings, Key, Sparkles, ArrowLeft
} from 'lucide-react';

export default function ChatHistoryPage() {
    return (
        <div className="min-h-screen bg-gray-50" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
            <main>
                <div className="max-w-6xl mx-auto">
                    <div className="flex items-center gap-3 mb-8">
                        <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                            <MessageSquare className="w-5 h-5 text-blue-600" />
                        </div>
                        <h1 className="text-2xl font-semibold text-gray-900">Chat History</h1>
                    </div>

                    <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                        <p className="text-gray-500">No chat conversations yet</p>
                        <p className="text-sm text-gray-400 mt-2">Chat history will appear here when you test agents</p>
                    </div>
                </div>
            </main>
        </div>
    );
}