'use client';

import { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
    Bot, Phone, Search, MoreVertical, Plus,
    LayoutGrid, BookOpen, PhoneCall, Layers, History, MessageSquare,
    BarChart3, Shield, HelpCircle, Bell, Sparkles, ChevronRight,
    Folder, Trash2, Edit3, Mic, Loader2, RefreshCw, Settings,
    LogOut, User, CreditCard, FileText, Key, Sliders, Zap,
    LineChart, Menu, X, MessageCircle, Copy
} from 'lucide-react';
import VoiceCallModal from '../../components/VoiceCallModal';
import ImportModal from '../../components/ImportModal';
import DuplicateAgentModal from '../../components/DuplicateAgentModal';
import { useToast } from '../../components/ToastProvider';
import Sidebar from '../components/Sidebar';

// API URL - uses relative path to work with both HTTP and HTTPS
const API_URL = '/api/';

interface Agent {
    id: number;
    name: string;
    display_name?: string | null;
    system_prompt: string;
    llm_model: string;
    voice: string;
    language: string;
    twilio_number: string | null;
    type?: string;
    last_edited?: string;
    edited_by?: string;
}

// Complete Sidebar Menu - ALL ITEMS
const SIDEBAR_MENU = {
    build: [
        { icon: Bot, label: 'Agents', href: '/', active: true },
        { icon: BookOpen, label: 'Knowledge Base', href: '/knowledge-base' },
        { icon: MessageCircle, label: 'Preview', href: '/chat-preview' },
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

export default function Dashboard() {
    const router = useRouter();
    const { showToast } = useToast();
    const [agents, setAgents] = useState<Agent[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [showVoiceCall, setShowVoiceCall] = useState(false);
    const [createLoading, setCreateLoading] = useState(false);
    const [showImportModal, setShowImportModal] = useState(false);
    const [showDuplicateModal, setShowDuplicateModal] = useState(false);
    const [selectedAgentForDuplicate, setSelectedAgentForDuplicate] = useState<Agent | null>(null);
    const [duplicateLoading, setDuplicateLoading] = useState(false);
    const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
    const [openMenuId, setOpenMenuId] = useState<number | null>(null);
    const [deleteLoading, setDeleteLoading] = useState<number | null>(null);
    const [showWorkspaceMenu, setShowWorkspaceMenu] = useState(false);
    const [workspaceType, setWorkspaceType] = useState<'voice' | 'chat'>('voice');
    const [showUserMenu, setShowUserMenu] = useState(false);
    const [sidebarOpen, setSidebarOpen] = useState(false); // Mobile sidebar state
    const menuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        fetchAgents();
        const interval = setInterval(fetchAgents, 30000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setShowWorkspaceMenu(false);
                setShowUserMenu(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const fetchAgents = async () => {
        try {
            const res = await axios.get<Agent[]>(`${API_URL}agents/`);
            const agentsWithMetadata = res.data.map((agent) => ({
                ...agent,
                name: agent.display_name || agent.name,
                type: agent.type || 'Single Prompt',
                voice: agent.voice || 'UK Voice',
                last_edited: new Date().toLocaleDateString('en-US', {
                    month: '2-digit',
                    day: '2-digit',
                    year: 'numeric'
                }) + ', ' + new Date().toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: false
                }),
                edited_by: 'team.oyik@gmail.com'
            }));
            setAgents(agentsWithMetadata);
        } catch (err) {
            console.error('Error fetching agents:', err);
            showToast('Failed to load agents', 'error');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const handleRefresh = () => {
        setRefreshing(true);
        fetchAgents();
        showToast('Refreshing data...', 'info');
    };

    const handleCreateAgentDirect = async () => {
        if (createLoading) return;

        setCreateLoading(true);
        try {
            const payload = {
                name: `New Agent ${new Date().toLocaleTimeString('en-US', { hour12: false })}`,
                system_prompt: 'u r a helpfull assitant',
                llm_model: 'gpt-4o-mini',
                llm_temperature: 0.2,
                voice: 'jessica',
                voice_speed: 1.0,
                language: 'en',
                welcome_message_type: 'user_speaks_first',
                welcome_message: '',
                max_call_duration: 1800,
                enable_recording: true,
                custom_params: {
                    tts_provider: 'deepgram',
                    llm_temperature: 0.2,
                    voice_speed: 1.0,
                    builtin_functions: {}
                }
            };

            const res = await axios.post<Agent>(`${API_URL}agents/`, payload);
            const newAgentId = res.data?.id;
            if (!newAgentId) {
                throw new Error('Agent created but ID was missing');
            }
            showToast('Agent created successfully', 'success');
            router.push(`/agent/${newAgentId}`);
        } catch (err: any) {
            console.error('Error creating agent:', err);
            const detail = err?.response?.data?.detail || 'Failed to create agent';
            showToast(detail, 'error');
        } finally {
            setCreateLoading(false);
        }
    };

    const handleDeleteAgent = async (agentId: number, e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();

        if (!confirm('Are you sure you want to delete this agent? This action cannot be undone.')) {
            setOpenMenuId(null);
            return;
        }

        setDeleteLoading(agentId);
        try {
            await axios.delete(`${API_URL}agents/${agentId}`);
            setAgents(agents.filter(a => a.id !== agentId));
            setOpenMenuId(null);
            showToast('Agent deleted successfully', 'success');
        } catch (err: any) {
            console.error('Error deleting agent:', err);
            const detail = err?.response?.data?.detail || 'Failed to delete agent';
            showToast(detail, 'error');
        } finally {
            setDeleteLoading(null);
        }
    };

    const handleWebCallClick = (agent: Agent, e?: React.MouseEvent) => {
        e?.preventDefault();
        e?.stopPropagation();
        setSelectedAgent(agent);
        setShowVoiceCall(true);
        setOpenMenuId(null);
    };

    const handleEditClick = (agentId: number, e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        router.push(`/agent/${agentId}`);
    };

    const handleImportClick = () => {
        setShowImportModal(true);
    };

    const handleDuplicateClick = (agent: Agent, e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setSelectedAgentForDuplicate(agent);
        setShowDuplicateModal(true);
        setOpenMenuId(null);
    };

    const handleDuplicateConfirm = async (newName: string) => {
        if (!selectedAgentForDuplicate) return;

        setDuplicateLoading(true);
        try {
            const response = await axios.post(`${API_URL}agents/${selectedAgentForDuplicate.id}/duplicate`, {
                name: newName
            });
            
            showToast('Agent duplicated successfully!', 'success');
            setShowDuplicateModal(false);
            setSelectedAgentForDuplicate(null);
            fetchAgents();
        } catch (err) {
            console.error('Error duplicating agent:', err);
            showToast('Failed to duplicate agent', 'error');
        } finally {
            setDuplicateLoading(false);
        }
    };

    const handleNavClick = (href: string, label: string, e: React.MouseEvent) => {
        if (workspaceType === 'chat' && href === '/') {
            e.preventDefault();
            router.push('/chat');
            return;
        }
        if (href === '#') {
            e.preventDefault();
            showToast(`${label} - Coming soon!`, 'info');
        }
    };

    const filteredAgents = agents.filter((agent) =>
        agent.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const getVoiceDisplay = (voice: string) => {
        const voiceMap: Record<string, string> = {
            'jessica': 'UK Voice',
            'mark': 'US Voice',
            'sarah': 'UK Voice',
            'michael': 'US Voice',
            'emma': 'UK Voice'
        };
        return voiceMap[voice] || voice;
    };

    const renderMenuSection = (title: string, items: any[]) => (
        <div className="mb-6">
            <h3 className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                {title}
            </h3>
            <div className="space-y-1">
                {items.map((item) => (
                    <Link
                        key={item.label}
                        href={item.href}
                        onClick={(e) => handleNavClick(item.href, item.label, e)}
                        className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${item.active
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
    );

    return (
        <div className="min-h-screen bg-gray-50 flex" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
            <Sidebar />

            {/* Main Content */}
            <main className="flex-1 flex flex-col min-w-0 lg:ml-60">
                {/* Mobile Header */}
                <header className="lg:hidden bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
                    <button
                        onClick={() => setSidebarOpen(true)}
                        className="p-2 hover:bg-gray-100 rounded-lg"
                    >
                        <Menu className="w-5 h-5" />
                    </button>
                    <div className="flex items-center gap-2">
                        <Sparkles className="w-5 h-5 text-gray-700" />
                        <span className="font-semibold text-gray-900">Retell AI</span>
                    </div>
                    <div className="w-9" />
                </header>



                {/* Agents List - Expanded to fill full width */}
                <div className="flex-1 flex flex-col bg-gray-50 min-w-0">
                    {/* Header */}
                    <header className="bg-white border-b border-gray-200 px-4 md:px-6 py-3 md:py-4">
                        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 md:gap-4">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2 md:gap-4">
                                    <h1 className="text-lg md:text-xl font-semibold text-gray-900">All Agents</h1>
                                    <button
                                        onClick={handleRefresh}
                                        disabled={refreshing}
                                        className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                                    >
                                        <RefreshCw className={`w-4 h-4 text-gray-400 ${refreshing ? 'animate-spin' : ''}`} />
                                    </button>
                                </div>
                            </div>

                            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3">
                                {/* Search */}
                                <div className="relative">
                                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                    <input
                                        type="text"
                                        placeholder="Search..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="w-full sm:w-40 md:w-64 pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-gray-400 transition-colors"
                                    />
                                </div>

                                {/* Import Button */}
                                <button
                                    onClick={handleImportClick}
                                    className="px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                                >
                                    Import
                                </button>

                                {/* Create Button */}
                                <button
                                    onClick={handleCreateAgentDirect}
                                    disabled={createLoading}
                                    className="flex items-center justify-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                                >
                                    {createLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4 md:hidden" />}
                                    <span className="hidden md:inline">{createLoading ? 'Creating...' : 'Create an Agent'}</span>
                                    <span className="md:hidden">{createLoading ? 'Creating...' : 'Create'}</span>
                                </button>
                            </div>
                        </div>
                    </header>

                    {/* Table */}
                    <div className="flex-1 p-6 overflow-auto">
                        {loading ? (
                            <div className="flex items-center justify-center h-64">
                                <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
                            </div>
                        ) : filteredAgents.length === 0 ? (
                            <div className="text-center py-20">
                                <Bot className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                                <p className="text-gray-500 text-sm mb-4">No agents found</p>
                                <button
                                    onClick={handleCreateAgentDirect}
                                    disabled={createLoading}
                                    className="px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800"
                                >
                                    {createLoading ? 'Creating...' : 'Create your first agent'}
                                </button>
                            </div>
                        ) : (
                            <>
                                {/* Desktop Table */}
                                <div className="hidden md:block bg-white rounded-lg border border-gray-200 overflow-hidden">
                                    <div className="overflow-x-auto">
                                        <table className="w-full">
                                            <thead>
                                                <tr className="border-b border-gray-100 bg-gray-50">
                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                        Agent Name
                                                    </th>
                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                        Agent Type
                                                    </th>
                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                        Voice
                                                    </th>
                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                        Phone
                                                    </th>
                                                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                        Edited by
                                                    </th>
                                                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">

                                                    </th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-gray-50">
                                                {filteredAgents.map((agent) => (
                                                    <tr
                                                        key={agent.id}
                                                        className="hover:bg-gray-50 transition-colors group cursor-pointer"
                                                        onClick={() => router.push(`/agent/${agent.id}`)}
                                                    >
                                                        <td className="px-4 py-3">
                                                            <div className="flex items-center gap-3">
                                                                <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                                                                    <Bot className="w-4 h-4 text-green-600" />
                                                                </div>
                                                                <span className="text-sm font-medium text-gray-900 truncate max-w-[150px]">
                                                                    {agent.name}
                                                                </span>
                                                            </div>
                                                        </td>
                                                        <td className="px-4 py-3">
                                                            <span className="text-sm text-gray-600">
                                                                {agent.type}
                                                            </span>
                                                        </td>
                                                        <td className="px-4 py-3">
                                                            <div className="flex items-center gap-2">
                                                                <div className="w-5 h-5 bg-gray-100 rounded-full flex items-center justify-center text-xs">
                                                                    👤
                                                                </div>
                                                                <span className="text-sm text-gray-600">
                                                                    {getVoiceDisplay(agent.voice)}
                                                                </span>
                                                            </div>
                                                        </td>
                                                        <td className="px-4 py-3">
                                                            {agent.twilio_number ? (
                                                                <span className="inline-flex items-center px-2.5 py-1 bg-blue-50 text-blue-700 text-xs font-medium rounded-full">
                                                                    {agent.twilio_number}
                                                                </span>
                                                            ) : (
                                                                <span className="text-sm text-gray-400">-</span>
                                                            )}
                                                        </td>
                                                        <td className="px-4 py-3">
                                                            <div className="text-sm text-gray-600">
                                                                {agent.last_edited}
                                                            </div>
                                                        </td>
                                                        <td className="px-4 py-3 text-right relative z-50" onClick={(e) => e.stopPropagation()}>
                                                            <button
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    setOpenMenuId(openMenuId === agent.id ? null : agent.id);
                                                                }}
                                                                className="p-1.5 hover:bg-gray-200 rounded transition-colors opacity-0 group-hover:opacity-100"
                                                            >
                                                                <MoreVertical className="w-4 h-4 text-gray-400" />
                                                            </button>

                                                            {openMenuId === agent.id && (
                                                                <div className="absolute right-0 top-full mt-1 w-40 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-[100]">
                                                                    <button
                                                                        onClick={(e) => handleWebCallClick(agent, e)}
                                                                        className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                                                                    >
                                                                        <Mic className="w-4 h-4" />
                                                                        Test Audio
                                                                    </button>
                                                                    <button
                                                                        onClick={(e) => handleEditClick(agent.id, e)}
                                                                        className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                                                                    >
                                                                        <Edit3 className="w-4 h-4" />
                                                                        Edit
                                                                    </button>
                                                                    <button
                                                                        onClick={(e) => handleDuplicateClick(agent, e)}
                                                                        className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
                                                                    >
                                                                        <Copy className="w-4 h-4" />
                                                                        Duplicate
                                                                    </button>
                                                                    <button
                                                                        onClick={(e) => handleDeleteAgent(agent.id, e)}
                                                                        disabled={deleteLoading === agent.id}
                                                                        className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2 disabled:opacity-50"
                                                                    >
                                                                        {deleteLoading === agent.id ? (
                                                                            <Loader2 className="w-4 h-4 animate-spin" />
                                                                        ) : (
                                                                            <Trash2 className="w-4 h-4" />
                                                                        )}
                                                                        Delete
                                                                    </button>
                                                                </div>
                                                            )}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>

                                {/* Mobile Card View */}
                                <div className="md:hidden space-y-3 p-4">
                                    {filteredAgents.map((agent) => (
                                        <div
                                            key={agent.id}
                                            className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-sm transition-shadow"
                                        >
                                            <Link href={`/agent/${agent.id}`} className="block">
                                                <div className="flex items-start justify-between">
                                                    <div className="flex items-center gap-3">
                                                        <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0">
                                                            <Bot className="w-5 h-5 text-green-600" />
                                                        </div>
                                                        <div className="min-w-0">
                                                            <h3 className="text-sm font-medium text-gray-900 truncate">
                                                                {agent.name}
                                                            </h3>
                                                            <p className="text-xs text-gray-500">
                                                                {agent.type}
                                                            </p>
                                                        </div>
                                                    </div>
                                                    <button
                                                        onClick={(e) => {
                                                            e.preventDefault();
                                                            e.stopPropagation();
                                                            setOpenMenuId(openMenuId === agent.id ? null : agent.id);
                                                        }}
                                                        className="p-1.5 hover:bg-gray-100 rounded"
                                                    >
                                                        <MoreVertical className="w-4 h-4 text-gray-400" />
                                                    </button>
                                                </div>

                                                <div className="mt-3 flex flex-wrap gap-2">
                                                    <span className="inline-flex items-center px-2 py-1 bg-gray-100 text-xs text-gray-600 rounded">
                                                        🎤 {getVoiceDisplay(agent.voice)}
                                                    </span>
                                                    {agent.twilio_number && (
                                                        <span className="inline-flex items-center px-2 py-1 bg-blue-50 text-xs text-blue-700 rounded">
                                                            📞 {agent.twilio_number}
                                                        </span>
                                                    )}
                                                </div>
                                            </Link>

                                            {/* Mobile Action Menu */}
                                            {openMenuId === agent.id && (
                                                <div className="mt-3 pt-3 border-t border-gray-100 flex gap-2">
                                                    <button
                                                        onClick={(e) => handleWebCallClick(agent, e)}
                                                        className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700"
                                                    >
                                                        <Phone className="w-4 h-4" />
                                                        Call
                                                    </button>
                                                    <button
                                                        onClick={(e) => handleEditClick(agent.id, e)}
                                                        className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border border-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-50"
                                                    >
                                                        <Edit3 className="w-4 h-4" />
                                                        Edit
                                                    </button>
                                                    <button
                                                        onClick={(e) => handleDuplicateClick(agent, e)}
                                                        className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border border-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-50"
                                                    >
                                                        <Copy className="w-4 h-4" />
                                                        Duplicate
                                                    </button>
                                                    <button
                                                        onClick={(e) => handleDeleteAgent(agent.id, e)}
                                                        className="flex-1 flex items-center justify-center gap-2 px-3 py-2 border border-red-200 text-red-600 text-sm rounded-lg hover:bg-red-50"
                                                    >
                                                        {deleteLoading === agent.id ? (
                                                            <Loader2 className="w-4 h-4 animate-spin" />
                                                        ) : (
                                                            <>
                                                                <Trash2 className="w-4 h-4" />
                                                                Delete
                                                            </>
                                                        )}
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </main>

            {/* Modals */}
            <VoiceCallModal
                isOpen={showVoiceCall}
                onClose={() => setShowVoiceCall(false)}
                agentId={selectedAgent?.id || 0}
                agentName={selectedAgent?.name || ''}
            />

            <ImportModal
                isOpen={showImportModal}
                onClose={() => setShowImportModal(false)}
            />

            <DuplicateAgentModal
                isOpen={showDuplicateModal}
                onClose={() => {
                    setShowDuplicateModal(false);
                    setSelectedAgentForDuplicate(null);
                }}
                onConfirm={handleDuplicateConfirm}
                originalAgentName={selectedAgentForDuplicate?.name || ''}
                isLoading={duplicateLoading}
            />
        </div>
    );
}
