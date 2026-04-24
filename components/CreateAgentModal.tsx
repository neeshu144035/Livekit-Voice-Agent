'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';
import { X, Bot, Loader2, Check, ChevronDown, Settings, Sparkles, Volume2, Cpu, Zap } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api/';

interface CreateAgentModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

interface ModelOption {
    value: string;
    label: string;
    provider: string;
    price: string;
}

interface VoiceOption {
    value: string;
    label: string;
    accent: string;
    gender: string;
    provider?: string;
}

interface TTSVoiceOption {
    id: string;
    label: string;
    accent?: string;
    gender?: string;
    category?: string;
}

interface TTSModelOption {
    id: string;
    name: string;
    is_v3?: boolean;
    supports_multilingual?: boolean;
    deprecated?: boolean;
}

const MODEL_OPTIONS: ModelOption[] = [
    { value: 'gpt-5.4', label: 'GPT-5.4 (Flagship)', provider: 'OpenAI', price: 'Varies' },
    { value: 'gpt-5.4-pro', label: 'GPT-5.4 Pro', provider: 'OpenAI', price: 'Varies' },
    { value: 'gpt-5.2', label: 'GPT-5.2', provider: 'OpenAI', price: '$0.060/min' },
    { value: 'gpt-5.2-pro', label: 'GPT-5.2 Pro', provider: 'OpenAI', price: 'Varies' },
    { value: 'gpt-5.1', label: 'GPT-5.1', provider: 'OpenAI', price: '$0.050/min' },
    { value: 'gpt-5-pro', label: 'GPT-5 Pro', provider: 'OpenAI', price: 'Varies' },
    { value: 'gpt-5', label: 'GPT-5', provider: 'OpenAI', price: '$0.040/min' },
    { value: 'gpt-5-mini', label: 'GPT-5 mini (Fast)', provider: 'OpenAI', price: '$0.010/min' },
    { value: 'gpt-5-nano', label: 'GPT-5 nano (Lite)', provider: 'OpenAI', price: '$0.005/min' },
    { value: 'gpt-4.1', label: 'GPT-4.1', provider: 'OpenAI', price: 'Varies' },
    { value: 'gpt-4.1-mini', label: 'GPT-4.1 mini', provider: 'OpenAI', price: 'Varies' },
    { value: 'gpt-4.1-nano', label: 'GPT-4.1 nano', provider: 'OpenAI', price: 'Varies' },
    { value: 'gpt-4o', label: 'GPT-4o', provider: 'OpenAI', price: '$0.080/min' },
    { value: 'gpt-4o-mini', label: 'GPT-4o mini', provider: 'OpenAI', price: '$0.015/min' },
    { value: 'gpt-4', label: 'GPT-4 (Legacy)', provider: 'OpenAI', price: 'Varies' },
    { value: 'o1', label: 'o1 (Reasoning)', provider: 'OpenAI', price: 'Varies' },
    { value: 'o1-pro', label: 'o1 Pro (Reasoning)', provider: 'OpenAI', price: 'Varies' },
    { value: 'o3', label: 'o3 (Reasoning)', provider: 'OpenAI', price: 'Varies' },
    { value: 'o3-mini', label: 'o3-mini (Reasoning)', provider: 'OpenAI', price: '$0.020/min' },
    { value: 'o4-mini', label: 'o4-mini (Reasoning)', provider: 'OpenAI', price: 'Varies' },
    { value: 'kimi-k2.5', label: 'Kimi K2.5 (Agentic)', provider: 'Moonshot', price: '$0.015/min' },
    { value: 'kimi-k2-thinking', label: 'Kimi K2 Thinking', provider: 'Moonshot', price: '$0.012/min' },
    { value: 'kimi-k2-instruct', label: 'Kimi K2 Instruct', provider: 'Moonshot', price: '$0.012/min' },
    { value: 'moonlight-16b-a3b', label: 'Moonlight 16B', provider: 'Moonshot', price: '$0.004/min' },
    { value: 'moonshot-v1-8k', label: 'Moonshot v1-8k', provider: 'Moonshot', price: '$0.006/min' },
    { value: 'moonshot-v1-32k', label: 'Moonshot v1-32k', provider: 'Moonshot', price: '$0.012/min' },
    { value: 'moonshot-v1-128k', label: 'Moonshot v1-128k', provider: 'Moonshot', price: '$0.024/min' },
];

