'use client';

import { useEffect, useMemo, useState, type FormEvent } from 'react';
import axios from 'axios';
import { ArrowRightLeft, Bot, Loader2, PhoneCall, X } from 'lucide-react';
import { useToast } from './ToastProvider';

const API_URL = '/api/';

interface AgentTransferFunctionModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentId: number;
  functionData?: AgentTransferFunctionData | null;
  onSuccess?: () => void;
}

export interface AgentTransferFunctionData {
  id?: number;
  name: string;
  description: string | null;
  method: string;
  url: string;
  timeout_ms: number;
  headers: Record<string, string>;
  query_params: Record<string, string>;
  parameters_schema: Record<string, any>;
  variables: Record<string, any>;
  speak_during_execution: boolean;
  speak_after_execution: boolean;
  system_type?: string | null;
  system_config?: {
    target_agent_id?: number;
    target_version_mode?: 'latest' | 'pinned' | string;
    target_version?: number;
  } | null;
}

interface SimpleAgent {
  id: number;
  name: string;
}

interface AgentVersion {
  version: number;
  published_at?: string;
}

const DEFAULT_FUNCTION: AgentTransferFunctionData = {
  name: '',
  description: '',
  method: 'SYSTEM',
  url: 'builtin://agent_transfer',
  timeout_ms: 15000,
  headers: {},
  query_params: {},
  parameters_schema: {
    type: 'object',
    properties: {},
  },
  variables: {},
  speak_during_execution: false,
  speak_after_execution: true,
  system_type: 'agent_transfer',
  system_config: {
    target_version_mode: 'latest',
  },
};

const normalizeSpeechFlags = (
  value: Pick<AgentTransferFunctionData, 'speak_during_execution' | 'speak_after_execution'>
) => {
  const during = Boolean(value.speak_during_execution);
  const after = Boolean(value.speak_after_execution);
  if ((during && !after) || (!during && after)) {
    return { speak_during_execution: during, speak_after_execution: after };
  }
  return { speak_during_execution: false, speak_after_execution: true };
};

const normalizeSystemConfig = (value?: AgentTransferFunctionData['system_config']) => {
  const targetAgentId = Number(value?.target_agent_id || 0) || undefined;
  const targetVersionMode = value?.target_version_mode === 'pinned' ? 'pinned' : 'latest';
  const targetVersion = value?.target_version !== undefined && value?.target_version !== null
    ? Number(value.target_version) || undefined
    : undefined;

  return {
    target_agent_id: targetAgentId,
    target_version_mode: targetVersionMode,
    ...(targetVersionMode === 'pinned' && targetVersion ? { target_version: targetVersion } : {}),
  };
};

const formatPublishedAt = (value?: string) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
};

