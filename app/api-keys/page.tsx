'use client';

import Link from 'next/link';
import {
    Bot, BookOpen, Phone, PhoneCall, History, MessageSquare,
    BarChart3, Settings, Key, Sparkles,
    Copy, Plus, Trash2
} from 'lucide-react';
import { useState } from 'react';
import { useToast } from '../../components/ToastProvider';

export default function APIKeysPage() {
    const { showToast } = useToast();
    const [apiKeys, setApiKeys] = useState([
        { id: '1', name: 'Production Key', key: 'sk_live_••••••••••••••••••••••••', created: '2024-01-15', lastUsed: '2 hours ago' },
    ]);

    const handleCopy = (key: string) => {
        navigator.clipboard.writeText(key);
        showToast('API key copied to clipboard', 'success');
    };

    const handleCreate = () => {
        showToast('Create new API key - Coming soon!', 'info');
    };

    const handleDelete = (id: string) => {
        showToast('Delete API key - Coming soon!', 'info');
    };

    return (
        <div className="min-h-screen bg-gray-50" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
            <main>
                <div className="max-w-4xl mx-auto">
                    <div className="flex items-center justify-between mb-8">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
                                <Key className="w-5 h-5 text-yellow-600" />
                            </div>
                            <h1 className="text-2xl font-semibold text-gray-900">API Keys</h1>
                        </div>
                        <button
                            onClick={handleCreate}
                            className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800"
                        >
                            <Plus className="w-4 h-4" />
                            Create API Key
                        </button>
                    </div>

                    <div className="bg-white rounded-xl border border-gray-200">
                        <div className="p-4 border-b border-gray-100">
                            <p className="text-sm text-gray-500">
                                Use these keys to authenticate your API requests. Keep them secure and never share them publicly.
                            </p>
                        </div>

                        <div className="divide-y divide-gray-100">
                            {apiKeys.map((apiKey) => (
                                <div key={apiKey.id} className="p-4 flex items-center justify-between">
                                    <div>
                                        <h3 className="font-medium text-gray-900">{apiKey.name}</h3>
                                        <p className="text-sm text-gray-500 font-mono mt-1">{apiKey.key}</p>
                                        <div className="flex gap-4 mt-2 text-xs text-gray-400">
                                            <span>Created: {apiKey.created}</span>
                                            <span>Last used: {apiKey.lastUsed}</span>
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleCopy(apiKey.key)}
                                            className="p-2 hover:bg-gray-100 rounded-lg text-gray-600"
                                        >
                                            <Copy className="w-4 h-4" />
                                        </button>
                                        <button
                                            onClick={() => handleDelete(apiKey.id)}
                                            className="p-2 hover:bg-red-50 rounded-lg text-red-600"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="mt-6 p-4 bg-blue-50 border border-blue-100 rounded-lg">
                        <h4 className="text-sm font-medium text-blue-900 mb-1">Security Tip</h4>
                        <p className="text-sm text-blue-700">
                            Rotate your API keys regularly and never commit them to version control. Use environment variables instead.
                        </p>
                    </div>
                </div>
            </main>
        </div>
    );
}