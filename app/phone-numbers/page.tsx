'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
    Bot, BookOpen, Phone, PhoneCall, History, MessageSquare,
    BarChart3, Settings, Key, Sparkles, Plus, Trash2, Copy,
    Check, AlertCircle, ExternalLink, Play, HelpCircle, Info, RefreshCw,
    Webhook, X
} from 'lucide-react';
import axios from 'axios';

const API_URL = '/api/';

interface Agent {
    id: number;
    name: string;
}

interface PhoneNumber {
    id: number;
    phone_number: string;
    description: string | null;
    termination_uri: string | null;
    sip_trunk_username: string | null;
    twilio_account_sid: string | null;
    twilio_sip_trunk_sid: string | null;
    livekit_inbound_trunk_id: string | null;
    livekit_outbound_trunk_id: string | null;
    livekit_dispatch_rule_id: string | null;
    livekit_sip_endpoint: string | null;
    inbound_agent_id: number | null;
    outbound_agent_id: number | null;
    inbound_agent_name: string | null;
    outbound_agent_name: string | null;
    status: string;
    error_message: string | null;
    enable_inbound: boolean;
    enable_outbound: boolean;
    enable_krisp_noise_cancellation: boolean;
    created_at: string;
}

interface SipEndpoint {
    sip_endpoint: string;
    livekit_url: string;
}

