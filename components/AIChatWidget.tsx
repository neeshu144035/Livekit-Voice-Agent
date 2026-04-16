import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Send, RefreshCw } from 'lucide-react';

interface Message {
    id: number;
    text: string;
    isUser: boolean;
    timestamp: Date;
    properties?: Property[];
}

// Property interface for property cards
interface Property {
    id: string;
    name: string;
    price: string;
    location: string;
    description: string;
    imageUrl: string;
    size?: string;
    type?: string;
    bedrooms?: number;
    bathrooms?: number;
}

interface QuickReply {
    id: number;
    text: string;
    icon: string;
}

interface WidgetPreviewConfig {
    webhookUrl: string;
    companyName: string;
    welcomeMessage: string;
    inputPlaceholder: string;
    sendLabel: string;
    launcherLabel: string;
    quickReplies: QuickReply[];
}

// Generate unique session ID for chat history
const generateSessionId = () => {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

const quickReplies = [
    { id: 1, text: 'I want to rent a property', icon: '🏠' },
    { id: 2, text: 'I want to buy a property', icon: '💰' },
];

const STORAGE_KEY = 'oyik_chatbot_dashboard_config_v1';
const defaultWidgetConfig: WidgetPreviewConfig = {
    webhookUrl: 'https://oyik.cloud/webhook/a05f977e-05e7-461d-a8a3-70f9c7c05025/chat',
    companyName: 'Ariya Property',
    welcomeMessage: 'Hello! Welcome to Ariya Property Services! How can I help you today?',
    inputPlaceholder: 'Type your message...',
    sendLabel: 'Send',
    launcherLabel: 'Chat',
    quickReplies,
};

const buildWelcomeMessage = (config: WidgetPreviewConfig): Message => ({
    id: 0,
    text: config.welcomeMessage,
    isUser: false,
    timestamp: new Date(),
});

const normalizeWidgetPreviewConfig = (raw: unknown): WidgetPreviewConfig => {
    if (!raw || typeof raw !== 'object') return defaultWidgetConfig;

    const data = raw as Record<string, unknown>;
    const normalizedReplies = Array.isArray(data.quickReplies)
        ? data.quickReplies
            .map((reply, index) => {
                const item = reply && typeof reply === 'object' ? (reply as Record<string, unknown>) : {};
                const text = typeof item.text === 'string' ? item.text.trim() : '';
                if (!text) return null;
                return {
                    id: typeof item.id === 'number' ? item.id : index + 1,
                    text,
                    icon: typeof item.icon === 'string' && item.icon.trim() ? item.icon : 'Ask',
                };
            })
            .filter(Boolean) as QuickReply[]
        : quickReplies;

    return {
        webhookUrl:
            typeof data.webhookUrl === 'string' && data.webhookUrl.trim()
                ? data.webhookUrl.trim()
                : defaultWidgetConfig.webhookUrl,
        companyName:
            typeof data.companyName === 'string' && data.companyName.trim()
                ? data.companyName.trim()
                : defaultWidgetConfig.companyName,
        welcomeMessage:
            typeof data.welcomeMessage === 'string' && data.welcomeMessage.trim()
                ? data.welcomeMessage
                : defaultWidgetConfig.welcomeMessage,
        inputPlaceholder:
            typeof data.inputPlaceholder === 'string' && data.inputPlaceholder.trim()
                ? data.inputPlaceholder
                : defaultWidgetConfig.inputPlaceholder,
        sendLabel:
            typeof data.sendLabel === 'string' && data.sendLabel.trim()
                ? data.sendLabel
                : defaultWidgetConfig.sendLabel,
        launcherLabel:
            typeof data.launcherLabel === 'string' && data.launcherLabel.trim()
                ? data.launcherLabel
                : defaultWidgetConfig.launcherLabel,
        quickReplies: normalizedReplies.length > 0 ? normalizedReplies : quickReplies,
    };
};

export function AIChatWidget() {
    const [widgetConfig, setWidgetConfig] = useState<WidgetPreviewConfig>(defaultWidgetConfig);
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<Message[]>([
        {
            id: 0,
            text: "Hello! 👋 Welcome to Ariya Property Services! 🏠 How can I help you today?",
            isUser: false,
            timestamp: new Date(),
        },
    ]);
    const [inputValue, setInputValue] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const [isMinimized, setIsMinimized] = useState(false);
    const [sessionId] = useState<string>(generateSessionId());
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping]);

    const handleSend = async () => {
        if (!inputValue.trim()) return;

        const userMessage: Message = {
            id: Date.now(),
            text: inputValue,
            isUser: true,
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        const messageToSend = inputValue;
        setInputValue('');
        setIsTyping(true);

        try {
            // Send to n8n webhook with session ID
            const response = await fetch('https://oyik.cloud/webhook/a05f977e-05e7-461d-a8a3-70f9c7c05025/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: messageToSend,
                    timestamp: new Date().toISOString(),
                    sessionId: sessionId,
                }),
            });

            if (response.ok) {
                const rawData = await response.text();
                let data: any = {};

                // Try to parse if it's a JSON string
                try {
                    data = JSON.parse(rawData);
                } catch {
                    // If not JSON, treat the entire response as message
                    data = { message: rawData };
                }

                // Extract the message - check multiple possible fields
                let botText = data.message || data.response || data.text || data.output || "Thank you for your message! Our team will get back to you shortly.";

                // Check if message field contains a JSON string (double-encoded)
                // If it starts with { or [, try to parse it
                if (typeof botText === 'string' && (botText.trim().startsWith('{') || botText.trim().startsWith('['))) {
                    try {
                        const nested = JSON.parse(botText);
                        if (typeof nested === 'object' && nested !== null) {
                            botText = nested.message || nested.response || nested.text || JSON.stringify(nested, null, 2);
                            // Extract nested properties
                            if (nested.properties) {
                                data.properties = nested.properties;
                            }
                        }
                    } catch {
                        // Not valid JSON, use as is
                    }
                }

                // Extract properties if available in response
                const properties = data.properties || [];

                const botMessage: Message = {
                    id: Date.now() + 1,
                    text: botText,
                    isUser: false,
                    timestamp: new Date(),
                    properties: properties.length > 0 ? properties : undefined,
                };
                setMessages((prev) => [...prev, botMessage]);
            } else {
                throw new Error('Webhook failed');
            }
        } catch (error) {
            console.error('Chat error:', error);
            // Fallback response if webhook fails
            const botMessage: Message = {
                id: Date.now() + 1,
                text: "Thank you for your message! Our team will get back to you shortly.",
                isUser: false,
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, botMessage]);
        } finally {
            setIsTyping(false);
        }
    };

    const handleQuickReply = async (reply: string) => {
        const userMessage: Message = {
            id: Date.now(),
            text: reply,
            isUser: true,
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setIsTyping(true);

        try {
            // Send to n8n webhook with session ID
            const response = await fetch('https://oyik.cloud/webhook/a05f977e-05e7-461d-a8a3-70f9c7c05025/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: reply,
                    timestamp: new Date().toISOString(),
                    sessionId: sessionId,
                }),
            });

            if (response.ok) {
                const rawData = await response.text();
                let data: any = {};

                // Try to parse if it's a JSON string
                try {
                    data = JSON.parse(rawData);
                } catch {
                    // If not JSON, treat the entire response as message
                    data = { message: rawData };
                }

                // Extract the message - check multiple possible fields
                let botText = data.message || data.response || data.text || data.output || "Thank you for your message! Our team will get back to you shortly.";

                // Check if message field contains a JSON string (double-encoded)
                if (typeof botText === 'string' && (botText.trim().startsWith('{') || botText.trim().startsWith('['))) {
                    try {
                        const nested = JSON.parse(botText);
                        if (typeof nested === 'object' && nested !== null) {
                            botText = nested.message || nested.response || nested.text || JSON.stringify(nested, null, 2);
                            if (nested.properties) {
                                data.properties = nested.properties;
                            }
                        }
                    } catch {
                        // Not valid JSON
                    }
                }

                // Extract properties if available in response
                const properties = data.properties || [];

                const botMessage: Message = {
                    id: Date.now() + 1,
                    text: botText,
                    isUser: false,
                    timestamp: new Date(),
                    properties: properties.length > 0 ? properties : undefined,
                };
                setMessages((prev) => [...prev, botMessage]);
            } else {
                throw new Error('Webhook failed');
            }
        } catch (error) {
            console.error('Chat error:', error);
            const botMessage: Message = {
                id: Date.now() + 1,
                text: "Thank you for your message! Our team will get back to you shortly.",
                isUser: false,
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, botMessage]);
        } finally {
            setIsTyping(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleRefresh = () => {
        setMessages([
            {
                id: 0,
                text: "Hello! 👋 Welcome to Ariya Property Services! 🏠 How can I help you today?",
                isUser: false,
                timestamp: new Date(),
            },
        ]);
        setIsMinimized(false);
    };

    const formatTime = (date: Date) => {
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    return (
        <>
            {/* Chat Window */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 20, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 20, scale: 0.95 }}
                        transition={{ duration: 0.3, ease: 'easeOut' }}
                        className="chat-widget-window premium"
                        style={{
                            position: 'fixed',
                            bottom: '100px',
                            right: '20px',
                            width: '400px',
                            height: isMinimized ? '80px' : '600px',
                            maxHeight: 'calc(100vh - 120px)',
                            background: 'linear-gradient(180deg, #1a1a2e 0%, #16213e 100%)',
                            borderRadius: '24px',
                            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.1)',
                            overflow: 'hidden',
                            zIndex: 9999,
                            display: 'flex',
                            flexDirection: 'column',
                        }}
                    >
                        {/* Premium Header */}
                        <motion.div
                            className="chat-widget-header premium"
                            style={{
                                background: 'linear-gradient(135deg, #1E3A8A 0%, #3B82F6 50%, #60A5FA 100%)',
                                padding: '20px 24px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                position: 'relative',
                                overflow: 'hidden',
                            }}
                        >
                            {/* Animated background effect */}
                            <div
                                style={{
                                    position: 'absolute',
                                    top: 0,
                                    left: 0,
                                    right: 0,
                                    bottom: 0,
                                    background: 'radial-gradient(circle at 20% 50%, rgba(255, 255, 255, 0.1) 0%, transparent 50%)',
                                }}
                            />

                            <div style={{ display: 'flex', alignItems: 'center', gap: '14px', position: 'relative', zIndex: 1 }}>
                                <motion.div
                                    whileHover={{ scale: 1.1, rotate: 5 }}
                                    style={{
                                        width: '48px',
                                        height: '48px',
                                        background: 'linear-gradient(135deg, #FF6B35 0%, #F7931E 100%)',
                                        borderRadius: '14px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        boxShadow: '0 4px 15px rgba(0, 0, 0, 0.2)',
                                    }}
                                >
                                    <svg width="32" height="32" viewBox="0 0 100 100">
                                        <rect x="20" y="25" width="60" height="50" rx="10" fill="white" />
                                        <circle cx="38" cy="45" r="8" fill="#FF6B35" />
                                        <circle cx="62" cy="45" r="8" fill="#FF6B35" />
                                        <rect x="47" y="10" width="6" height="20" fill="white" />
                                        <circle cx="50" cy="8" r="5" fill="white" />
                                        <rect x="35" y="60" width="30" height="6" rx="3" fill="#FF6B35" />
                                    </svg>
                                </motion.div>
                                <div>
                                    <h3 style={{
                                        color: 'white',
                                        fontSize: '18px',
                                        fontWeight: '700',
                                        margin: 0,
                                        textShadow: '0 2px 4px rgba(0, 0, 0, 0.2)',
                                    }}>
                                        Ariya Property
                                    </h3>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                                        <motion.div
                                            animate={{ scale: [1, 1.2, 1] }}
                                            transition={{ repeat: Infinity, duration: 2 }}
                                            style={{
                                                width: '8px',
                                                height: '8px',
                                                background: '#22c55e',
                                                borderRadius: '50%',
                                                boxShadow: '0 0 10px #22c55e',
                                            }}
                                        />
                                        <span style={{ color: 'rgba(255, 255, 255, 0.9)', fontSize: '13px', fontWeight: '500' }}>
                                            Online - AI Powered
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div style={{ display: 'flex', gap: '8px', position: 'relative', zIndex: 1 }}>
                                <motion.button
                                    whileHover={{ scale: 1.1, rotate: 180 }}
                                    whileTap={{ scale: 0.9 }}
                                    transition={{ duration: 0.3 }}
                                    onClick={handleRefresh}
                                    title="Refresh chat"
                                    style={{
                                        background: 'rgba(255, 255, 255, 0.15)',
                                        border: 'none',
                                        borderRadius: '12px',
                                        padding: '10px',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        backdropFilter: 'blur(10px)',
                                    }}
                                >
                                    <RefreshCw size={18} style={{ color: 'white' }} />
                                </motion.button>
                                <motion.button
                                    whileHover={{ scale: 1.1 }}
                                    whileTap={{ scale: 0.9 }}
                                    transition={{ duration: 0.2 }}
                                    onClick={() => setIsOpen(false)}
                                    title="Close chat"
                                    style={{
                                        background: 'rgba(255, 255, 255, 0.15)',
                                        border: 'none',
                                        borderRadius: '12px',
                                        padding: '10px',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        backdropFilter: 'blur(10px)',
                                    }}
                                >
                                    <X size={18} style={{ color: 'white' }} />
                                </motion.button>
                            </div>
                        </motion.div>

                        {/* Minimized content */}
                        <AnimatePresence>
                            {!isMinimized && (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
                                >
                                    {/* Messages Area */}
                                    <div
                                        className="chat-widget-messages premium"
                                        style={{
                                            flex: 1,
                                            overflowY: 'auto',
                                            padding: '20px',
                                            display: 'flex',
                                            flexDirection: 'column',
                                            gap: '16px',
                                            scrollbarWidth: 'thin',
                                            scrollbarColor: 'rgba(255, 255, 255, 0.2) transparent',
                                        }}
                                    >
                                        {/* Welcome Message */}
                                        <motion.div
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: 0.2 }}
                                            className="chat-message bot premium"
                                            style={{
                                                display: 'flex',
                                                alignItems: 'flex-start',
                                                gap: '12px',
                                            }}
                                        >
                                            <motion.div
                                                whileHover={{ scale: 1.05 }}
                                                style={{
                                                    width: '40px',
                                                    height: '40px',
                                                    background: 'linear-gradient(135deg, #FF6B35 0%, #F7931E 100%)',
                                                    borderRadius: '12px',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    flexShrink: 0,
                                                    boxShadow: '0 4px 12px rgba(255, 107, 53, 0.3)',
                                                }}
                                            >
                                                <svg width="24" height="24" viewBox="0 0 100 100">
                                                    <rect x="20" y="25" width="60" height="50" rx="8" fill="white" />
                                                    <circle cx="38" cy="45" r="7" fill="#FF6B35" />
                                                    <circle cx="62" cy="45" r="7" fill="#FF6B35" />
                                                    <rect x="47" y="12" width="6" height="18" fill="white" />
                                                    <circle cx="50" cy="10" r="4" fill="white" />
                                                    <rect x="38" y="58" width="24" height="5" rx="2" fill="#FF6B35" />
                                                </svg>
                                            </motion.div>
                                            <motion.div
                                                initial={{ opacity: 0, x: -10 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                transition={{ delay: 0.3 }}
                                                style={{
                                                    maxWidth: '80%',
                                                    padding: '16px 20px',
                                                    background: 'rgba(255, 255, 255, 0.08)',
                                                    borderRadius: '20px',
                                                    borderBottomLeftRadius: '4px',
                                                    backdropFilter: 'blur(10px)',
                                                    border: '1px solid rgba(255, 255, 255, 0.1)',
                                                }}
                                            >
                                                <p style={{
                                                    color: 'white',
                                                    fontSize: '15px',
                                                    lineHeight: '1.6',
                                                    margin: 0,
                                                    fontWeight: '400',
                                                    whiteSpace: 'pre-wrap',
                                                    wordBreak: 'break-word',
                                                }}>
                                                    👋 Welcome to Ariya Property Services!
                                                    <span style={{ color: '#F97316', fontWeight: '600' }}>Your trusted partner</span> for property rentals, sales, and management.
                                                </p>
                                            </motion.div>
                                        </motion.div>

                                        {/* Messages */}
                                        {messages.slice(1).map((message, index) => (
                                            <motion.div
                                                key={message.id}
                                                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                                transition={{ delay: index * 0.05 }}
                                                className={`chat-message ${message.isUser ? 'user' : 'bot'} premium`}
                                                style={{
                                                    display: 'flex',
                                                    flexDirection: 'column',
                                                    alignItems: message.isUser ? 'flex-end' : 'flex-start',
                                                    gap: '12px',
                                                }}
                                            >
                                                <div style={{
                                                    display: 'flex',
                                                    alignItems: 'flex-start',
                                                    gap: '12px',
                                                    flexDirection: message.isUser ? 'row-reverse' : 'row',
                                                }}>
                                                    {!message.isUser ? (
                                                        <motion.div
                                                            whileHover={{ scale: 1.05 }}
                                                            style={{
                                                                width: '40px',
                                                                height: '40px',
                                                                background: 'linear-gradient(135deg, #FF6B35 0%, #F7931E 100%)',
                                                                borderRadius: '12px',
                                                                display: 'flex',
                                                                alignItems: 'center',
                                                                justifyContent: 'center',
                                                                flexShrink: 0,
                                                                boxShadow: '0 4px 12px rgba(255, 107, 53, 0.3)',
                                                            }}
                                                        >
                                                            <svg width="24" height="24" viewBox="0 0 100 100">
                                                                <circle cx="50" cy="40" r="30" fill="white" />
                                                                <circle cx="50" cy="85" r="35" fill="white" />
                                                                <circle cx="40" cy="38" r="5" fill="#FF6B35" />
                                                                <circle cx="60" cy="38" r="5" fill="#FF6B35" />
                                                                <circle cx="40" cy="38" r="2" fill="white" />
                                                                <circle cx="60" cy="38" r="2" fill="white" />
                                                            </svg>
                                                        </motion.div>
                                                    ) : (
                                                        <motion.div
                                                            whileHover={{ scale: 1.05 }}
                                                            style={{
                                                                width: '40px',
                                                                height: '40px',
                                                                background: 'linear-gradient(135deg, #6B7280 0%, #9CA3AF 100%)',
                                                                borderRadius: '12px',
                                                                display: 'flex',
                                                                alignItems: 'center',
                                                                justifyContent: 'center',
                                                                flexShrink: 0,
                                                                boxShadow: '0 4px 12px rgba(107, 114, 128, 0.3)',
                                                            }}
                                                        >
                                                            <svg width="24" height="24" viewBox="0 0 100 100">
                                                                <circle cx="50" cy="40" r="30" fill="white" />
                                                                <circle cx="50" cy="85" r="35" fill="white" />
                                                                <circle cx="40" cy="38" r="5" fill="#6B7280" />
                                                                <circle cx="60" cy="38" r="5" fill="#6B7280" />
                                                                <circle cx="40" cy="38" r="2" fill="white" />
                                                                <circle cx="60" cy="38" r="2" fill="white" />
                                                            </svg>
                                                        </motion.div>
                                                    )}
                                                    <motion.div
                                                        style={{
                                                            maxWidth: message.isUser ? '75%' : '80%',
                                                            padding: '14px 18px',
                                                            background: message.isUser
                                                                ? 'linear-gradient(135deg, #F97316 0%, #FB923C 100%)'
                                                                : 'rgba(255, 255, 255, 0.08)',
                                                            borderRadius: '20px',
                                                            borderBottomRightRadius: message.isUser ? '4px' : '20px',
                                                            borderBottomLeftRadius: message.isUser ? '20px' : '4px',
                                                            boxShadow: message.isUser
                                                                ? '0 4px 15px rgba(249, 115, 22, 0.3)'
                                                                : 'none',
                                                            border: message.isUser ? 'none' : '1px solid rgba(255, 255, 255, 0.1)',
                                                        }}
                                                    >
                                                        <p style={{
                                                            color: 'white',
                                                            fontSize: '14px',
                                                            lineHeight: '1.6',
                                                            margin: 0,
                                                            fontWeight: '400',
                                                            whiteSpace: 'pre-wrap',
                                                            wordBreak: 'break-word',
                                                        }}>
                                                            {message.text}
                                                        </p>
                                                        <span style={{
                                                            fontSize: '11px',
                                                            color: 'rgba(255, 255, 255, 0.5)',
                                                            marginTop: '6px',
                                                            display: 'block',
                                                        }}>
                                                            {formatTime(message.timestamp)}
                                                        </span>
                                                    </motion.div>
                                                </div>

                                                {/* Property Cards */}
                                                {message.properties && message.properties.length > 0 && (
                                                    <motion.div
                                                        initial={{ opacity: 0, y: 10 }}
                                                        animate={{ opacity: 1, y: 0 }}
                                                        transition={{ delay: 0.2 }}
                                                        style={{
                                                            display: 'flex',
                                                            flexDirection: 'row',
                                                            gap: '12px',
                                                            marginTop: '12px',
                                                            width: message.isUser ? '75%' : '80%',
                                                            overflowX: 'auto',
                                                            paddingBottom: '8px',
                                                            justifyContent: 'flex-start',
                                                            marginLeft: message.isUser ? 0 : '52px',
                                                        }}
                                                    >
                                                        {message.properties.map((property, idx) => (
                                                            <motion.div
                                                                key={property.id || idx}
                                                                initial={{ opacity: 0, scale: 0.9 }}
                                                                animate={{ opacity: 1, scale: 1 }}
                                                                transition={{ delay: 0.3 + idx * 0.1 }}
                                                                whileHover={{ scale: 1.02 }}
                                                                style={{
                                                                    background: 'rgba(255, 255, 255, 0.08)',
                                                                    borderRadius: '16px',
                                                                    padding: '12px',
                                                                    display: 'flex',
                                                                    flexDirection: 'column',
                                                                    gap: '12px',
                                                                    border: '1px solid rgba(255, 255, 255, 0.1)',
                                                                    cursor: 'pointer',
                                                                    minWidth: '200px',
                                                                    maxWidth: '250px',
                                                                }}
                                                            >
                                                                <div style={{ flexShrink: 0, width: '100%' }}>
                                                                    <img
                                                                        src={property.imageUrl.replace('http://72.61.147.184:8089/images/', '/images/')}
                                                                        alt={property.name}
                                                                        style={{
                                                                            width: '100%',
                                                                            height: '150px',
                                                                            objectFit: 'cover',
                                                                            borderRadius: '10px',
                                                                        }}
                                                                    />
                                                                </div>
                                                                <div style={{ flex: 1, minWidth: 0 }}>
                                                                    <h4 style={{
                                                                        margin: '0 0 4px 0',
                                                                        color: 'white',
                                                                        fontSize: '14px',
                                                                        fontWeight: '600',
                                                                    }}>
                                                                        {property.name}
                                                                    </h4>
                                                                    <div style={{
                                                                        display: 'flex',
                                                                        alignItems: 'center',
                                                                        gap: '6px',
                                                                        marginBottom: '4px',
                                                                        color: '#F97316',
                                                                        fontSize: '13px',
                                                                        fontWeight: '600',
                                                                    }}>
                                                                        {property.price}
                                                                    </div>
                                                                    <p style={{
                                                                        fontSize: '12px',
                                                                        color: 'rgba(255, 255, 255, 0.7)',
                                                                        margin: 0,
                                                                        lineHeight: '1.4',
                                                                        overflow: 'hidden',
                                                                        textOverflow: 'ellipsis',
                                                                        whiteSpace: 'nowrap',
                                                                    }}>
                                                                        {property.location}
                                                                    </p>
                                                                </div>
                                                            </motion.div>
                                                        ))}
                                                    </motion.div>
                                                )}
                                            </motion.div>
                                        ))}

                                        {/* Typing Indicator */}
                                        <AnimatePresence>
                                            {isTyping && (
                                                <motion.div
                                                    initial={{ opacity: 0, y: 10 }}
                                                    animate={{ opacity: 1, y: 0 }}
                                                    exit={{ opacity: 0, y: -10 }}
                                                    className="chat-message bot premium"
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'flex-start',
                                                        gap: '12px',
                                                    }}
                                                >
                                                    <motion.div
                                                        whileHover={{ scale: 1.05 }}
                                                        style={{
                                                            width: '40px',
                                                            height: '40px',
                                                            background: 'linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%)',
                                                            borderRadius: '14px',
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            justifyContent: 'center',
                                                            flexShrink: 0,
                                                            boxShadow: '0 4px 12px rgba(30, 58, 138, 0.3)',
                                                        }}
                                                    >
                                                        <svg viewBox="0 0 40 40" style={{ width: '24px', height: '24px', color: 'white' }}>
                                                            <defs>
                                                                <radialGradient id="botGradient" cx="20" cy="20" r="20">
                                                                    <stop offset="0%" style={{ stopColor: '#4FC3F7', stopOpacity: 1 }} />
                                                                    <stop offset="100%" style={{ stopColor: '#2196F3', stopOpacity: 1 }} />
                                                                </radialGradient>
                                                            </defs>
                                                            <circle cx="20" cy="15" r="4" fill="white" />
                                                            <circle cx="15" cy="25" r="3" fill="white" />
                                                            <circle cx="25" cy="25" r="3" fill="white" />
                                                            <path d="M10 35h20v-3H10v3z" fill="url(#botGradient)" opacity="0.7" />
                                                            <circle cx="20" cy="20" r="8" fill="url(#botGradient)" opacity="0.5" />
                                                        </svg>
                                                    </motion.div>
                                                    <div
                                                        style={{
                                                            padding: '16px 20px',
                                                            background: 'rgba(255, 255, 255, 0.08)',
                                                            borderRadius: '20px',
                                                            borderBottomLeftRadius: '4px',
                                                            border: '1px solid rgba(255, 255, 255, 0.1)',
                                                            display: 'flex',
                                                            gap: '6px',
                                                            alignItems: 'center',
                                                        }}
                                                    >
                                                        {[0, 1, 2].map((dot) => (
                                                            <motion.div
                                                                key={dot}
                                                                animate={{ y: [0, -8, 0] }}
                                                                transition={{
                                                                    repeat: Infinity,
                                                                    duration: 1,
                                                                    delay: dot * 0.2,
                                                                    ease: 'easeInOut',
                                                                }}
                                                                style={{
                                                                    width: '10px',
                                                                    height: '10px',
                                                                    background: '#3B82F6',
                                                                    borderRadius: '50%',
                                                                    boxShadow: '0 0 10px rgba(59, 130, 246, 0.5)',
                                                                }}
                                                            />
                                                        ))}
                                                    </div>
                                                </motion.div>
                                            )}
                                        </AnimatePresence>

                                        {/* Quick Replies - only show before first user message */}
                                        {messages.length <= 2 && (
                                            <motion.div
                                                initial={{ opacity: 0, y: 20 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                transition={{ delay: 0.5 }}
                                                style={{
                                                    display: 'flex',
                                                    flexDirection: 'column',
                                                    gap: '10px',
                                                    marginTop: '8px',
                                                }}
                                            >
                                                <span style={{
                                                    fontSize: '12px',
                                                    color: 'rgba(255, 255, 255, 0.5)',
                                                    fontWeight: '500',
                                                }}>
                                                    Quick actions
                                                </span>
                                                <div style={{
                                                    display: 'flex',
                                                    flexWrap: 'wrap',
                                                    gap: '8px',
                                                }}>
                                                    {quickReplies.map((reply, index) => (
                                                        <motion.button
                                                            key={reply.id}
                                                            initial={{ opacity: 0, scale: 0.8 }}
                                                            animate={{ opacity: 1, scale: 1 }}
                                                            transition={{ delay: 0.6 + index * 0.1 }}
                                                            whileHover={{ scale: 1.02, backgroundColor: 'rgba(255, 255, 255, 0.15)' }}
                                                            whileTap={{ scale: 0.98 }}
                                                            onClick={() => handleQuickReply(reply.text)}
                                                            style={{
                                                                background: 'rgba(255, 255, 255, 0.08)',
                                                                border: '1px solid rgba(255, 255, 255, 0.12)',
                                                                borderRadius: '20px',
                                                                padding: '10px 16px',
                                                                cursor: 'pointer',
                                                                display: 'flex',
                                                                alignItems: 'center',
                                                                gap: '8px',
                                                                fontSize: '13px',
                                                                color: 'white',
                                                                backdropFilter: 'blur(10px)',
                                                                transition: 'all 0.2s ease',
                                                            }}
                                                        >
                                                            <span>{reply.icon}</span>
                                                            <span style={{ fontWeight: '500' }}>{reply.text}</span>
                                                        </motion.button>
                                                    ))}
                                                </div>
                                            </motion.div>
                                        )}

                                        <div ref={messagesEndRef} />
                                    </div>

                                    {/* Premium Input Area */}
                                    <div
                                        style={{
                                            padding: '16px 20px',
                                            background: 'linear-gradient(180deg, rgba(0, 0, 0, 0.3) 0%, rgba(0, 0, 0, 0.5) 100%)',
                                            borderTop: '1px solid rgba(255, 255, 255, 0.1)',
                                            backdropFilter: 'blur(20px)',
                                        }}
                                    >
                                        <div
                                            style={{
                                                display: 'flex',
                                                gap: '10px',
                                                alignItems: 'center',
                                                background: 'rgba(255, 255, 255, 0.08)',
                                                borderRadius: '16px',
                                                padding: '8px 12px',
                                                border: '1px solid rgba(255, 255, 255, 0.1)',
                                                backdropFilter: 'blur(10px)',
                                            }}
                                        >
                                            <input
                                                type="text"
                                                value={inputValue}
                                                onChange={(e) => setInputValue(e.target.value)}
                                                onKeyPress={handleKeyPress}
                                                placeholder="Type your message..."
                                                style={{
                                                    flex: 1,
                                                    background: 'transparent',
                                                    border: 'none',
                                                    color: 'white',
                                                    fontSize: '15px',
                                                    outline: 'none',
                                                    padding: '8px 4px',
                                                }}
                                            />
                                            <motion.button
                                                whileHover={{ scale: 1.05 }}
                                                whileTap={{ scale: 0.95 }}
                                                onClick={handleSend}
                                                disabled={!inputValue.trim()}
                                                style={{
                                                    width: '44px',
                                                    height: '44px',
                                                    background: inputValue.trim()
                                                        ? 'linear-gradient(135deg, #F97316 0%, #FB923C 100%)'
                                                        : 'rgba(255, 255, 255, 0.1)',
                                                    border: 'none',
                                                    borderRadius: '14px',
                                                    cursor: inputValue.trim() ? 'pointer' : 'not-allowed',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    boxShadow: inputValue.trim()
                                                        ? '0 4px 15px rgba(249, 115, 22, 0.4)'
                                                        : 'none',
                                                    transition: 'all 0.2s ease',
                                                }}
                                            >
                                                <Send size={20} style={{ color: 'white', marginLeft: '2px' }} />
                                            </motion.button>
                                        </div>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Premium Chat Button */}
            <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                onClick={() => setIsOpen(true)}
                style={{
                    position: 'fixed',
                    bottom: '30px',
                    right: '30px',
                    width: '70px',
                    height: '70px',
                    background: 'linear-gradient(135deg, #FF6B35 0%, #F7931E 50%, #FFA500 100%)',
                    border: 'none',
                    borderRadius: '28px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 20px 60px rgba(255, 107, 53, 0.6), 0 0 0 6px rgba(255, 107, 53, 0.2)',
                    zIndex: 9998,
                }}
            >
                {/* Animated background effect */}
                <motion.div
                    animate={{
                        scale: [1, 1.3, 1],
                        opacity: [0.5, 0.9, 0.5],
                    }}
                    transition={{ repeat: Infinity, duration: 2 }}
                    style={{
                        position: 'absolute',
                        width: '100%',
                        height: '100%',
                        borderRadius: '28px',
                        background: 'radial-gradient(circle, rgba(255, 255, 255, 0.3) 0%, transparent 70%)',
                    }}
                />

                <motion.div
                    animate={{ rotate: [0, 8, 0, -8, 0] }}
                    transition={{ repeat: Infinity, duration: 4 }}
                >
                    <svg viewBox="0 0 100 100" style={{ width: '40px', height: '40px', position: 'relative', zIndex: 1 }}>
                        <defs>
                            <linearGradient id="newIconGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" style={{ stopColor: '#FFFFFF', stopOpacity: 1 }} />
                                <stop offset="100%" style={{ stopColor: '#E0E0E0', stopOpacity: 1 }} />
                            </linearGradient>
                        </defs>
                        {/* Robot Head */}
                        <rect x="20" y="25" width="60" height="50" rx="10" fill="url(#newIconGradient)" />
                        {/* Eyes */}
                        <circle cx="38" cy="45" r="8" fill="#1a1a2e" />
                        <circle cx="62" cy="45" r="8" fill="#1a1a2e" />
                        {/* Antenna */}
                        <rect x="47" y="10" width="6" height="20" fill="url(#newIconGradient)" />
                        <circle cx="50" cy="8" r="5" fill="url(#newIconGradient)" />
                        {/* Mouth */}
                        <rect x="35" y="60" width="30" height="6" rx="3" fill="#1a1a2e" />
                    </svg>
                </motion.div>

                {/* Tooltip */}
                <motion.div
                    initial={{ opacity: 0, x: 10 }}
                    whileHover={{ opacity: 1, x: 0 }}
                    style={{
                        position: 'absolute',
                        left: '85px',
                        bottom: '15px',
                        background: 'linear-gradient(135deg, #FF6B35 0%, #F7931E 100%)',
                        color: 'white',
                        padding: '12px 20px',
                        borderRadius: '14px',
                        fontSize: '14px',
                        fontWeight: '700',
                        whiteSpace: 'nowrap',
                        boxShadow: '0 6px 25px rgba(255, 107, 53, 0.5)',
                        opacity: 0,
                        pointerEvents: 'none',
                    }}
                >
                    Chat with AI Agent
                    <div
                        style={{
                            position: 'absolute',
                            right: '-6px',
                            top: '50%',
                            transform: 'translateY(-50%)',
                            borderWidth: '6px 0 6px 6px',
                            borderStyle: 'solid',
                            borderColor: 'transparent transparent transparent #F7931E',
                        }}
                    />
                </motion.div>
            </motion.button>

            {/* CSS for scrollbar */}
            <style>{`
        .chat-widget-messages.premium::-webkit-scrollbar {
          width: 6px;
        }
        .chat-widget-messages.premium::-webkit-scrollbar-track {
          background: transparent;
        }
        .chat-widget-messages.premium::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.2);
          border-radius: 3px;
        }
        .chat-widget-messages.premium::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.3);
        }

        @media (max-width: 480px) {
          .chat-widget-window.premium {
            width: calc(100vw - 30px) !important;
            right: 10px !important;
            bottom: 90px !important;
            height: 70vh !important;
          }
        }
      `}</style>
        </>
    );
}

export default AIChatWidget;
