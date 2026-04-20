'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
    Bot, Phone, BookOpen, PhoneCall, History, BarChart3, Settings, Key, X,
    ChevronRight, Sparkles, MessageSquare, GitBranch, Mic, Globe, Cpu,
    Check, ArrowRight, ArrowLeft, Plus, Trash2, Play
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

const AGENT_TYPES = [
    {
        id: 'conversation-flow',
        name: 'Conversation Flow Agent',
        description: 'Multi-step, branching conversations with visual flow builder',
        icon: GitBranch,
        bestFor: 'Complex interactions with multiple paths'
    },
    {
        id: 'single-prompt',
        name: 'Single Prompt Agent',
        description: 'Simple, one-off interactions with a single system prompt',
        icon: MessageSquare,
        bestFor: 'Quick Q&A and simple tasks'
    },
    {
        id: 'multi-prompt',
        name: 'Multi-Prompt Agent',
        description: 'Sequential data collection with multiple prompts',
        icon: MessageSquare,
        bestFor: 'Form filling and data gathering'
    },
    {
        id: 'custom-llm',
        name: 'Custom LLM Agent',
        description: 'Bring your own language model and configuration',
        icon: Cpu,
        bestFor: 'Advanced users with specific requirements'
    }
];

const TTS_PROVIDER_OPTIONS = [
    { value: 'deepgram', label: 'Deepgram' },
    { value: 'elevenlabs', label: 'ElevenLabs' },
];

interface TTSVoiceOption {
    id: string;
    label: string;
    accent?: string | null;
    gender?: string | null;
}

interface TTSModelOption {
    id: string;
    name: string;
    is_v3?: boolean;
    streaming_type?: string;
    languages_count?: number;
    languages?: string[];
    supports_multilingual?: boolean;
}

const DEEPGRAM_VOICE_OPTIONS: TTSVoiceOption[] = [
    { id: 'jessica', label: 'Jessica', accent: 'English (UK)', gender: 'Female' },
    { id: 'mark', label: 'Mark', accent: 'English (US)', gender: 'Male' },
    { id: 'sarah', label: 'Sarah', accent: 'English (UK)', gender: 'Female' },
    { id: 'michael', label: 'Michael', accent: 'English (US)', gender: 'Male' },
    { id: 'emma', label: 'Emma', accent: 'English (UK)', gender: 'Female' },
    { id: 'james', label: 'James', accent: 'English (US)', gender: 'Male' },
];
const DEEPGRAM_VOICE_IDS = new Set([
    ...DEEPGRAM_VOICE_OPTIONS.map((voice) => voice.id),
    'aura-asteria-en',
    'aura-luna-en',
    'aura-hera-en',
    'aura-orion-en',
    'aura-perseus-en',
    'aura-zeus-en',
]);

