'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import axios from 'axios';
import Link from 'next/link';
import {
    ArrowLeft, Bot, Loader2, Save, Phone, Copy, Edit3,
    ChevronDown, Mic, Settings, Wrench, FileText,
    Volume2, Trash2, Play, MessageSquare,
    Shield, Webhook, Cpu, BookOpen, Activity, Plus,
    Home, History, BarChart3, Key, Users, FileCode, PhoneCall, X, Menu
} from 'lucide-react';
import { useToast } from '../../../components/ToastProvider';
import VoiceCallModal from '../../../components/VoiceCallModal';
import TestChatModal from '../../../components/TestChatModal';
import FunctionModal from '../../../components/FunctionModal';

// Simple Sidebar Menu
const SIDEBAR_MENU = [
    { id: 'dashboard', label: 'Dashboard', icon: Home, href: '/' },
    { id: 'agents', label: 'Agents', icon: Bot, href: '/' },
    { id: 'phone', label: 'Phone Numbers', icon: PhoneCall, href: '/phone-numbers' },
    { id: 'call-history', label: 'Call History', icon: History, href: '/call-history' },
    { id: 'analytics', label: 'Analytics', icon: BarChart3, href: '/analytics' },
    { id: 'batch-call', label: 'Batch Call', icon: Users, href: '/batch-call' },
    { id: 'api-keys', label: 'API Keys', icon: Key, href: '/api-keys' },
    { id: 'knowledge', label: 'Knowledge Base', icon: BookOpen, href: '/knowledge-base' },
    { id: 'chat-history', label: 'Chat History', icon: FileCode, href: '/chat-history' },
];
const API_URL = '/api/';

interface Agent {
    id: number;
    name: string;
    display_name?: string | null;
    agent_name?: string | null;
    system_prompt: string;
    llm_model: string;
    voice: string;
    tts_provider?: string;
    tts_model?: string | null;
    language: string;
    twilio_number: string | null;
    welcome_message_type?: string;
    welcome_message?: string;
    llm_temperature?: number;
    voice_speed?: number;
    custom_params?: Record<string, any>;
}

interface PublishedAgentVersion {
    version: number;
    published_at?: string;
    snapshot?: Record<string, any>;
}

interface Function {
    id: number;
    name: string;
    description: string | null;
    method: string;
    url: string;
    timeout_ms: number;
    headers: Record<string, string>;
    query_params: Record<string, string>;
    parameters_schema: Record<string, any>;
    variables: Record<string, string>;
    speak_during_execution: boolean;
    speak_after_execution: boolean;
    created_at: string;
    updated_at: string;
}

interface BuiltinFunctionDefinition {
    id: string;
    name: string;
    description?: string | null;
    speak_during_execution?: boolean;
    speak_after_execution?: boolean;
}

type BuiltinFunctionState = {
    enabled: boolean;
    config?: Record<string, any>;
    speak_during_execution?: boolean;
    speak_after_execution?: boolean;
};

type BuiltinFunctionsState = Record<string, BuiltinFunctionState>;

