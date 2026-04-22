'use client';

import { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { Phone, PhoneOff, Mic, MicOff } from 'lucide-react';
import { Room, RoomEvent, RemoteTrack, RemoteTrackPublication, RemoteParticipant, Track, TextStreamReader } from 'livekit-client';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api/';

interface Message {
    id: string;
    role: 'user' | 'agent';
    content: string;
    timestamp: Date;
    isFinal?: boolean;
}

interface SimpleVoiceCallProps {
    agentId: number;
    agentName: string;
}

export default function SimpleVoiceCall({ agentId, agentName }: SimpleVoiceCallProps) {
    const [token, setToken] = useState<string | null>(null);
    const [isCallActive, setIsCallActive] = useState(false);
    const [isMuted, setIsMuted] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [isConnecting, setIsConnecting] = useState(false);
    const roomRef = useRef<Room | null>(null);
    const audioElementRef = useRef<HTMLAudioElement | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        fetchToken();
        return () => {
            if (roomRef.current) {
                roomRef.current.disconnect();
            }
        };
    }, [agentId]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const fetchToken = async () => {
        try {
            const res = await axios.get(`${API_URL}token/${agentId}`);
            setToken(res.data.token);
        } catch (err) {
            console.error('Error fetching token:', err);
        }
    };

    const addMessage = (role: 'user' | 'agent', content: string, isFinal: boolean = true) => {
        if (!isFinal) {
            setMessages(prev => {
                const existing = prev.find(m => m.role === role && !m.isFinal);
                if (existing) {
                    return prev.map(m => m.id === existing.id ? { ...m, content } : m);
                }
                return [...prev, {
                    id: 'temp-' + Date.now(),
                    role,
                    content,
                    timestamp: new Date(),
                    isFinal: false
                }];
            });
        } else {
            setMessages(prev => {
                const cleaned = prev.filter(m => m.role !== role || m.isFinal);
                return [...cleaned, {
                    id: Date.now().toString() + Math.random().toString(),
                    role,
                    content,
                    timestamp: new Date(),
                    isFinal: true
                }];
            });
        }
    };

    const handleStartCall = async () => {
        if (!token) return;

        setIsConnecting(true);
        setMessages([]);

        try {
            const LIVEKIT_URL = process.env.NEXT_PUBLIC_LIVEKIT_URL || 'wss://13.135.81.172/rtc';

            const room = new Room({
                adaptiveStream: true,
                dynacast: true,
                audioCaptureDefaults: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
                publishDefaults: {
                    audioPreset: {
                        maxBitrate: 128000,
                    },
                    dtx: false,
                    stopMicTrackOnMute: false,
                },
                stopLocalTrackOnUnpublish: true,
            });

            roomRef.current = room;

            room.on(RoomEvent.Connected, () => {
                setIsCallActive(true);
                setIsConnecting(false);
                console.log('[Room] Connected');
            });

            room.on(RoomEvent.Disconnected, () => {
                setIsCallActive(false);
                setIsMuted(false);
                console.log('[Room] Disconnected');
            });

            room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
                if (track.kind === Track.Kind.Audio) {
                    console.log('[Room] Audio track subscribed from:', participant.identity);
                    const audioElement = track.attach();
                    audioElementRef.current = audioElement;
                    audioElement.autoplay = true;
                    audioElement.muted = false;
                    document.body.appendChild(audioElement);
                    const AudioCtx = (window as any).AudioContext || (window as any).webkitAudioContext;
                    if (AudioCtx) {
                        const ctx = new AudioCtx();
                        if (ctx.state === 'suspended') {
                            ctx.resume().catch(() => {});
                        }
                    }
                    audioElement.play().catch(console.error);
                }
            });

            room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack) => {
                if (track.kind === Track.Kind.Audio) {
                    track.detach();
                }
            });

            room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant: RemoteParticipant | undefined) => {
                console.log('[DataReceived] Raw payload:', payload.length, 'bytes');
                try {
                    const data = JSON.parse(new TextDecoder().decode(payload));
                    console.log('[DataReceived] Parsed:', data);
                    
                    if (data.type === 'transcript') {
                        console.log('[DataReceived] Transcript:', data.role, '-', data.text);
                        addMessage(data.role, data.text, data.is_final);
                    }
                    if (data.type === 'tool_call') {
                        console.log('[DataReceived] Tool call:', data.tool_name);
                        addMessage('agent', `🔧 Calling tool: ${data.tool_name}\n${JSON.stringify(data.parameters || {}, null, 2)}`, true);
                    }
                    if (data.type === 'tool_result') {
                        console.log('[DataReceived] Tool result:', data.tool_name);
                        addMessage('agent', `✅ ${data.tool_name} result:\n${JSON.stringify(data.result, null, 2)}`, true);
                    }
                } catch (e) {
                    console.error('[DataReceived] Error:', e);
                }
            });

            room.registerTextStreamHandler('lk.transcription', async (reader, participantInfo) => {
                console.log('[lk.transcription] Stream started for:', participantInfo.identity);
                try {
                    const message = await reader.readAll();
                    const attrs = reader.info.attributes || {};
                    const isFinal = attrs['lk.transcription_final'] === 'true';
                    const isTranscription = attrs['lk.transcribed_track_id'] !== undefined;
                    
                    console.log('[lk.transcription] Received:', {
                        from: participantInfo.identity,
                        message,
                        isFinal,
                        isTranscription,
                        attrs
                    });
                    
                    if (message && message.trim()) {
                        const isAgent = participantInfo.identity.includes('agent') || participantInfo.identity.includes('voice');
                        console.log('[lk.transcription] Adding message:', isAgent ? 'agent' : 'user', message);
                        addMessage(isAgent ? 'agent' : 'user', message, isFinal);
                    }
                } catch (e) {
                    console.error('[lk.transcription] Error:', e);
                }
            });

            console.log('[Room] About to connect to:', LIVEKIT_URL);
            await room.connect(LIVEKIT_URL, token);
            console.log('[Room] Connected to LiveKit');

            const remoteParticipants = Array.from(room.remoteParticipants.values());
            console.log('[Room] Remote participants:', remoteParticipants.length);

            await room.localParticipant.setMicrophoneEnabled(true);
            console.log('[Room] Microphone enabled');

        } catch (err) {
            console.error('Error starting call:', err);
            setIsConnecting(false);
        }
    };

    const handleEndCall = () => {
        if (roomRef.current) {
            roomRef.current.disconnect();
            roomRef.current = null;
        }
        setIsCallActive(false);
        setIsMuted(false);
    };

    const toggleMute = async () => {
        if (roomRef.current) {
            const newMuted = !isMuted;
            await roomRef.current.localParticipant.setMicrophoneEnabled(!newMuted);
            setIsMuted(newMuted);
        }
    };

    return (
        <div className="flex flex-col h-full bg-white">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-700">Test Audio</span>
                    <span className="text-sm text-gray-400">|</span>
                    <span className="text-sm text-gray-500">Test Chat</span>
                </div>
                {isCallActive && (
                    <button
                        onClick={handleEndCall}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-md hover:bg-red-50"
                    >
                        <PhoneOff className="w-4 h-4" />
                        End the Call
                    </button>
                )}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
                {!isCallActive && messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-gray-400">
                        <svg className="w-12 h-12 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                        </svg>
                        <p className="text-sm">Test your agent</p>
                        <p className="text-xs mt-1">Please note call transfer is not supported in Webcall.</p>
                    </div>
                )}

                {messages.map((message) => (
                    <div
                        key={message.id}
                        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        <div
                            className={`max-w-[85%] px-4 py-2.5 rounded-2xl text-sm ${message.role === 'user'
                                    ? 'bg-blue-600 text-white rounded-br-md'
                                    : 'bg-gray-100 text-gray-800 rounded-bl-md'
                                }`}
                        >
                            {message.content}
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Start Call Button or Controls */}
            {!isCallActive ? (
                <div className="p-4 border-t border-gray-200">
                    <button
                        onClick={handleStartCall}
                        disabled={isConnecting || !token}
                        className="w-full py-2.5 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                    >
                        {isConnecting ? 'Connecting...' : 'Test'}
                    </button>
                </div>
            ) : (
                <div className="flex items-center justify-center gap-4 p-4 border-t border-gray-200">
                    <button
                        onClick={toggleMute}
                        className={`p-3 rounded-full ${isMuted ? 'bg-gray-100 text-gray-600' : 'bg-gray-100 text-gray-600'}`}
                    >
                        {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                    </button>
                </div>
            )}
        </div>
    );
}