const SUPPORTED_LANGUAGE_OPTIONS = [
    { value: 'en-US', label: 'English (US)' },
    { value: 'en-GB', label: 'English (UK)' },
    { value: 'en-AU', label: 'English (Australia)' },
    { value: 'en-IN', label: 'English (India)' },
    { value: 'es', label: 'Spanish' },
    { value: 'fr', label: 'French' },
    { value: 'de', label: 'German' },
    { value: 'it', label: 'Italian' },
    { value: 'hi', label: 'Hindi' },
    { value: 'ml', label: 'Malayalam' },
    { value: 'multi', label: 'Multilingual (Auto)' },
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

const ELEVENLABS_LANGUAGE_ID_MAP: Record<string, string[]> = {
    'en': ['eng'],
    'en-US': ['eng'],
    'en-GB': ['eng'],
    'en-AU': ['eng'],
    'en-IN': ['eng'],
    'es': ['spa'],
    'fr': ['fra'],
    'de': ['deu'],
    'it': ['ita'],
    'hi': ['hin'],
    'hi-IN': ['hin'],
    'ml': ['mal'],
    'ml-IN': ['mal'],
};

const languageRequiresElevenLabsTts = (language: string) => !DEEPGRAM_TTS_SUPPORTED_LANGUAGES.has(language);

const isElevenV3Model = (modelId?: string | null) => {
    const normalized = String(modelId || '').toLowerCase();
    return normalized.includes('v3') && !normalized.includes('flash');
};

const modelSupportsLanguage = (model: TTSModelOption, language: string) => {
    if (!model?.id) return false;
    if (model.is_v3 || isElevenV3Model(model.id)) return true;
    if (language === 'multi') {
        return Boolean(model.supports_multilingual);
    }
    const requiredLanguageIds = ELEVENLABS_LANGUAGE_ID_MAP[language] || [];
    if (requiredLanguageIds.length === 0) return true;
    const modelLanguages = Array.isArray(model.languages)
        ? model.languages.map((entry) => String(entry || '').toLowerCase())
        : [];
    if (modelLanguages.length === 0) return true;
    return requiredLanguageIds.some((languageId) => modelLanguages.includes(languageId));
};

const getCompatibleElevenModels = (models: TTSModelOption[], language: string) =>
    models.filter((model) => modelSupportsLanguage(model, language));

const getLanguageLabel = (language: string) =>
    SUPPORTED_LANGUAGE_OPTIONS.find((option) => option.value === language)?.label || language;

const LLM_OPTIONS = [
    { value: 'gpt-5.4', name: 'GPT-5.4', provider: 'OpenAI', description: 'Latest flagship model' },
    { value: 'gpt-5.4-pro', name: 'GPT-5.4 Pro', provider: 'OpenAI', description: 'Maximum capability' },
    { value: 'gpt-5.2', name: 'GPT-5.2', provider: 'OpenAI', description: 'Flagship balance' },
    { value: 'gpt-5.2-pro', name: 'GPT-5.2 Pro', provider: 'OpenAI', description: 'Higher capability' },
    { value: 'gpt-5.1', name: 'GPT-5.1', provider: 'OpenAI', description: 'Strong general model' },
    { value: 'gpt-5-pro', name: 'GPT-5 Pro', provider: 'OpenAI', description: 'High capability' },
    { value: 'gpt-5', name: 'GPT-5', provider: 'OpenAI', description: 'Standard GPT-5' },
    { value: 'gpt-5-mini', name: 'GPT-5 mini', provider: 'OpenAI', description: 'Fast & cost-efficient' },
    { value: 'gpt-5-nano', name: 'GPT-5 nano', provider: 'OpenAI', description: 'Lowest latency' },
    { value: 'gpt-4.1', name: 'GPT-4.1', provider: 'OpenAI', description: 'Strong instruction following' },
    { value: 'gpt-4.1-mini', name: 'GPT-4.1 mini', provider: 'OpenAI', description: 'Fast & cheap' },
    { value: 'gpt-4.1-nano', name: 'GPT-4.1 nano', provider: 'OpenAI', description: 'Ultra low cost' },
    { value: 'gpt-4o', name: 'GPT-4o', provider: 'OpenAI', description: 'Omni model' },
    { value: 'gpt-4o-mini', name: 'GPT-4o mini', provider: 'OpenAI', description: 'Fast & cheap' },
    { value: 'gpt-4', name: 'GPT-4 (Legacy)', provider: 'OpenAI', description: 'Legacy GPT-4' },
    { value: 'o1', name: 'o1', provider: 'OpenAI', description: 'Reasoning model' },
    { value: 'o1-pro', name: 'o1 Pro', provider: 'OpenAI', description: 'Advanced reasoning' },
    { value: 'o3', name: 'o3', provider: 'OpenAI', description: 'Reasoning model' },
    { value: 'o3-mini', name: 'o3-mini', provider: 'OpenAI', description: 'Fast reasoning' },
    { value: 'o4-mini', name: 'o4-mini', provider: 'OpenAI', description: 'Reasoning mini' },
    { value: 'moonshot-v1-8k', name: 'Moonshot V1 8K', provider: 'Moonshot AI', description: 'Standard Moonshot model' },
    { value: 'moonshot-v1-32k', name: 'Moonshot V1 32K', provider: 'Moonshot AI', description: 'Extended context model' },
    { value: 'moonshot-v1-128k', name: 'Moonshot V1 128K', provider: 'Moonshot AI', description: 'Longest context model' },
    { value: 'kimi-k2.5', name: 'Kimi K2.5', provider: 'Moonshot AI', description: 'Agentic model' },
    { value: 'kimi-k2-thinking', name: 'Kimi K2 Thinking', provider: 'Moonshot AI', description: 'Reasoning-focused' },
    { value: 'kimi-k2-instruct', name: 'Kimi K2 Instruct', provider: 'Moonshot AI', description: 'Instruction-following' },
    { value: 'moonlight-16b-a3b', name: 'Moonlight 16B', provider: 'Moonshot AI', description: 'Lightweight model' },
];

const NODE_TYPES = [
    { type: 'conversation', name: 'Conversation Node', description: 'Ask questions, capture responses', icon: MessageSquare },
    { type: 'logic', name: 'Logic Split Node', description: 'Branch based on conditions', icon: GitBranch },
    { type: 'function', name: 'Function Node', description: 'Call APIs, trigger actions', icon: Cpu },
    { type: 'transfer', name: 'Call Transfer Node', description: 'Route to human agents', icon: Phone },
    { type: 'digit', name: 'Press Digit Node', description: 'DTMF/keypad input', icon: PhoneCall },
    { type: 'end', name: 'Ending Node', description: 'Gracefully end calls', icon: Check },
];

const PREBUILT_FUNCTIONS = [
    { id: 'book-appointment', name: 'Book Appointment', description: 'Schedule appointments in calendar' },
    { id: 'transfer-call', name: 'Transfer Call', description: 'Route to human agents' },
    { id: 'send-sms', name: 'Send SMS', description: 'Send text messages' },
    { id: 'update-crm', name: 'Update CRM', description: 'Update customer records' },
    { id: 'check-order', name: 'Check Order Status', description: 'Lookup order information' },
    { id: 'navigate-ivr', name: 'Navigate IVR', description: 'Interactive voice response' },
];

interface CreateAgentWizardProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export default function CreateAgentWizard({ isOpen, onClose, onSuccess }: CreateAgentWizardProps) {
    const router = useRouter();
    const [toast, setToast] = useState<{message: string, type: string} | null>(null);
    const showToast = (msg: string, type: string = 'info') => { setToast({message: msg, type}); setTimeout(() => setToast(null), 3000); };
    const [currentStep, setCurrentStep] = useState(1);
    const [isLoading, setIsLoading] = useState(false);

    // Step 1: Agent Type
    const [selectedType, setSelectedType] = useState('conversation-flow');

    // Step 2: Configure Settings
    const [agentName, setAgentName] = useState('');
    const [selectedTtsProvider, setSelectedTtsProvider] = useState('deepgram');
    const [selectedTtsModel, setSelectedTtsModel] = useState('');
    const [selectedVoice, setSelectedVoice] = useState('jessica');
    const [customElevenVoiceId, setCustomElevenVoiceId] = useState('');
    const [ttsVoices, setTtsVoices] = useState<TTSVoiceOption[]>([]);
    const [ttsModels, setTtsModels] = useState<TTSModelOption[]>([]);
    const [ttsLoading, setTtsLoading] = useState(false);
    const [selectedLLM, setSelectedLLM] = useState('moonshot-v1-8k');
    const [globalPrompt, setGlobalPrompt] = useState('');
    const [primaryLanguage, setPrimaryLanguage] = useState('en-GB');
    const [voiceRuntimeMode, setVoiceRuntimeMode] = useState('pipeline');
    const [voiceRealtimeModel, setVoiceRealtimeModel] = useState('');

    // Step 3: Flow Builder (for conversation flow agents)
    const [nodes, setNodes] = useState<any[]>([]);
    const [selectedNodeType, setSelectedNodeType] = useState<string | null>(null);

    // Step 4: Functions
    const [selectedFunctions, setSelectedFunctions] = useState<string[]>([]);

    // Step 5: Testing
    const [testMessages, setTestMessages] = useState<any[]>([]);
    const [testInput, setTestInput] = useState('');
    const compatibleElevenModels = getCompatibleElevenModels(ttsModels, primaryLanguage);
    const visibleElevenModels = compatibleElevenModels.length > 0 ? compatibleElevenModels : ttsModels;
    const selectedLanguageLabel = getLanguageLabel(primaryLanguage);
    const selectedTtsModelMeta =
        visibleElevenModels.find((model) => model.id === selectedTtsModel)
        || ttsModels.find((model) => model.id === selectedTtsModel)
        || null;

    const loadTtsVoicesForModel = async (provider: string, modelId?: string) => {
        const normalized = provider === 'elevenlabs' ? 'elevenlabs' : 'deepgram';
        if (normalized !== 'elevenlabs') return;
        setTtsLoading(true);
        try {
            const modelParam = modelId ? `&model=${encodeURIComponent(modelId)}` : '';
            const voicesData = await fetch(`${API_URL}/tts/voices?provider=${normalized}${modelParam}`).then((r) => r.json());
            const voices = (voicesData?.voices || []) as TTSVoiceOption[];
            setTtsVoices(voices);
        } catch (e) {
            // Keep existing voices on error
        } finally {
            setTtsLoading(false);
        }
    };

    const loadTtsOptions = async (provider: string) => {
        const normalized = provider === 'elevenlabs' ? 'elevenlabs' : 'deepgram';
        setTtsLoading(true);
        if (normalized === 'deepgram') {
            setTtsVoices(DEEPGRAM_VOICE_OPTIONS);
            setTtsModels([]);
            setTtsLoading(false);
            return;
        }

        setTtsVoices([]);
        setTtsModels([]);
        try {
            const voicesPromise = fetch(`${API_URL}/tts/voices?provider=${normalized}`).then((r) => r.json());
            const modelsPromise = normalized === 'elevenlabs'
                ? fetch(`${API_URL}/tts/models?provider=${normalized}`).then((r) => r.json())
                : Promise.resolve({ models: [] });
            const [voicesData, modelsData] = await Promise.all([voicesPromise, modelsPromise]);

            if (normalized === 'elevenlabs' && modelsData?.available === false) {
                showToast('ElevenLabs is not configured on the server (missing ELEVEN_API_KEY).', 'error');
            }

            const voices = (voicesData?.voices || []) as TTSVoiceOption[];
            setTtsVoices(voices);

            if (normalized === 'elevenlabs') {
                const models = (modelsData?.models || []) as TTSModelOption[];
                setTtsModels(models);
            } else {
                setTtsModels([]);
            }
        } catch (e) {
            if (normalized === 'elevenlabs') {
                showToast('Could not load ElevenLabs voices. Configure ELEVEN_API_KEY on backend.', 'error');
            }
            setTtsVoices([]);
            setTtsModels([]);
        } finally {
            setTtsLoading(false);
        }
    };

    useEffect(() => {
        if (!isOpen) return;
        loadTtsOptions(selectedTtsProvider);
    }, [isOpen, selectedTtsProvider]);

    // Re-fetch voices when ElevenLabs model changes (v3 shows all voices, v2.5 filters by compatibility)
    useEffect(() => {
        if (!isOpen || selectedTtsProvider !== 'elevenlabs' || !selectedTtsModel) return;
        loadTtsVoicesForModel('elevenlabs', selectedTtsModel);
    }, [selectedTtsModel]);

    useEffect(() => {
        if (selectedTtsProvider !== 'elevenlabs') return;
        if (!selectedVoice) return;
        if (!DEEPGRAM_VOICE_IDS.has(selectedVoice)) return;
        setSelectedVoice('');
    }, [selectedTtsProvider, selectedVoice]);

    useEffect(() => {
        if (selectedTtsProvider !== 'elevenlabs') return;
        if (!selectedVoice) return;
        if (DEEPGRAM_VOICE_IDS.has(selectedVoice)) return;
        if (ttsVoices.find((voice) => voice.id === selectedVoice)) return;
        setTtsVoices((prev) => [
            { id: selectedVoice, label: `Custom Voice ID (${selectedVoice})` },
            ...prev,
        ]);
    }, [selectedTtsProvider, selectedVoice, ttsVoices]);

    const handleNext = () => {
        if (currentStep === 2 && !agentName.trim()) {
            showToast('Please enter an agent name', 'error');
            return;
        }
        if (currentStep < 6) {
            setCurrentStep(currentStep + 1);
        }
    };

    const handleBack = () => {
        if (currentStep > 1) {
            setCurrentStep(currentStep - 1);
        }
    };

    const handleCreate = async () => {
        if (selectedTtsProvider === 'deepgram' && languageRequiresElevenLabsTts(primaryLanguage)) {
            showToast(`Use ElevenLabs for ${selectedLanguageLabel}. Deepgram TTS does not support that language.`, 'error');
            return;
        }
        if (!selectedVoice) {
            showToast(`Select a ${selectedTtsProvider === 'elevenlabs' ? 'voice ID' : 'voice'}`, 'error');
            return;
        }
        if (selectedTtsProvider === 'elevenlabs') {
            if (ttsVoices.length === 0) {
                showToast('ElevenLabs voices are not available. Configure ELEVEN_API_KEY on the server.', 'error');
                return;
            }
            if (visibleElevenModels.length === 0) {
                showToast('ElevenLabs models are not available. Configure ELEVEN_API_KEY on the server.', 'error');
                return;
            }
            if (!selectedTtsModel) {
                showToast('Select an ElevenLabs model', 'error');
                return;
            }
        }
        if (voiceRuntimeMode === 'realtime_text_tts' && !voiceRealtimeModel.trim()) {
            showToast('Enter the realtime model to use for realtime mode', 'error');
            return;
        }
        setIsLoading(true);
        try {
            const response = await fetch(`${API_URL}/agents/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: agentName,
                    type: selectedType,
                    voice: selectedVoice,
                    tts_provider: selectedTtsProvider,
                    tts_model: selectedTtsProvider === 'elevenlabs' ? selectedTtsModel : null,
                    llm_model: selectedLLM,
                    system_prompt: globalPrompt,
                    language: primaryLanguage,
                    functions: selectedFunctions,
                    flow: nodes,
                    custom_params: voiceRuntimeMode === 'realtime_text_tts'
                        ? {
                            voice_runtime_mode: 'realtime_text_tts',
                            voice_realtime_model: voiceRealtimeModel.trim(),
                        }
                        : {}
                })
            });

            if (response.ok) {
                showToast('Agent created successfully!', 'success');
                onSuccess();
                onClose();
                // Reset form
                setCurrentStep(1);
                setAgentName('');
                setGlobalPrompt('');
                setSelectedTtsProvider('deepgram');
                setSelectedTtsModel('');
                setSelectedVoice('jessica');
                setPrimaryLanguage('en-GB');
                setVoiceRuntimeMode('pipeline');
                setVoiceRealtimeModel('');
                setNodes([]);
                setSelectedFunctions([]);
            } else {
                throw new Error('Failed to create agent');
            }
        } catch (error) {
            showToast('Failed to create agent', 'error');
        } finally {
            setIsLoading(false);
        }
    };

    const applyCustomElevenVoiceId = () => {
        const voiceId = customElevenVoiceId.trim();
        if (!voiceId) {
            showToast('Enter an ElevenLabs voice ID', 'error');
            return;
        }
        if (DEEPGRAM_VOICE_IDS.has(voiceId)) {
            showToast('Enter a valid ElevenLabs voice_id, not a Deepgram voice.', 'error');
            return;
        }
        if (!ttsVoices.find((voice) => voice.id === voiceId)) {
            setTtsVoices((prev) => [{ id: voiceId, label: `Custom Voice ID (${voiceId})` }, ...prev]);
        }
        setSelectedVoice(voiceId);
        showToast('Custom ElevenLabs voice ID selected', 'success');
    };

    const addNode = (type: string) => {
        const newNode = {
            id: Date.now().toString(),
            type,
            position: { x: 100 + nodes.length * 50, y: 100 },
            data: { label: `${type} Node` }
        };
        setNodes([...nodes, newNode]);
        showToast(`${type} node added`, 'success');
    };

    const toggleFunction = (funcId: string) => {
        if (selectedFunctions.includes(funcId)) {
            setSelectedFunctions(selectedFunctions.filter(id => id !== funcId));
        } else {
            setSelectedFunctions([...selectedFunctions, funcId]);
        }
    };

    const handleTestSend = () => {
        if (!testInput.trim()) return;

        const userMessage = { role: 'user', content: testInput, timestamp: new Date() };
        setTestMessages([...testMessages, userMessage]);
        setTestInput('');

        // Simulate agent response
            setTimeout(() => {
                const agentMessage = {
                    role: 'agent',
                    content: `This is a test response from ${agentName || 'your agent'}. In production, this would connect to your LLM.`,
                    timestamp: new Date()
                };
                setTestMessages(prev => [...prev, agentMessage]);
            }, 1000);
        };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl h-[90vh] flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                    <div>
                        <h2 className="text-xl font-semibold text-gray-900">Create New Agent</h2>
                        <p className="text-sm text-gray-500">Step {currentStep} of 6</p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
                        <X className="w-5 h-5 text-gray-400" />
                    </button>
                </div>
                {toast && (
                    <div className={`mx-6 mt-2 px-4 py-2 rounded-lg text-sm ${toast.type === 'success' ? 'bg-green-100 text-green-800' : toast.type === 'error' ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'}`}>
                        {toast.message}
                    </div>
                )}

                {/* Progress Bar */}
                <div className="flex items-center px-6 py-4 bg-gray-50 border-b border-gray-100">
                    {['Type', 'Configure', 'Flow', 'Functions', 'Test', 'Deploy'].map((step, index) => (
                        <div key={step} className="flex items-center">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${currentStep > index + 1 ? 'bg-green-500 text-white' :
                                    currentStep === index + 1 ? 'bg-gray-900 text-white' :
                                        'bg-gray-200 text-gray-500'
                                }`}>
                                {currentStep > index + 1 ? <Check className="w-4 h-4" /> : index + 1}
                            </div>
                            <span className={`ml-2 text-sm ${currentStep === index + 1 ? 'text-gray-900 font-medium' : 'text-gray-500'
                                }`}>
                                {step}
                            </span>
                            {index < 5 && <ChevronRight className="w-4 h-4 text-gray-400 mx-2" />}
                        </div>
                    ))}
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {/* Step 1: Choose Agent Type */}
                    {currentStep === 1 && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-medium text-gray-900 mb-4">Choose Agent Type</h3>
                            <div className="grid grid-cols-2 gap-4">
                                {AGENT_TYPES.map((type) => (
                                    <button
                                        key={type.id}
                                        onClick={() => setSelectedType(type.id)}
                                        className={`p-6 rounded-xl border-2 text-left transition-all ${selectedType === type.id
                                                ? 'border-gray-900 bg-gray-50'
                                                : 'border-gray-200 hover:border-gray-300'
                                            }`}
                                    >
                                        <type.icon className={`w-8 h-8 mb-3 ${selectedType === type.id ? 'text-gray-900' : 'text-gray-400'
                                            }`} />
                                        <h4 className="font-semibold text-gray-900 mb-1">{type.name}</h4>
                                        <p className="text-sm text-gray-500 mb-2">{type.description}</p>
                                        <p className="text-xs text-gray-400">Best for: {type.bestFor}</p>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Step 2: Configure Settings */}
                    {currentStep === 2 && (
                        <div className="space-y-6 max-w-2xl">
                            <h3 className="text-lg font-medium text-gray-900">Configure Settings</h3>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Agent Name</label>
                                <input
                                    type="text"
                                    value={agentName}
                                    onChange={(e) => setAgentName(e.target.value)}
                                    placeholder="e.g., Customer Support Agent"
                                    className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-gray-400"
                                />
                            </div>

                            <div className="grid grid-cols-3 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">TTS Provider</label>
                                    <select
                                        value={selectedTtsProvider}
                                        onChange={(e) => setSelectedTtsProvider(e.target.value)}
                                        className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-gray-400"
                                    >
                                        {TTS_PROVIDER_OPTIONS.map((provider) => (
                                            <option key={provider.value} value={provider.value}>
                                                {provider.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Voice</label>
                                    <select
                                        value={selectedVoice}
                                        onChange={(e) => setSelectedVoice(e.target.value)}
                                        disabled={ttsLoading}
                                        className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-gray-400"
                                    >
                                        <option value="">
                                            {selectedTtsProvider === 'elevenlabs' ? 'Select an ElevenLabs voice' : 'Select a voice'}
                                        </option>
                                        {ttsVoices.map((voice) => (
                                            <option key={voice.id} value={voice.id}>
                                                {voice.label}{voice.accent ? ` (${voice.accent}${voice.gender ? `, ${voice.gender}` : ''})` : ''}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Language Model</label>
                                    <select
                                        value={selectedLLM}
                                        onChange={(e) => setSelectedLLM(e.target.value)}
                                        className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-gray-400"
                                    >
                                        {LLM_OPTIONS.map((llm) => (
                                            <option key={llm.value} value={llm.value}>
                                                {llm.name} - {llm.description}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            {selectedTtsProvider === 'elevenlabs' && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">ElevenLabs Model</label>
                                    <div className="space-y-2">
                                        <select
                                            value={selectedTtsModel}
                                            onChange={(e) => setSelectedTtsModel(e.target.value)}
                                            disabled={ttsLoading}
                                            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-gray-400"
                                        >
                                            <option value="">Select an ElevenLabs model</option>
                                            {visibleElevenModels.map((model) => (
                                                <option key={model.id} value={model.id}>
                                                    {model.name}
                                                    {model.is_v3 ? ' (v3)' : model.supports_multilingual ? ' (Multilingual)' : ''}
                                                </option>
                                            ))}
                                        </select>
                                        {selectedTtsModel && selectedTtsModel.includes('v3') && (
                                            <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-lg">
                                                <span className="w-2 h-2 bg-amber-500 rounded-full" />
                                                <span className="text-xs text-amber-700 font-medium">v3 is the expressive path, but Flash v2.5 is the lower-latency choice for live calls when the language supports it</span>
                                            </div>
                                        )}
                                        {compatibleElevenModels.length > 0 && compatibleElevenModels.length !== ttsModels.length && (
                                            <div className="flex items-center gap-2 px-3 py-1.5 bg-sky-50 border border-sky-200 rounded-lg">
                                                <span className="w-2 h-2 bg-sky-500 rounded-full" />
                                                <span className="text-xs text-sky-700 font-medium">Showing models compatible with {selectedLanguageLabel}</span>
                                            </div>
                                        )}
                                        {selectedTtsModel && !selectedTtsModel.includes('v3') && ttsVoices.length > 0 && (
                                            <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-lg">
                                                <span className="w-2 h-2 bg-amber-500 rounded-full" />
                                                <span className="text-xs text-amber-700 font-medium">Showing {ttsVoices.length} voices compatible with {selectedTtsModel}</span>
                                            </div>
                                        )}
                                        <div className="flex items-center gap-2">
                                            <input
                                                type="text"
                                                value={customElevenVoiceId}
                                                onChange={(e) => setCustomElevenVoiceId(e.target.value)}
                                                placeholder="Enter ElevenLabs Voice ID"
                                                className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-gray-400"
                                            />
                                            <button
                                                type="button"
                                                onClick={applyCustomElevenVoiceId}
                                                className="px-4 py-2 bg-violet-600 text-white rounded-lg text-sm font-medium hover:bg-violet-700 transition-colors"
                                            >
                                                Use ID
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Voice Runtime</label>
                                <div className="space-y-2">
                                    <select
                                        value={voiceRuntimeMode}
                                        onChange={(e) => setVoiceRuntimeMode(e.target.value)}
                                        className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-gray-400"
                                    >
                                        <option value="pipeline">Pipeline</option>
                                        <option value="realtime_text_tts">Realtime text + TTS</option>
                                    </select>
                                    {voiceRuntimeMode === 'realtime_text_tts' && (
                                        <input
                                            type="text"
                                            value={voiceRealtimeModel}
                                            onChange={(e) => setVoiceRealtimeModel(e.target.value)}
                                            placeholder="e.g. gpt-realtime"
                                            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-gray-400"
                                        />
                                    )}
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Global Prompt</label>
                                <textarea
                                    value={globalPrompt}
                                    onChange={(e) => setGlobalPrompt(e.target.value)}
                                    placeholder="Define your agent's personality and role..."
                                    rows={6}
                                    className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-gray-400 resize-none"
                                />
                                <p className="text-xs text-gray-500 mt-1">
                                    This prompt defines how your agent behaves and responds to callers.
                                </p>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">Primary Language</label>
                                <select
                                    value={primaryLanguage}
                                    onChange={(e) => setPrimaryLanguage(e.target.value)}
                                    className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-gray-400"
                                >
                                    {SUPPORTED_LANGUAGE_OPTIONS.map((language) => (
                                        <option key={language.value} value={language.value}>
                                            {language.label}
                                        </option>
                                    ))}
                                </select>
                                {selectedTtsProvider === 'elevenlabs' && primaryLanguage === 'multi' && (
                                    <p className="text-xs text-blue-600 mt-1">
                                        Multilingual mode keeps ElevenLabs on a multilingual model and lets the agent follow the caller&apos;s language naturally.
                                    </p>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Step 3: Build Conversation Flow */}
                    {currentStep === 3 && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-medium text-gray-900">Build Conversation Flow</h3>
                            <p className="text-sm text-gray-500">Add nodes to create your conversation flow</p>

                            <div className="grid grid-cols-3 gap-3 mb-4">
                                {NODE_TYPES.map((node) => (
                                    <button
                                        key={node.type}
                                        onClick={() => addNode(node.type)}
                                        className="p-4 border border-gray-200 rounded-lg hover:border-gray-400 hover:bg-gray-50 transition-all text-left"
                                    >
                                        <node.icon className="w-5 h-5 text-gray-600 mb-2" />
                                        <h5 className="font-medium text-sm text-gray-900">{node.name}</h5>
                                        <p className="text-xs text-gray-500">{node.description}</p>
                                    </button>
                                ))}
                            </div>

                            <div className="bg-gray-50 border-2 border-dashed border-gray-300 rounded-xl p-8 min-h-[300px]">
                                {nodes.length === 0 ? (
                                    <div className="text-center">
                                        <p className="text-gray-500 mb-2">No nodes added yet</p>
                                        <p className="text-sm text-gray-400">Click a node type above to add it to your flow</p>
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        {nodes.map((node, index) => (
                                            <div key={node.id} className="flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-200">
                                                <span className="w-6 h-6 bg-gray-900 text-white rounded-full flex items-center justify-center text-xs">
                                                    {index + 1}
                                                </span>
                                                <span className="font-medium text-sm capitalize">{node.type} Node</span>
                                                <button
                                                    onClick={() => setNodes(nodes.filter(n => n.id !== node.id))}
                                                    className="ml-auto p-1 hover:bg-red-50 text-red-500 rounded"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Step 4: Add Functions */}
                    {currentStep === 4 && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-medium text-gray-900">Add Functions</h3>
                            <p className="text-sm text-gray-500">Select functions your agent can use during conversations</p>

                            <div className="grid grid-cols-2 gap-3">
                                {PREBUILT_FUNCTIONS.map((func) => (
                                    <button
                                        key={func.id}
                                        onClick={() => toggleFunction(func.id)}
                                        className={`p-4 border-2 rounded-lg text-left transition-all ${selectedFunctions.includes(func.id)
                                                ? 'border-gray-900 bg-gray-50'
                                                : 'border-gray-200 hover:border-gray-300'
                                            }`}
                                    >
                                        <div className="flex items-start justify-between">
                                            <div>
                                                <h5 className="font-medium text-gray-900">{func.name}</h5>
                                                <p className="text-sm text-gray-500">{func.description}</p>
                                            </div>
                                            {selectedFunctions.includes(func.id) && (
                                                <Check className="w-5 h-5 text-gray-900" />
                                            )}
                                        </div>
                                    </button>
                                ))}
                            </div>

                            <button
                                onClick={() => showToast('Custom function builder coming soon!', 'info')}
                                className="w-full py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-gray-400 hover:text-gray-600 transition-all"
                            >
                                <Plus className="w-5 h-5 inline mr-2" />
                                Create Custom Function
                            </button>
                        </div>
                    )}

                    {/* Step 5: Test in Playground */}
                    {currentStep === 5 && (
                        <div className="space-y-4">
                            <h3 className="text-lg font-medium text-gray-900">Test in Playground</h3>
                            <p className="text-sm text-gray-500">Test your agent before deploying</p>

                            <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 h-[400px] flex flex-col">
                                <div className="flex-1 overflow-y-auto space-y-3 mb-4">
                                    {testMessages.length === 0 ? (
                                        <div className="text-center text-gray-400 mt-8">
                                            <p>Start a conversation to test your agent</p>
                                        </div>
                                    ) : (
                                        testMessages.map((msg, idx) => (
                                            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                                <div className={`max-w-[70%] px-4 py-2 rounded-lg ${msg.role === 'user'
                                                        ? 'bg-gray-900 text-white'
                                                        : 'bg-white border border-gray-200'
                                                    }`}>
                                                    <p className="text-sm">{msg.content}</p>
                                                    <span className="text-xs opacity-60">
                                                        {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                    </span>
                                                </div>
                                            </div>
                                        ))
                                    )}
                                </div>

                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={testInput}
                                        onChange={(e) => setTestInput(e.target.value)}
                                        onKeyPress={(e) => e.key === 'Enter' && handleTestSend()}
                                        placeholder="Type a message..."
                                        className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-gray-400"
                                    />
                                    <button
                                        onClick={handleTestSend}
                                        className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800"
                                    >
                                        <ArrowRight className="w-5 h-5" />
                                    </button>
                                </div>
                            </div>

                            <div className="flex gap-4 text-sm text-gray-500">
                                <span className="flex items-center gap-1">
                                    <span className="w-2 h-2 bg-green-500 rounded-full" />
                                    Latency: ~800ms
                                </span>
                                <span className="flex items-center gap-1">
                                    <span className="w-2 h-2 bg-blue-500 rounded-full" />
                                    Model: {selectedLLM}
                                </span>
                            </div>
                        </div>
                    )}

                    {/* Step 6: Deploy */}
                    {currentStep === 6 && (
                        <div className="space-y-6 text-center">
                            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                                <Check className="w-10 h-10 text-green-600" />
                            </div>

                            <div>
                                <h3 className="text-2xl font-semibold text-gray-900 mb-2">Ready to Deploy!</h3>
                                <p className="text-gray-500">Your agent is configured and ready to go live</p>
                            </div>

                            <div className="bg-gray-50 rounded-xl p-6 text-left max-w-md mx-auto">
                                <h4 className="font-medium text-gray-900 mb-4">Agent Summary</h4>
                                <div className="space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span className="text-gray-500">Name:</span>
                                        <span className="font-medium">{agentName || 'Not set'}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-500">Type:</span>
                                        <span className="font-medium capitalize">{selectedType.replace('-', ' ')}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-500">Voice:</span>
                                        <span className="font-medium">{ttsVoices.find(v => v.id === selectedVoice)?.label || selectedVoice}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-500">TTS Provider:</span>
                                        <span className="font-medium">{TTS_PROVIDER_OPTIONS.find(p => p.value === selectedTtsProvider)?.label}</span>
                                    </div>
                                    {selectedTtsProvider === 'elevenlabs' && (
                                        <div className="flex justify-between">
                                            <span className="text-gray-500">TTS Model:</span>
                                            <span className="font-medium">{selectedTtsModelMeta?.name || selectedTtsModel}</span>
                                        </div>
                                    )}
                                    <div className="flex justify-between">
                                        <span className="text-gray-500">LLM:</span>
                                        <span className="font-medium">{LLM_OPTIONS.find(l => l.value === selectedLLM)?.name}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-500">Functions:</span>
                                        <span className="font-medium">{selectedFunctions.length} enabled</span>
                                    </div>
                                </div>
                            </div>

                            <div className="flex gap-3 justify-center">
                                <button
                                    onClick={() => setCurrentStep(1)}
                                    className="px-6 py-3 border border-gray-200 rounded-lg text-gray-700 hover:bg-gray-50"
                                >
                                    Edit Configuration
                                </button>
                                <button
                                    onClick={handleCreate}
                                    disabled={isLoading}
                                    className="px-6 py-3 bg-gray-900 text-white rounded-lg hover:bg-gray-800 flex items-center gap-2 disabled:opacity-50"
                                >
                                    {isLoading ? (
                                        <>
                                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                            Creating...
                                        </>
                                    ) : (
                                        <>
                                            <Play className="w-4 h-4" />
                                            Deploy Agent
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100">
                    <button
                        onClick={handleBack}
                        disabled={currentStep === 1}
                        className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg disabled:opacity-50"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        Back
                    </button>

                    {currentStep < 6 ? (
                        <button
                            onClick={handleNext}
                            className="flex items-center gap-2 px-6 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800"
                        >
                            Next
                            <ArrowRight className="w-4 h-4" />
                        </button>
                    ) : null}
                </div>
            </div>
        </div>
    );
}