const VOICE_OPTIONS: VoiceOption[] = [
    { value: 'aura-asteria-en', label: 'Asteria (Jessica)', accent: 'UK', gender: 'Female', provider: 'deepgram' },
    { value: 'aura-luna-en', label: 'Luna (Sarah)', accent: 'UK', gender: 'Female', provider: 'deepgram' },
    { value: 'aura-hera-en', label: 'Hera (Emma)', accent: 'US', gender: 'Female', provider: 'deepgram' },
    { value: 'aura-orion-en', label: 'Orion (Mark)', accent: 'US', gender: 'Male', provider: 'deepgram' },
    { value: 'aura-perseus-en', label: 'Perseus (Michael)', accent: 'US', gender: 'Male', provider: 'deepgram' },
    { value: 'aura-zeus-en', label: 'Zeus (James)', accent: 'US', gender: 'Male', provider: 'deepgram' },
    { value: 'jessica', label: 'Jessica (Legacy)', accent: 'UK', gender: 'Female', provider: 'deepgram' },
    { value: 'mark', label: 'Mark (Legacy)', accent: 'US', gender: 'Male', provider: 'deepgram' },
];

const DEEPGRAM_VOICE_IDS = new Set(VOICE_OPTIONS.map((voice) => voice.value));
const XAI_DEFAULT_MODEL = 'grok-voice-think-fast-1.0';
const XAI_VOICE_IDS = new Set(['ara', 'eve', 'leo', 'rex', 'sal']);

const TTS_PROVIDERS = [
    { value: 'deepgram', label: 'Deepgram', description: 'Fast & affordable' },
    { value: 'elevenlabs', label: 'ElevenLabs', description: 'High quality voices' },
    { value: 'xai', label: 'xAI', description: 'Unified realtime voice' },
];

const LANGUAGE_OPTIONS = [
    { value: 'en-US', label: 'English (US)', flag: '🇺🇸' },
    { value: 'en-GB', label: 'English (UK)', flag: '🇬🇧' },
    { value: 'en-AU', label: 'English (Australia)', flag: '🇦🇺' },
    { value: 'es', label: 'Spanish', flag: '🇪🇸' },
    { value: 'fr', label: 'French', flag: '🇫🇷' },
    { value: 'de', label: 'German', flag: '🇩🇪' },
    { value: 'it', label: 'Italian', flag: '🇮🇹' },
];

type TabType = 'llm' | 'voice' | 'tts';

const SUPPORTED_LANGUAGE_OPTIONS = [
    ...LANGUAGE_OPTIONS,
    { value: 'en-IN', label: 'English (India)', flag: '' },
    { value: 'hi', label: 'Hindi', flag: '' },
    { value: 'hi-IN', label: 'Hindi (India)', flag: '' },
    { value: 'ml', label: 'Malayalam', flag: '' },
    { value: 'ml-IN', label: 'Malayalam (India)', flag: '' },
    { value: 'multi', label: 'Multilingual (Auto)', flag: '' },
];

const DEEPGRAM_TTS_SUPPORTED_LANGUAGES = new Set([
    'en',
    'en-US',
    'en-GB',
    'en-AU',
    'en-IN',
    'es',
    'fr',
    'de',
    'it',
]);

