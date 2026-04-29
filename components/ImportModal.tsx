'use client';

import { useState } from 'react';
import { X, Upload, FileJson, FileSpreadsheet } from 'lucide-react';
import { useToast } from './ToastProvider';

interface ImportModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function ImportModal({ isOpen, onClose }: ImportModalProps) {
    const { showToast } = useToast();
    const [dragActive, setDragActive] = useState(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);

    if (!isOpen) return null;

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setSelectedFile(e.dataTransfer.files[0]);
        }
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setSelectedFile(e.target.files[0]);
        }
    };

    const importRetellAgent = async (jsonData: any) => {
        if (!jsonData.agent_name && !jsonData.retellLlmData) {
            throw new Error('Invalid Retell agent JSON format');
        }

        const agentData = {
            name: jsonData.agent_name || 'Imported Agent',
            agent_name: 'sarah',
            system_prompt: jsonData.retellLlmData?.general_prompt || jsonData.system_prompt || '',
            llm_model: jsonData.retellLlmData?.model || 'gpt-4o',
            voice: 'ara',
            language: 'multi',
            tts_provider: 'xai',
            tts_model: 'grok-voice-think-fast-1.0',
            max_call_duration: Math.floor((jsonData.max_call_duration_ms || 3600000) / 1000),
            welcome_message_type: 'agent_greets', // Always greet first for better responsiveness
            welcome_message: jsonData.begin_message || '',
            enable_recording: true,
            custom_params: {
                voice_runtime_mode: 'realtime_unified',
                voice_realtime_model: 'grok-voice-think-fast-1.0',
                welcome_message_mode: 'custom',
                interruption_sensitivity: jsonData.interruption_sensitivity || 0.8,
                llm_temperature: jsonData.voice_temperature || 0.2,
            }
        };

        const agentResponse = await fetch('/api/agents/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(agentData),
        });
        
        if (!agentResponse.ok) {
            const error = await agentResponse.json();
            throw new Error(error.detail || 'Failed to create agent');
        }
        
        const newAgent = await agentResponse.json();
        const agentId = newAgent.id;

        const tools = jsonData.retellLlmData?.general_tools || jsonData.tools || [];
        const builtinFunctions: any = {};
        let createdCount = 0;
        let failedCount = 0;

        for (const tool of tools) {
            const dest = tool.transfer_destination;
            const phone = (typeof dest === 'object' ? dest?.number : dest) || tool.phone_number || '';

            if (tool.type === 'transfer_call' || tool.type === 'agent_transfer') {
                // Always create as a System Function to support multiple transfer destinations
                const isAgentTransfer = tool.type === 'agent_transfer';
                const functionPayload = {
                    name: tool.name,
                    description: tool.description || (isAgentTransfer ? `Transfer to agent ${tool.agent_id || tool.target_agent_id}` : `Transfer call to ${phone}`),
                    url: isAgentTransfer ? 'builtin://agent_transfer' : 'builtin://transfer_call',
                    method: 'SYSTEM',
                    system_type: isAgentTransfer ? 'agent_transfer' : 'transfer_call',
                    system_config: isAgentTransfer ? { 
                        target_agent_id: tool.agent_id || tool.target_agent_id,
                        target_version_mode: 'latest'
                    } : { phone_number: phone },
                    phone_number: isAgentTransfer ? '' : phone, // Set at top level for agent runtime reliability
                    parameters_schema: { type: 'object', properties: {} },
                    speak_during_execution: true,
                    speak_after_execution: false,
                };
                console.log(`[Import] Creating transfer function: ${tool.name}`, functionPayload);
                const fnResp = await fetch(`/api/agents/${agentId}/functions`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(functionPayload),
                });
                if (fnResp.ok) {
                    createdCount++;
                    console.log(`[Import] Created transfer function: ${tool.name}`);
                } else {
                    failedCount++;
                    const errText = await fnResp.text();
                    console.warn(`[Import] FAILED transfer function ${tool.name}: ${fnResp.status} ${errText}`);
                }
            } else if (tool.type === 'end_call') {
                builtinFunctions['builtin_end_call'] = {
                    enabled: true,
                    config: {},
                    speak_during_execution: false,
                    speak_after_execution: true,
                };
                createdCount++;
                console.log(`[Import] Registered builtin end_call`);
            } else if (tool.type === 'custom' || !tool.type) {
                // Explicit custom tool handling with correct field mapping from Retell format
                const functionPayload = {
                    name: tool.name || 'custom_tool',
                    description: tool.description || '',
                    url: tool.url || tool.webhook_url || '',
                    method: (tool.method || 'POST').toUpperCase(),
                    timeout_ms: tool.timeout_ms || 120000,
                    headers: tool.headers || {},
                    query_params: tool.query_params || {},
                    parameters_schema: tool.parameters || tool.parameters_schema || { type: 'object', properties: {} },
                    variables: tool.variables || {},
                    speak_during_execution: tool.speak_during_execution !== undefined ? tool.speak_during_execution : false,
                    speak_after_execution: tool.speak_after_execution !== undefined ? tool.speak_after_execution : true,
                };
                console.log(`[Import] Creating custom function: ${tool.name}`, functionPayload);
                const fnResp = await fetch(`/api/agents/${agentId}/functions`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(functionPayload),
                });
                if (fnResp.ok) {
                    createdCount++;
                    console.log(`[Import] Created custom function: ${tool.name}`);
                } else {
                    failedCount++;
                    const errText = await fnResp.text();
                    console.warn(`[Import] FAILED custom function ${tool.name}: ${fnResp.status} ${errText}`);
                }
            } else {
                // Fallback: treat any other tool type as custom with same mapping
                console.warn(`[Import] Unknown tool type "${tool.type}" for ${tool.name}, treating as custom.`);
                const functionPayload = {
                    name: tool.name || 'custom_tool',
                    description: tool.description || '',
                    url: tool.url || tool.webhook_url || '',
                    method: (tool.method || 'POST').toUpperCase(),
                    timeout_ms: tool.timeout_ms || 120000,
                    headers: tool.headers || {},
                    query_params: tool.query_params || {},
                    parameters_schema: tool.parameters || tool.parameters_schema || { type: 'object', properties: {} },
                    variables: tool.variables || {},
                    speak_during_execution: tool.speak_during_execution !== undefined ? tool.speak_during_execution : false,
                    speak_after_execution: tool.speak_after_execution !== undefined ? tool.speak_after_execution : true,
                };
                console.log(`[Import] Creating fallback function: ${tool.name}`, functionPayload);
                const fnResp = await fetch(`/api/agents/${agentId}/functions`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(functionPayload),
                });
                if (fnResp.ok) {
                    createdCount++;
                    console.log(`[Import] Created fallback function: ${tool.name}`);
                } else {
                    failedCount++;
                    const errText = await fnResp.text();
                    console.warn(`[Import] FAILED fallback function ${tool.name}: ${fnResp.status} ${errText}`);
                }
            }
        }

        if (Object.keys(builtinFunctions).length > 0) {
            await fetch(`/api/agents/${agentId}/builtin-functions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(builtinFunctions),
            });
        }

        return { agent: newAgent, createdCount, failedCount };
    };

    const handleImport = async () => {
        if (!selectedFile) {
            showToast('Please select a file first', 'error');
            return;
        }
        
        try {
            if (selectedFile.name.endsWith('.json')) {
                const text = await selectedFile.text();
                const jsonData = JSON.parse(text);
                
                showToast(`Importing agent: ${jsonData.agent_name || selectedFile.name}...`, 'info');
                
                const result = await importRetellAgent(jsonData);
                
                if (result.failedCount > 0) {
                    showToast(`Agent imported with ${result.createdCount} tools created, ${result.failedCount} failed. Check browser console for details.`, 'info');
                } else {
                    showToast(`Agent imported successfully with ${result.createdCount} tools!`, 'success');
                }
                onClose();
                setSelectedFile(null);
                // Force a page refresh to show the new agent
                window.location.reload();
            } else {
                showToast('CSV import is not yet implemented. Please use JSON.', 'error');
            }
        } catch (error: any) {
            console.error('Import failed:', error);
            showToast(`Import failed: ${error.message}`, 'error');
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                    <h2 className="text-lg font-semibold text-gray-900">Import Agents</h2>
                    <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
                        <X className="w-5 h-5 text-gray-400" />
                    </button>
                </div>

                <div className="p-6">
                    <div
                        onDragEnter={handleDrag}
                        onDragLeave={handleDrag}
                        onDragOver={handleDrag}
                        onDrop={handleDrop}
                        className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                            dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
                        }`}
                    >
                        <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
                        <p className="text-sm text-gray-600 mb-2">
                            Drag and drop your file here, or{' '}
                            <label className="text-blue-600 hover:text-blue-700 cursor-pointer">
                                browse
                                <input
                                    type="file"
                                    className="hidden"
                                    accept=".json,.csv"
                                    onChange={handleFileSelect}
                                />
                            </label>
                        </p>
                        <p className="text-xs text-gray-400">Supports JSON and CSV files</p>
                    </div>

                    {selectedFile && (
                        <div className="mt-4 p-3 bg-gray-50 rounded-lg flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                {selectedFile.name.endsWith('.json') ? (
                                    <FileJson className="w-5 h-5 text-blue-500" />
                                ) : (
                                    <FileSpreadsheet className="w-5 h-5 text-green-500" />
                                )}
                                <span className="text-sm text-gray-700">{selectedFile.name}</span>
                            </div>
                            <button 
                                onClick={() => setSelectedFile(null)}
                                className="p-1 hover:bg-gray-200 rounded"
                            >
                                <X className="w-4 h-4 text-gray-400" />
                            </button>
                        </div>
                    )}

                    <div className="mt-6 flex gap-3">
                        <button
                            onClick={onClose}
                            className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleImport}
                            disabled={!selectedFile}
                            className="flex-1 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Import
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}