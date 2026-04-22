'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';
import {
    Bot,
    Phone,
    Plus,
    Search,
    LayoutDashboard,
    BarChart3,
    X,
    Cpu,
    Play,
    Edit,
    Trash2,
    Clock,
    TrendingUp,
} from 'lucide-react';
import VoiceCallModal from './components/VoiceCallModal';

const API_URL = 'http://13.135.81.172:8000';

interface Agent {
    id: number;
    agent_id: string;
    name: string;
    description: string | null;
    llm_model: string;
    voice_id: string;
    status: string;
    created_at: string;
    updated_at: string;
}

interface Analytics {
    total_calls: number;
    completed_calls: number;
    failed_calls: number;
    success_rate: number;
    total_duration_seconds: number;
    average_duration_seconds: number;
    total_cost_usd: number;
}

interface Call {
    call_id: string;
    agent_id: number;
    status: string;
    call_type: string;
    direction: string;
    from_number: string | null;
    to_number: string | null;
    started_at: string | null;
    ended_at: string | null;
    duration_seconds: number | null;
    created_at: string;
}

export default function Dashboard() {
    const [agents, setAgents] = useState<Agent[]>([]);
    const [calls, setCalls] = useState<Call[]>([]);
    const [analytics, setAnalytics] = useState<Analytics | null>(null);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [activeTab, setActiveTab] = useState<'dashboard' | 'agents' | 'calls' | 'phone'>('dashboard');
    const [newAgent, setNewAgent] = useState({
        name: '',
        description: '',
        system_prompt: 'You are a helpful and friendly AI voice assistant. Keep responses short and concise.',
        llm_model: 'moonshot-v1-8k',
        voice_id: 'jessica',
        stt_language: 'en',
        temperature: 0.7,
        max_tokens: 150,
        welcome_message: 'Hello, how can I help you today?',
        enable_interruptions: true,
        silence_timeout_ms: 1500,
        max_call_duration: 3600,
    });
    const [callingAgentId, setCallingAgentId] = useState<number | null>(null);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [agentsRes, callsRes, analyticsRes] = await Promise.all([
                axios.get(`${API_URL}/agents/`),
                axios.get(`${API_URL}/calls?limit=50`),
                axios.get(`${API_URL}/analytics?days=7`),
            ]);
            setAgents(agentsRes.data);
            setCalls(callsRes.data);
            setAnalytics(analyticsRes.data);
        } catch (err) {
            console.error('Error fetching data:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateAgent = async () => {
        try {
            await axios.post(`${API_URL}/agents`, newAgent);
            setShowCreateModal(false);
            setNewAgent({
                name: '',
                description: '',
                system_prompt: 'You are a helpful and friendly AI voice assistant. Keep responses short and concise.',
                llm_model: 'moonshot-v1-8k',
                voice_id: 'jessica',
                stt_language: 'en',
                temperature: 0.7,
                max_tokens: 150,
                welcome_message: 'Hello, how can I help you today?',
                enable_interruptions: true,
                silence_timeout_ms: 1500,
                max_call_duration: 3600,
            });
            fetchData();
        } catch (err) {
            console.error('Error creating agent:', err);
        }
    };

    const handleDeleteAgent = async (agentId: number) => {
        if (!confirm('Are you sure you want to delete this agent?')) return;
        try {
            await axios.delete(`${API_URL}/agents/${agentId}`);
            fetchData();
        } catch (err) {
            console.error('Error deleting agent:', err);
        }
    };

    const filteredAgents = agents.filter((agent) =>
        agent.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const sidebarItems = [
        { icon: LayoutDashboard, label: 'Dashboard', key: 'dashboard' },
        { icon: Bot, label: 'Agents', key: 'agents' },
        { icon: Phone, label: 'Call History', key: 'calls' },
        { icon: BarChart3, label: 'Phone Numbers', key: 'phone' },
    ];

    const formatDuration = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}m ${secs}s`;
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed': return 'bg-green-100 text-green-700';
            case 'in-progress': return 'bg-blue-100 text-blue-700';
            case 'failed': return 'bg-red-100 text-red-700';
            case 'pending': return 'bg-yellow-100 text-yellow-700';
            default: return 'bg-gray-100 text-gray-700';
        }
    };

    return (
        <div className="flex h-screen bg-gray-50">
            <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
                <div className="px-6 py-5 border-b border-gray-200">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center">
                            <Cpu className="w-4 h-4 text-white" />
                        </div>
                        <span className="text-lg font-semibold text-black tracking-tight">Voice AI</span>
                    </div>
                </div>

                <nav className="flex-1 px-3 py-4 space-y-1">
                    {sidebarItems.map((item) => {
                        const Icon = item.icon;
                        return (
                            <button
                                key={item.key}
                                onClick={() => setActiveTab(item.key as any)}
                                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                                    activeTab === item.key ? 'bg-black text-white shadow-sm' : 'text-gray-600 hover:bg-gray-100'
                                }`}
                            >
                                <Icon className="w-[18px] h-[18px]" />
                                {item.label}
                            </button>
                        );
                    })}
                </nav>

                <div className="px-4 py-4 border-t border-gray-200">
                    <div className="flex items-center gap-3 px-2">
                        <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                            <span className="text-xs font-semibold text-gray-600">A</span>
                        </div>
                        <div>
                            <p className="text-sm font-medium text-black">Admin</p>
                            <p className="text-xs text-gray-400">admin@oyik.info</p>
                        </div>
                    </div>
                </div>
            </aside>

            <main className="flex-1 overflow-auto bg-gray-50">
                <header className="sticky top-0 z-10 bg-white border-b border-gray-200 px-8 py-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-2xl font-bold text-black">
                                {activeTab === 'dashboard' && 'Dashboard'}
                                {activeTab === 'agents' && 'Voice Agents'}
                                {activeTab === 'calls' && 'Call History'}
                                {activeTab === 'phone' && 'Phone Numbers'}
                            </h1>
                            <p className="text-sm text-gray-500 mt-0.5">
                                {activeTab === 'dashboard' && 'Overview of your voice AI platform'}
                                {activeTab === 'agents' && 'Manage your AI voice agents'}
                                {activeTab === 'calls' && 'View all past and ongoing calls'}
                                {activeTab === 'phone' && 'Manage phone numbers for inbound calls'}
                            </p>
                        </div>
                        {activeTab === 'agents' && (
                            <button onClick={() => setShowCreateModal(true)} className="flex items-center gap-2 bg-black text-white px-4 py-2.5 rounded-lg text-sm font-medium">
                                <Plus className="w-4 h-4" /> Create Agent
                            </button>
                        )}
                    </div>
                </header>

                <div className="p-8">
                    {loading ? (
                        <div className="flex items-center justify-center py-20">
                            <div className="w-6 h-6 border-2 border-gray-200 border-t-black rounded-full animate-spin" />
                        </div>
                    ) : activeTab === 'dashboard' ? (
                        <div className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                                <div className="bg-white rounded-xl p-6 shadow-sm border">
                                    <div className="flex items-center justify-between">
                                        <div><p className="text-sm text-gray-500">Total Calls</p><p className="text-3xl font-bold mt-1">{analytics?.total_calls || 0}</p></div>
                                        <div className="w-12 h-12 bg-blue-50 rounded-lg flex items-center justify-center"><Phone className="w-6 h-6 text-blue-600" /></div>
                                    </div>
                                </div>
                                <div className="bg-white rounded-xl p-6 shadow-sm border">
                                    <div className="flex items-center justify-between">
                                        <div><p className="text-sm text-gray-500">Completed</p><p className="text-3xl font-bold mt-1 text-green-600">{analytics?.completed_calls || 0}</p></div>
                                        <div className="w-12 h-12 bg-green-50 rounded-lg flex items-center justify-center"><TrendingUp className="w-6 h-6 text-green-600" /></div>
                                    </div>
                                </div>
                                <div className="bg-white rounded-xl p-6 shadow-sm border">
                                    <div className="flex items-center justify-between">
                                        <div><p className="text-sm text-gray-500">Avg Duration</p><p className="text-3xl font-bold mt-1">{formatDuration(analytics?.average_duration_seconds || 0)}</p></div>
                                        <div className="w-12 h-12 bg-purple-50 rounded-lg flex items-center justify-center"><Clock className="w-6 h-6 text-purple-600" /></div>
                                    </div>
                                </div>
                                <div className="bg-white rounded-xl p-6 shadow-sm border">
                                    <div className="flex items-center justify-between">
                                        <div><p className="text-sm text-gray-500">Success Rate</p><p className="text-3xl font-bold mt-1">{(analytics?.success_rate || 0).toFixed(1)}%</p></div>
                                        <div className="w-12 h-12 bg-yellow-50 rounded-lg flex items-center justify-center"><BarChart3 className="w-6 h-6 text-yellow-600" /></div>
                                    </div>
                                </div>
                            </div>

                            <div className="bg-white rounded-xl shadow-sm border">
                                <div className="px-6 py-4 border-b flex justify-between items-center">
                                    <h2 className="text-lg font-semibold">Recent Agents</h2>
                                    <button onClick={() => setActiveTab('agents')} className="text-sm text-blue-600">View all</button>
                                </div>
                                <div className="divide-y">
                                    {agents.slice(0, 5).map((agent) => (
                                        <div key={agent.id} className="px-6 py-4 flex justify-between items-center hover:bg-gray-50">
                                            <div className="flex items-center gap-4">
                                                <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center"><Bot className="w-5 h-5 text-gray-600" /></div>
                                                <div><p className="font-medium">{agent.name}</p><p className="text-sm text-gray-500">{agent.llm_model}</p></div>
                                            </div>
                                            <span className={`px-3 py-1 rounded-full text-xs ${agent.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>{agent.status}</span>
                                        </div>
                                    ))}
                                    {agents.length === 0 && <div className="px-6 py-8 text-center text-gray-500">No agents yet</div>}
                                </div>
                            </div>

                            <div className="bg-white rounded-xl shadow-sm border">
                                <div className="px-6 py-4 border-b flex justify-between items-center">
                                    <h2 className="text-lg font-semibold">Recent Calls</h2>
                                    <button onClick={() => setActiveTab('calls')} className="text-sm text-blue-600">View all</button>
                                </div>
                                <div className="divide-y">
                                    {calls.slice(0, 5).map((call) => (
                                        <div key={call.call_id} className="px-6 py-4 flex justify-between items-center hover:bg-gray-50">
                                            <div><p className="font-medium text-sm">{call.call_id}</p><p className="text-sm text-gray-500">{formatDate(call.created_at)}</p></div>
                                            <div className="flex items-center gap-4">
                                                <span className={`px-3 py-1 rounded-full text-xs ${getStatusColor(call.status)}`}>{call.status}</span>
                                                {call.duration_seconds && <span className="text-sm text-gray-500">{formatDuration(call.duration_seconds)}</span>}
                                            </div>
                                        </div>
                                    ))}
                                    {calls.length === 0 && <div className="px-6 py-8 text-center text-gray-500">No calls yet</div>}
                                </div>
                            </div>
                        </div>
                    ) : activeTab === 'agents' ? (
                        <div className="space-y-6">
                            <div className="relative max-w-md">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                <input type="text" placeholder="Search agents..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="w-full pl-10 pr-4 py-2.5 bg-white border rounded-lg text-sm" />
                            </div>

                            <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
                                <table className="w-full">
                                    <thead className="bg-gray-50 border-b">
                                        <tr>
                                            <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Agent</th>
                                            <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Model</th>
                                            <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Voice</th>
                                            <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Status</th>
                                            <th className="px-6 py-3 text-right text-xs font-semibold text-gray-600 uppercase">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y">
                                        {filteredAgents.map((agent) => (
                                            <tr key={agent.id} className="hover:bg-gray-50">
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center gap-3">
                                                        <div className="w-9 h-9 bg-gray-100 rounded-lg flex items-center justify-center"><Bot className="w-4 h-4 text-gray-600" /></div>
                                                        <div><p className="text-sm font-semibold">{agent.name}</p><p className="text-xs text-gray-400">ID: {agent.agent_id}</p></div>
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4 text-sm">{agent.llm_model}</td>
                                                <td className="px-6 py-4 text-sm">{agent.voice_id}</td>
                                                <td className="px-6 py-4"><span className={`px-3 py-1 rounded-full text-xs ${agent.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>{agent.status}</span></td>
                                                <td className="px-6 py-4 text-right">
                                                    <div className="flex justify-end gap-2">
                                                        <button onClick={() => setCallingAgentId(agent.id)} className="p-2 text-green-600 hover:bg-green-50 rounded-lg" title="Start Call"><Play className="w-4 h-4" /></button>
                                                        <button className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg" title="Edit"><Edit className="w-4 h-4" /></button>
                                                        <button onClick={() => handleDeleteAgent(agent.id)} className="p-2 text-red-600 hover:bg-red-50 rounded-lg" title="Delete"><Trash2 className="w-4 h-4" /></button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                                {filteredAgents.length === 0 && <div className="text-center py-12 text-gray-500">No agents found</div>}
                            </div>
                        </div>
                    ) : activeTab === 'calls' ? (
                        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
                            <table className="w-full">
                                <thead className="bg-gray-50 border-b">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600">Call ID</th>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600">Agent</th>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600">Type</th>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600">Status</th>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600">Duration</th>
                                        <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600">Created</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y">
                                    {calls.map((call) => (
                                        <tr key={call.call_id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 text-sm font-mono">{call.call_id}</td>
                                            <td className="px-6 py-4 text-sm">{call.agent_id}</td>
                                            <td className="px-6 py-4 text-sm capitalize">{call.call_type}</td>
                                            <td className="px-6 py-4"><span className={`px-3 py-1 rounded-full text-xs ${getStatusColor(call.status)}`}>{call.status}</span></td>
                                            <td className="px-6 py-4 text-sm">{call.duration_seconds ? formatDuration(call.duration_seconds) : '-'}</td>
                                            <td className="px-6 py-4 text-sm text-gray-500">{formatDate(call.created_at)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {calls.length === 0 && <div className="text-center py-12 text-gray-500">No calls yet</div>}
                        </div>
                    ) : (
                        <div className="text-center py-12">
                            <Phone className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                            <p className="text-gray-500">Phone number management coming soon</p>
                        </div>
                    )}
                </div>
            </main>

            {showCreateModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
                        <div className="px-6 py-4 border-b flex justify-between items-center">
                            <div><h2 className="text-xl font-bold">Create New Agent</h2><p className="text-sm text-gray-500">Configure your AI voice agent</p></div>
                            <button onClick={() => setShowCreateModal(false)} className="w-8 h-8 rounded-lg hover:bg-gray-100"><X className="w-4 h-4" /></button>
                        </div>
                        <div className="p-6 overflow-y-auto flex-1 space-y-5">
                            <div className="grid grid-cols-2 gap-4">
                                <div><label className="block text-sm font-semibold mb-2">Agent Name</label><input type="text" value={newAgent.name} onChange={(e) => setNewAgent({...newAgent, name: e.target.value})} className="w-full px-4 py-2.5 border rounded-lg text-sm" placeholder="e.g., Support Bot" /></div>
                                <div><label className="block text-sm font-semibold mb-2">LLM Model</label><select value={newAgent.llm_model} onChange={(e) => setNewAgent({...newAgent, llm_model: e.target.value})} className="w-full px-4 py-2.5 border rounded-lg text-sm"><option value="moonshot-v1-8k">Moonshot v1 8K</option><option value="moonshot-v1-32k">Moonshot v1 32K</option><option value="moonshot-v1-128k">Moonshot v1 128K</option><option value="gpt-4o">OpenAI GPT-4o</option><option value="gpt-4o-mini">OpenAI GPT-4o-mini</option><option value="gpt-4-turbo">OpenAI GPT-4-turbo</option></select></div>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div><label className="block text-sm font-semibold mb-2">Voice</label><select value={newAgent.voice_id} onChange={(e) => setNewAgent({...newAgent, voice_id: e.target.value})} className="w-full px-4 py-2.5 border rounded-lg text-sm"><option value="jessica">Jessica (UK Female)</option><option value="mark">Mark (US Male)</option><option value="sarah">Sarah (UK Female)</option><option value="michael">Michael (US Male)</option><option value="emma">Emma (UK Female)</option><option value="james">James (US Male)</option></select></div>
                                <div><label className="block text-sm font-semibold mb-2">Language</label><select value={newAgent.stt_language} onChange={(e) => setNewAgent({...newAgent, stt_language: e.target.value})} className="w-full px-4 py-2.5 border rounded-lg text-sm"><option value="en">English</option><option value="en-US">English (US)</option><option value="en-GB">English (UK)</option><option value="es">Spanish</option><option value="fr">French</option><option value="de">German</option><option value="it">Italian</option></select></div>
                            </div>
                            <div><label className="block text-sm font-semibold mb-2">Welcome Message</label><input type="text" value={newAgent.welcome_message} onChange={(e) => setNewAgent({...newAgent, welcome_message: e.target.value})} className="w-full px-4 py-2.5 border rounded-lg text-sm" /></div>
                            <div><label className="block text-sm font-semibold mb-2">System Prompt</label><textarea value={newAgent.system_prompt} onChange={(e) => setNewAgent({...newAgent, system_prompt: e.target.value})} rows={4} className="w-full px-4 py-2.5 border rounded-lg text-sm resize-none" /></div>
                            <div className="grid grid-cols-2 gap-4">
                                <div><label className="block text-sm font-semibold mb-2">Temperature</label><input type="number" step="0.1" min="0" max="2" value={newAgent.temperature} onChange={(e) => setNewAgent({...newAgent, temperature: parseFloat(e.target.value)})} className="w-full px-4 py-2.5 border rounded-lg text-sm" /></div>
                                <div><label className="block text-sm font-semibold mb-2">Max Tokens</label><input type="number" value={newAgent.max_tokens} onChange={(e) => setNewAgent({...newAgent, max_tokens: parseInt(e.target.value)})} className="w-full px-4 py-2.5 border rounded-lg text-sm" /></div>
                            </div>
                            <div className="flex items-center gap-3">
                                <input type="checkbox" id="interruptions" checked={newAgent.enable_interruptions} onChange={(e) => setNewAgent({...newAgent, enable_interruptions: e.target.checked})} className="w-4 h-4" />
                                <label htmlFor="interruptions" className="text-sm">Enable agent interruptions</label>
                            </div>
                        </div>
                        <div className="px-6 py-4 border-t flex justify-end gap-3">
                            <button onClick={() => setShowCreateModal(false)} className="px-4 py-2.5 text-sm font-medium hover:bg-gray-100 rounded-lg">Cancel</button>
                            <button onClick={handleCreateAgent} disabled={!newAgent.name || !newAgent.system_prompt} className="px-4 py-2.5 text-sm font-medium bg-black text-white rounded-lg hover:bg-gray-800 disabled:opacity-50">Create Agent</button>
                        </div>
                    </div>
                </div>
            )}

            {callingAgentId && (
                <VoiceCallModal 
                    isOpen={true} 
                    onClose={() => setCallingAgentId(null)} 
                    agentId={callingAgentId} 
                    agentName={agents.find(a => a.id === callingAgentId)?.name || 'Agent'}
                />
            )}
        </div>
    );
}