export default function CreateAgentModal({ isOpen, onClose, onSuccess }: CreateAgentModalProps) {
    const [activeTab, setActiveTab] = useState<TabType>('llm');
    const [name, setName] = useState('');
    const [agentName, setAgentName] = useState('');
    const [systemPrompt, setSystemPrompt] = useState('');
    const [selectedModel, setSelectedModel] = useState('kimi-k2.5');
    const [selectedTtsProvider, setSelectedTtsProvider] = useState('deepgram');
    const [selectedVoice, setSelectedVoice] = useState('aura-asteria-en');
    const [selectedTtsModel, setSelectedTtsModel] = useState('');
    const [selectedLanguage, setSelectedLanguage] = useState('en-US');
    const [voiceRuntimeMode, setVoiceRuntimeMode] = useState('pipeline');
    const [voiceRealtimeModel, setVoiceRealtimeModel] = useState('');
    const [ttsVoices, setTtsVoices] = useState<TTSVoiceOption[]>([]);
    const [ttsModels, setTtsModels] = useState<TTSModelOption[]>([]);
    const [ttsLoading, setTtsLoading] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [created, setCreated] = useState(false);

    const loadProviderVoices = async (provider: string, modelId?: string) => {
        setTtsLoading(true);
        try {
            const params = modelId
                ? { provider, model: modelId }
                : { provider };
            const response = await axios.get(`${API_URL}tts/voices`, { params });
            setTtsVoices(response.data?.voices || []);
        } catch (fetchError) {
            setTtsVoices([]);
        } finally {
            setTtsLoading(false);
        }
    };

    const loadTtsOptions = async (provider: string) => {
        if (provider === 'deepgram') {
            setTtsVoices([]);
            setTtsModels([]);
            setSelectedTtsModel('');
            return;
        }

        setTtsLoading(true);
        try {
            const [voicesResponse, modelsResponse] = await Promise.all([
                axios.get(`${API_URL}tts/voices`, { params: { provider } }),
                axios.get(`${API_URL}tts/models`, { params: { provider } }),
            ]);
            setTtsVoices(voicesResponse.data?.voices || []);
            setTtsModels(modelsResponse.data?.models || []);
            if (modelsResponse.data?.available === false) {
                setError(provider === 'xai'
                    ? 'xAI is not configured on the server yet. Add XAI_API_KEY before using it live.'
                    : 'ElevenLabs is not configured on the server yet. Add ELEVEN_API_KEY before using it live.');
            }
        } catch (fetchError) {
            setTtsVoices([]);
            setTtsModels([]);
        } finally {
            setTtsLoading(false);
        }
    };

    useEffect(() => {
        if (!isOpen) return;
        void loadTtsOptions(selectedTtsProvider);
    }, [isOpen, selectedTtsProvider]);

    useEffect(() => {
        if (!isOpen || selectedTtsProvider !== 'elevenlabs' || !selectedTtsModel) return;
        void loadProviderVoices('elevenlabs', selectedTtsModel);
    }, [isOpen, selectedTtsProvider, selectedTtsModel]);

    useEffect(() => {
        if (selectedTtsProvider === 'xai') {
            if (!selectedVoice || !XAI_VOICE_IDS.has(selectedVoice)) {
                setSelectedVoice('eve');
            }
            if (!selectedTtsModel) {
                setSelectedTtsModel(XAI_DEFAULT_MODEL);
            }
            return;
        }
        if (selectedTtsProvider === 'deepgram') {
            if (!DEEPGRAM_VOICE_IDS.has(selectedVoice)) {
                setSelectedVoice('aura-asteria-en');
            }
            return;
        }
        if (!DEEPGRAM_VOICE_IDS.has(selectedVoice) && !XAI_VOICE_IDS.has(selectedVoice)) return;
        setSelectedVoice('');
    }, [selectedTtsProvider, selectedVoice, selectedTtsModel]);

    const tabs = [
        { id: 'llm' as TabType, label: 'LLM', icon: Cpu, description: 'Language Model' },
        { id: 'voice' as TabType, label: 'Voice', icon: Volume2, description: 'Voice Settings' },
        { id: 'tts' as TabType, label: 'TTS', icon: Zap, description: 'Text-to-Speech' },
    ];

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!name.trim()) {
            setError('Agent name is required');
            return;
        }
        if (selectedTtsProvider === 'deepgram' && !DEEPGRAM_TTS_SUPPORTED_LANGUAGES.has(selectedLanguage)) {
            setError('Use ElevenLabs or xAI for Hindi, Malayalam, or multilingual output.');
            return;
        }
        if (!selectedVoice) {
            const voiceLabel = selectedTtsProvider === 'elevenlabs'
                ? 'voice ID'
                : selectedTtsProvider === 'xai'
                    ? 'xAI voice'
                    : 'voice';
            setError(`Select a ${voiceLabel}.`);
            return;
        }
        if (selectedTtsProvider === 'elevenlabs' && !selectedTtsModel) {
            setError('Select an ElevenLabs model.');
            return;
        }
        if (selectedTtsProvider === 'xai' && !selectedTtsModel) {
            setError('Select an xAI voice model.');
            return;
        }
        if (selectedTtsProvider !== 'xai' && voiceRuntimeMode === 'realtime_text_tts' && !voiceRealtimeModel.trim()) {
            setError('Enter the realtime model you want this agent to use.');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            await axios.post(`${API_URL}agents/`, {
                name: name.trim(),
                agent_name: agentName.trim() || null,
                system_prompt: systemPrompt.trim() || 'You are a helpful AI assistant.',
                llm_model: selectedModel,
                voice: selectedVoice,
                tts_provider: selectedTtsProvider,
                tts_model: selectedTtsProvider === 'deepgram' ? null : selectedTtsModel,
                language: selectedLanguage,
                twilio_number: null,
                custom_params: selectedTtsProvider === 'xai'
                    ? {
                        voice_runtime_mode: 'realtime_unified',
                        voice_realtime_model: selectedTtsModel || XAI_DEFAULT_MODEL,
                    }
                    : voiceRuntimeMode === 'realtime_text_tts'
                        ? {
                            voice_runtime_mode: 'realtime_text_tts',
                            voice_realtime_model: voiceRealtimeModel.trim(),
                        }
                        : {}
            });

            setCreated(true);
            setTimeout(() => {
                onSuccess();
                onClose();
                setName('');
                setAgentName('');
                setSystemPrompt('');
                setSelectedModel('kimi-k2.5');
                setSelectedTtsProvider('deepgram');
                setSelectedVoice('aura-asteria-en');
                setSelectedTtsModel('');
                setSelectedLanguage('en-US');
                setVoiceRuntimeMode('pipeline');
                setVoiceRealtimeModel('');
                setCreated(false);
            }, 1500);
        } catch (err) {
            console.error('Error creating agent:', err);
            setError('Failed to create agent. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const getProviderColor = (provider: string) => {
        switch (provider) {
            case 'OpenAI': return 'bg-green-100 text-green-700';
            case 'Moonshot': return 'bg-purple-100 text-purple-700';
            default: return 'bg-gray-100 text-gray-700';
        }
    };

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white">
                    <div className="flex items-center gap-3">
                        <div className="w-11 h-11 bg-gradient-to-br from-green-500 to-emerald-600 rounded-xl flex items-center justify-center shadow-lg shadow-green-200">
                            <Bot className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-gray-900">Create New Agent</h2>
                            <p className="text-sm text-gray-500">Configure your AI voice assistant</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-xl transition-colors"
                    >
                        <X className="w-5 h-5 text-gray-400" />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="flex-1 overflow-hidden flex flex-col">
                    <div className="flex-1 overflow-y-auto p-6">
                        {error && (
                            <div className="mb-5 p-4 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600 flex items-center gap-2">
                                <span className="w-5 h-5 bg-red-100 rounded-full flex items-center justify-center text-red-500">!</span>
                                {error}
                            </div>
                        )}

                        {created && (
                            <div className="mb-5 p-4 bg-green-50 border border-green-100 rounded-xl text-sm text-green-600 flex items-center gap-2">
                                <Check className="w-5 h-5" />
                                Agent created successfully!
                            </div>
                        )}

                        <div className="space-y-6">
                            {/* Agent Name */}
                            <div className="bg-gray-50 rounded-xl p-5 border border-gray-100">
                                <label className="block text-sm font-semibold text-gray-700 mb-2">
                                    Agent Name <span className="text-red-500">*</span>
                                </label>
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    placeholder="e.g., Customer Support Agent"
                                    className="w-full px-4 py-3 bg-white border border-gray-200 rounded-lg text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all"
                                    required
                                />
                            </div>

                            {/* Tabs */}
                            <div className="flex gap-2 p-1 bg-gray-100 rounded-xl">
                                {tabs.map((tab) => {
                                    const Icon = tab.icon;
                                    return (
                                        <button
                                            key={tab.id}
                                            type="button"
                                            onClick={() => setActiveTab(tab.id)}
                                            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                                                activeTab === tab.id
                                                    ? 'bg-white text-gray-900 shadow-md'
                                                    : 'text-gray-500 hover:text-gray-700'
                                            }`}
                                        >
                                            <Icon className={`w-4 h-4 ${activeTab === tab.id ? 'text-green-600' : ''}`} />
                                            {tab.label}
                                        </button>
                                    );
                                })}
                            </div>

                            {/* Tab Content */}
                            <div className="bg-gray-50 rounded-xl p-5 border border-gray-100 min-h-[280px]">
                                {/* LLM Tab */}
                                {activeTab === 'llm' && (
                                    <div className="space-y-4">
                                        <div className="flex items-center gap-2 mb-4">
                                            <Cpu className="w-5 h-5 text-gray-400" />
                                            <h3 className="text-sm font-semibold text-gray-700">Language Model</h3>
                                        </div>
                                        <div className="space-y-2">
                                            {MODEL_OPTIONS.map((model) => (
                                                <button
                                                    key={model.value}
                                                    type="button"
                                                    onClick={() => setSelectedModel(model.value)}
                                                    className={`w-full flex items-center justify-between p-4 rounded-xl border-2 transition-all ${
                                                        selectedModel === model.value
                                                            ? 'border-green-500 bg-white shadow-md'
                                                            : 'border-gray-100 hover:border-gray-200 bg-white'
                                                    }`}
                                                >
                                                    <div className="flex items-center gap-3">
                                                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${getProviderColor(model.provider)}`}>
                                                            <Sparkles className="w-5 h-5" />
                                                        </div>
                                                        <div className="text-left">
                                                            <p className="font-medium text-gray-900">{model.label}</p>
                                                            <p className="text-xs text-gray-500">{model.provider}</p>
                                                        </div>
                                                    </div>
                                                    <div className="text-right">
                                                        <span className="text-sm font-semibold text-green-600">{model.price}</span>
                                                        {selectedModel === model.value && (
                                                            <Check className="w-5 h-5 text-green-500 ml-2" />
                                                        )}
                                                    </div>
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Voice Tab */}
                                {activeTab === 'voice' && (
                                    <div className="space-y-4">
                                        <div className="flex items-center justify-between mb-4">
                                            <div className="flex items-center gap-2">
                                                <Volume2 className="w-5 h-5 text-gray-400" />
                                                <h3 className="text-sm font-semibold text-gray-700">Voice Selection</h3>
                                            </div>
                                            <select
                                                value={selectedLanguage}
                                                onChange={(e) => setSelectedLanguage(e.target.value)}
                                                className="px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-green-500"
                                            >
                                                {SUPPORTED_LANGUAGE_OPTIONS.map((lang) => (
                                                    <option key={lang.value} value={lang.value}>
                                                        {lang.flag} {lang.label}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                        {selectedTtsProvider === 'deepgram' ? (
                                            <div className="grid grid-cols-2 gap-3">
                                                {VOICE_OPTIONS.map((voice) => (
                                                    <button
                                                        key={voice.value}
                                                        type="button"
                                                        onClick={() => setSelectedVoice(voice.value)}
                                                        className={`flex items-center gap-3 p-3 rounded-xl border-2 transition-all ${
                                                            selectedVoice === voice.value
                                                                ? 'border-green-500 bg-white shadow-md'
                                                                : 'border-gray-100 hover:border-gray-200 bg-white'
                                                        }`}
                                                    >
                                                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                                                            voice.gender === 'Female' ? 'bg-pink-100' : 'bg-blue-100'
                                                        }`}>
                                                            <Volume2 className={`w-5 h-5 ${voice.gender === 'Female' ? 'text-pink-500' : 'text-blue-500'}`} />
                                                        </div>
                                                        <div className="text-left flex-1">
                                                            <p className="font-medium text-gray-900 text-sm">{voice.label}</p>
                                                            <p className="text-xs text-gray-500">{voice.accent} • {voice.gender}</p>
                                                        </div>
                                                        {selectedVoice === voice.value && (
                                                            <Check className="w-5 h-5 text-green-500" />
                                                        )}
                                                    </button>
                                                ))}
                                            </div>
                                        ) : (
                                            <div className="space-y-3">
                                                <select
                                                    value={selectedVoice}
                                                    onChange={(e) => setSelectedVoice(e.target.value)}
                                                    disabled={ttsLoading}
                                                    className="w-full px-4 py-3 bg-white border border-gray-200 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                                                >
                                                    <option value="">
                                                        {selectedTtsProvider === 'xai' ? 'Select an xAI voice' : 'Select an ElevenLabs voice'}
                                                    </option>
                                                    {ttsVoices.map((voice) => (
                                                        <option key={voice.id} value={voice.id}>
                                                            {voice.label}
                                                            {voice.category ? ` [${voice.category}]` : ''}
                                                        </option>
                                                    ))}
                                                </select>
                                                <p className="text-xs text-gray-500">
                                                    {selectedTtsProvider === 'xai'
                                                        ? 'xAI voices come from the backend provider catalog and stay on the unified realtime path.'
                                                        : 'Voice IDs come directly from the backend&apos;s ElevenLabs integration. Nothing is auto-picked.'}
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* TTS Tab */}
                                {activeTab === 'tts' && (
                                    <div className="space-y-4">
                                        <div className="flex items-center gap-2 mb-4">
                                            <Zap className="w-5 h-5 text-gray-400" />
                                            <h3 className="text-sm font-semibold text-gray-700">Text-to-Speech Provider</h3>
                                        </div>
                                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                            {TTS_PROVIDERS.map((provider) => (
                                                <button
                                                    key={provider.value}
                                                    type="button"
                                                    onClick={() => setSelectedTtsProvider(provider.value)}
                                                    className={`flex flex-col items-center justify-center p-5 rounded-xl border-2 transition-all ${
                                                        selectedTtsProvider === provider.value
                                                            ? 'border-green-500 bg-white shadow-md'
                                                            : 'border-gray-100 hover:border-gray-200 bg-white'
                                                    }`}
                                                >
                                                    <div className={`w-14 h-14 rounded-xl flex items-center justify-center mb-3 ${
                                                        provider.value === 'deepgram' 
                                                            ? 'bg-gradient-to-br from-purple-500 to-purple-600' 
                                                            : provider.value === 'xai'
                                                                ? 'bg-gradient-to-br from-sky-500 to-cyan-600'
                                                                : 'bg-gradient-to-br from-orange-500 to-red-500'
                                                    }`}>
                                                        <Zap className="w-7 h-7 text-white" />
                                                    </div>
                                                    <p className="font-semibold text-gray-900">{provider.label}</p>
                                                    <p className="text-xs text-gray-500 mt-1">{provider.description}</p>
                                                    {selectedTtsProvider === provider.value && (
                                                        <Check className="w-5 h-5 text-green-500 mt-2" />
                                                    )}
                                                </button>
                                            ))}
                                        </div>
                                        {selectedTtsProvider !== 'deepgram' && (
                                            <div className="space-y-3">
                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                                        {selectedTtsProvider === 'xai' ? 'xAI Voice Model' : 'ElevenLabs Model'}
                                                    </label>
                                                    <select
                                                        value={selectedTtsModel}
                                                        onChange={(e) => setSelectedTtsModel(e.target.value)}
                                                        disabled={ttsLoading}
                                                        className="w-full px-4 py-3 bg-white border border-gray-200 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                                                    >
                                                        <option value="">{selectedTtsProvider === 'xai' ? 'Select an xAI model' : 'Select an ElevenLabs model'}</option>
                                                        {ttsModels.map((model) => (
                                                            <option key={model.id} value={model.id}>
                                                                {model.name}
                                                                {selectedTtsProvider === 'xai'
                                                                    ? model.deprecated ? ' (Legacy)' : ' (Unified)'
                                                                    : model.is_v3 ? ' (v3)' : model.supports_multilingual ? ' (Multilingual)' : ''}
                                                            </option>
                                                        ))}
                                                    </select>
                                                </div>
                                                {selectedTtsProvider === 'elevenlabs' && selectedTtsModel && selectedTtsModel.includes('v3') && (
                                                    <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
                                                        `eleven_v3` stays available when you choose it, but it is the slower HTTP path for live synthesis.
                                                    </div>
                                                )}
                                                {selectedTtsProvider === 'xai' && (
                                                    <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-700">
                                                        xAI uses a unified realtime voice model, so STT, reasoning, and voice output all come from the same provider session.
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                        <div className="space-y-3">
                                            <div>
                                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                                    Voice Runtime
                                                </label>
                                                {selectedTtsProvider === 'xai' ? (
                                                    <select
                                                        value="realtime_unified"
                                                        disabled
                                                        className="w-full px-4 py-3 bg-gray-100 border border-gray-200 rounded-lg text-gray-900 cursor-not-allowed"
                                                    >
                                                        <option value="realtime_unified">Realtime unified (xAI)</option>
                                                    </select>
                                                ) : (
                                                    <select
                                                        value={voiceRuntimeMode}
                                                        onChange={(e) => setVoiceRuntimeMode(e.target.value)}
                                                        className="w-full px-4 py-3 bg-white border border-gray-200 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                                                    >
                                                        <option value="pipeline">Pipeline</option>
                                                        <option value="realtime_text_tts">Realtime text + TTS</option>
                                                    </select>
                                                )}
                                            </div>
                                            {selectedTtsProvider !== 'xai' && voiceRuntimeMode === 'realtime_text_tts' && (
                                                <div>
                                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                                        Realtime Model
                                                    </label>
                                                    <input
                                                        type="text"
                                                        value={voiceRealtimeModel}
                                                        onChange={(e) => setVoiceRealtimeModel(e.target.value)}
                                                        placeholder="e.g. gpt-realtime"
                                                        className="w-full px-4 py-3 bg-white border border-gray-200 rounded-lg text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                                                    />
                                                    <p className="mt-2 text-xs text-gray-500">
                                                        This is saved only when you explicitly choose realtime here.
                                                    </p>
                                                </div>
                                            )}
                                            {selectedTtsProvider === 'xai' && (
                                                <p className="text-xs text-gray-500">
                                                    Choosing xAI automatically saves this agent on the unified realtime voice path.
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* System Prompt */}
                            <div>
                                <label className="block text-sm font-semibold text-gray-700 mb-2">
                                    System Prompt
                                </label>
                                <textarea
                                    value={systemPrompt}
                                    onChange={(e) => setSystemPrompt(e.target.value)}
                                    placeholder="Define how your agent should behave..."
                                    rows={4}
                                    className="w-full px-4 py-3 border border-gray-200 rounded-xl text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all resize-none"
                                />
                                <p className="mt-2 text-xs text-gray-500">
                                    This prompt defines your agent&apos;s personality and behavior.
                                </p>
                            </div>

                            {/* Advanced - Agent Name */}
                            <details className="group">
                                <summary className="flex items-center gap-2 cursor-pointer text-sm font-medium text-gray-600 hover:text-gray-900">
                                    <Settings className="w-4 h-4" />
                                    Advanced Settings
                                    <ChevronDown className="w-4 h-4 transition-transform group-open:rotate-180" />
                                </summary>
                                <div className="mt-4 p-4 bg-gray-50 rounded-xl border border-gray-100">
                                    <label className="block text-sm font-medium text-gray-700 mb-1.5">
                                        LiveKit Agent Name (for dispatch)
                                    </label>
                                    <input
                                        type="text"
                                        value={agentName}
                                        onChange={(e) => setAgentName(e.target.value)}
                                        placeholder="e.g., sarah"
                                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500"
                                    />
                                    <p className="mt-1.5 text-xs text-gray-500">
                                        The agent name used for dispatching. Must match your voice agent worker.
                                    </p>
                                </div>
                            </details>
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100 bg-gray-50">
                        <p className="text-xs text-gray-500">
                            Creating a voice-enabled AI agent
                        </p>
                        <div className="flex items-center gap-3">
                            <button
                                type="button"
                                onClick={onClose}
                                className="px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-xl transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                disabled={loading || created}
                                className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-green-500 to-emerald-600 text-white text-sm font-semibold rounded-xl hover:from-green-600 hover:to-emerald-700 transition-all shadow-lg shadow-green-200 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {loading ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        Creating...
                                    </>
                                ) : (
                                    <>
                                        <Bot className="w-4 h-4" />
                                        Create Agent
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    );
}
