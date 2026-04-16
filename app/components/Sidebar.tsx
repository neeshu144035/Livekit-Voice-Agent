'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import {
    Bot, Phone, BookOpen, PhoneCall, Layers, History, MessageSquare,
    BarChart3, Shield, HelpCircle, Bell, Sparkles, ChevronRight,
    Folder, Trash2, Edit3, Mic, Loader2, RefreshCw, Settings,
    LogOut, User, CreditCard, FileText, Key, Sliders, Zap,
    LineChart, Menu, X, MessageCircle, ChevronDown
} from 'lucide-react';

const SIDEBAR_MENU = {
    build: [
        { icon: Bot, label: 'Agents', href: '/' },
        { icon: BookOpen, label: 'Knowledge Base', href: '/knowledge-base' },
        { icon: MessageCircle, label: 'Preview', href: '/chat-preview' },
        { icon: MessageSquare, label: 'Chat Widget', href: '/chatbot-dashboard' },
    ],
    deploy: [
        { icon: Phone, label: 'Phone Numbers', href: '/phone-numbers' },
        { icon: PhoneCall, label: 'Batch Call', href: '/batch-call' },
    ],
    monitor: [
        { icon: History, label: 'Call History', href: '/call-history' },
        { icon: MessageSquare, label: 'Chat History', href: '/chat-history' },
        { icon: BarChart3, label: 'Analytics', href: '/analytics' },
    ],
    settings: [
        { icon: Settings, label: 'Settings', href: '/settings' },
        { icon: Key, label: 'API Keys', href: '/api-keys' },
    ]
};

export default function Sidebar() {
    const router = useRouter();
    const pathname = usePathname();
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [showWorkspaceMenu, setShowWorkspaceMenu] = useState(false);
    const [workspaceType, setWorkspaceType] = useState<'voice' | 'chat'>('voice');
    const menuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setShowWorkspaceMenu(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleNavClick = (href: string, label: string, e: React.MouseEvent) => {
        if (href === '#') {
            e.preventDefault();
        }
    };

    const isActive = (href: string) => {
        if (href === '/') {
            return pathname === '/';
        }
        return pathname.startsWith(href);
    };

    return (
        <>
            {/* Mobile Sidebar Overlay */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 bg-black/50 z-40 lg:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside className={`
                fixed lg:static inset-y-0 left-0 z-50 
                w-60 bg-white border-r border-gray-200 
                transform transition-transform duration-200 ease-in-out
                ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
            `}>
                {/* Mobile Close Button */}
                <button
                    onClick={() => setSidebarOpen(false)}
                    className="lg:hidden absolute top-4 right-4 p-1"
                >
                    <X className="w-5 h-5" />
                </button>

                {/* Logo */}
                <div className="p-4 border-b border-gray-100">
                    <div className="flex items-center gap-2">
                        <img 
                            src="/INSTA WHITE LOGO and BLUE BG.jpg.jpeg" 
                            alt="Oyik AI" 
                            className="w-8 h-8 rounded-lg object-cover"
                        />
                        <span className="text-sm font-bold text-gray-900">Oyik AI</span>
                    </div>
                </div>

                {/* Workspace & User Info */}
                <div className="p-3 border-b border-gray-100">
                    <button
                        onClick={() => setShowWorkspaceMenu(!showWorkspaceMenu)}
                        className="w-full flex items-center justify-between p-2 hover:bg-gray-50 rounded-lg"
                    >
                        <div className="flex items-center gap-2">
                            <div className="w-6 h-6 bg-blue-100 rounded flex items-center justify-center">
                                {workspaceType === 'voice' ? (
                                    <Phone className="w-3.5 h-3.5 text-blue-600" />
                                ) : (
                                    <MessageCircle className="w-3.5 h-3.5 text-blue-600" />
                                )}
                            </div>
                            <span className="text-sm font-medium text-gray-900 capitalize">{workspaceType}</span>
                        </div>
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                    </button>

                    {showWorkspaceMenu && (
                        <div className="mt-2 flex gap-1 p-1 bg-gray-100 rounded-lg">
                            <button
                                onClick={() => { setWorkspaceType('voice'); setShowWorkspaceMenu(false); }}
                                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded text-xs font-medium transition-colors ${workspaceType === 'voice'
                                        ? 'bg-white text-gray-900 shadow-sm'
                                        : 'text-gray-500 hover:text-gray-700'
                                    }`}
                            >
                                <Phone className="w-3.5 h-3.5" />
                                Voice
                            </button>
                            <button
                                onClick={() => { setWorkspaceType('chat'); setShowWorkspaceMenu(false); router.push('/chatbot-dashboard'); }}
                                className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded text-xs font-medium transition-colors ${workspaceType === 'chat'
                                        ? 'bg-white text-gray-900 shadow-sm'
                                        : 'text-gray-500 hover:text-gray-700'
                                    }`}
                            >
                                <MessageCircle className="w-3.5 h-3.5" />
                                Chat
                            </button>
                        </div>
                    )}
                </div>

                {/* Navigation Menu */}
                <nav className="p-3 space-y-6 overflow-y-auto h-[calc(100vh-140px)]">
                    {Object.entries(SIDEBAR_MENU).map(([section, items]) => (
                        <div key={section}>
                            <h3 className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                                {section}
                            </h3>
                            <div className="space-y-1">
                                {items.map((item) => (
                                    <Link
                                        key={item.label}
                                        href={item.href}
                                        onClick={(e) => handleNavClick(item.href, item.label, e)}
                                        className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${isActive(item.href)
                                                ? 'bg-gray-100 text-gray-900 font-medium'
                                                : 'text-gray-600 hover:bg-gray-50'
                                            }`}
                                    >
                                        <item.icon className="w-4 h-4" />
                                        {item.label}
                                    </Link>
                                ))}
                            </div>
                        </div>
                    ))}
                </nav>
            </aside>

            {/* Mobile Menu Button - Can be used by parent components */}
            <button
                onClick={() => setSidebarOpen(true)}
                className="lg:hidden fixed top-4 left-4 z-30 p-2 bg-white rounded-lg shadow"
            >
                <Menu className="w-5 h-5" />
            </button>
        </>
    );
}