export default function AgentTransferFunctionModal({
  isOpen,
  onClose,
  agentId,
  functionData,
  onSuccess,
}: AgentTransferFunctionModalProps) {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [agents, setAgents] = useState<SimpleAgent[]>([]);
  const [versions, setVersions] = useState<AgentVersion[]>([]);
  const [formData, setFormData] = useState<AgentTransferFunctionData>(DEFAULT_FUNCTION);

  const targetAgentId = Number(formData.system_config?.target_agent_id || 0) || 0;
  const targetVersionMode = formData.system_config?.target_version_mode === 'pinned' ? 'pinned' : 'latest';

  const targetAgentLabel = useMemo(
    () => agents.find((agent) => agent.id === targetAgentId)?.name || '',
    [agents, targetAgentId]
  );

  useEffect(() => {
    if (!isOpen) return;
    const nextData = functionData
      ? {
          ...DEFAULT_FUNCTION,
          ...functionData,
          ...normalizeSpeechFlags(functionData),
          system_type: 'agent_transfer',
          method: 'SYSTEM',
          url: 'builtin://agent_transfer',
          system_config: normalizeSystemConfig(functionData.system_config),
        }
      : DEFAULT_FUNCTION;
    setFormData(nextData);
  }, [functionData, isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    let ignore = false;

    const run = async () => {
      setLoadingAgents(true);
      try {
        const res = await axios.get<SimpleAgent[]>(`${API_URL}agents/list-simple`);
        if (ignore) return;
        const availableAgents = (res.data || []).filter((agent) => agent.id !== agentId);
        setAgents(availableAgents);
      } catch (error) {
        if (!ignore) {
          console.error('Failed to load agent transfer targets:', error);
          showToast('Failed to load agents for transfer', 'error');
        }
      } finally {
        if (!ignore) setLoadingAgents(false);
      }
    };

    void run();
    return () => {
      ignore = true;
    };
  }, [agentId, isOpen, showToast]);

  useEffect(() => {
    if (!isOpen || !targetAgentId) {
      setVersions([]);
      return;
    }

    let ignore = false;
    const run = async () => {
      setLoadingVersions(true);
      try {
        const res = await axios.get<{ versions?: AgentVersion[] }>(`${API_URL}agents/${targetAgentId}/versions`);
        if (ignore) return;
        setVersions(Array.isArray(res.data?.versions) ? res.data.versions : []);
      } catch (error) {
        if (!ignore) {
          console.error('Failed to load target agent versions:', error);
          setVersions([]);
        }
      } finally {
        if (!ignore) setLoadingVersions(false);
      }
    };

    void run();
    return () => {
      ignore = true;
    };
  }, [isOpen, targetAgentId]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const systemConfig = normalizeSystemConfig(formData.system_config);
    if (!formData.name.trim()) {
      showToast('Please enter a tool name', 'error');
      return;
    }
    if (!systemConfig.target_agent_id) {
      showToast('Please choose a target agent', 'error');
      return;
    }
    if (systemConfig.target_version_mode === 'pinned' && !systemConfig.target_version) {
      showToast('Please choose a published target version', 'error');
      return;
    }

    setLoading(true);
    try {
      const speechFlags = normalizeSpeechFlags(formData);
      const payload = {
        name: formData.name.trim(),
        description: formData.description?.trim() || '',
        method: 'SYSTEM',
        url: 'builtin://agent_transfer',
        timeout_ms: formData.timeout_ms || 15000,
        headers: {},
        query_params: {},
        parameters_schema: {
          type: 'object',
          properties: {},
        },
        variables: {},
        system_config: systemConfig,
        ...speechFlags,
      };

      if (functionData?.id) {
        await axios.patch(`${API_URL}agents/${agentId}/functions/${functionData.id}`, payload);
        showToast('Agent transfer tool updated', 'success');
      } else {
        await axios.post(`${API_URL}agents/${agentId}/functions`, payload);
        showToast('Agent transfer tool created', 'success');
      }

      onSuccess?.();
      onClose();
    } catch (error: any) {
      console.error('Failed to save agent transfer tool:', error);
      showToast(error?.response?.data?.detail || 'Failed to save agent transfer tool', 'error');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="w-full max-w-2xl overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-100">
              <ArrowRightLeft className="h-5 w-5 text-violet-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {functionData?.id ? 'Edit Agent Transfer' : 'Agent Transfer'}
              </h2>
              <p className="text-sm text-gray-500">
                Create a named handoff tool that switches the live phone call to another agent.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="max-h-[90vh] overflow-y-auto">
          <div className="space-y-6 p-6">
            <div className="rounded-xl border border-violet-200 bg-violet-50 p-4">
              <div className="flex items-start gap-3">
                <PhoneCall className="mt-0.5 h-4 w-4 text-violet-600" />
                <div>
                  <p className="text-sm font-medium text-violet-900">Phone calls only</p>
                  <p className="mt-1 text-xs text-violet-700">
                    This tool is available during live phone calls. Web test chat and web calls return a phone-only result.
                  </p>
                </div>
              </div>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Tool Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(event) => setFormData((prev) => ({ ...prev, name: event.target.value }))}
                placeholder="e.g. billing_handoff"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-violet-500 focus:outline-none"
                required
              />
              <p className="mt-1 text-xs text-gray-500">
                Use a clear tool name so your prompt can say exactly when to call it.
              </p>
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
              <textarea
                rows={3}
                value={formData.description || ''}
                onChange={(event) => setFormData((prev) => ({ ...prev, description: event.target.value }))}
                placeholder="Explain when this handoff should be used."
                className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-violet-500 focus:outline-none"
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Target Agent</label>
                <div className="relative">
                  <select
                    value={targetAgentId || ''}
                    onChange={(event) => {
                      const nextTargetId = Number(event.target.value) || undefined;
                      setFormData((prev) => ({
                        ...prev,
                        system_config: {
                          target_agent_id: nextTargetId,
                          target_version_mode: 'latest',
                        },
                      }));
                    }}
                    disabled={loadingAgents}
                    className="w-full appearance-none rounded-lg border border-gray-300 bg-white px-3 py-2 pr-10 text-sm text-gray-900 focus:border-violet-500 focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-50"
                    required
                  >
                    <option value="">Select target agent</option>
                    {agents.map((agent) => (
                      <option key={agent.id} value={agent.id}>
                        {agent.name}
                      </option>
                    ))}
                  </select>
                  {loadingAgents && <Loader2 className="pointer-events-none absolute right-3 top-2.5 h-4 w-4 animate-spin text-gray-400" />}
                </div>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Target Version</label>
                <select
                  value={targetVersionMode}
                  onChange={(event) => {
                    const nextMode = event.target.value === 'pinned' ? 'pinned' : 'latest';
                    setFormData((prev) => ({
                      ...prev,
                      system_config: {
                        ...(prev.system_config || {}),
                        target_agent_id: Number(prev.system_config?.target_agent_id || 0) || undefined,
                        target_version_mode: nextMode,
                        ...(nextMode === 'pinned' && prev.system_config?.target_version
                          ? { target_version: prev.system_config.target_version }
                          : {}),
                      },
                    }));
                  }}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-violet-500 focus:outline-none"
                  disabled={!targetAgentId}
                >
                  <option value="latest">Latest published/live draft</option>
                  <option value="pinned" disabled={versions.length === 0}>
                    Published version
                  </option>
                </select>
              </div>
            </div>

            {targetVersionMode === 'pinned' && (
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Published Snapshot</label>
                <div className="relative">
                  <select
                    value={formData.system_config?.target_version || ''}
                    onChange={(event) => {
                      const nextVersion = Number(event.target.value) || undefined;
                      setFormData((prev) => ({
                        ...prev,
                        system_config: {
                          ...(prev.system_config || {}),
                          target_version_mode: 'pinned',
                          target_version: nextVersion,
                        },
                      }));
                    }}
                    disabled={!targetAgentId || loadingVersions || versions.length === 0}
                    className="w-full appearance-none rounded-lg border border-gray-300 bg-white px-3 py-2 pr-10 text-sm text-gray-900 focus:border-violet-500 focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-50"
                    required={targetVersionMode === 'pinned'}
                  >
                    <option value="">Select published version</option>
                    {versions.map((version) => (
                      <option key={version.version} value={version.version}>
                        {`v${version.version}${version.published_at ? ` • ${formatPublishedAt(version.published_at)}` : ''}`}
                      </option>
                    ))}
                  </select>
                  {loadingVersions && <Loader2 className="pointer-events-none absolute right-3 top-2.5 h-4 w-4 animate-spin text-gray-400" />}
                </div>
                {versions.length === 0 && !loadingVersions && (
                  <p className="mt-1 text-xs text-amber-600">
                    No published snapshots found for this target yet. Publish the target agent first to pin a version.
                  </p>
                )}
              </div>
            )}

            <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
              <label className="mb-2 block text-sm font-medium text-gray-700">Tool Speech Mode</label>
              <select
                value={formData.speak_during_execution ? 'during' : 'after'}
                onChange={(event) => {
                  const nextMode = event.target.value === 'during' ? 'during' : 'after';
                  setFormData((prev) => ({
                    ...prev,
                    speak_during_execution: nextMode === 'during',
                    speak_after_execution: nextMode === 'after',
                  }));
                }}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-violet-500 focus:outline-none"
              >
                <option value="during">Speak During Execution</option>
                <option value="after">Speak After Execution</option>
              </select>
              <p className="mt-2 text-xs text-gray-500">
                During: announce the handoff before switching. After: switch first, then let the new agent greet.
              </p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
              <div className="flex items-start gap-3">
                <Bot className="mt-0.5 h-4 w-4 text-gray-500" />
                <div>
                  <p className="text-sm font-medium text-gray-800">Current target</p>
                  <p className="mt-1 text-sm text-gray-600">
                    {targetAgentLabel
                      ? `${targetAgentLabel}${targetVersionMode === 'pinned' && formData.system_config?.target_version ? ` • v${formData.system_config.target_version}` : ' • latest'}`
                      : 'Choose a target agent to finish this tool.'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 border-t border-gray-200 px-6 py-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRightLeft className="h-4 w-4" />}
              {functionData?.id ? 'Save Agent Transfer' : 'Create Agent Transfer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