export default function PhoneNumbersPage() {
    const emptyFormData = {
        phone_number: '',
        termination_uri: '',
        inbound_agent_id: 0,
        outbound_agent_id: 0,
        enable_inbound: true,
        enable_outbound: true,
        enable_krisp_noise_cancellation: true,
    };

    const [phoneNumbers, setPhoneNumbers] = useState<PhoneNumber[]>([]);
    const [agents, setAgents] = useState<Agent[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [editingPhoneId, setEditingPhoneId] = useState<number | null>(null);
    const [showSetupGuide, setShowSetupGuide] = useState(true);
    const [activeTab, setActiveTab] = useState<'numbers' | 'guide' | 'integrations'>('numbers');
    const [sipEndpoint, setSipEndpoint] = useState<SipEndpoint | null>(null);
    const [copied, setCopied] = useState<string | null>(null);
    const [formData, setFormData] = useState(emptyFormData);
    const [formLoading, setFormLoading] = useState(false);
    const [formError, setFormError] = useState('');
    const [formSuccess, setFormSuccess] = useState('');
    const [showSipSetupPopup, setShowSipSetupPopup] = useState(false);
    // Outbound call state
    const [showOutboundModal, setShowOutboundModal] = useState(false);
    const [outboundTargetPhone, setOutboundTargetPhone] = useState('');
    const [outboundLoading, setOutboundLoading] = useState(false);
    const [outboundError, setOutboundError] = useState('');
    const [selectedPhoneNumber, setSelectedPhoneNumber] = useState<PhoneNumber | null>(null);

    useEffect(() => {
        fetchPhoneNumbers();
        fetchAgents();
        fetchSipEndpoint();
    }, []);

    const fetchPhoneNumbers = async () => {
        try {
            const response = await axios.get(`${API_URL}phone-numbers/`);
            setPhoneNumbers(response.data);
        } catch (error) {
            console.error('Error fetching phone numbers:', error);
        } finally {
            setLoading(false);
        }
    };

    const fetchAgents = async () => {
        try {
            const response = await axios.get(`${API_URL}agents/list-simple`);
            setAgents(response.data);
        } catch (error) {
            console.error('Error fetching agents:', error);
        }
    };

    const fetchSipEndpoint = async () => {
        try {
            const response = await axios.get(`${API_URL}phone-numbers/sip-endpoint`);
            setSipEndpoint(response.data);
        } catch (error) {
            console.error('Error fetching SIP endpoint:', error);
        }
    };

    const resetForm = () => {
        setFormData(emptyFormData);
        setEditingPhoneId(null);
        setFormError('');
        setFormSuccess('');
    };

    const openCreateForm = () => {
        resetForm();
        setShowForm(true);
    };

    const openEditForm = (phone: PhoneNumber) => {
        setEditingPhoneId(phone.id);
        setFormData({
            phone_number: phone.phone_number,
            termination_uri: phone.termination_uri || '',
            inbound_agent_id: phone.inbound_agent_id || 0,
            outbound_agent_id: phone.outbound_agent_id || 0,
            enable_inbound: !!phone.enable_inbound,
            enable_outbound: !!phone.enable_outbound,
            enable_krisp_noise_cancellation: !!phone.enable_krisp_noise_cancellation,
        });
        setFormError('');
        setFormSuccess('');
        setShowForm(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setFormLoading(true);
        setFormError('');
        setFormSuccess('');

        try {
            const payload = {
                phone_number: formData.phone_number,
                termination_uri: formData.termination_uri || null,
                inbound_agent_id: formData.inbound_agent_id || null,
                outbound_agent_id: formData.outbound_agent_id || null,
                enable_inbound: formData.enable_inbound,
                enable_outbound: formData.enable_outbound,
                enable_krisp_noise_cancellation: formData.enable_krisp_noise_cancellation,
            };

            if (editingPhoneId) {
                // Phone number itself is immutable in update endpoint.
                const { phone_number, ...updatePayload } = payload;
                await axios.patch(`${API_URL}phone-numbers/${editingPhoneId}`, updatePayload);
                setFormSuccess('Phone number updated successfully!');
            } else {
                await axios.post(`${API_URL}phone-numbers/`, payload);
                setFormSuccess('Phone number added successfully!');
            }

            fetchPhoneNumbers();
            setShowForm(false);
            resetForm();
        } catch (error: any) {
            setFormError(error.response?.data?.detail || `Failed to ${editingPhoneId ? 'update' : 'add'} phone number`);
        } finally {
            setFormLoading(false);
        }
    };

    const handleConfigure = async (id: number) => {
        try {
            const response = await axios.post(`${API_URL}phone-numbers/${id}/configure`);
            alert(response.data.message);
            fetchPhoneNumbers();
        } catch (error: any) {
            console.error('Error configuring phone number:', error);
            alert(error.response?.data?.detail || 'Failed to configure phone number');
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm('Are you sure you want to delete this phone number?')) return;

        try {
            await axios.delete(`${API_URL}phone-numbers/${id}`);
            fetchPhoneNumbers();
        } catch (error) {
            console.error('Error deleting phone number:', error);
        }
    };

    const openOutboundModal = (phone: PhoneNumber) => {
        setSelectedPhoneNumber(phone);
        setOutboundTargetPhone('');
        setOutboundError('');
        setShowOutboundModal(true);
    };

    const handleOutboundCall = async () => {
        if (!outboundTargetPhone.trim()) {
            setOutboundError('Please enter a phone number to call');
            return;
        }
        if (!selectedPhoneNumber) return;

        setOutboundLoading(true);
        setOutboundError('');

        try {
            const response = await axios.post(
                `${API_URL}phone-numbers/${selectedPhoneNumber.id}/outbound`,
                {
                    to_number: outboundTargetPhone,
                    phone_number_id: selectedPhoneNumber.id
                }
            );
            alert(`Outbound call initiated! Room: ${response.data.room_name}`);
            setShowOutboundModal(false);
        } catch (error: any) {
            console.error('Error making outbound call:', error);
            // Handle different error response formats
            const errorData = error.response?.data;
            let errorMessage = 'Failed to initiate outbound call';

            if (errorData) {
                if (typeof errorData.detail === 'string') {
                    errorMessage = errorData.detail;
                } else if (errorData.detail && Array.isArray(errorData.detail)) {
                    // Pydantic validation error array
                    errorMessage = errorData.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
                } else if (typeof errorData === 'string') {
                    errorMessage = errorData;
                }
            }
            setOutboundError(errorMessage);
        } finally {
            setOutboundLoading(false);
        }
    };

    const copyToClipboard = (text: string, key: string) => {
        navigator.clipboard.writeText(text);
        setCopied(key);
        setTimeout(() => setCopied(null), 2000);
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'active': return 'bg-green-100 text-green-800';
            case 'configured': return 'bg-blue-100 text-blue-800';
            case 'pending': return 'bg-yellow-100 text-yellow-800';
            case 'error': return 'bg-red-100 text-red-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="min-h-screen bg-gray-50" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
            {/* Main Content - with margin for fixed sidebar */}
            <main className="p-8">
                <div className="max-w-6xl mx-auto">
                    <div className="flex items-center justify-between mb-8">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                                <Phone className="w-5 h-5 text-purple-600" />
                            </div>
                            <h1 className="text-2xl font-semibold text-gray-900">Phone Numbers</h1>
                        </div>
                        <button
                            onClick={() => {
                                if (showForm && !editingPhoneId) {
                                    setShowForm(false);
                                    resetForm();
                                    return;
                                }
                                openCreateForm();
                            }}
                            className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800"
                        >
                            <Plus className="w-4 h-4" />
                            Add Number
                        </button>
                    </div>

                    {/* Tab Navigation */}
                    <div className="flex border-b border-gray-200 mb-6">
                        <button
                            onClick={() => setActiveTab('numbers')}
                            className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'numbers'
                                ? 'border-purple-600 text-purple-700'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                }`}
                        >
                            <Phone className="w-4 h-4" />
                            My Numbers
                            {phoneNumbers.length > 0 && (
                                <span className="ml-1 px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full">{phoneNumbers.length}</span>
                            )}
                        </button>
                        <button
                            onClick={() => setActiveTab('guide')}
                            className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'guide'
                                ? 'border-blue-600 text-blue-700'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                }`}
                        >
                            <BookOpen className="w-4 h-4" />
                            Setup Guide
                        </button>
                        <button
                            onClick={() => setActiveTab('integrations')}
                            className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'integrations'
                                ? 'border-green-600 text-green-700'
                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                }`}
                        >
                            <Webhook className="w-4 h-4" />
                            Integrations
                        </button>
                    </div>

                    {/* ===== MY NUMBERS TAB ===== */}
                    {activeTab === 'numbers' && (
                        <>
                            {/* Add Phone Number Form */}
                            {showForm && (
                                <div className="bg-white rounded-xl border border-gray-200 mb-8 overflow-hidden">
                                    <div className="p-6 border-b border-gray-200 bg-indigo-50">
                                        <div className="flex items-center justify-between gap-3">
                                            <h2 className="text-lg font-semibold text-indigo-900">
                                                {editingPhoneId ? 'Edit Phone Number Configuration' : 'Add Phone Number'}
                                            </h2>
                                            <button
                                                type="button"
                                                onClick={() => setShowSipSetupPopup(true)}
                                                className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-white px-3 py-2 text-sm font-medium text-indigo-700 hover:bg-indigo-50"
                                            >
                                                <Info className="h-4 w-4" />
                                                SIP Setup
                                            </button>
                                        </div>
                                    </div>

                                    <form onSubmit={handleSubmit} className="p-6">
                                        {formError && (
                                            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
                                                <AlertCircle className="w-4 h-4" />
                                                {formError}
                                            </div>
                                        )}

                                        {formSuccess && (
                                            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700">
                                                {formSuccess}
                                            </div>
                                        )}

                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                            {/* Phone Number */}
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    Phone Number (E.164 format) <span className="text-red-500">*</span>
                                                </label>
                                                <input
                                                    type="text"
                                                    value={formData.phone_number}
                                                    onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                                                    placeholder="+1234567890"
                                                    className={`w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent ${editingPhoneId ? 'bg-gray-100 text-gray-600 cursor-not-allowed' : ''}`}
                                                    required
                                                    disabled={!!editingPhoneId}
                                                />
                                                <p className="text-xs text-gray-500 mt-1">
                                                    {editingPhoneId
                                                        ? 'Phone number is locked. Create a new record to change the number itself.'
                                                        : 'Example: +1234567890 (include + and country code)'}
                                                </p>
                                            </div>

                                            {/* Pure SIP Termination URI */}
                                            <div>
                                                <div className="mb-1 flex items-center justify-between gap-2">
                                                    <label className="block text-sm font-medium text-gray-700">
                                                        Termination URI (For Outbound) <span className="text-red-500">*</span>
                                                    </label>
                                                    <button
                                                        type="button"
                                                        onClick={() => setShowSipSetupPopup(true)}
                                                        className="text-xs font-medium text-blue-600 hover:text-blue-700"
                                                    >
                                                        Where do I get this?
                                                    </button>
                                                </div>
                                                <input
                                                    type="text"
                                                    value={formData.termination_uri}
                                                    onChange={(e) => setFormData({ ...formData, termination_uri: e.target.value })}
                                                    placeholder="your-trunk.pstn.twilio.com"
                                                    required
                                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                                />
                                            </div>

                                            {/* Inbound Agent */}
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    Agent for Inbound Calls (when someone calls this number)
                                                </label>
                                                <select
                                                    value={formData.inbound_agent_id}
                                                    onChange={(e) => setFormData({ ...formData, inbound_agent_id: parseInt(e.target.value) })}
                                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                                >
                                                    <option value={0}>-- Select Agent --</option>
                                                    {agents.map((agent) => (
                                                        <option key={agent.id} value={agent.id}>{agent.name}</option>
                                                    ))}
                                                </select>
                                            </div>

                                            {/* Outbound Agent */}
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                                    Agent for Outbound Calls (when agent calls out)
                                                </label>
                                                <select
                                                    value={formData.outbound_agent_id}
                                                    onChange={(e) => setFormData({ ...formData, outbound_agent_id: parseInt(e.target.value) })}
                                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                                                >
                                                    <option value={0}>-- Select Agent --</option>
                                                    {agents.map((agent) => (
                                                        <option key={agent.id} value={agent.id}>{agent.name}</option>
                                                    ))}
                                                </select>
                                            </div>

                                            {/* Toggles */}
                                            <div className="flex flex-col gap-3">
                                                <label className="flex items-center gap-2">
                                                    <input
                                                        type="checkbox"
                                                        checked={formData.enable_inbound}
                                                        onChange={(e) => setFormData({ ...formData, enable_inbound: e.target.checked })}
                                                        className="w-4 h-4 text-purple-600 rounded"
                                                    />
                                                    <span className="text-sm text-gray-700">Enable Inbound Calls</span>
                                                </label>
                                                <label className="flex items-center gap-2">
                                                    <input
                                                        type="checkbox"
                                                        checked={formData.enable_outbound}
                                                        onChange={(e) => setFormData({ ...formData, enable_outbound: e.target.checked })}
                                                        className="w-4 h-4 text-purple-600 rounded"
                                                    />
                                                    <span className="text-sm text-gray-700">Enable Outbound Calls</span>
                                                </label>
                                                <label className="flex items-center gap-2">
                                                    <input
                                                        type="checkbox"
                                                        checked={formData.enable_krisp_noise_cancellation}
                                                        onChange={(e) => setFormData({ ...formData, enable_krisp_noise_cancellation: e.target.checked })}
                                                        className="w-4 h-4 text-purple-600 rounded"
                                                    />
                                                    <span className="text-sm text-gray-700">Enable Noise Cancellation</span>
                                                </label>
                                            </div>
                                        </div>

                                        <div className="mt-6 flex gap-3">
                                            <button
                                                type="submit"
                                                disabled={formLoading}
                                                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                                            >
                                                {formLoading ? (editingPhoneId ? 'Saving...' : 'Adding...') : (editingPhoneId ? 'Save Changes' : 'Add Phone Number')}
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setShowForm(false);
                                                    resetForm();
                                                }}
                                                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
                                            >
                                                Cancel
                                            </button>
                                        </div>
                                    </form>
                                </div>
                            )}

                            {/* Phone Numbers List */}
                            {loading ? (
                                <div className="text-center py-12">
                                    <div className="animate-spin w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full mx-auto"></div>
                                    <p className="text-gray-500 mt-2">Loading phone numbers...</p>
                                </div>
                            ) : phoneNumbers.length === 0 ? (
                                <div className="bg-white rounded-xl border border-gray-200">
                                    <div className="p-12 text-center">
                                        <Phone className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                                        <p className="text-gray-500">No phone numbers configured yet</p>
                                        <p className="text-sm text-gray-400 mt-2">Click "+ Add Number" to add your first number, or check the <button onClick={() => setActiveTab('guide')} className="text-blue-600 hover:underline font-medium">Setup Guide</button> for step-by-step instructions.</p>
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {phoneNumbers.map((pn) => (
                                        <div key={pn.id} className="bg-white rounded-xl border border-gray-200 p-6">
                                            <div className="flex items-start justify-between">
                                                <div className="flex items-center gap-4">
                                                    <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                                                        <Phone className="w-6 h-6 text-purple-600" />
                                                    </div>
                                                    <div>
                                                        <div className="flex items-center gap-2">
                                                            <h3 className="text-lg font-semibold text-gray-900">{pn.phone_number}</h3>
                                                            <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getStatusColor(pn.status)}`}>
                                                                {pn.status}
                                                            </span>
                                                        </div>
                                                        {pn.description && (
                                                            <p className="text-sm text-gray-500">{pn.description}</p>
                                                        )}
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <button
                                                        onClick={() => handleConfigure(pn.id)}
                                                        className="p-2 text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg"
                                                        title="Sync with LiveKit"
                                                    >
                                                        <RefreshCw className={`w-5 h-5 ${pn.status === 'pending' ? 'animate-pulse' : ''}`} />
                                                    </button>
                                                    <button
                                                        onClick={() => openOutboundModal(pn)}
                                                        className="p-2 text-green-600 hover:text-green-700 hover:bg-green-50 rounded-lg"
                                                        title="Make Outbound Call"
                                                    >
                                                        <PhoneCall className="w-5 h-5" />
                                                    </button>
                                                    <button
                                                        onClick={() => openEditForm(pn)}
                                                        className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
                                                        title="Edit number configuration"
                                                    >
                                                        <Settings className="w-5 h-5" />
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(pn.id)}
                                                        className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg"
                                                        title="Delete"
                                                    >
                                                        <Trash2 className="w-5 h-5" />
                                                    </button>
                                                </div>
                                            </div>

                                            {/* Agent Info */}
                                            <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                                <div>
                                                    <p className="text-gray-500">Inbound Agent</p>
                                                    <p className="font-medium text-gray-900">{pn.inbound_agent_name || 'Not set'}</p>
                                                </div>
                                                <div>
                                                    <p className="text-gray-500">Outbound Agent</p>
                                                    <p className="font-medium text-gray-900">{pn.outbound_agent_name || 'Not set'}</p>
                                                </div>
                                                <div>
                                                    <p className="text-gray-500">LiveKit Endpoint</p>
                                                    <p className="font-medium text-gray-900 font-mono text-xs">{pn.livekit_sip_endpoint || 'N/A'}</p>
                                                </div>
                                                <div>
                                                    <p className="text-gray-500">Noise Cancellation</p>
                                                    <p className="font-medium text-gray-900">{pn.enable_krisp_noise_cancellation ? 'Enabled' : 'Disabled'}</p>
                                                </div>
                                            </div>

                                            {/* Error Message */}
                                            {pn.error_message && (
                                                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
                                                    <AlertCircle className="w-4 h-4" />
                                                    {pn.error_message}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </>
                    )}

                    {/* ===== SETUP GUIDE TAB ===== */}
                    {activeTab === 'guide' && (
                        <div className="space-y-6">
                            {/* Header */}
                            <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-xl p-6 text-white">
                                <div className="flex items-center gap-3 mb-2">
                                    <BookOpen className="w-6 h-6" />
                                    <h2 className="text-xl font-bold">Twilio SIP Trunk Setup Guide</h2>
                                </div>
                                <p className="text-blue-100 text-sm">Complete step-by-step instructions to connect your Twilio phone number with LiveKit voice agents.</p>
                            </div>

                            {/* Step 0 - SIP Endpoint */}
                            <div className="bg-yellow-50 border-2 border-yellow-300 rounded-xl p-5">
                                <div className="flex items-start gap-4">
                                    <div className="w-10 h-10 bg-yellow-500 text-white rounded-full flex items-center justify-center font-bold text-lg shrink-0">0</div>
                                    <div className="flex-1">
                                        <h3 className="font-bold text-lg text-yellow-900">Your LiveKit SIP Endpoint</h3>
                                        <p className="text-sm text-yellow-700 mt-1">Copy this value — you will need it in Step 3 for the Origination URI.</p>
                                        <div className="mt-3 flex items-center gap-2">
                                            <code className="flex-1 px-4 py-3 bg-white border-2 border-yellow-400 rounded-lg text-xl font-mono text-yellow-900 font-bold">
                                                {sipEndpoint?.sip_endpoint || 'Loading...'}
                                            </code>
                                            {sipEndpoint && (
                                                <button
                                                    onClick={() => copyToClipboard(sipEndpoint.sip_endpoint, 'guide-sip-endpoint')}
                                                    className="p-3 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors"
                                                >
                                                    {copied === 'guide-sip-endpoint' ? <Check className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Step 1 */}
                            <div className="bg-white rounded-xl border border-gray-200 p-5">
                                <div className="flex items-start gap-4">
                                    <div className="w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-lg shrink-0">1</div>
                                    <div className="flex-1">
                                        <h3 className="font-bold text-lg text-gray-900">Buy a Phone Number in Twilio</h3>
                                        <ul className="mt-3 text-gray-600 space-y-2">
                                            <li className="flex items-start gap-2"><span className="text-blue-500 mt-0.5">•</span><span>Go to <a href="https://console.twilio.com/us1/develop/sms/buy-phone-numbers" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline font-medium">Twilio Console → Phone Numbers → Buy a Number <ExternalLink className="w-3 h-3 inline" /></a></span></li>
                                            <li className="flex items-start gap-2"><span className="text-blue-500 mt-0.5">•</span><span>Search for and buy a phone number — make sure it supports <strong>Voice</strong></span></li>
                                            <li className="flex items-start gap-2"><span className="text-blue-500 mt-0.5">•</span><span>Note down the number in E.164 format (e.g., <code className="bg-gray-100 px-1 rounded">+1234567890</code>)</span></li>
                                        </ul>
                                    </div>
                                </div>
                            </div>

                            {/* Step 2 */}
                            <div className="bg-white rounded-xl border border-gray-200 p-5">
                                <div className="flex items-start gap-4">
                                    <div className="w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-lg shrink-0">2</div>
                                    <div className="flex-1">
                                        <h3 className="font-bold text-lg text-gray-900">Create a SIP Trunk in Twilio</h3>
                                        <ul className="mt-3 text-gray-600 space-y-2">
                                            <li className="flex items-start gap-2"><span className="text-blue-500 mt-0.5">•</span><span>Go to <a href="https://console.twilio.com/us1/develop/sip-trunking/trunks" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline font-medium">Elastic SIP Trunking → Trunks <ExternalLink className="w-3 h-3 inline" /></a></span></li>
                                            <li className="flex items-start gap-2"><span className="text-blue-500 mt-0.5">•</span><span>Click <strong>"Create new SIP Trunk"</strong></span></li>
                                            <li className="flex items-start gap-2"><span className="text-blue-500 mt-0.5">•</span><span>Friendly Name: <code className="bg-gray-100 px-1 rounded">LiveKit-Trunk</code></span></li>
                                        </ul>

                                        {/* General Settings */}
                                        <div className="mt-4 p-4 bg-amber-50 rounded-lg border border-amber-200">
                                            <p className="text-sm font-bold text-amber-800">⚠️ Under "General" tab → Enable these settings:</p>
                                            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                                                <div className="flex items-center gap-2 bg-white rounded p-2 border border-amber-100">
                                                    <Check className="w-4 h-4 text-green-500 shrink-0" />
                                                    <span><strong>Call Transfer (SIP REFER)</strong></span>
                                                </div>
                                                <div className="flex items-center gap-2 bg-white rounded p-2 border border-amber-100">
                                                    <Check className="w-4 h-4 text-green-500 shrink-0" />
                                                    <span><strong>Enable PSTN Transfer</strong></span>
                                                </div>
                                                <div className="flex items-center gap-2 bg-white rounded p-2 border border-amber-100">
                                                    <Check className="w-4 h-4 text-green-500 shrink-0" />
                                                    <span><strong>Symmetric RTP</strong></span>
                                                </div>
                                                <div className="flex items-center gap-2 bg-white rounded p-2 border border-amber-100">
                                                    <Settings className="w-4 h-4 text-blue-500 shrink-0" />
                                                    <span><strong>Caller ID:</strong> Transferee</span>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Termination Settings */}
                                        <div className="mt-4 p-4 bg-indigo-50 rounded-lg border border-indigo-200">
                                            <p className="text-sm font-bold text-indigo-800">📞 Under "Termination" tab (For Outbound Calls):</p>
                                            <div className="mt-3 text-sm text-indigo-900 space-y-3">
                                                <div>
                                                    <strong>Termination SIP URI:</strong>
                                                    <div className="mt-1 px-3 py-2 bg-white rounded border border-indigo-200 font-mono text-sm">
                                                        yourcompany.pstn.twilio.com
                                                    </div>
                                                    <p className="text-xs text-indigo-600 mt-1">⚠️ Must end in <code>.pstn.twilio.com</code> — use your own prefix (e.g., <code>oyik.pstn.twilio.com</code>)</p>
                                                </div>

                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                    <div className="p-3 bg-white rounded-lg border border-green-200">
                                                        <p className="text-xs font-bold text-green-700 mb-2">✅ Option A — IP Access Control (Recommended)</p>
                                                        <ul className="text-xs text-gray-600 space-y-1">
                                                            <li>1. Go to "IP Access Control Lists" → Create new</li>
                                                            <li>2. Name: <code className="bg-gray-100 px-1">LiveKit-Server</code></li>
                                                            <li>3. Add IP: <code className="bg-yellow-100 px-1 font-bold">13.135.81.172</code></li>
                                                            <li>4. In Termination tab → select this ACL</li>
                                                        </ul>
                                                    </div>
                                                    <div className="p-3 bg-white rounded-lg border border-gray-200">
                                                        <p className="text-xs font-bold text-gray-700 mb-2">Option B — Credential List</p>
                                                        <ul className="text-xs text-gray-600 space-y-1">
                                                            <li>1. Go to "Credential Lists" → Create new</li>
                                                            <li>2. Create a username and password</li>
                                                            <li>3. Save credentials for adding number below</li>
                                                            <li>4. In Termination tab → select this list</li>
                                                        </ul>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Step 3 - Origination */}
                            <div className="bg-white rounded-xl border-2 border-red-200 p-5">
                                <div className="flex items-start gap-4">
                                    <div className="w-10 h-10 bg-red-600 text-white rounded-full flex items-center justify-center font-bold text-lg shrink-0">3</div>
                                    <div className="flex-1">
                                        <h3 className="font-bold text-lg text-red-900">Configure Origination (Inbound Calls)</h3>
                                        <p className="text-sm text-gray-600 mt-1">This tells Twilio <strong>where to route incoming calls</strong>. Go to "Origination" tab → "Add new Origination URI":</p>

                                        <div className="mt-4 p-4 bg-red-50 rounded-lg border border-red-200">
                                            <div className="space-y-3">
                                                <div>
                                                    <label className="text-sm font-semibold text-gray-700">Origination SIP URI:</label>
                                                    <div className="flex items-center gap-2 mt-1">
                                                        <code className="flex-1 px-4 py-3 bg-white border-2 border-red-300 rounded-lg text-lg font-mono text-red-800 font-bold">
                                                            sip:{sipEndpoint?.sip_endpoint || 'YOUR_SIP_ENDPOINT'}
                                                        </code>
                                                        <button
                                                            onClick={() => copyToClipboard(`sip:${sipEndpoint?.sip_endpoint}`, 'guide-sip-uri')}
                                                            className="p-3 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                                                        >
                                                            {copied === 'guide-sip-uri' ? <Check className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
                                                        </button>
                                                    </div>
                                                </div>
                                                <div className="grid grid-cols-2 gap-4">
                                                    <div className="bg-white p-2 rounded border border-red-100">
                                                        <span className="text-xs text-gray-500">Priority</span>
                                                        <p className="font-bold text-gray-900">10</p>
                                                    </div>
                                                    <div className="bg-white p-2 rounded border border-red-100">
                                                        <span className="text-xs text-gray-500">Weight</span>
                                                        <p className="font-bold text-gray-900">10</p>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="mt-2 flex items-center gap-2 text-sm text-red-700">
                                            <AlertCircle className="w-4 h-4" />
                                            <span>This is the most critical step — it routes calls from Twilio to your LiveKit server!</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Step 4 */}
                            <div className="bg-white rounded-xl border border-gray-200 p-5">
                                <div className="flex items-start gap-4">
                                    <div className="w-10 h-10 bg-purple-600 text-white rounded-full flex items-center justify-center font-bold text-lg shrink-0">4</div>
                                    <div className="flex-1">
                                        <h3 className="font-bold text-lg text-gray-900">Add Phone Number to Trunk</h3>
                                        <p className="text-sm text-gray-600 mt-1">In the SAME trunk, go to the "Numbers" tab:</p>
                                        <ul className="mt-3 text-gray-600 space-y-2 text-sm">
                                            <li className="flex items-start gap-2"><span className="text-purple-500 mt-0.5">•</span><span>Click <strong>"Add a Number"</strong></span></li>
                                            <li className="flex items-start gap-2"><span className="text-purple-500 mt-0.5">•</span><span>Your purchased Twilio numbers will appear in the list</span></li>
                                            <li className="flex items-start gap-2"><span className="text-purple-500 mt-0.5">•</span><span>Click on your number to add it to the trunk</span></li>
                                        </ul>
                                        <div className="mt-3 p-3 bg-gray-50 rounded-lg text-xs text-gray-600">
                                            <strong>Alternative:</strong> Phone Numbers → Manage → Active Numbers → Select number → Configure With: SIP Trunk → Choose your trunk
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Step 5 */}
                            <div className="bg-white rounded-xl border-2 border-green-200 p-5">
                                <div className="flex items-start gap-4">
                                    <div className="w-10 h-10 bg-green-600 text-white rounded-full flex items-center justify-center font-bold text-lg shrink-0">5</div>
                                    <div className="flex-1">
                                        <h3 className="font-bold text-lg text-green-900">Add Phone Number to This Dashboard</h3>
                                        <p className="text-sm text-gray-600 mt-1">Now register it here to connect with your AI agent:</p>
                                        <ul className="mt-3 text-gray-600 space-y-2 text-sm">
                                            <li className="flex items-start gap-2"><span className="text-green-500 mt-0.5">1.</span><span>Switch to the <strong>"My Numbers"</strong> tab and click <strong>"+ Add Number"</strong></span></li>
                                            <li className="flex items-start gap-2"><span className="text-green-500 mt-0.5">2.</span><span>Enter your Twilio phone number (e.g., <code className="bg-gray-100 px-1 rounded">+447426999697</code>)</span></li>
                                            <li className="flex items-start gap-2"><span className="text-green-500 mt-0.5">3.</span><span><strong>Termination URI:</strong> The one you created in Step 2 (e.g., <code className="bg-gray-100 px-1 rounded">oyik.pstn.twilio.com</code>)</span></li>
                                            <li className="flex items-start gap-2"><span className="text-green-500 mt-0.5">4.</span><span><strong>SIP Credentials:</strong> If using IP ACL (recommended), leave username/password blank</span></li>
                                            <li className="flex items-start gap-2"><span className="text-green-500 mt-0.5">5.</span><span>Select which <strong>agent</strong> should answer inbound calls and make outbound calls</span></li>
                                            <li className="flex items-start gap-2"><span className="text-green-500 mt-0.5">6.</span><span>Click <strong>"Add Phone Number"</strong>, then click the <RefreshCw className="w-3 h-3 inline" /> Sync button</span></li>
                                        </ul>
                                        <div className="mt-4">
                                            <button
                                                onClick={() => { setActiveTab('numbers'); setShowForm(true); }}
                                                className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium"
                                            >
                                                <Plus className="w-4 h-4" />
                                                Go Add a Number Now
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Call Flow Diagram */}
                            <div className="bg-gradient-to-r from-cyan-50 to-blue-50 rounded-xl border border-cyan-200 p-5">
                                <div className="flex items-start gap-4">
                                    <div className="w-10 h-10 bg-cyan-600 text-white rounded-full flex items-center justify-center shrink-0">
                                        <Info className="w-5 h-5" />
                                    </div>
                                    <div className="flex-1">
                                        <h3 className="font-bold text-lg text-cyan-900">How It Works — Call Flow</h3>
                                        <div className="mt-3 space-y-2">
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 bg-white border-2 border-cyan-300 rounded-full flex items-center justify-center text-xs font-bold text-cyan-700">1</div>
                                                <div className="flex-1 bg-white rounded-lg p-2 border border-cyan-100 text-sm">Caller dials your Twilio number (e.g., +447426999697)</div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 bg-white border-2 border-cyan-300 rounded-full flex items-center justify-center text-xs font-bold text-cyan-700">2</div>
                                                <div className="flex-1 bg-white rounded-lg p-2 border border-cyan-100 text-sm">Twilio routes the call to <code className="bg-cyan-50 px-1">sip:{sipEndpoint?.sip_endpoint || '13.135.81.172:5060'}</code></div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 bg-white border-2 border-cyan-300 rounded-full flex items-center justify-center text-xs font-bold text-cyan-700">3</div>
                                                <div className="flex-1 bg-white rounded-lg p-2 border border-cyan-100 text-sm">LiveKit SIP bridge receives the call and creates a room</div>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 bg-white border-2 border-cyan-300 rounded-full flex items-center justify-center text-xs font-bold text-cyan-700">4</div>
                                                <div className="flex-1 bg-white rounded-lg p-2 border border-cyan-100 text-sm">Your AI voice agent automatically joins the room and starts talking</div>
                                            </div>
                                        </div>

                                        <div className="mt-4 p-3 bg-amber-50 rounded-lg border border-amber-200 text-sm text-amber-800">
                                            <strong>Important:</strong> Make sure your voice agent Docker container is running and connected to LiveKit. Ports <code className="bg-white px-1">5060</code> (SIP) and <code className="bg-white px-1">10000-20000</code> (RTP/media) must be open in your firewall.
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Webhook for Outbound Calls (n8n compatible) */}
                            <div className="bg-white rounded-xl border border-gray-200 p-5">
                                <h3 className="font-bold text-lg text-gray-900 mb-4">🌐 Webhook for Outbound Calls</h3>
                                <p className="text-sm text-gray-600 mb-4">
                                    Use this endpoint to trigger outbound calls from n8n, Zapier, or any automation tool.
                                </p>

                                <div className="space-y-4">
                                    <div>
                                        <p className="text-sm font-semibold text-gray-700 mb-2">Endpoint:</p>
                                        <code className="block px-4 py-3 bg-gray-900 text-green-400 rounded-lg font-mono text-sm">
                                            POST /api/webhook/outbound-call
                                        </code>
                                    </div>

                                    <div>
                                        <p className="text-sm font-semibold text-gray-700 mb-2">Full URL:</p>
                                        <code className="block px-4 py-3 bg-gray-900 text-green-400 rounded-lg font-mono text-sm">
                                            http://13.135.81.172:8000/api/webhook/outbound-call
                                        </code>
                                    </div>

                                    <div>
                                        <p className="text-sm font-semibold text-gray-700 mb-2">Payload (JSON):</p>
                                        <pre className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-xs overflow-x-auto">
                                            {`{
  "to_number": "+1234567890",   // Phone to call (E.164 format)
  "agent_id": 1,               // Agent ID
  "phone_id": 1                // Optional: Phone number ID
}`}
                                        </pre>
                                    </div>

                                    <div>
                                        <p className="text-sm font-semibold text-gray-700 mb-2">Example Response:</p>
                                        <pre className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-xs overflow-x-auto">
                                            {`{
  "success": true,
  "call_id": "outbound_abc123def456",
  "room_name": "call_1_abc123",
  "message": "Outbound call initiated"
}`}
                                        </pre>
                                    </div>

                                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                        <p className="text-sm text-blue-800 font-semibold mb-2">💡 n8n Example:</p>
                                        <p className="text-xs text-blue-700 mb-2">In n8n, use HTTP Request node with:</p>
                                        <ul className="text-xs text-blue-700 list-disc list-inside space-y-1">
                                            <li>Method: POST</li>
                                            <li>URL: http://13.135.81.172:8000/api/webhook/outbound-call</li>
                                            <li>Body Content Type: JSON</li>
                                            <li>Body: use JSON with to_number and agent_id</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>

                            {/* Troubleshooting */}
                            <div className="bg-white rounded-xl border border-gray-200 p-5">
                                <h3 className="font-bold text-lg text-gray-900 mb-4">🔧 Troubleshooting</h3>
                                <div className="space-y-3">
                                    <div className="p-3 bg-red-50 rounded-lg border border-red-100">
                                        <p className="text-sm font-semibold text-red-800">Call connects but agent is silent</p>
                                        <p className="text-xs text-red-600 mt-1">Check that your voice agent has valid LLM API keys (OpenAI, etc.) and the model is correct.</p>
                                    </div>
                                    <div className="p-3 bg-orange-50 rounded-lg border border-orange-100">
                                        <p className="text-sm font-semibold text-orange-800">403 Forbidden error</p>
                                        <p className="text-xs text-orange-600 mt-1">Your server IP (<code>13.135.81.172</code>) is not in Twilio's IP Access Control List. Add it in the Termination tab.</p>
                                    </div>
                                    <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-100">
                                        <p className="text-sm font-semibold text-yellow-800">No ringing / call doesn't connect</p>
                                        <p className="text-xs text-yellow-600 mt-1">Ensure ports 5060 (SIP) and 10000-20000 (RTP) are open in your server firewall (security groups).</p>
                                    </div>
                                    <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
                                        <p className="text-sm font-semibold text-blue-800">"SIP trunk does not exist" error</p>
                                        <p className="text-xs text-blue-600 mt-1">Click the <RefreshCw className="w-3 h-3 inline" /> Sync button on your phone number to create/update the LiveKit trunk.</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'integrations' && (
                        <div className="space-y-6">
                            {/* Header */}
                            <div className="bg-gradient-to-r from-green-600 to-teal-700 rounded-xl p-6 text-white">
                                <div className="flex items-center gap-3 mb-2">
                                    <Webhook className="w-6 h-6" />
                                    <h2 className="text-xl font-bold">Integrations & Webhooks</h2>
                                </div>
                                <p className="text-green-100 text-sm">Connect with n8n, Zapier, Make, or any automation tool using webhooks.</p>
                            </div>

                            {/* Webhook for Outbound Calls */}
                            <div className="bg-white rounded-xl border border-gray-200 p-5">
                                <h3 className="font-bold text-lg text-gray-900 mb-4">🌐 Webhook for Outbound Calls</h3>
                                <p className="text-sm text-gray-600 mb-4">
                                    Use this endpoint to trigger outbound calls from n8n, Zapier, or any automation tool.
                                </p>

                                <div className="space-y-4">
                                    <div>
                                        <p className="text-sm font-semibold text-gray-700 mb-2">Endpoint:</p>
                                        <code className="block px-4 py-3 bg-gray-900 text-green-400 rounded-lg font-mono text-sm">
                                            POST /api/webhook/outbound-call
                                        </code>
                                    </div>

                                    <div>
                                        <p className="text-sm font-semibold text-gray-700 mb-2">Full URL:</p>
                                        <code className="block px-4 py-3 bg-gray-900 text-green-400 rounded-lg font-mono text-sm">
                                            http://13.135.81.172:8000/api/webhook/outbound-call
                                        </code>
                                    </div>

                                    <div>
                                        <p className="text-sm font-semibold text-gray-700 mb-2">Payload (JSON):</p>
                                        <pre className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-xs overflow-x-auto">
{`{
  "to_number": "+1234567890",
  "agent_id": 1,
  "phone_id": 1
}`}
                                        </pre>
                                    </div>

                                    <div>
                                        <p className="text-sm font-semibold text-gray-700 mb-2">Example Response:</p>
                                        <pre className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-xs overflow-x-auto">
{`{
  "success": true,
  "call_id": "outbound_abc123",
  "room_name": "call_1_abc123",
  "message": "Outbound call initiated"
}`}
                                        </pre>
                                    </div>
                                </div>
                            </div>

                            {/* n8n Example */}
                            <div className="bg-white rounded-xl border border-gray-200 p-5">
                                <h3 className="font-bold text-lg text-gray-900 mb-4">🔗 n8n Integration Example</h3>
                                <div className="space-y-4">
                                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                        <p className="text-sm text-blue-800 font-semibold mb-2">Setup Steps:</p>
                                        <ol className="text-sm text-blue-700 list-decimal list-inside space-y-2">
                                            <li>Create a new workflow in n8n</li>
                                            <li>Add a <strong>Webhook</strong> node as the trigger</li>
                                            <li>Add an <strong>HTTP Request</strong> node after it</li>
                                            <li>Configure the HTTP node to call our API</li>
                                        </ol>
                                    </div>

                                    <div>
                                        <p className="text-sm font-semibold text-gray-700 mb-2">HTTP Request Node Configuration:</p>
                                        <table className="w-full text-sm border-collapse">
                                            <tbody>
                                                <tr className="border-b">
                                                    <td className="py-2 font-medium text-gray-600">Method</td>
                                                    <td className="py-2 font-mono text-green-600">POST</td>
                                                </tr>
                                                <tr className="border-b">
                                                    <td className="py-2 font-medium text-gray-600">URL</td>
                                                    <td className="py-2 font-mono text-green-600">http://13.135.81.172:8000/api/webhook/outbound-call</td>
                                                </tr>
                                                <tr className="border-b">
                                                    <td className="py-2 font-medium text-gray-600">Body Content Type</td>
                                                    <td className="py-2 font-mono text-green-600">JSON</td>
                                                </tr>
                                                <tr>
                                                    <td className="py-2 font-medium text-gray-600">JSON Body</td>
                                                    <td className="py-2 font-mono text-green-600 text-xs">{'{{json}}'}</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>

                                    <div className="bg-gray-900 p-4 rounded-lg">
                                        <p className="text-sm font-semibold text-gray-300 mb-2">Sample Webhook Trigger JSON (test with):</p>
                                        <pre className="text-green-400 font-mono text-xs overflow-x-auto">
{`{
  "to_number": "+1234567890",
  "agent_id": 1
}`}
                                        </pre>
                                    </div>
                                </div>
                            </div>

                            {/* Zapier Example */}
                            <div className="bg-white rounded-xl border border-gray-200 p-5">
                                <h3 className="font-bold text-lg text-gray-900 mb-4">⚡ Zapier Integration</h3>
                                <div className="space-y-4">
                                    <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                                        <p className="text-sm text-orange-800 font-semibold mb-2">Setup Steps:</p>
                                        <ol className="text-sm text-orange-700 list-decimal list-inside space-y-2">
                                            <li>Create a new Zap in Zapier</li>
                                            <li>Choose a trigger (e.g., <strong>New Row in Google Sheets</strong>)</li>
                                            <li>Add an action: <strong>POST request</strong></li>
                                            <li>Configure the URL and body as shown below</li>
                                        </ol>
                                    </div>

                                    <div>
                                        <p className="text-sm font-semibold text-gray-700 mb-2">Zapier Action Configuration:</p>
                                        <table className="w-full text-sm border-collapse">
                                            <tbody>
                                                <tr className="border-b">
                                                    <td className="py-2 font-medium text-gray-600">URL</td>
                                                    <td className="py-2 font-mono text-green-600">http://13.135.81.172:8000/api/webhook/outbound-call</td>
                                                </tr>
                                                <tr className="border-b">
                                                    <td className="py-2 font-medium text-gray-600">Method</td>
                                                    <td className="py-2 font-mono text-green-600">POST</td>
                                                </tr>
                                                <tr>
                                                    <td className="py-2 font-medium text-gray-600">Data</td>
                                                    <td className="py-2 font-mono text-green-600 text-xs">{"{ \"to_number\": \"+1234567890\", \"agent_id\": 1 }"}</td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>

                            {/* Call Webhook (incoming call data) */}
                            <div className="bg-white rounded-xl border border-gray-200 p-5">
                                <h3 className="font-bold text-lg text-gray-900 mb-4">📥 Call Webhook (Incoming Data)</h3>
                                <p className="text-sm text-gray-600 mb-4">
                                    When a call ends, you can receive call data via webhook. Configure this in your agent settings.
                                </p>

                                <div className="space-y-4">
                                    <div>
                                        <p className="text-sm font-semibold text-gray-700 mb-2">Webhook Payload (sent to your URL):</p>
                                        <pre className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-xs overflow-x-auto">
{`{
  "call_id": "outbound_abc123",
  "status": "completed",
  "duration_seconds": 120,
  "cost_usd": 0.05,
  "direction": "outbound",
  "from_number": "+1987654321",
  "to_number": "+1234567890",
  "transcript": "...",
  "recording_url": "..."
}`}
                                        </pre>
                                    </div>

                                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                                        <p className="text-sm text-yellow-800 font-semibold mb-2">💡 Tip:</p>
                                        <p className="text-sm text-yellow-700">
                                            Configure your webhook URL in the <strong>Post-Call Data Extraction</strong> tab of your agent settings.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                </div>
            </main>

            {showSipSetupPopup && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
                    <div className="w-full max-w-md rounded-2xl bg-white shadow-2xl">
                        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
                            <div>
                                <h3 className="text-base font-semibold text-gray-900">SIP Setup</h3>
                                <p className="text-sm text-gray-500">Only the required Twilio details for IP ACL setup.</p>
                            </div>
                            <button
                                type="button"
                                onClick={() => setShowSipSetupPopup(false)}
                                className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                            >
                                <X className="h-5 w-5" />
                            </button>
                        </div>
                        <div className="space-y-3 px-5 py-4 text-sm text-gray-700">
                            <p>Keep the Twilio phone number assigned to the SIP trunk.</p>
                            <p>Paste the trunk&apos;s <span className="font-medium text-gray-900">Termination SIP URI</span> into this form.</p>
                            <p>Add this server IP to your Twilio IP Access Control List: <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs">13.135.81.172</code></p>
                            <p>Nothing else is needed in this form for your IP ACL setup.</p>
                        </div>
                        <div className="border-t border-gray-100 px-5 py-4">
                            <button
                                type="button"
                                onClick={() => setShowSipSetupPopup(false)}
                                className="w-full rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Outbound Call Modal */}
            {showOutboundModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-gray-900">Make Outbound Call</h3>
                            <button
                                onClick={() => setShowOutboundModal(false)}
                                className="text-gray-400 hover:text-gray-600"
                            >
                                ✕
                            </button>
                        </div>

                        <div className="mb-4">
                            <p className="text-sm text-gray-600 mb-2">
                                Calling from: <span className="font-semibold">{selectedPhoneNumber?.phone_number}</span>
                            </p>
                            <p className="text-sm text-gray-600 mb-4">
                                Agent: <span className="font-semibold">{selectedPhoneNumber?.outbound_agent_name || 'Not configured'}</span>
                            </p>

                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Target Phone Number <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="tel"
                                value={outboundTargetPhone}
                                onChange={(e) => setOutboundTargetPhone(e.target.value)}
                                placeholder="+1234567890"
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Enter the number you want the agent to call (include country code, e.g., +1 for US)
                            </p>
                        </div>

                        {outboundError && (
                            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                                {outboundError}
                            </div>
                        )}

                        <div className="flex gap-3">
                            <button
                                onClick={() => setShowOutboundModal(false)}
                                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleOutboundCall}
                                disabled={outboundLoading}
                                className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                            >
                                {outboundLoading ? 'Calling...' : 'Make Call'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
