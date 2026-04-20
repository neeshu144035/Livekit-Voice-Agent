'use client';

import { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { Phone, Mic, MicOff, PhoneOff, Loader2, MessageSquare, User, Bot } from 'lucide-react';
import { Room, RoomEvent, RemoteParticipant, RemoteTrack, RemoteTrackPublication, Track } from 'livekit-client';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api/';

interface Message {
    id: string;
    role: 'user' | 'agent';
    content: string;
    timestamp: Date;
}

interface EmbeddedVoiceCallProps {
    agentId: number;
    agentName: string;
}

export default function EmbeddedVoiceCall({ agentId, agentName }: EmbeddedVoiceCallProps) {
    const [token, setToken] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isCallActive, setIsCallActive] = useState(false);
    const [isMuted, setIsMuted] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);
    const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [isUserSpeaking, setIsUserSpeaking] = useState(false);
    const roomRef = useRef<Room | null>(null);
    const audioElementRef = useRef<HTMLAudioElement | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (agentId) {
            fetchToken();
        }

        return () => {
            if (audioElementRef.current) {
                audioElementRef.current.pause();
                audioElementRef.current = null;
            }
            if (roomRef.current) {
                roomRef.current.disconnect();
                roomRef.current = null;
            }
        };
    }, [agentId]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const fetchToken = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await axios.get(`${API_URL}token/${agentId}`);
            setToken(res.data.token);
        } catch (err) {
            console.error('Error fetching token:', err);
            setError('Failed to fetch call token');
        } finally {
            setLoading(false);
        }
    };

    const addMessage = (role: 'user' | 'agent', content: string) => {
        setMessages(prev => [...prev, {
            id: Date.now().toString(),
            role,
            content,
            timestamp: new Date()
        }]);
    };

    const handleStartCall = async () => {
        if (!token) return;

        setIsConnecting(true);
        setMessages([]); // Clear previous messages

        try {
            const LIVEKIT_URL = process.env.NEXT_PUBLIC_LIVEKIT_URL || 'wss://13.135.81.172/rtc';

            const room = new Room({
                adaptiveStream: true,
                dynacast: true,
            });

            roomRef.current = room;

            room.on(RoomEvent.Connected, () => {
                console.log('Connected to LiveKit room');
                setIsCallActive(true);
                setIsConnecting(false);
                addMessage('agent', 'Connected. Waiting for agent to speak...');
            });

            room.on(RoomEvent.Disconnected, () => {
                console.log('Disconnected from LiveKit room');
                setIsCallActive(false);
                setIsMuted(false);
                setIsAgentSpeaking(false);
                setIsUserSpeaking(false);
            });

            room.on(RoomEvent.MediaDevicesError, (e) => {
                console.error('Media devices error:', e);
                setError('Microphone access denied');
                setIsConnecting(false);
            });

            // Track local audio (user speaking)
            room.on(RoomEvent.LocalTrackPublished, () => {
                setIsUserSpeaking(true);
            });

            // Subscribe to remote audio tracks (agent's voice)
            room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
                console.log('Subscribed to track:', track.kind, 'from', participant.identity);
                if (track.kind === Track.Kind.Audio) {
                    const audioElement = track.attach();
                    audioElementRef.current = audioElement;
                    audioElement.play().catch(e => console.error('Error playing audio:', e));
                    setIsAgentSpeaking(true);

                    // Add transcription placeholder for agent
                    if (participant.identity.includes('agent')) {
                        addMessage('agent', '🎤 Agent speaking...');
                    }
                }
            });

            room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
                console.log('Unsubscribed from track:', track.kind, 'from', participant.identity);
                if (track.kind === Track.Kind.Audio) {
                    track.detach();
                    setIsAgentSpeaking(false);
                }
            });

            // Speech detection for user
            room.on(RoomEvent.LocalTrackPublished, (publication) => {
                if (publication.track?.kind === Track.Kind.Audio) {
                    setIsUserSpeaking(true);
                    addMessage('user', '🎤 You: ');
                }
            });

            await room.connect(LIVEKIT_URL, token);
            await room.localParticipant.setMicrophoneEnabled(true);

        } catch (err) {
            console.error('Error starting call:', err);
            setError('Failed to connect');
            setIsConnecting(false);

            if (roomRef.current) {
                roomRef.current.disconnect();
                roomRef.current = null;
            }
        }
    };

    const handleEndCall = async () => {
        if (roomRef.current) {
            roomRef.current.disconnect();
            roomRef.current = null;
        }
        setIsCallActive(false);
        setIsMuted(false);
        setIsAgentSpeaking(false);
        setIsUserSpeaking(false);
        addMessage('agent', 'Call ended');
    };

    const toggleMute = async () => {
        if (roomRef.current) {
            const newMutedState = !isMuted;
            await roomRef.current.localParticipant.setMicrophoneEnabled(!newMutedState);
            setIsMuted(newMutedState);
            if (newMutedState) {
                addMessage('user', '🔇 Microphone muted');
            }
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center h-64 text-center">
                <p className="text-sm text-red-600 mb-2">{error}</p>
                <button
                    onClick={fetchToken}
                    className="px-4 py-2 bg-gray-900 text-white text-sm rounded-lg hover:bg-gray-800"
                >
                    Retry
                </button>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-white rounded-xl border border-gray-200 overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-gray-50">
                <div className="flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-gray-500" />
                    <span className="text-sm font-medium text-gray-700">Live Conversation</span>
                    {isCallActive && (
                        <span className="flex items-center gap-1 text-xs text-green-600">
                            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                            Live
                        </span>
                    )}
                </div>
                {!isCallActive ? (
                    <button
                        onClick={handleStartCall}
                        disabled={isConnecting}
                        className="flex items-center gap-2 px-3 py-1.5 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50"
                    >
                        {isConnecting ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            <Phone className="w-4 h-4" />
                        )}
                        {isConnecting ? 'Connecting...' : 'Start Call'}
                    </button>
                ) : (
                    <div className="flex items-center gap-2">
                        <button
                            onClick={toggleMute}
                            className={`p-2 rounded-lg transition-colors ${isMuted ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                }`}
                        >
                            {isMuted ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                        </button>
                        <button
                            onClick={handleEndCall}
                            className="p-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
                        >
                            <PhoneOff className="w-4 h-4" />
                        </button>
                    </div>
                )}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 && !isCallActive && (
                    <div className="text-center text-gray-400 py-8">
                        <p className="text-sm">Click "Start Call" to begin conversation</p>
                        <p className="text-xs mt-1">Transcription will appear here</p>
                    </div>
                )}

                {messages.map((message) => (
                    <div
                        key={message.id}
                        className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
                    >
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${message.role === 'user' ? 'bg-blue-100' : 'bg-green-100'
                            }`}>
                            {message.role === 'user' ? (
                                <User className="w-4 h-4 text-blue-600" />
                            ) : (
                                <Bot className="w-4 h-4 text-green-600" />
                            )}
                        </div>
                        <div className={`max-w-[75%] px-4 py-2 rounded-2xl text-sm ${message.role === 'user'
                                ? 'bg-blue-600 text-white rounded-br-none'
                                : 'bg-gray-100 text-gray-800 rounded-bl-none'
                            }`}>
                            {message.content}
                        </div>
                    </div>
                ))}

                {/* Speaking indicators */}
                {isCallActive && (
                    <div className="flex items-center justify-center gap-4 py-2">
                        {isUserSpeaking && (
                            <div className="flex items-center gap-2 text-xs text-blue-600">
                                <div className="flex gap-0.5">
                                    <div className="w-1 h-3 bg-blue-500 rounded-full animate-pulse" />
                                    <div className="w-1 h-4 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '0.1s' }} />
                                    <div className="w-1 h-2 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }} />
                                </div>
                                You
                            </div>
                        )}
                        {isAgentSpeaking && (
                            <div className="flex items-center gap-2 text-xs text-green-600">
                                <div className="flex gap-0.5">
                                    <div className="w-1 h-4 bg-green-500 rounded-full animate-pulse" />
                                    <div className="w-1 h-3 bg-green-500 rounded-full animate-pulse" style={{ animationDelay: '0.1s' }} />
                                    <div className="w-1 h-2 bg-green-500 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }} />
                                </div>
                                Agent
                            </div>
                        )}
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Status bar */}
            {isCallActive && (
                <div className="px-4 py-2 border-t border-gray-100 bg-gray-50 text-xs text-gray-500 text-center">
                    {isAgentSpeaking ? 'Agent is speaking...' : isUserSpeaking ? 'You are speaking...' : 'Listening...'}
                </div>
            )}
        </div>
    );
}