// Valid Models for Moonshot/Kimi API & OpenAI
const MODEL_OPTIONS = [
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

const TTS_PROVIDER_OPTIONS = [
    { value: 'deepgram', label: 'Deepgram' },
    { value: 'elevenlabs', label: 'ElevenLabs' },
    { value: 'xai', label: 'xAI' },
];

interface TTSVoiceOption {
    id: string;
    label: string;
    accent?: string | null;
    gender?: string | null;
    provider?: string;
    category?: string;
}

interface TTSModelOption {
    id: string;
    name: string;
    is_v3?: boolean;
    streaming_type?: string;
    supports_fallback?: string;
    languages_count?: number;
    languages?: string[];
    supports_multilingual?: boolean;
    deprecated?: boolean;
}

// Voices available for Deepgram TTS
const DEEPGRAM_VOICE_OPTIONS: TTSVoiceOption[] = [
    { id: 'aura-asteria-en', label: 'Jessica (Asteria)', accent: 'UK', gender: 'Female', provider: 'deepgram' },
    { id: 'aura-luna-en', label: 'Sarah (Luna)', accent: 'UK', gender: 'Female', provider: 'deepgram' },
    { id: 'aura-hera-en', label: 'Emma (Hera)', accent: 'US', gender: 'Female', provider: 'deepgram' },
    { id: 'aura-orion-en', label: 'Mark (Orion)', accent: 'US', gender: 'Male', provider: 'deepgram' },
    { id: 'aura-perseus-en', label: 'Michael (Perseus)', accent: 'US', gender: 'Male', provider: 'deepgram' },
    { id: 'aura-zeus-en', label: 'James (Zeus)', accent: 'US', gender: 'Male', provider: 'deepgram' },
    { id: 'jessica', label: 'Jessica', accent: 'UK', gender: 'Female', provider: 'deepgram' },
    { id: 'mark', label: 'Mark', accent: 'US', gender: 'Male', provider: 'deepgram' },
    { id: 'sarah', label: 'Sarah', accent: 'UK', gender: 'Female', provider: 'deepgram' },
    { id: 'michael', label: 'Michael', accent: 'US', gender: 'Male', provider: 'deepgram' },
    { id: 'emma', label: 'Emma', accent: 'UK', gender: 'Female', provider: 'deepgram' },
    { id: 'james', label: 'James', accent: 'US', gender: 'Male', provider: 'deepgram' },
];
const DEEPGRAM_VOICE_IDS = new Set(DEEPGRAM_VOICE_OPTIONS.map((voice) => voice.id));
const XAI_DEFAULT_MODEL = 'grok-voice-think-fast-1.0';
const XAI_VOICE_OPTIONS: TTSVoiceOption[] = [
    { id: 'ara', label: 'Ara', accent: 'Warm, friendly', gender: 'Female', provider: 'xai' },
    { id: 'eve', label: 'Eve', accent: 'Energetic, upbeat', gender: 'Female', provider: 'xai' },
    { id: 'leo', label: 'Leo', accent: 'Authoritative, strong', gender: 'Male', provider: 'xai' },
    { id: 'rex', label: 'Rex', accent: 'Confident, clear', gender: 'Male', provider: 'xai' },
    { id: 'sal', label: 'Sal', accent: 'Smooth, balanced', gender: 'Neutral', provider: 'xai' },
];
const XAI_VOICE_IDS = new Set(XAI_VOICE_OPTIONS.map((voice) => voice.id));
const CUSTOM_ELEVEN_VOICE_OPTION_ID = '__custom_eleven_voice_option__';

// Language options
const LANGUAGE_OPTIONS = [
    { value: 'en-US', label: 'English (US)', flag: '🇺🇸' },
    { value: 'en-GB', label: 'English (UK)', flag: '🇬🇧' },
    { value: 'en-AU', label: 'English (Australia)', flag: '🇦🇺' },
    { value: 'en-IN', label: 'English (India)', flag: '🇮🇳' },
    { value: 'es', label: 'Spanish', flag: '🇪🇸' },
    { value: 'fr', label: 'French', flag: '🇫🇷' },
    { value: 'de', label: 'German', flag: '🇩🇪' },
    { value: 'it', label: 'Italian', flag: '🇮🇹' },
    { value: 'hi', label: 'Hindi', flag: '🇮🇳' },
    { value: 'hi-IN', label: 'Hindi (India)', flag: '🇮🇳' },
    { value: 'ml', label: 'Malayalam', flag: '🇮🇳' },
    { value: 'ml-IN', label: 'Malayalam (India)', flag: '🇮🇳' },
];

const SUPPORTED_LANGUAGE_OPTIONS = [
    ...LANGUAGE_OPTIONS,
    { value: 'multi', label: 'Multilingual (Auto)', flag: '' },
];
const XAI_SUPPORTED_LANGUAGE_VALUES = ['multi', 'en-US', 'en-GB', 'en-AU', 'en-IN', 'hi', 'hi-IN', 'ml', 'ml-IN'];
const XAI_SUPPORTED_LANGUAGE_SET = new Set(XAI_SUPPORTED_LANGUAGE_VALUES);

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

const getProviderLanguageOptions = (provider: string) => {
    if (provider !== 'xai') return SUPPORTED_LANGUAGE_OPTIONS;
    return [
        ...SUPPORTED_LANGUAGE_OPTIONS.filter((option) => option.value === 'multi'),
        ...SUPPORTED_LANGUAGE_OPTIONS.filter((option) => option.value !== 'multi' && XAI_SUPPORTED_LANGUAGE_SET.has(option.value)),
    ];
};

const normalizeLanguageForProvider = (provider: string, language: string) => {
    const options = getProviderLanguageOptions(provider);
    return options.some((option) => option.value === language) ? language : (options[0]?.value || 'en-GB');
};

const normalizePublishedVersions = (raw: any): PublishedAgentVersion[] => {
    if (!Array.isArray(raw)) return [];
    return raw
        .filter((item) => item && typeof item === 'object')
        .map((item) => ({
            version: Number(item.version) || 0,
            published_at: typeof item.published_at === 'string' ? item.published_at : '',
            snapshot: item.snapshot && typeof item.snapshot === 'object' ? item.snapshot : {},
        }))
        .filter((item) => item.version > 0)
        .sort((a, b) => b.version - a.version);
};

const WELCOME_OPTIONS = [
    { value: 'user_speaks_first', label: 'User speaks first' },
    { value: 'agent_greets', label: 'Agent greets first' },
];
const WELCOME_MESSAGE_MODE_OPTIONS = [
    { value: 'dynamic', label: 'Dynamic message' },
    { value: 'custom', label: 'Custom message' },
];

const DEFAULT_VOICE_SPEED = 1.0;
const MIN_VOICE_SPEED = 0.8;
const MAX_VOICE_SPEED = 1.2;
const DEFAULT_PHONE_LLM_MODEL = 'gpt-4o';

interface SettingsSection {
    id: string;
    label: string;
    icon: React.ElementType;
}

const SETTINGS_SECTIONS: SettingsSection[] = [
    { id: 'functions', label: 'Functions', icon: Wrench },
    { id: 'knowledge', label: 'Knowledge Base', icon: BookOpen },
    { id: 'speech', label: 'Speech Settings', icon: Volume2 },
    { id: 'transcription', label: 'Realtime Transcription Settings', icon: Activity },
    { id: 'call', label: 'Call Settings', icon: PhoneCall },
    { id: 'postcall', label: 'Post-Call Data Extraction', icon: FileText },
    { id: 'security', label: 'Security & Fallback Settings', icon: Shield },
    { id: 'webhook', label: 'Webhook Settings', icon: Webhook },
    { id: 'mcp', label: 'MCPs', icon: Cpu },
];

export default function AgentDetailPage() {
    const router = useRouter();
    const { showToast } = useToast();
    const params = useParams();
    const [agent, setAgent] = useState<Agent | null>(null);
    const [systemPrompt, setSystemPrompt] = useState('');
    const [selectedModel, setSelectedModel] = useState('moonshot-v1-8k');
    const [selectedTtsProvider, setSelectedTtsProvider] = useState('deepgram');
    const [selectedTtsModel, setSelectedTtsModel] = useState('');
    const [selectedVoice, setSelectedVoice] = useState('jessica');
    const [customElevenVoiceId, setCustomElevenVoiceId] = useState('');
    const [showCustomElevenVoiceInput, setShowCustomElevenVoiceInput] = useState(false);
    const [customElevenVoiceLookupLoading, setCustomElevenVoiceLookupLoading] = useState(false);
    const [customElevenVoiceCandidate, setCustomElevenVoiceCandidate] = useState<TTSVoiceOption | null>(null);
    const [selectedLanguage, setSelectedLanguage] = useState('en-GB');
    const [voiceSpeed, setVoiceSpeed] = useState(DEFAULT_VOICE_SPEED);
    const [showAdvancedVoiceLlmSettings, setShowAdvancedVoiceLlmSettings] = useState(false);
    const [phoneLlmOverrideEnabled, setPhoneLlmOverrideEnabled] = useState(false);
    const [phoneLlmModel, setPhoneLlmModel] = useState(DEFAULT_PHONE_LLM_MODEL);
    const [voiceRuntimeMode, setVoiceRuntimeMode] = useState('pipeline');
    const [voiceRealtimeModel, setVoiceRealtimeModel] = useState('');
    const [agentCustomParams, setAgentCustomParams] = useState<Record<string, any>>({});
    const [ttsVoices, setTtsVoices] = useState<TTSVoiceOption[]>([]);
    const [ttsModels, setTtsModels] = useState<TTSModelOption[]>([]);
    const [ttsLoading, setTtsLoading] = useState(false);
    const [welcomeOption, setWelcomeOption] = useState('user_speaks_first');
    const [welcomeMessageMode, setWelcomeMessageMode] = useState('dynamic');
    const [welcomeMessage, setWelcomeMessage] = useState('');
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [publishing, setPublishing] = useState(false);
    const [expandedSections, setExpandedSections] = useState<string[]>([]);
    const [isEditingName, setIsEditingName] = useState(false);
    const [agentName, setAgentName] = useState('');
    const [livekitAgentName, setLivekitAgentName] = useState('');
    const [showVoiceCall, setShowVoiceCall] = useState(false);
    const [showTestChat, setShowTestChat] = useState(false);
    const [functions, setFunctions] = useState<Function[]>([]);
    const [builtinFunctions, setBuiltinFunctions] = useState<BuiltinFunctionDefinition[]>([]);
    const [allBuiltinFunctions, setAllBuiltinFunctions] = useState<BuiltinFunctionsState>({});
    const [builtinSaving, setBuiltinSaving] = useState(false);
    const [builtinSaved, setBuiltinSaved] = useState(false);
    const [showFunctionModal, setShowFunctionModal] = useState(false);
    const [selectedFunction, setSelectedFunction] = useState<Function | null>(null);
    const [showFunctionSelector, setShowFunctionSelector] = useState(false);
    const [showBuiltinConfigModal, setShowBuiltinConfigModal] = useState(false);
    const [selectedBuiltinFunctionId, setSelectedBuiltinFunctionId] = useState<string | null>(null);
    const [builtinDraftConfig, setBuiltinDraftConfig] = useState<BuiltinFunctionState | null>(null);

    const agentId = params.id as string;
    const compatibleElevenModels = getCompatibleElevenModels(ttsModels, selectedLanguage);
    const visibleElevenModels = compatibleElevenModels.length > 0 ? compatibleElevenModels : ttsModels;
    const visibleProviderModels = selectedTtsProvider === 'elevenlabs' ? visibleElevenModels : ttsModels;
    const selectedLanguageLabel = getLanguageLabel(selectedLanguage);
    const providerLanguageOptions = getProviderLanguageOptions(selectedTtsProvider);
    const publishedVersions = normalizePublishedVersions(agentCustomParams?.published_versions || agent?.custom_params?.published_versions);
    const latestPublishedVersion = publishedVersions[0]?.version || 0;
    const nextPublishedVersion = latestPublishedVersion + 1;

    const toggleSection = (section: string) => {
        setExpandedSections(prev =>
            prev.includes(section)
                ? prev.filter(s => s !== section)
                : [...prev, section]
        );
    };

    const inferProviderFromVoice = (voice?: string, explicit?: string) => {
        if (explicit === 'deepgram' || explicit === 'elevenlabs' || explicit === 'xai') return explicit;
        if (!voice) return 'deepgram';
        if (XAI_VOICE_IDS.has(voice)) return 'xai';
        if (voice.startsWith('aura-') || ['jessica', 'mark', 'sarah', 'michael', 'emma', 'james'].includes(voice)) {
            return 'deepgram';
        }
        return 'elevenlabs';
    };

    const clampNumber = (value: number, min: number, max: number, fallback: number) => {
        if (Number.isNaN(value)) return fallback;
        return Math.min(max, Math.max(min, value));
    };

    const normalizeBuiltinSpeechFlags = (value: any) => {
        const during = Boolean(value?.speak_during_execution);
        const after = Boolean(value?.speak_after_execution);
        if ((during && !after) || (!during && after)) {
            return { speak_during_execution: during, speak_after_execution: after };
        }
        return { speak_during_execution: false, speak_after_execution: true };
    };

    const normalizeBuiltinFunctionsConfig = (raw: any): BuiltinFunctionsState => {
        if (!raw || typeof raw !== 'object') return {};
        const normalized: BuiltinFunctionsState = {};
        for (const [id, value] of Object.entries(raw)) {
            if (!value || typeof value !== 'object') continue;
            const entry = value as any;
            const speechFlags = normalizeBuiltinSpeechFlags(entry);
            normalized[id] = {
                enabled: Boolean(entry.enabled),
                config: entry.config && typeof entry.config === 'object' ? entry.config : {},
                ...speechFlags,
            };
        }
        return normalized;
    };

    const formatBuiltinFunctionName = (name?: string | null) => {
        const cleaned = String(name || '')
            .replace(/^builtin_/, '')
            .replace(/_/g, ' ')
            .trim();

        if (!cleaned) return 'Built-in Function';

        return cleaned.replace(/\b\w/g, (char) => char.toUpperCase());
    };

    const openBuiltinConfigModal = (funcId: string) => {
        const func = builtinFunctions.find((entry) => entry.id === funcId);
        const existing = allBuiltinFunctions[funcId] || {};
        setSelectedBuiltinFunctionId(funcId);
        setBuiltinDraftConfig({
            enabled: existing.enabled ?? true,
            config: existing.config && typeof existing.config === 'object' ? { ...existing.config } : {},
            ...normalizeBuiltinSpeechFlags({
                speak_during_execution: existing.speak_during_execution ?? func?.speak_during_execution,
                speak_after_execution: existing.speak_after_execution ?? func?.speak_after_execution,
            }),
        });
        setShowBuiltinConfigModal(true);
    };

    const closeBuiltinConfigModal = () => {
        setShowBuiltinConfigModal(false);
        setSelectedBuiltinFunctionId(null);
        setBuiltinDraftConfig(null);
    };

    const fetchBuiltinFunctionsConfig = async () => {
        const res = await axios.get(`${API_URL}agents/${agentId}/builtin-functions/config`, {
            params: { _ts: Date.now() },
            headers: { 'Cache-Control': 'no-cache' },
        });
        const normalized = normalizeBuiltinFunctionsConfig(res.data);
        console.log('Builtin functions config loaded:', normalized);
        setAllBuiltinFunctions(normalized);
        setAgentCustomParams((prev) => ({
            ...(prev || {}),
            builtin_functions: normalized,
        }));
        setAgent((prev) => prev ? ({
            ...prev,
            custom_params: {
                ...(prev.custom_params || {}),
                builtin_functions: normalized,
            },
        }) : prev);
    };

    const loadTtsVoicesForModel = async (provider: string, modelId?: string) => {
        const normalized = provider === 'xai' ? 'xai' : provider === 'elevenlabs' ? 'elevenlabs' : 'deepgram';
        if (normalized !== 'elevenlabs') return;
        setTtsLoading(true);
        try {
            const modelParam = modelId ? { provider: normalized, model: modelId } : { provider: normalized };
            const voicesRes = await axios.get(`${API_URL}tts/voices`, { params: modelParam });
            const voices = (voicesRes.data?.voices || []) as TTSVoiceOption[];
            setTtsVoices(voices);
        } catch (e) {
            // Keep existing voices on error
        } finally {
            setTtsLoading(false);
        }
    };

    const loadTtsOptions = async (provider: string) => {
        const normalizedProvider = provider === 'xai' ? 'xai' : provider === 'elevenlabs' ? 'elevenlabs' : 'deepgram';
        setTtsLoading(true);
        if (normalizedProvider === 'deepgram') {
            setTtsVoices(DEEPGRAM_VOICE_OPTIONS);
            setTtsModels([]);
            setTtsLoading(false);
            return;
        }

        // Provider-managed voices/models: do not show fallback rows, only backend API results.
        setTtsVoices([]);
        setTtsModels([]);
        try {
            const voicesPromise = axios.get(`${API_URL}tts/voices`, {
                params: { provider: normalizedProvider },
            });
            const modelsPromise = axios.get(`${API_URL}tts/models`, { params: { provider: normalizedProvider } });

            const [voicesRes, modelsRes] = await Promise.all([voicesPromise, modelsPromise]);
            if (modelsRes.data?.available === false) {
                if (normalizedProvider === 'elevenlabs') {
                    showToast('ElevenLabs is not configured on the server (missing ELEVEN_API_KEY).', 'error');
                } else if (normalizedProvider === 'xai') {
                    showToast('xAI is not configured on the server (missing XAI_API_KEY).', 'error');
                }
            }

            const voices = (voicesRes.data?.voices || []) as TTSVoiceOption[];
            setTtsVoices(voices);
            const models = (modelsRes.data?.models || []) as TTSModelOption[];
            setTtsModels(models);
        } catch (err: any) {
            if (normalizedProvider === 'elevenlabs') {
                showToast(err?.response?.data?.detail || 'Failed to load ElevenLabs voices. Check ELEVEN_API_KEY on server.', 'error');
            } else if (normalizedProvider === 'xai') {
                showToast(err?.response?.data?.detail || 'Failed to load xAI voices. Check XAI_API_KEY on server.', 'error');
            }
            setTtsVoices([]);
            setTtsModels([]);
        } finally {
            setTtsLoading(false);
        }
    };

    useEffect(() => {
        fetchAgent();
        fetchFunctions();
    }, [agentId]);

    useEffect(() => {
        loadTtsOptions(selectedTtsProvider);
    }, [selectedTtsProvider]);

    useEffect(() => {
        const normalizedLanguage = normalizeLanguageForProvider(selectedTtsProvider, selectedLanguage);
        if (normalizedLanguage !== selectedLanguage) {
            setSelectedLanguage(normalizedLanguage);
        }
    }, [selectedTtsProvider, selectedLanguage]);

    useEffect(() => {
        if (selectedTtsProvider !== 'xai') return;
        if (!selectedVoice || !XAI_VOICE_IDS.has(selectedVoice)) {
            setSelectedVoice('eve');
        }
        if (!selectedTtsModel) {
            setSelectedTtsModel(XAI_DEFAULT_MODEL);
        }
    }, [selectedTtsProvider, selectedVoice, selectedTtsModel]);

    // Re-fetch voices when ElevenLabs model changes (v3 shows all voices, v2.5 filters by compatibility)
    useEffect(() => {
        if (selectedTtsProvider !== 'elevenlabs' || !selectedTtsModel) return;
        loadTtsVoicesForModel('elevenlabs', selectedTtsModel);
    }, [selectedTtsModel]);

    useEffect(() => {
        if (!selectedVoice) return;
        if (selectedTtsProvider === 'deepgram') {
            if (!DEEPGRAM_VOICE_IDS.has(selectedVoice)) {
                setSelectedVoice(DEEPGRAM_VOICE_OPTIONS[0]?.id || 'jessica');
            }
            return;
        }
        if (selectedTtsProvider === 'xai') {
            if (!XAI_VOICE_IDS.has(selectedVoice)) {
                setSelectedVoice('eve');
            }
            return;
        }
        if (DEEPGRAM_VOICE_IDS.has(selectedVoice) || XAI_VOICE_IDS.has(selectedVoice)) {
            setSelectedVoice('');
        }
    }, [selectedTtsProvider, selectedVoice]);

    useEffect(() => {
        if (selectedTtsProvider !== 'elevenlabs') return;
        if (!selectedVoice) return;
        if (DEEPGRAM_VOICE_IDS.has(selectedVoice)) return;
        if (ttsVoices.find(v => v.id === selectedVoice)) return;
        setTtsVoices(prev => [
            { id: selectedVoice, label: `Custom Voice ID (${selectedVoice})`, provider: 'elevenlabs' },
            ...prev,
        ]);
    }, [selectedTtsProvider, selectedVoice, ttsVoices]);

    useEffect(() => {
        if (selectedTtsProvider === 'elevenlabs') return;
        setShowCustomElevenVoiceInput(false);
        setCustomElevenVoiceId('');
        setCustomElevenVoiceCandidate(null);
    }, [selectedTtsProvider]);

    const fetchAgent = async () => {
        try {
            const res = await axios.get<Agent>(`${API_URL}agents/${agentId}`);
            const data = res.data;
            setAgent(data);
            setAgentName(data.display_name || data.name);
            setLivekitAgentName(data.agent_name || '');
            setSystemPrompt(data.system_prompt);
            setSelectedModel(data.llm_model || 'moonshot-v1-8k');
            const provider = inferProviderFromVoice(data.voice, data.tts_provider);
            setSelectedTtsProvider(provider);
            setSelectedTtsModel(data.tts_model || (provider === 'xai' ? XAI_DEFAULT_MODEL : ''));
            setSelectedVoice(data.voice || (provider === 'xai' ? 'eve' : 'jessica'));
            setSelectedLanguage(data.language || 'en-GB');
            setWelcomeOption(data.welcome_message_type || 'user_speaks_first');
            const customParams = data.custom_params || {};
            setWelcomeMessageMode(customParams.welcome_message_mode === 'custom' ? 'custom' : 'dynamic');
            setWelcomeMessage(data.welcome_message || '');
            setAgentCustomParams(customParams);
            const overrideEnabled = customParams.force_phone_llm_model_override;
            setPhoneLlmOverrideEnabled(overrideEnabled === undefined ? false : Boolean(overrideEnabled));
            setPhoneLlmModel(customParams.phone_llm_model || data.llm_model || DEFAULT_PHONE_LLM_MODEL);
            setVoiceRuntimeMode(
                provider === 'xai'
                    ? 'realtime_unified'
                    : customParams.voice_runtime_mode === 'realtime_text_tts'
                        ? 'realtime_text_tts'
                        : 'pipeline'
            );
            setVoiceRealtimeModel(customParams.voice_realtime_model || (provider === 'xai' ? (data.tts_model || XAI_DEFAULT_MODEL) : ''));
            const persistedSpeed = Number(data.voice_speed ?? customParams.voice_speed ?? DEFAULT_VOICE_SPEED);
            setVoiceSpeed(clampNumber(persistedSpeed, MIN_VOICE_SPEED, MAX_VOICE_SPEED, DEFAULT_VOICE_SPEED));
        } catch (err) {
            showToast('Failed to load agent', 'error');
        } finally {
            setLoading(false);
        }
    };

    const fetchFunctions = async () => {
        try {
            console.log('Loading functions for agent:', agentId);
            const res = await axios.get<Function[]>(`${API_URL}agents/${agentId}/functions`);
            console.log('Functions loaded:', res.data);
            setFunctions(res.data || []);
        } catch (err) {
            console.error('Failed to load functions:', err);
            showToast('Failed to load functions', 'error');
        }
        
        // Load builtin functions
        try {
            const res = await axios.get(`${API_URL}agents/${agentId}/builtin-functions`);
            console.log('Builtin functions loaded:', res.data);
            setBuiltinFunctions(res.data || []);
        } catch (err) {
            console.error('Failed to load builtin functions:', err);
        }
        
        // Load builtin functions config
        try {
            await fetchBuiltinFunctionsConfig();
        } catch (err) {
            console.error('Failed to load builtin functions config:', err);
        }
    };

    const handleSaveBuiltinFunctions = async (
        configOverride?: BuiltinFunctionsState,
        silent: boolean = false
    ) => {
        const configToSave = normalizeBuiltinFunctionsConfig(configOverride ?? allBuiltinFunctions);
        const normalizedToSave: BuiltinFunctionsState = {};
        for (const [id, entry] of Object.entries(configToSave)) {
            normalizedToSave[id] = {
                enabled: Boolean(entry.enabled),
                config: entry.config && typeof entry.config === 'object' ? entry.config : {},
                ...normalizeBuiltinSpeechFlags(entry),
            };
        }
        console.log('Saving builtin functions:', configToSave);

        // Validate transfer function has phone number if enabled
        if (normalizedToSave['builtin_transfer_call']?.enabled) {
            if (!normalizedToSave['builtin_transfer_call']?.config?.phone_number || normalizedToSave['builtin_transfer_call']?.config.phone_number.trim() === '') {
                if (!silent) showToast('Please enter a phone number for transfer function', 'error');
                return;
            }
        }

        setBuiltinSaving(true);
        try {
            const saveRes = await axios.post(`${API_URL}agents/${agentId}/builtin-functions`, normalizedToSave);
            console.log('Save response:', saveRes.data);
            const persistedConfig = normalizeBuiltinFunctionsConfig(saveRes.data?.config ?? normalizedToSave);
            setAllBuiltinFunctions(persistedConfig);
            setAgentCustomParams((prev) => ({
                ...(prev || {}),
                builtin_functions: persistedConfig,
            }));
            setAgent((prev) => prev ? ({
                ...prev,
                custom_params: {
                    ...(prev.custom_params || {}),
                    builtin_functions: persistedConfig,
                },
            }) : prev);
            if (!silent) showToast('Builtin functions saved successfully', 'success');
            setBuiltinSaved(true);
            
            setTimeout(() => setBuiltinSaved(false), 3000);
        } catch (err: any) {
            console.error('Failed to save builtin functions:', err);
            if (!silent) showToast(err.response?.data?.detail || 'Failed to save builtin functions', 'error');
        } finally {
            setBuiltinSaving(false);
        }
    };

    const handleDeleteFunction = async (functionId: number) => {
        if (!confirm('Are you sure you want to delete this function?')) return;

        try {
            await axios.delete(`${API_URL}agents/${agentId}/functions/${functionId}`);
            showToast('Function deleted successfully', 'success');
            fetchFunctions();
        } catch (err) {
            showToast('Failed to delete function', 'error');
        }
    };

    const handleSaveBuiltinConfigModal = async () => {
        if (!selectedBuiltinFunctionId || !builtinDraftConfig) return;

        const next: BuiltinFunctionsState = {
            ...allBuiltinFunctions,
            [selectedBuiltinFunctionId]: {
                enabled: true,
                config: builtinDraftConfig.config && typeof builtinDraftConfig.config === 'object'
                    ? builtinDraftConfig.config
                    : {},
                ...normalizeBuiltinSpeechFlags(builtinDraftConfig),
            },
        };

        setAllBuiltinFunctions(next);
        await handleSaveBuiltinFunctions(next);
        closeBuiltinConfigModal();
    };

    const applyPersistedAgent = (persisted: Agent) => {
        const persistedProvider = inferProviderFromVoice(
            persisted.voice || selectedVoice,
            persisted.tts_provider || selectedTtsProvider,
        );
        const persistedCustomParams = persisted.custom_params || {};
        const normalizedLanguage = normalizeLanguageForProvider(
            persistedProvider,
            persisted.language || selectedLanguage,
        );

        setAgent((prev) => ({
            ...(prev || {}),
            ...persisted,
        }));
        setAgentName(persisted.display_name || persisted.name);
        setLivekitAgentName(persisted.agent_name || '');
        setSystemPrompt(persisted.system_prompt || '');
        setSelectedModel(persisted.llm_model || selectedModel);
        setSelectedVoice(persisted.voice || selectedVoice);
        setSelectedLanguage(normalizedLanguage);
        setWelcomeOption(persisted.welcome_message_type || 'user_speaks_first');
        setSelectedTtsProvider(persistedProvider);
        setSelectedTtsModel(persisted.tts_model || (persistedProvider === 'xai' ? XAI_DEFAULT_MODEL : ''));
        setWelcomeMessageMode(persistedCustomParams.welcome_message_mode === 'custom' ? 'custom' : 'dynamic');
        setWelcomeMessage(persisted.welcome_message || '');
        setAgentCustomParams(persistedCustomParams);
        const persistedOverride = persistedCustomParams.force_phone_llm_model_override;
        setPhoneLlmOverrideEnabled(persistedOverride === undefined ? false : Boolean(persistedOverride));
        setPhoneLlmModel(persistedCustomParams.phone_llm_model || persisted.llm_model || phoneLlmModel);
        setVoiceRuntimeMode(
            persistedProvider === 'xai'
                ? 'realtime_unified'
                : persistedCustomParams.voice_runtime_mode === 'realtime_text_tts'
                    ? 'realtime_text_tts'
                    : 'pipeline'
        );
        setVoiceRealtimeModel(
            persistedCustomParams.voice_realtime_model
            || (persistedProvider === 'xai' ? (persisted.tts_model || XAI_DEFAULT_MODEL) : '')
        );
        const persistedSpeed = Number(persisted.voice_speed ?? persistedCustomParams.voice_speed ?? voiceSpeed);
        setVoiceSpeed(clampNumber(persistedSpeed, MIN_VOICE_SPEED, MAX_VOICE_SPEED, voiceSpeed));
    };

    const handleSave = async (options?: { silent?: boolean }) => {
        if (!agent) return null;
        if (selectedTtsProvider === 'deepgram' && languageRequiresElevenLabsTts(selectedLanguage)) {
            showToast(`Use ElevenLabs or xAI for ${selectedLanguageLabel}. Deepgram TTS does not support that language.`, 'error');
            return null;
        }
        if (!selectedVoice) {
            const voiceLabel = selectedTtsProvider === 'elevenlabs'
                ? 'voice ID'
                : selectedTtsProvider === 'xai'
                    ? 'xAI voice'
                    : 'voice';
            showToast(`Select a ${voiceLabel}`, 'error');
            return null;
        }
        if (selectedTtsProvider === 'elevenlabs') {
            if (ttsVoices.length === 0) {
                showToast('ElevenLabs voices are not available. Configure ELEVEN_API_KEY on the server.', 'error');
                return null;
            }
            if (visibleElevenModels.length === 0) {
                showToast('ElevenLabs models are not available. Configure ELEVEN_API_KEY on the server.', 'error');
                return null;
            }
            if (!selectedTtsModel) {
                showToast('Select an ElevenLabs model', 'error');
                return null;
            }
        }
        if (selectedTtsProvider === 'xai' && !selectedTtsModel) {
            showToast('Select an xAI voice model', 'error');
            return null;
        }
        if (selectedTtsProvider !== 'xai' && voiceRuntimeMode === 'realtime_text_tts' && !voiceRealtimeModel.trim()) {
            showToast('Enter the realtime model to use for realtime mode', 'error');
            return null;
        }
        setSaving(true);
        try {
            const nextCustomParams: Record<string, any> = {
                ...(agent.custom_params || {}),
                ...(agentCustomParams || {}),
                voice_speed: voiceSpeed,
            };
            if (welcomeOption === 'agent_greets') {
                nextCustomParams.welcome_message_mode = welcomeMessageMode === 'custom' ? 'custom' : 'dynamic';
            } else {
                delete nextCustomParams.welcome_message_mode;
            }
            nextCustomParams.force_phone_llm_model_override = phoneLlmOverrideEnabled;
            if (phoneLlmOverrideEnabled) {
                nextCustomParams.phone_llm_model = phoneLlmModel;
            } else {
                delete nextCustomParams.phone_llm_model;
            }
            nextCustomParams.voice_runtime_mode = selectedTtsProvider === 'xai' ? 'realtime_unified' : voiceRuntimeMode;
            if (selectedTtsProvider === 'xai') {
                nextCustomParams.voice_realtime_model = selectedTtsModel || XAI_DEFAULT_MODEL;
            } else if (voiceRuntimeMode === 'realtime_text_tts') {
                nextCustomParams.voice_realtime_model = voiceRealtimeModel.trim();
            } else {
                delete nextCustomParams.voice_realtime_model;
            }
            const saveRes = await axios.patch(`${API_URL}agents/${agentId}`, {
                name: agentName,
                display_name: agentName,
                agent_name: livekitAgentName,
                system_prompt: systemPrompt,
                llm_model: selectedModel,
                voice: selectedVoice,
                tts_provider: selectedTtsProvider,
                tts_model: selectedTtsProvider === 'deepgram' ? null : selectedTtsModel,
                language: selectedLanguage,
                voice_speed: voiceSpeed,
                twilio_number: agent.twilio_number,
                welcome_message_type: welcomeOption,
                welcome_message: welcomeMessage,
                custom_params: nextCustomParams,
            });

            const persisted = saveRes.data as Agent;
            applyPersistedAgent(persisted);

            if ((persisted.system_prompt || '') !== systemPrompt) {
                showToast('Saved, but backend normalized system prompt. Editor now shows exact backend value.', 'error');
            }

            if (!options?.silent) {
                showToast('Saved successfully!', 'success');
            }
            return persisted;
        } catch (err) {
            console.error('Save error:', err);
            showToast('Failed to save changes', 'error');
            return null;
        } finally {
            setSaving(false);
        }
    };

    const handlePublish = async () => {
        if (publishing) return;
        setPublishing(true);
        try {
            const persisted = await handleSave({ silent: true });
            if (!persisted) return;
            const publishRes = await axios.post(`${API_URL}agents/${agentId}/publish`);
            const publishedAgent = publishRes.data?.agent as Agent | undefined;
            if (publishedAgent) {
                applyPersistedAgent(publishedAgent);
            }
            const publishedVersion = Number(publishRes.data?.version) || nextPublishedVersion;
            showToast(`Published version v${publishedVersion}`, 'success');
        } catch (err) {
            console.error('Publish error:', err);
            showToast('Failed to publish version', 'error');
        } finally {
            setPublishing(false);
        }
    };

    const lookupCustomElevenVoiceId = async () => {
        const voiceId = customElevenVoiceId.trim();
        if (!voiceId) {
            showToast('Enter an ElevenLabs voice ID', 'error');
            return;
        }
        if (DEEPGRAM_VOICE_IDS.has(voiceId)) {
            showToast('Enter a valid ElevenLabs voice_id, not a Deepgram voice.', 'error');
            return;
        }
        setCustomElevenVoiceLookupLoading(true);
        setCustomElevenVoiceCandidate(null);
        try {
            const res = await axios.get(`${API_URL}tts/voices/lookup`, {
                params: {
                    provider: 'elevenlabs',
                    voice_id: voiceId,
                },
            });
            const voice = res.data?.voice as TTSVoiceOption | undefined;
            if (!voice?.id) {
                showToast('Voice ID lookup failed', 'error');
                return;
            }
            setCustomElevenVoiceCandidate(voice);
        } catch (err: any) {
            const detail = err?.response?.data?.detail || 'Voice ID not found for this ElevenLabs account';
            showToast(detail, 'error');
        } finally {
            setCustomElevenVoiceLookupLoading(false);
        }
    };

    const addCustomElevenVoice = () => {
        if (!customElevenVoiceCandidate?.id) {
            showToast('Lookup a valid ElevenLabs voice ID first', 'error');
            return;
        }
        if (!ttsVoices.find(v => v.id === customElevenVoiceCandidate.id)) {
            setTtsVoices(prev => [customElevenVoiceCandidate, ...prev]);
        }
        setSelectedVoice(customElevenVoiceCandidate.id);
        setShowCustomElevenVoiceInput(false);
        setCustomElevenVoiceId('');
        setCustomElevenVoiceCandidate(null);
        showToast('Custom ElevenLabs voice added', 'success');
    };

    const handleDelete = async () => {
        if (!confirm('Delete this agent?')) return;
        try {
            await axios.delete(`${API_URL}agents/${agentId}`);
            router.push('/');
            showToast('Agent deleted', 'success');
        } catch (err: any) {
            const detail = err?.response?.data?.detail || 'Delete failed';
            showToast(detail, 'error');
        }
    };

    const handleCopyId = () => {
        navigator.clipboard.writeText(agentId);
        showToast('ID copied', 'success');
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
        );
    }

    if (!agent) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <p className="text-red-600 mb-4">Agent not found</p>
                    <Link href="/" className="text-blue-600">Back</Link>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
            {/* Main Content - full screen for agent editing */}
            <main className="overflow-hidden">
                {/* Header */}
                <div className="border-b border-gray-200 bg-white">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between px-4 sm:px-6 py-3 sm:h-16 gap-3">
                        <div className="flex items-center gap-3 sm:gap-4">
                            <Link href="/" className="p-2 hover:bg-gray-100 rounded-lg">
                                <ArrowLeft className="w-5 h-5 text-gray-600" />
                            </Link>

                            <div className="flex items-center gap-3">
                                <div className="w-8 sm:w-10 bg-gray-100 rounded-lg flex items-center justify-center">
                                    <Bot className="w-4 sm:w-5 text-gray-600" />
                                </div>
                                <div>
                                    <div className="flex items-center gap-2">
                                        {isEditingName ? (
                                            <input
                                                type="text"
                                                value={agentName}
                                                onChange={(e) => setAgentName(e.target.value)}
                                                onBlur={() => {
                                                    setIsEditingName(false);
                                                    handleSave();
                                                }}
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter') {
                                                        setIsEditingName(false);
                                                        handleSave();
                                                    }
                                                }}
                                                className="text-base sm:text-lg font-semibold text-gray-900 border-b border-blue-500 focus:outline-none bg-transparent"
                                                autoFocus
                                            />
                                        ) : (
                                            <h1 className="text-base sm:text-lg font-semibold text-gray-900">{agentName}</h1>
                                        )}
                                        <button
                                            onClick={() => setIsEditingName(true)}
                                            className="p-1 hover:bg-gray-100 rounded"
                                        >
                                            <Edit3 className="w-4 h-4 text-gray-400" />
                                        </button>
                                    </div>
                                    <div className="hidden sm:flex items-center gap-2 text-xs text-gray-500">
                                        <span>Agent ID: {agentId.slice(0, 8)}...</span>
                                        <button onClick={handleCopyId} className="hover:text-gray-700">
                                            <Copy className="w-3 h-3" />
                                        </button>
                                        <span>•</span>
                                        <span>{MODEL_OPTIONS.find(m => m.value === selectedModel)?.price || '$0.00/min'}</span>
                                        <span>&bull;</span>
                                        <span>{latestPublishedVersion > 0 ? `Published v${latestPublishedVersion}` : 'Draft only'}</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center gap-2 sm:gap-3">
                            <button
                                onClick={() => { void handleSave(); }}
                                disabled={saving}
                                className="flex items-center gap-2 px-3 sm:px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-50"
                            >
                                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                                <span className="hidden sm:inline">Save</span>
                            </button>

                            <button
                                onClick={handleDelete}
                                className="p-2 hover:bg-red-50 rounded-lg"
                            >
                                <Trash2 className="w-5 h-5 text-red-500" />
                            </button>

                            <button
                                onClick={() => { void handlePublish(); }}
                                disabled={saving || publishing}
                                className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-60"
                            >
                                {publishing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                                <span className="hidden sm:inline">Publish v{nextPublishedVersion}</span>
                            </button>
                        </div>
                    </div>
                </div>

                {/* Main Content - 3 Column Layout */}
                <div className="flex h-[calc(100vh-64px)] overflow-hidden">

                    {/* Left Column - Prompt Editor (45%) */}
                    <div className="flex min-h-0 min-w-0 w-[45%] flex-col border-r border-gray-200 bg-white">
                        {/* Model Selectors */}
                        <div className="px-4 sm:px-6 py-3 border-b border-gray-200">
                            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                                {/* Model Dropdown */}
                                <div className="relative min-w-[230px] flex-1 sm:flex-none">
                                    <select
                                        value={selectedModel}
                                        onChange={(e) => setSelectedModel(e.target.value)}
                                        className="w-full appearance-none px-3 py-2 pr-8 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 focus:outline-none cursor-pointer"
                                    >
                                        {MODEL_OPTIONS.map(model => (
                                            <option key={model.value} value={model.value}>
                                                {model.label} ({model.price})
                                            </option>
                                        ))}
                                    </select>
                                    <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
                                </div>

                                {/* TTS Provider Dropdown */}
                                <div className="relative min-w-[150px]">
                                    <select
                                        value={selectedTtsProvider}
                                        onChange={(e) => setSelectedTtsProvider(e.target.value)}
                                        className="w-full appearance-none px-3 py-2 pr-8 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 focus:outline-none cursor-pointer"
                                    >
                                        {TTS_PROVIDER_OPTIONS.map((provider) => (
                                            <option key={provider.value} value={provider.value}>
                                                {provider.label}
                                            </option>
                                        ))}
                                    </select>
                                    <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
                                </div>

                                {/* Voice Dropdown */}
                                <div className="relative min-w-[270px] flex-1">
                                    <select
                                        value={selectedVoice}
                                        onChange={(e) => {
                                            const nextValue = e.target.value;
                                            if (selectedTtsProvider === 'elevenlabs' && nextValue === CUSTOM_ELEVEN_VOICE_OPTION_ID) {
                                                setShowCustomElevenVoiceInput(true);
                                                return;
                                            }
                                            setSelectedVoice(nextValue);
                                            setShowCustomElevenVoiceInput(false);
                                            setCustomElevenVoiceCandidate(null);
                                        }}
                                        disabled={ttsLoading}
                                        className="w-full appearance-none px-3 py-2 pr-8 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 focus:outline-none cursor-pointer"
                                    >
                                        <option value="">
                                            {selectedTtsProvider === 'elevenlabs'
                                                ? 'Select an ElevenLabs voice'
                                                : selectedTtsProvider === 'xai'
                                                    ? 'Select an xAI voice'
                                                    : 'Select a voice'}
                                        </option>
{ttsVoices.map(voice => (
                                                <option key={voice.id} value={voice.id}>
                                                    {voice.label}
                                                    {voice.category ? ` [${voice.category}]` : ''}
                                                </option>
                                            ))}
                                        {selectedTtsProvider === 'elevenlabs' && (
                                            <option value={CUSTOM_ELEVEN_VOICE_OPTION_ID}>
                                                + Add custom voice ID
                                            </option>
                                        )}
                                    </select>
                                    <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
                                </div>

                                {/* Provider Model Dropdown */}
                                {selectedTtsProvider !== 'deepgram' && (
                                    <div className="relative min-w-[190px]">
                                        <select
                                            value={selectedTtsModel}
                                            onChange={(e) => setSelectedTtsModel(e.target.value)}
                                            disabled={ttsLoading}
                                            className="w-full appearance-none px-3 py-2 pr-8 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 focus:outline-none cursor-pointer"
                                        >
                                            <option value="">
                                                {selectedTtsProvider === 'elevenlabs' ? 'Select an ElevenLabs model' : 'Select an xAI model'}
                                            </option>
                                            {visibleProviderModels.map(model => (
                                                <option key={model.id} value={model.id}>
                                                    {model.name}
                                                    {selectedTtsProvider === 'elevenlabs'
                                                        ? model.is_v3
                                                            ? ' (v3)'
                                                            : model.streaming_type === 'http'
                                                                ? ' (HTTP)'
                                                                : model.supports_multilingual
                                                                    ? ' (Multilingual)'
                                                                    : ' (WS)'
                                                        : model.deprecated
                                                            ? ' (Legacy)'
                                                            : ' (Unified)'}
                                                </option>
                                            ))}
                                        </select>
                                        <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
                                    </div>
                                )}

                                {/* Language Dropdown */}
                                <div className="relative min-w-[175px]">
                                    <select
                                        value={selectedLanguage}
                                        onChange={(e) => setSelectedLanguage(e.target.value)}
                                        className="w-full appearance-none px-3 py-2 pr-8 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 focus:outline-none cursor-pointer"
                                    >
                                        {providerLanguageOptions.map(lang => (
                                            <option key={lang.value} value={lang.value}>
                                                {lang.flag} {lang.label}
                                            </option>
                                        ))}
                                    </select>
                                    <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
                                </div>
                                <button
                                    type="button"
                                    onClick={() => setShowAdvancedVoiceLlmSettings(prev => !prev)}
                                    className={`p-2 rounded-lg border transition-colors ${showAdvancedVoiceLlmSettings ? 'bg-gray-900 text-white border-gray-900' : 'bg-gray-100 text-gray-700 border-gray-200 hover:bg-gray-200'}`}
                                    title="Voice speed settings"
                                >
                                    <Settings className="w-4 h-4" />
                                </button>
                            </div>

                            {showAdvancedVoiceLlmSettings && (
                                <div className="mt-3 rounded-lg border border-gray-200 bg-gray-50 px-3 py-3 space-y-3">
                                    <div>
                                        <div className="flex items-center justify-between mb-1">
                                            <label className="text-xs font-medium text-gray-700">Voice Speed</label>
                                            <span className="text-xs text-gray-500">{voiceSpeed.toFixed(2)}x</span>
                                        </div>
                                        <input
                                            type="range"
                                            min={MIN_VOICE_SPEED}
                                            max={MAX_VOICE_SPEED}
                                            step={0.05}
                                            value={voiceSpeed}
                                            onChange={(e) => {
                                                const next = Number(e.target.value);
                                                setVoiceSpeed(clampNumber(next, MIN_VOICE_SPEED, MAX_VOICE_SPEED, DEFAULT_VOICE_SPEED));
                                            }}
                                            className="w-full accent-gray-900"
                                        />
                                        {selectedTtsProvider !== 'elevenlabs' && (
                                            <p className="mt-1 text-[11px] text-gray-500">
                                                Voice speed is applied only for ElevenLabs voices.
                                            </p>
                                        )}
                                        <p className="mt-1 text-[11px] text-gray-500">
                                            Stable speaking range: 0.8x to 1.2x.
                                        </p>
                                    </div>
                                    <div>
                                        <div className="flex items-center justify-between mb-1">
                                            <label className="text-xs font-medium text-gray-700">Phone LLM Override</label>
                                            <label className="flex items-center gap-2 text-[11px] text-gray-600">
                                                <input
                                                    type="checkbox"
                                                    checked={phoneLlmOverrideEnabled}
                                                    onChange={(e) => setPhoneLlmOverrideEnabled(e.target.checked)}
                                                    className="h-3.5 w-3.5 rounded border-gray-300 text-gray-900"
                                                />
                                                Enable override
                                            </label>
                                        </div>
                                        <select
                                            value={phoneLlmModel}
                                            onChange={(e) => setPhoneLlmModel(e.target.value)}
                                            disabled={!phoneLlmOverrideEnabled}
                                            className="w-full appearance-none px-3 py-2 pr-8 bg-white text-gray-700 rounded-lg text-sm font-medium border border-gray-200 hover:bg-gray-50 focus:outline-none cursor-pointer disabled:opacity-60"
                                        >
                                            {MODEL_OPTIONS.map(model => (
                                                <option key={model.value} value={model.value}>
                                                    {model.label} ({model.price})
                                                </option>
                                            ))}
                                        </select>
                                        <p className="mt-1 text-[11px] text-gray-500">
                                            Used only for live calls to keep latency low.
                                        </p>
                                    </div>
                                    <div>
                                        <div className="flex items-center justify-between mb-1">
                                            <label className="text-xs font-medium text-gray-700">Voice Runtime</label>
                                        </div>
                                        {selectedTtsProvider === 'xai' ? (
                                            <>
                                                <select
                                                    value="realtime_unified"
                                                    disabled
                                                    className="w-full appearance-none px-3 py-2 pr-8 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium border border-gray-200 cursor-not-allowed"
                                                >
                                                    <option value="realtime_unified">Realtime unified (xAI)</option>
                                                </select>
                                            </>
                                        ) : (
                                            <>
                                                <select
                                                    value={voiceRuntimeMode}
                                                    onChange={(e) => setVoiceRuntimeMode(e.target.value)}
                                                    className="w-full appearance-none px-3 py-2 pr-8 bg-white text-gray-700 rounded-lg text-sm font-medium border border-gray-200 hover:bg-gray-50 focus:outline-none cursor-pointer"
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
                                                        className="mt-2 w-full px-3 py-2 bg-white text-gray-700 rounded-lg text-sm font-medium border border-gray-200 focus:outline-none focus:border-gray-400"
                                                    />
                                                )}
                                            </>
                                        )}
                                    </div>
                                </div>
                            )}

                            {selectedTtsProvider === 'elevenlabs' && showCustomElevenVoiceInput && (
                                <div className="mt-3 rounded-lg border border-violet-200 bg-violet-50 px-3 py-3">
                                    <p className="text-xs font-medium text-violet-900 mb-2">Add custom ElevenLabs voice</p>
                                    <div className="flex flex-wrap items-center gap-2">
                                        <input
                                            type="text"
                                            value={customElevenVoiceId}
                                            onChange={(e) => {
                                                setCustomElevenVoiceId(e.target.value);
                                                setCustomElevenVoiceCandidate(null);
                                            }}
                                            placeholder="Enter ElevenLabs Voice ID"
                                            className="flex-1 min-w-[240px] px-3 py-2 bg-white border border-violet-300 rounded-lg text-sm text-gray-700 focus:outline-none focus:border-violet-500"
                                        />
                                        <button
                                            type="button"
                                            onClick={lookupCustomElevenVoiceId}
                                            disabled={customElevenVoiceLookupLoading}
                                            className="px-3 py-2 bg-violet-600 text-white rounded-lg text-sm font-medium hover:bg-violet-700 transition-colors disabled:opacity-60"
                                        >
                                            {customElevenVoiceLookupLoading ? 'Checking...' : 'Check ID'}
                                        </button>
                                    </div>

                                    {customElevenVoiceCandidate && (
                                        <div className="mt-2 flex flex-wrap items-center justify-between gap-2 rounded-md border border-violet-300 bg-white px-3 py-2">
                                            <div className="text-sm text-gray-800">
                                                <span className="font-medium">{customElevenVoiceCandidate.label}</span>
                                                <span className="text-gray-500"> ({customElevenVoiceCandidate.id})</span>
                                            </div>
                                            <button
                                                type="button"
                                                onClick={addCustomElevenVoice}
                                                className="px-3 py-1.5 bg-violet-600 text-white rounded-lg text-sm font-medium hover:bg-violet-700 transition-colors"
                                            >
                                                Add to voices
                                            </button>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Prompt Text Area */}
                        <div className="min-h-0 flex-1 px-6 pb-4 pt-4">
                            <textarea
                                value={systemPrompt}
                                onChange={(e) => setSystemPrompt(e.target.value)}
                                placeholder="Enter your system prompt here..."
                                className="h-full min-h-[320px] w-full resize-none overflow-y-auto rounded-2xl border border-gray-200 bg-white px-4 py-4 text-sm leading-relaxed text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-gray-400"
                            />
                        </div>

                        {/* Welcome Message */}
                        <div className="shrink-0 border-t border-gray-200 bg-white px-6 py-4">
                            <label className="block text-sm font-medium text-gray-700 mb-2">Welcome Message</label>
                            <select
                                value={welcomeOption}
                                onChange={(e) => setWelcomeOption(e.target.value)}
                                className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 focus:outline-none focus:border-gray-400"
                            >
                                {WELCOME_OPTIONS.map(option => (
                                    <option key={option.value} value={option.value}>{option.label}</option>
                                ))}
                            </select>

                            {welcomeOption === 'agent_greets' && (
                                <div className="mt-4">
                                    <label className="block text-sm font-medium text-gray-700 mb-2">Message Type</label>
                                    <select
                                        value={welcomeMessageMode}
                                        onChange={(e) => setWelcomeMessageMode(e.target.value)}
                                        className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 focus:outline-none focus:border-gray-400"
                                    >
                                        {WELCOME_MESSAGE_MODE_OPTIONS.map(option => (
                                            <option key={option.value} value={option.value}>{option.label}</option>
                                        ))}
                                    </select>
                                    {welcomeMessageMode === 'dynamic' ? (
                                        <p className="mt-2 text-xs text-gray-500">
                                            Dynamic message uses the greeting written in your prompt.
                                        </p>
                                    ) : (
                                        <>
                                            <label className="mt-4 block text-sm font-medium text-gray-700 mb-2">Custom Message</label>
                                            <textarea
                                                value={welcomeMessage}
                                                onChange={(e) => setWelcomeMessage(e.target.value)}
                                                placeholder="Write the exact first sentence to speak"
                                                className="w-full h-24 p-3 text-sm text-gray-900 border border-gray-300 rounded-lg placeholder:text-gray-400 focus:outline-none focus:border-blue-500 resize-none leading-relaxed"
                                            />
                                            <p className="mt-2 text-xs text-gray-500">
                                                If this is left empty, the runtime will use the greeting written in your prompt.
                                            </p>
                                        </>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Middle Column - Settings (25%) */}
                    <div className="min-h-0 w-[30%] overflow-y-auto border-r border-gray-200 bg-white">
                        {SETTINGS_SECTIONS.map((section) => {
                            const Icon = section.icon;
                            const isExpanded = expandedSections.includes(section.id);

                            return (
                                <div key={section.id} className="border-b border-gray-200">
                                    <button
                                        onClick={() => toggleSection(section.id)}
                                        className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
                                    >
                                        <div className="flex items-center gap-3">
                                            <Icon className="w-5 h-5 text-gray-500" />
                                            <span className="text-sm font-medium text-gray-700">{section.label}</span>
                                        </div>
                                        <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                                    </button>

                                    {isExpanded && (
                                        <div className="px-6 pb-4">
                                            {section.id === 'functions' ? (
                                                <div className="space-y-3">
                                                    <p className="text-sm text-gray-600 mb-3">
                                                        Enable your agent with capabilities such as calendar bookings, call termination, etc.
                                                    </p>

                                                    {/* Selected Functions List */}
                                                    {(Object.keys(allBuiltinFunctions).length > 0 || functions.length > 0) && (
                                                        <div className="space-y-2 mb-4">
                                                            <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Configured Functions</p>

                                                            {/* Selected Built-in Functions */}
                                                            {Object.entries(allBuiltinFunctions).map(([funcId, config]: [string, any]) => {
                                                                const func = builtinFunctions.find(f => f.id === funcId);
                                                                if (!func || !config?.enabled) return null;
                                                                return (
                                                                    <div key={funcId} className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
                                                                        <div className="flex items-center gap-3">
                                                                            <div className="flex h-5 w-5 items-center justify-center rounded bg-blue-600 text-[9px] font-semibold text-white">
                                                                                BI
                                                                            </div>
                                                                            <span className="text-sm font-medium text-gray-900">
                                                                                {formatBuiltinFunctionName(func.name)}
                                                                            </span>
                                                                        </div>
                                                                        <div className="flex items-center gap-2">
                                                                            <button
                                                                                onClick={() => openBuiltinConfigModal(funcId)}
                                                                                className="p-1.5 text-gray-400 hover:text-blue-600 transition-colors"
                                                                            >
                                                                                <Edit3 className="w-4 h-4" />
                                                                            </button>
                                                                            <button
                                                                                onClick={() => {
                                                                                    setAllBuiltinFunctions((prev: BuiltinFunctionsState) => {
                                                                                        const next: BuiltinFunctionsState = {
                                                                                            ...prev,
                                                                                            [funcId]: { ...prev[funcId], enabled: false },
                                                                                        };
                                                                                        void handleSaveBuiltinFunctions(next, true);
                                                                                        return next;
                                                                                    });
                                                                                    setBuiltinSaved(false);
                                                                                }}
                                                                                className="p-1.5 text-gray-400 hover:text-red-600 transition-colors"
                                                                            >
                                                                                <Trash2 className="w-4 h-4" />
                                                                            </button>
                                                                        </div>
                                                                    </div>
                                                                );
                                                            })}

                                                            {/* Custom Functions */}
                                                            {functions.map((func) => (
                                                                <div key={func.id} className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
                                                                    <div className="flex items-center gap-3">
                                                                        {func.method === 'POST' || func.method === 'GET' ? (
                                                                            <svg className="w-5 h-5 text-gray-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                                                <path d="M13 10V3L4 14h7v7l9-11h-7z" />
                                                                            </svg>
                                                                        ) : (
                                                                            <Phone className="w-5 h-5 text-gray-500" />
                                                                        )}
                                                                        <span className="text-sm font-medium text-gray-900">{func.name}</span>
                                                                    </div>
                                                                    <div className="flex items-center gap-2">
                                                                        <button
                                                                            onClick={() => {
                                                                                setSelectedFunction(func);
                                                                                setShowFunctionModal(true);
                                                                            }}
                                                                            className="p-1.5 text-gray-400 hover:text-blue-600 transition-colors"
                                                                        >
                                                                            <Edit3 className="w-4 h-4" />
                                                                        </button>
                                                                        <button
                                                                            onClick={() => handleDeleteFunction(func.id)}
                                                                            className="p-1.5 text-gray-400 hover:text-red-600 transition-colors"
                                                                        >
                                                                            <Trash2 className="w-4 h-4" />
                                                                        </button>
                                                                    </div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}

                                                    {/* Add Function Button */}
                                                    <button
                                                        onClick={() => setShowFunctionSelector(true)}
                                                        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
                                                    >
                                                        <Plus className="w-4 h-4" />
                                                        Add Function
                                                    </button>

                                                    {/* Save Builtin Functions Button */}
                                                    {Object.keys(allBuiltinFunctions).length > 0 && (
                                                        <button
                                                            onClick={() => { void handleSaveBuiltinFunctions(); }}
                                                            disabled={builtinSaved}
                                                            className={`w-full flex items-center justify-center gap-2 px-4 py-2 mt-3 rounded-lg text-sm font-medium transition-colors ${builtinSaved
                                                                ? 'bg-green-100 text-green-700 border border-green-300 cursor-default'
                                                                : 'bg-green-600 text-white hover:bg-green-700'
                                                                }`}
                                                        >
                                                            <Save className="w-4 h-4" />
                                                            {builtinSaved ? 'Saved!' : 'Save Functions'}
                                                        </button>
                                                    )}
                                                </div>
                                            ) : (
                                                <div className="space-y-4">
                                                    {section.id === 'call' && (
                                                        <div>
                                                            <div className="mb-4">
                                                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                                                    LiveKit Agent Name
                                                                </label>
                                                                <input
                                                                    type="text"
                                                                    value={livekitAgentName}
                                                                    onChange={(e) => setLivekitAgentName(e.target.value)}
                                                                    placeholder="e.g. sarah"
                                                                    className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 focus:outline-none focus:border-blue-500"
                                                                />
                                                                <p className="text-xs text-gray-500 mt-1">
                                                                    The agent name used for dispatching. Must match your voice agent worker registration.
                                                                </p>
                                                            </div>
                                                            <div className="bg-gray-50 rounded-lg p-3">
                                                                <p className="text-sm text-gray-500">
                                                                    Max duration: 30 minutes
                                                                </p>
                                                            </div>
                                                        </div>
                                                    )}
                                                    {section.id !== 'call' && (
                                                        <>
                                                            <p className="text-sm text-gray-500 mb-3">
                                                                {section.id === 'knowledge' && 'No documents uploaded'}
                                                                {section.id === 'speech' && `Voice: ${selectedVoice} (${selectedLanguage})`}
                                                                {section.id === 'transcription' && 'Realtime transcription enabled'}
                                                                {section.id === 'postcall' && 'Auto-generate call summary'}
                                                                {section.id === 'security' && 'Fallback settings configured'}
                                                                {section.id === 'webhook' && 'No webhook configured'}
                                                                {section.id === 'mcp' && 'No MCPs configured'}
                                                            </p>
                                                            <button className="text-sm text-blue-600 hover:text-blue-700 font-medium">
                                                                + Configure
                                                            </button>
                                                        </>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>

                    {/* Right Column - Testing (25%) */}
                    <div className="flex min-h-0 w-[25%] flex-col overflow-hidden bg-gray-50">
                        {/* Test Buttons */}
                        <div className="shrink-0 border-b border-gray-200 p-4">
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setShowVoiceCall(true)}
                                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
                                >
                                    <Phone className="w-4 h-4" />
                                    Test Audio
                                </button>
                                <button
                                    onClick={() => setShowTestChat(true)}
                                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
                                >
                                    <MessageSquare className="w-4 h-4" />
                                    Test Chat
                                </button>
                            </div>
                        </div>

                        {/* Test Area */}
                        <div className="flex flex-1 flex-col items-center justify-center p-6 text-center">
                            <div className="w-16 h-16 mb-4 text-gray-300">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                    <path d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
                                </svg>
                            </div>
                            <h3 className="text-base font-medium text-gray-900 mb-1">Test your agent</h3>

                            <div className="flex items-start gap-2 mt-4 text-xs text-gray-500 bg-blue-50 border border-blue-100 rounded-lg p-3">
                                <span className="text-blue-500 mt-0.5">ⓘ</span>
                                <span>Please note call transfer is not supported in Webcall.</span>
                            </div>

                            <button
                                onClick={() => setShowVoiceCall(true)}
                                className="mt-6 px-8 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
                            >
                                Test
                            </button>
                        </div>
                    </div>
                </div>

                {/* Voice Call Modal */}
                <VoiceCallModal
                    isOpen={showVoiceCall}
                    onClose={() => setShowVoiceCall(false)}
                    agentId={parseInt(agentId)}
                    agentName={agentName || agent?.name || ''}
                />
                <TestChatModal
                    isOpen={showTestChat}
                    onClose={() => setShowTestChat(false)}
                    agentId={parseInt(agentId)}
                    agentName={agentName || agent?.name || ''}
                />

                {/* Function Modal */}
                <FunctionModal
                    isOpen={showFunctionModal}
                    onClose={() => setShowFunctionModal(false)}
                    agentId={parseInt(agentId)}
                    functionData={selectedFunction}
                    onSuccess={fetchFunctions}
                />

                {showBuiltinConfigModal && selectedBuiltinFunctionId && builtinDraftConfig && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
                        <div className="mx-4 w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
                            <div className="mb-5 flex items-start justify-between gap-4">
                                <div>
                                    <h3 className="text-lg font-semibold text-gray-900">
                                        Configure {formatBuiltinFunctionName(builtinFunctions.find((func) => func.id === selectedBuiltinFunctionId)?.name)}
                                    </h3>
                                    <p className="mt-1 text-sm text-gray-500">
                                        Match the built-in function layout to the cleaner custom function editing flow.
                                    </p>
                                </div>
                                <button
                                    onClick={closeBuiltinConfigModal}
                                    className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
                                >
                                    <X className="h-5 w-5" />
                                </button>
                            </div>

                            <div className="space-y-4">
                                <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                                    <label className="mb-2 block text-sm font-medium text-gray-700">
                                        Tool Speech Mode
                                    </label>
                                    <select
                                        value={builtinDraftConfig.speak_during_execution ? 'during' : 'after'}
                                        onChange={(e) => {
                                            const nextMode = e.target.value === 'during' ? 'during' : 'after';
                                            setBuiltinDraftConfig((prev) => prev ? ({
                                                ...prev,
                                                speak_during_execution: nextMode === 'during',
                                                speak_after_execution: nextMode === 'after',
                                            }) : prev);
                                        }}
                                        className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-blue-500 focus:outline-none"
                                    >
                                        <option value="during">Speak During Execution</option>
                                        <option value="after">Speak After Execution</option>
                                    </select>
                                </div>

                                {(builtinFunctions.find((func) => func.id === selectedBuiltinFunctionId)?.name === 'call_transfer' ||
                                    builtinFunctions.find((func) => func.id === selectedBuiltinFunctionId)?.name === 'transfer_call') && (
                                    <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                                        <label className="mb-2 block text-sm font-medium text-gray-700">
                                            Transfer Phone Number
                                        </label>
                                        <input
                                            type="tel"
                                            inputMode="tel"
                                            autoComplete="off"
                                            placeholder="+1234567890"
                                            value={builtinDraftConfig.config?.phone_number || ''}
                                            onChange={(e) => {
                                                const nextValue = e.target.value;
                                                setBuiltinDraftConfig((prev) => prev ? ({
                                                    ...prev,
                                                    config: { ...(prev.config || {}), phone_number: nextValue },
                                                }) : prev);
                                            }}
                                            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-blue-500 focus:outline-none"
                                        />
                                        <p className="mt-2 text-xs text-gray-500">
                                            Enter the destination number in E.164 format.
                                        </p>
                                    </div>
                                )}
                            </div>

                            <div className="mt-6 flex items-center justify-end gap-3">
                                <button
                                    onClick={closeBuiltinConfigModal}
                                    className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={() => { void handleSaveBuiltinConfigModal(); }}
                                    className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
                                >
                                    <Save className="h-4 w-4" />
                                    Save Built-in Function
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Function Selector Modal */}
                {showFunctionSelector && (
                    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                        <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-lg font-semibold text-gray-900">Add Function</h3>
                                <button
                                    onClick={() => setShowFunctionSelector(false)}
                                    className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            <p className="text-sm text-gray-600 mb-4">
                                Choose a function to add to this agent:
                            </p>

                            <div className="space-y-2">
                                {/* Built-in Functions */}
                                {builtinFunctions.map((func) => {
                                    const isSelected = allBuiltinFunctions[func.id]?.enabled;
                                    return (
                                        <button
                                            key={func.id}
                                            onClick={() => {
                                                setAllBuiltinFunctions((prev: BuiltinFunctionsState) => {
                                                    const existing = prev[func.id] || {};
                                                    const next: BuiltinFunctionsState = {
                                                        ...prev,
                                                        [func.id]: {
                                                            enabled: true,
                                                            config: existing.config || {},
                                                            ...normalizeBuiltinSpeechFlags({
                                                                speak_during_execution: existing.speak_during_execution ?? func.speak_during_execution,
                                                                speak_after_execution: existing.speak_after_execution ?? func.speak_after_execution,
                                                            }),
                                                        },
                                                    };
                                                    void handleSaveBuiltinFunctions(next, true);
                                                    return next;
                                                });
                                                setBuiltinSaved(false);
                                                setShowFunctionSelector(false);
                                            }}
                                            disabled={isSelected}
                                            className={`w-full text-left p-3 rounded-lg border transition-colors ${isSelected
                                                ? 'bg-gray-50 border-gray-200 opacity-50 cursor-not-allowed'
                                                : 'bg-blue-50 border-blue-200 hover:bg-blue-100'
                                                }`}
                                        >
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center">
                                                        <span className="text-white text-xs font-bold">S</span>
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-medium text-gray-900">{func.name}</p>
                                                        <p className="text-xs text-gray-500">{func.description}</p>
                                                    </div>
                                                </div>
                                                {isSelected && (
                                                    <span className="text-xs text-green-600 font-medium">Added</span>
                                                )}
                                            </div>
                                        </button>
                                    );
                                })}

                                {/* Custom Function Option */}
                                <button
                                    onClick={() => {
                                        setShowFunctionSelector(false);
                                        setSelectedFunction(null);
                                        setShowFunctionModal(true);
                                    }}
                                    className="w-full text-left p-3 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 transition-colors"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-full bg-gray-500 flex items-center justify-center">
                                            <Plus className="w-4 h-4 text-white" />
                                        </div>
                                        <div>
                                            <p className="text-sm font-medium text-gray-900">Custom Function</p>
                                            <p className="text-xs text-gray-500">Create your own webhook function</p>
                                        </div>
                                    </div>
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
