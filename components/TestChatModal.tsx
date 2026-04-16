'use client';

import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Room, RoomEvent, RemoteParticipant } from 'livekit-client';
import { X, Send, Bot, User, Loader2, Wrench } from 'lucide-react';

const API_URL = '/api/';

interface TestChatModalProps {
    isOpen: boolean;
    onClose: () => void;
    agentId: number;
    agentName: string;
}

interface ChatEntry {
    id: string;
    type: 'message' | 'tool_call' | 'tool_response' | 'system' | 'error';
    role?: 'user' | 'agent';
    text?: string;
    toolName?: string;
    toolPayload?: any;
    timestamp: number;
}

export default function TestChatModal({ isOpen, onClose, agentId, agentName }: TestChatModalProps) {
    const [entries, setEntries] = useState<ChatEntry[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [connected, setConnected] = useState(false);
    const [fallbackMode, setFallbackMode] = useState(false);
    const [fallbackHistory, setFallbackHistory] = useState<any[]>([]);
    const [error, setError] = useState<string | null>(null);
    const roomRef = useRef<Room | null>(null);
    const endRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!isOpen || !agentId) return;
        void connectChatRoom();

        return () => {
            if (roomRef.current) {
                roomRef.current.disconnect();
                roomRef.current = null;
            }
            setConnected(false);
            setFallbackMode(false);
            setFallbackHistory([]);
            setLoading(false);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen, agentId]);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [entries]);

    if (!isOpen) return null;

    const addEntry = (entry: Omit<ChatEntry, 'id' | 'timestamp'>) => {
        const item: ChatEntry = {
            id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
            timestamp: Date.now(),
            ...entry,
        };
        setEntries((prev) => [...prev, item]);
    };

    const connectChatRoom = async () => {
        setLoading(true);
        setError(null);
        setEntries([]);
        setFallbackMode(false);
        setFallbackHistory([]);
        try {
            const tokenRes = await axios.get(`${API_URL}token/${agentId}`);
            const token = tokenRes.data?.token;
            // Match Test Audio behavior: prefer frontend-configured LiveKit URL.
            // Some backend-reported URLs are reachable from server, not browser.
            const livekitUrl =
                process.env.NEXT_PUBLIC_LIVEKIT_URL ||
                tokenRes.data?.livekit_url ||
                'wss://13.135.81.172:7880';

            if (!token) {
                throw new Error('Missing LiveKit token');
            }

            const room = new Room();
            roomRef.current = room;

            room.on(RoomEvent.Connected, () => {
                setConnected(true);
                addEntry({ type: 'system', text: 'Chat connected' });
            });

            room.on(RoomEvent.Disconnected, () => {
                setConnected(false);
                addEntry({ type: 'system', text: 'Chat disconnected' });
            });

            room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant?: RemoteParticipant) => {
                try {
                    const decoded = new TextDecoder().decode(payload);
                    const data = JSON.parse(decoded);

                    if (data.type === 'transcript' && data.role === 'agent' && data.text) {
                        addEntry({ type: 'message', role: 'agent', text: data.text });
                        return;
                    }
                    if (data.type === 'tool_call') {
                        addEntry({
                            type: 'tool_call',
                            toolName: data.tool_name || 'tool',
                            toolPayload: data.args || {},
                        });
                        return;
                    }
                    if (data.type === 'tool_response') {
                        addEntry({
                            type: 'tool_response',
                            toolName: data.tool_name || 'tool',
                            toolPayload: data.response || {},
                        });
                        return;
                    }
                    if (data.type === 'error') {
                        addEntry({ type: 'error', text: data.error || 'Unknown error' });
                        return;
                    }
                } catch {
                    // Ignore non-JSON data packets.
                }
            });

            room.registerTextStreamHandler('lk.chat', async (reader, participantInfo) => {
                try {
                    const message = await reader.readAll();
                    if (!message || !message.trim()) return;

                    const identity = participantInfo?.identity || '';
                    const role: 'user' | 'agent' = identity.includes('agent') ? 'agent' : 'user';

                    if (role === 'agent') {
                        addEntry({ type: 'message', role: 'agent', text: message });
                    }
                } catch (e) {
                    console.error('lk.chat handler error:', e);
                }
            });

            await room.connect(livekitUrl, token);
            await room.localParticipant.setMicrophoneEnabled(false);
        } catch (err: any) {
            console.error('Test chat connect error:', err);
            const detail = err?.response?.data?.detail || err?.message || 'Failed to connect chat';
            const isPcFailure = /pc connection|peer connection/i.test(String(detail));
            if (!isPcFailure) {
                setError(detail);
                addEntry({ type: 'error', text: detail });
                return;
            }

            // Fallback mode for networks where WebRTC peer connection cannot be established.
            setFallbackMode(true);
            setConnected(true);
            setError(null);
            addEntry({ type: 'system', text: 'LiveKit WebRTC unavailable. Using fallback chat mode.' });

            try {
                const startRes = await axios.post(`${API_URL}agents/${agentId}/test-chat`, {
                    start: true,
                    history: [],
                });
                const reply = (startRes.data?.reply || '').trim();
                if (Array.isArray(startRes.data?.history)) {
                    setFallbackHistory(startRes.data.history);
                }
                if (reply) {
                    addEntry({ type: 'message', role: 'agent', text: reply });
                }
            } catch (fallbackErr: any) {
                const fallbackDetail =
                    fallbackErr?.response?.data?.detail ||
                    fallbackErr?.message ||
                    'Fallback chat mode failed';
                setError(fallbackDetail);
                addEntry({ type: 'error', text: fallbackDetail });
            }
        } finally {
            setLoading(false);
        }
    };

    const sendMessage = async () => {
        const text = input.trim();
        if (!text || !connected) return;

        setInput('');
        addEntry({ type: 'message', role: 'user', text });

        if (fallbackMode) {
            try {
                const res = await axios.post(`${API_URL}agents/${agentId}/test-chat`, {
                    message: text,
                    history: fallbackHistory,
                });

                const events = Array.isArray(res.data?.events) ? res.data.events : [];
                for (const ev of events) {
                    if (ev?.type === 'tool_call') {
                        addEntry({
                            type: 'tool_call',
                            toolName: ev.tool_name || 'tool',
                            toolPayload: ev.args || {},
                        });
                    } else if (ev?.type === 'tool_response') {
                        addEntry({
                            type: 'tool_response',
                            toolName: ev.tool_name || 'tool',
                            toolPayload: ev.response || {},
                        });
                    }
                }

                const reply = (res.data?.reply || '').trim();
                if (reply) {
                    addEntry({ type: 'message', role: 'agent', text: reply });
                }

                if (Array.isArray(res.data?.history)) {
                    setFallbackHistory(res.data.history);
                } else {
                    setFallbackHistory((prev) => [...prev, { role: 'user', content: text }, { role: 'assistant', content: reply }]);
                }
            } catch (fallbackErr: any) {
                const detail =
                    fallbackErr?.response?.data?.detail ||
                    fallbackErr?.message ||
                    'Failed to get fallback chat response';
                addEntry({ type: 'error', text: detail });
            }
            return;
        }

        if (!roomRef.current) return;
        try {
            const payload = new TextEncoder().encode(JSON.stringify({ type: 'user_message', text }));
            await roomRef.current.localParticipant.publishData(payload, { topic: 'lk.chat' });
        } catch (err) {
            console.error('publishData failed:', err);
            addEntry({ type: 'error', text: 'Failed to send message to LiveKit chat' });
        }
    };

    const onKeyDown = async (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            await sendMessage();
        }
    };

    const handleClose = () => {
        if (roomRef.current) {
            roomRef.current.disconnect();
            roomRef.current = null;
        }
        onClose();
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl h-[680px] flex flex-col">
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                            <Bot className="w-5 h-5 text-green-600" />
                        </div>
                        <div>
                            <h2 className="text-lg font-semibold text-gray-900">{agentName}</h2>
                            <p className="text-sm text-gray-500">
                                Test Chat ({connected ? 'connected' : loading ? 'connecting' : 'offline'})
                            </p>
                        </div>
                    </div>
                    <button onClick={handleClose} className="p-2 hover:bg-gray-100 rounded-lg">
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
                    {entries.map((entry) => {
                        if (entry.type === 'message') {
                            return (
                                <div key={entry.id} className={`flex gap-3 ${entry.role === 'user' ? 'flex-row-reverse' : ''}`}>
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${entry.role === 'user' ? 'bg-blue-100' : 'bg-green-100'}`}>
                                        {entry.role === 'user' ? (
                                            <User className="w-4 h-4 text-blue-600" />
                                        ) : (
                                            <Bot className="w-4 h-4 text-green-600" />
                                        )}
                                    </div>
                                    <div className={`max-w-[80%] px-4 py-2 rounded-lg text-sm ${entry.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white border border-gray-200 text-gray-900'}`}>
                                        {entry.text}
                                    </div>
                                </div>
                            );
                        }

                        if (entry.type === 'tool_call' || entry.type === 'tool_response') {
                            const isCall = entry.type === 'tool_call';
                            return (
                                <div key={entry.id} className="rounded-lg border border-purple-200 bg-purple-50 px-3 py-2 text-xs text-purple-900">
                                    <div className="flex items-center gap-2 font-medium mb-1">
                                        <Wrench className="w-3.5 h-3.5" />
                                        {isCall ? `Calling tool: ${entry.toolName}` : `Tool response: ${entry.toolName}`}
                                    </div>
                                    <pre className="whitespace-pre-wrap break-words text-[11px] leading-relaxed">
                                        {JSON.stringify(entry.toolPayload ?? {}, null, 2)}
                                    </pre>
                                </div>
                            );
                        }

                        return (
                            <div key={entry.id} className={`text-xs rounded-lg px-3 py-2 ${entry.type === 'error' ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-gray-100 text-gray-700'}`}>
                                {entry.text}
                            </div>
                        );
                    })}
                    {loading && (
                        <div className="flex items-center gap-2 text-sm text-gray-500">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Connecting to LiveKit...
                        </div>
                    )}
                    {error && !loading && (
                        <div className="text-xs text-red-600">{error}</div>
                    )}
                    <div ref={endRef} />
                </div>

                <div className="p-4 border-t border-gray-100 bg-white">
                    <div className="flex gap-2">
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={onKeyDown}
                            placeholder={connected ? 'Type your message...' : 'Connect first...'}
                            className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm resize-none focus:outline-none focus:border-gray-400"
                            rows={2}
                            disabled={!connected}
                        />
                        <button
                            onClick={() => {
                                void sendMessage();
                            }}
                            disabled={!connected || !input.trim()}
                            className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <Send className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
