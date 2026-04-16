'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';
import {
    Bot, BookOpen, Phone, PhoneCall, History, MessageSquare,
    BarChart3, Settings, Key, Sparkles, Users, ChevronDown,
    HelpCircle, Bell, Zap, LayoutGrid, MessageCircle
} from 'lucide-react';

export default function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const [showModeDropdown, setShowModeDropdown] = useState(false);
    const [workspaceType, setWorkspaceType] = useState<'voice' | 'chat'>('voice');

    // Don't show sidebar on agent edit/create pages
    if (pathname?.startsWith('/agent/')) {
        return null;
    }

    const isActive = (href: string) => {
        if (href === '/') {
            return pathname === '/';
        }
        return pathname?.startsWith(href);
    };

    const handleModeChange = (mode: string) => {
        setShowModeDropdown(false);
        if (mode === 'chat') {
            setWorkspaceType('chat');
            router.push('/chatbot-dashboard');
        } else {
            setWorkspaceType('voice');
            router.push('/');
        }
    };

    // Check if currently in chat mode
    const isChatMode = pathname === '/chatbot-dashboard';

    return (
        <aside className="fixed inset-y-0 left-0 w-60 bg-white border-r border-gray-200 flex flex-col z-50">
            {/* Logo */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100">
                <img 
                    src="/INSTA WHITE LOGO and BLUE BG.jpg.jpeg" 
                    alt="Oyik AI" 
                    className="w-8 h-8 rounded-lg object-cover"
                />
                <span className="text-lg font-bold text-gray-900">Oyik AI</span>
            </div>

            {/* Workspace */}
            <div className="px-4 py-2">
                <div className="relative">
                    <button
                        className="w-full flex items-center justify-between px-3 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg border border-gray-200 transition-colors"
                        onClick={() => setShowModeDropdown(!showModeDropdown)}
                    >
                        <div className="flex items-center gap-2">
                            <div className="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center text-white text-xs font-bold">
                                {workspaceType === 'voice' ? (
                                    <Phone className="w-3.5 h-3.5" />
                                ) : (
                                    <MessageCircle className="w-3.5 h-3.5" />
                                )}
                            </div>
                            <span className="text-sm font-medium text-gray-900 capitalize">{workspaceType}</span>
                        </div>
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                    </button>

                    {/* Voice/Chat Toggle Dropdown */}
                    {showModeDropdown && (
                        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
                            <button
                                onClick={() => handleModeChange('voice')}
                                className={`w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 rounded-t-lg ${workspaceType === 'voice' ? 'bg-purple-50 text-purple-600' : 'text-gray-700'
                                    }`}
                            >
                                <Phone className="w-4 h-4" />
                                Voice
                                {workspaceType === 'voice' && <span className="ml-auto text-xs text-purple-600">✓</span>}
                            </button>
                            <button
                                onClick={() => handleModeChange('chat')}
                                className={`w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50 rounded-b-lg ${workspaceType === 'chat' ? 'bg-purple-50 text-purple-600' : 'text-gray-700'
                                    }`}
                            >
                                <MessageCircle className="w-4 h-4" />
                                Chat
                                {workspaceType === 'chat' && <span className="ml-auto text-xs text-purple-600">✓</span>}
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 overflow-y-auto px-2 py-2">
                {/* BUILD */}
                <div className="mb-4">
                    <p className="px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">BUILD</p>
                    <div className="mt-1 space-y-1">
                        <Link
                            href="/"
                            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${isActive('/') ? 'text-purple-600 font-medium' : 'text-gray-700 hover:bg-gray-50'
                                }`}
                        >
                            <Bot className="w-4 h-4" />
                            Agents
                        </Link>
                        <Link
                            href="/knowledge-base"
                            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${isActive('/knowledge-base') ? 'text-purple-600 font-medium' : 'text-gray-700 hover:bg-gray-50'
                                }`}
                        >
                            <BookOpen className="w-4 h-4" />
                            Knowledge Base
                        </Link>
                    </div>
                </div>

                {/* DEPLOY */}
                <div className="mb-4">
                    <p className="px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">DEPLOY</p>
                    <div className="mt-1 space-y-1">
                        <Link
                            href="/phone-numbers"
                            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${isActive('/phone-numbers') ? 'text-purple-600 font-medium' : 'text-gray-700 hover:bg-gray-50'
                                }`}
                        >
                            <Phone className="w-4 h-4" />
                            Phone Numbers
                        </Link>
                        <Link
                            href="/batch-call"
                            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${isActive('/batch-call') ? 'text-purple-600 font-medium' : 'text-gray-700 hover:bg-gray-50'
                                }`}
                        >
                            <PhoneCall className="w-4 h-4" />
                            Batch Call
                        </Link>
                    </div>
                </div>

                {/* MONITOR */}
                <div className="mb-4">
                    <p className="px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">MONITOR</p>
                    <div className="mt-1 space-y-1">
                        <Link
                            href="/call-history"
                            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${isActive('/call-history') ? 'text-purple-600 font-medium' : 'text-gray-700 hover:bg-gray-50'
                                }`}
                        >
                            <History className="w-4 h-4" />
                            Call History
                        </Link>
                        <Link
                            href="/chat-history"
                            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${isActive('/chat-history') ? 'text-purple-600 font-medium' : 'text-gray-700 hover:bg-gray-50'
                                }`}
                        >
                            <MessageSquare className="w-4 h-4" />
                            Chat History
                        </Link>
                        <Link
                            href="/analytics"
                            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${isActive('/analytics') ? 'text-purple-600 font-medium' : 'text-gray-700 hover:bg-gray-50'
                                }`}
                        >
                            <BarChart3 className="w-4 h-4" />
                            Analytics
                        </Link>
                    </div>
                </div>
            </nav>

            {/* Settings */}
            <div className="px-2 py-2 border-t border-gray-200">
                <p className="px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">SETTINGS</p>
                <div className="mt-1 space-y-1">
                    <Link
                        href="/settings"
                        className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${isActive('/settings') ? 'text-purple-600 font-medium' : 'text-gray-700 hover:bg-gray-50'
                            }`}
                    >
                        <Settings className="w-4 h-4" />
                        Settings
                    </Link>
                    <Link
                        href="/api-keys"
                        className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${isActive('/api-keys') ? 'text-purple-600 font-medium' : 'text-gray-700 hover:bg-gray-50'
                            }`}
                    >
                        <Key className="w-4 h-4" />
                        API Keys
                    </Link>
                </div>
            </div>

            {/* Bottom - Account */}
            <div className="px-2 py-2 border-t border-gray-200">
                <button className="w-full flex items-center justify-between px-3 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg border border-gray-200 transition-colors">
                    <div className="flex items-center gap-2">
                        <div className="w-5 h-5 bg-blue-600 rounded flex items-center justify-center">
                            <Zap className="w-3 h-3 text-white" />
                        </div>
                        <span className="text-sm font-medium text-gray-900">Pay As You Go</span>
                    </div>
                    <ChevronDown className="w-4 h-4 text-gray-400" />
                </button>

                <button className="w-full flex items-center justify-between px-3 py-2 mt-2 hover:bg-gray-50 rounded-lg transition-colors">
                    <div className="flex items-center gap-2">
                        <div className="w-5 h-5 bg-pink-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                            O
                        </div>
                        <span className="text-sm text-gray-600 truncate">team.oyik@gmail...</span>
                    </div>
                    <ChevronDown className="w-4 h-4 text-gray-400" />
                </button>

                <div className="flex items-center gap-4 px-3 mt-2">
                    <button className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700">
                        <HelpCircle className="w-4 h-4" />
                        Help
                    </button>
                    <button className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700">
                        <Bell className="w-4 h-4" />
                        Updates
                    </button>
                </div>
            </div>
        </aside>
    );
}
