'use client';

import { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { X, Phone, Mic, MicOff, PhoneOff, Loader2, Bot, MessageSquare } from 'lucide-react';
import { Room, RoomEvent, RemoteTrack, RemoteParticipant, Track } from 'livekit-client';

const API_URL = '/api/';

interface LogEntry {
  id: string;
  type: 'transcript' | 'tool_call' | 'tool_response' | 'error' | 'system';
  role?: 'agent' | 'user';
  text?: string;
  toolName?: string;
  toolArgs?: any;
  response?: any;
  error?: string;
  timestamp: number;
}

interface VoiceCallModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentId: number;
  agentName: string;
}

export default function VoiceCallModal({ isOpen, onClose, agentId, agentName }: VoiceCallModalProps) {
  const [token, setToken] = useState<string | null>(null);
  const [livekitUrl, setLivekitUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCallActive, setIsCallActive] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const roomRef = useRef<Room | null>(null);
  const audioElementRef = useRef<HTMLAudioElement | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (isOpen && agentId) {
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
  }, [isOpen, agentId]);

  useEffect(() => {
    if (transcriptEndRef.current) {
      transcriptEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const fetchToken = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`${API_URL}token/${agentId}`);
      setToken(res.data.token);
      setLivekitUrl(res.data.livekit_url || null);
    } catch (err: any) {
      console.error('Error fetching token:', err);
      setError(err.response?.data?.detail || 'Failed to fetch call token. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartCall = async () => {
    if (!token) return;

    setIsConnecting(true);
    setLogs([]);
    setError(null);

    try {
      const LIVEKIT_URL = livekitUrl || process.env.NEXT_PUBLIC_LIVEKIT_URL || 'wss://13.135.81.172/rtc';

      const room = new Room({
        audioCaptureDefaults: {
          echoCancellation: true,
          noiseSuppression: true,
        },
        publishDefaults: {
          audioPreset: {
            maxBitrate: 24000,
          },
          dtx: true,
        },
        stopLocalTrackOnUnpublish: true,
      });

      roomRef.current = room;

      room.on(RoomEvent.Connected, () => {
        console.log('Room Connected');
        setIsCallActive(true);
        setIsConnecting(false);
        setLogs(prev => [...prev, {
          id: Date.now().toString(),
          type: 'system',
          text: 'Call connected',
          timestamp: Date.now()
        }]);
      });

      room.on(RoomEvent.Disconnected, (reason) => {
        console.log('Room Disconnected:', reason);
        setIsCallActive(false);
        setIsMuted(false);
        setIsAgentSpeaking(false);
        setLogs(prev => [...prev, {
          id: Date.now().toString(),
          type: 'system',
          text: `Call disconnected: ${reason}`,
          timestamp: Date.now()
        }]);
      });

      room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack) => {
        console.log('Track Subscribed:', track.sid, track.kind);
        if (track.kind === Track.Kind.Audio) {
          const audioElement = track.attach();
          audioElementRef.current = audioElement;
          audioElement.play().catch(e => console.error('Error playing audio:', e));
          setIsAgentSpeaking(true);
        }
      });

      room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack) => {
        console.log('Track Unsubscribed:', track.sid);
        if (track.kind === Track.Kind.Audio) {
          track.detach();
          setIsAgentSpeaking(false);
        }
      });

      // Handle data messages from agent (transcripts, tool calls, etc.)
      room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant?: RemoteParticipant) => {
        const decoder = new TextDecoder();
        try {
          const decoded = decoder.decode(payload);
          console.log('Data Received:', decoded, 'from:', participant?.identity);
          const data = JSON.parse(decoded);
          
          if (data.type === 'transcript') {
            // Deduplicate by checking if same text already exists in last 3 entries
            setLogs(prev => {
              const recentLogs = prev.slice(-3);
              const isDuplicate = recentLogs.some(log => 
                log.type === 'transcript' && 
                log.role === data.role && 
                log.text === data.text
              );
              if (isDuplicate) return prev;
              
              return [...prev, {
                id: Date.now().toString(),
                type: 'transcript',
                role: data.role,
                text: data.text,
                timestamp: Date.now()
              }];
            });
          } else if (data.type === 'tool_call') {
            setLogs(prev => [...prev, {
              id: Date.now().toString(),
              type: 'tool_call',
              toolName: data.tool_name,
              toolArgs: data.args,
              timestamp: Date.now()
            }]);
          } else if (data.type === 'tool_response') {
            setLogs(prev => [...prev, {
              id: Date.now().toString(),
              type: 'tool_response',
              toolName: data.tool_name,
              response: data.response,
              timestamp: Date.now()
            }]);
          } else if (data.type === 'error') {
            setLogs(prev => [...prev, {
              id: Date.now().toString(),
              type: 'error',
              error: data.error,
              timestamp: Date.now()
            }]);
          }
        } catch (e) {
          console.error('Error parsing data message:', e);
        }
      });

      // Handle LiveKit transcription stream (captures audio transcription)
      room.registerTextStreamHandler('lk.transcription', async (reader, participantInfo) => {
        try {
          const message = await reader.readAll();
          const attrs = reader.info.attributes || {};
          const isFinal = attrs['lk.transcription_final'] === 'true';
          
          if (message && message.trim()) {
            const isAgent = participantInfo.identity.includes('agent') || participantInfo.identity.includes('voice');
            console.log('[lk.transcription] Received from:', participantInfo.identity, 'message:', message, 'isFinal:', isFinal);
            
            // Only show final transcriptions
            if (isFinal) {
              setLogs(prev => {
                const recentLogs = prev.slice(-3);
                const isDuplicate = recentLogs.some(log => log.text === message);
                if (isDuplicate) return prev;
                
                return [...prev, {
                  id: Date.now().toString(),
                  type: 'transcript',
                  role: isAgent ? 'agent' : 'user',
                  text: message,
                  timestamp: Date.now()
                }];
              });
            }
          }
        } catch (e) {
          console.error('[lk.transcription] Error:', e);
        }
      });

      await room.connect(LIVEKIT_URL, token);
      await room.localParticipant.setMicrophoneEnabled(true);

    } catch (err: any) {
      console.error('Error starting call:', err);
      setError(err.message || 'Failed to connect. Please check LiveKit server configuration.');
      setIsConnecting(false);
    }
  };

  const handleEndCall = async () => {
    if (roomRef.current) {
      roomRef.current.disconnect();
    }
    setIsCallActive(false);
    onClose();
  };

  const toggleMute = async () => {
    if (roomRef.current) {
      const newMutedState = !isMuted;
      await roomRef.current.localParticipant.setMicrophoneEnabled(!newMutedState);
      setIsMuted(newMutedState);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col h-[600px]">
        {/* Header */}
        <div className="flex items-center justify-between px-8 py-6 border-b border-gray-100">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center shadow-lg">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">{agentName}</h2>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${isCallActive ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`} />
                <p className="text-sm font-medium text-gray-500">{isCallActive ? 'On Call' : 'Ready'}</p>
              </div>
            </div>
          </div>
          <button onClick={handleEndCall} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
            <X className="w-6 h-6 text-gray-400" />
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Detailed Log View */}
          <div className="flex-1 flex flex-col bg-gray-50/50 p-6 overflow-hidden">
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest">Call Log</p>
              <div className="flex items-center gap-2 text-xs">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span>User</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500"></span>Agent</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-purple-500"></span>Tool</span>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
              {logs.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center opacity-40">
                  <MessageSquare className="w-12 h-12 mb-2" />
                  <p className="text-sm">Call logs will appear here...</p>
                </div>
              ) : (
                logs.map((log) => (
                  <div key={log.id} className="animate-in fade-in slide-in-from-bottom-2 duration-200">
                    {/* Transcript Entry */}
                    {log.type === 'transcript' && (
                      <div className={`flex flex-col ${log.role === 'user' ? 'items-end' : 'items-start'}`}>
                        <div className={`max-w-[85%] p-3 rounded-2xl shadow-sm text-sm ${log.role === 'user'
                          ? 'bg-blue-600 text-white rounded-tr-none'
                          : 'bg-white text-gray-900 rounded-tl-none border border-gray-200'
                          }`}>
                          <div className="flex items-center gap-2 mb-1 opacity-70">
                            <span className="text-xs font-medium">{log.role === 'user' ? 'You' : agentName}</span>
                            <span className="text-xs">{new Date(log.timestamp).toLocaleTimeString()}</span>
                          </div>
                          {log.text}
                        </div>
                      </div>
                    )}
                    
                    {/* Tool Call Entry */}
                    {log.type === 'tool_call' && (
                      <div className="flex items-start gap-2 bg-purple-50 border border-purple-200 rounded-lg p-3 mx-4">
                        <div className="w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center flex-shrink-0">
                          <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                          </svg>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold text-purple-700 mb-1">Tool Called: {log.toolName}</p>
                          <div className="bg-purple-100 rounded p-2 text-xs font-mono text-purple-900 overflow-x-auto">
                            <pre>{JSON.stringify(log.toolArgs, null, 2)}</pre>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {/* Tool Response Entry */}
                    {log.type === 'tool_response' && (
                      <div className="flex items-start gap-2 bg-green-50 border border-green-200 rounded-lg p-3 mx-4">
                        <div className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center flex-shrink-0">
                          <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold text-green-700 mb-1">Tool Response: {log.toolName}</p>
                          <div className="bg-green-100 rounded p-2 text-xs font-mono text-green-900 overflow-x-auto">
                            <pre>{JSON.stringify(log.response, null, 2)}</pre>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {/* Error Entry */}
                    {log.type === 'error' && (
                      <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg p-3 mx-4">
                        <div className="w-6 h-6 bg-red-500 rounded-full flex items-center justify-center flex-shrink-0">
                          <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold text-red-700 mb-1">Error</p>
                          <p className="text-xs text-red-600">{log.error}</p>
                        </div>
                      </div>
                    )}
                    
                    {/* System Entry */}
                    {log.type === 'system' && (
                      <div className="flex justify-center">
                        <span className="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full">
                          {log.text}
                        </span>
                      </div>
                    )}
                  </div>
                ))
              )}
              <div ref={transcriptEndRef} />
            </div>
          </div>

          {/* Stats/Controls Sidebar */}
          <div className="w-48 border-l border-gray-100 p-6 flex flex-col items-center justify-between">
            <div className="space-y-6 w-full text-center">
              {isCallActive && (
                <div className="space-y-2">
                  <p className="text-xs text-gray-400 font-medium uppercase tracking-wider">Live Status</p>
                  <div className="h-6 flex items-center justify-center gap-1">
                    {[...Array(5)].map((_, i) => (
                      <div
                        key={i}
                        className={`w-1 bg-purple-500 rounded-full transition-all duration-150 ${isAgentSpeaking ? 'animate-bounce' : 'h-1 opacity-20'
                          }`}
                        style={{ animationDelay: `${i * 0.1}s`, height: isAgentSpeaking ? '24px' : '4px' }}
                      />
                    ))}
                  </div>
                </div>
              )}

              <div>
                <p className="text-xs text-gray-400 font-medium uppercase tracking-wider mb-2">Latency</p>
                <div className="text-sm font-semibold text-gray-900">
                  {isCallActive ? '< 150ms' : '--'}
                </div>
              </div>
            </div>

            {/* Controls */}
            <div className="flex flex-col gap-4 w-full">
              {isCallActive ? (
                <>
                  <button
                    onClick={toggleMute}
                    className={`w-full py-3 rounded-xl flex items-center justify-center gap-2 transition-all ${isMuted ? 'bg-red-50 text-red-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                  >
                    {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                    <span className="text-sm font-semibold">{isMuted ? 'Muted' : 'Mute'}</span>
                  </button>
                  <button
                    onClick={handleEndCall}
                    className="w-full py-4 bg-red-600 text-white rounded-2xl flex items-center justify-center gap-2 shadow-lg shadow-red-200 hover:bg-red-700 transition-all"
                  >
                    <PhoneOff className="w-5 h-5" />
                    <span className="text-sm font-bold">End Call</span>
                  </button>
                </>
              ) : (
                <button
                  onClick={handleStartCall}
                  disabled={isConnecting || loading}
                  className="w-full py-4 bg-gray-900 text-white rounded-2xl flex items-center justify-center gap-2 shadow-xl shadow-gray-200 hover:bg-black disabled:opacity-50 transition-all font-bold"
                >
                  {isConnecting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Phone className="w-5 h-5" />}
                  Start Call
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
