'use client';

import { useEffect, useState, type FormEvent } from 'react';
import axios from 'axios';
import { Loader2, PhoneCall, PhoneForwarded, X } from 'lucide-react';
import { useToast } from './ToastProvider';

const API_URL = '/api/';

interface CallTransferFunctionModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentId: number;
  functionData?: CallTransferFunctionData | null;
  onSuccess?: () => void;
}

export interface CallTransferFunctionData {
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
    phone_number?: string;
  } | null;
}

const DEFAULT_FUNCTION: CallTransferFunctionData = {
  name: 'Call Transfer',
  description: '',
  method: 'SYSTEM',
  url: 'builtin://transfer_call',
  timeout_ms: 15000,
  headers: {},
  query_params: {},
  parameters_schema: {
    type: 'object',
    properties: {},
  },
  variables: {},
  speak_during_execution: true,
  speak_after_execution: false,
  system_type: 'transfer_call',
  system_config: {
    phone_number: '',
  },
};

const normalizeSpeechFlags = (
  value: Pick<CallTransferFunctionData, 'speak_during_execution' | 'speak_after_execution'>
) => {
  const during = Boolean(value.speak_during_execution);
  const after = Boolean(value.speak_after_execution);
  if ((during && !after) || (!during && after)) {
    return { speak_during_execution: during, speak_after_execution: after };
  }
  return { speak_during_execution: true, speak_after_execution: false };
};

const normalizeSystemConfig = (value?: CallTransferFunctionData['system_config']) => {
  return {
    phone_number: value?.phone_number || '',
  };
};

export default function CallTransferFunctionModal({
  isOpen,
  onClose,
  agentId,
  functionData,
  onSuccess,
}: CallTransferFunctionModalProps) {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<CallTransferFunctionData>(DEFAULT_FUNCTION);

  // Convert a DB-normalized underscore name (e.g. "sales_transfer") to
  // a display-friendly Title Case label (e.g. "Sales Transfer") for the form.
  const toDisplayName = (raw: string): string =>
    (raw || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  useEffect(() => {
    if (!isOpen) return;
    if (functionData) {
      const displayName = toDisplayName(functionData.name || '');
      setFormData({
        ...DEFAULT_FUNCTION,
        ...functionData,
        name: displayName,
        ...normalizeSpeechFlags(functionData),
        system_type: 'transfer_call',
        method: 'SYSTEM',
        url: 'builtin://transfer_call',
        system_config: normalizeSystemConfig(functionData.system_config),
      });
    } else {
      setFormData(DEFAULT_FUNCTION);
    }
  }, [functionData, isOpen]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const systemConfig = normalizeSystemConfig(formData.system_config);
    if (!formData.name.trim()) {
      showToast('Please enter a tool name', 'error');
      return;
    }
    if (!systemConfig.phone_number) {
      showToast('Please enter a target phone number', 'error');
      return;
    }

    setLoading(true);
    try {
      const speechFlags = normalizeSpeechFlags(formData);
      const payload = {
        name: formData.name.trim(),
        description: formData.description?.trim() || '',
        method: 'SYSTEM',
        url: 'builtin://transfer_call',
        timeout_ms: formData.timeout_ms || 15000,
        headers: {},
        query_params: {},
        parameters_schema: {
          type: 'object',
          properties: {},
        },
        variables: {},
        system_type: 'transfer_call',
        system_config: systemConfig,
        ...speechFlags,
      };

      if (functionData?.id) {
        await axios.patch(`${API_URL}agents/${agentId}/functions/${functionData.id}`, payload);
        showToast('Call transfer tool updated', 'success');
      } else {
        await axios.post(`${API_URL}agents/${agentId}/functions`, payload);
        showToast('Call transfer tool created', 'success');
      }

      onSuccess?.();
      onClose();
    } catch (error: any) {
      console.error('Failed to save call transfer tool:', error);
      showToast(error?.response?.data?.detail || 'Failed to save call transfer tool', 'error');
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
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-green-100">
              <PhoneForwarded className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {functionData?.id ? 'Edit Call Transfer' : 'Call Transfer'}
              </h2>
              <p className="text-sm text-gray-500">
                Create a named handoff tool that switches the live phone call to an external phone number.
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
            <div className="rounded-xl border border-green-200 bg-green-50 p-4">
              <div className="flex items-start gap-3">
                <PhoneCall className="mt-0.5 h-4 w-4 text-green-600" />
                <div>
                  <p className="text-sm font-medium text-green-900">Phone calls only</p>
                  <p className="mt-1 text-xs text-green-700">
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
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-green-500 focus:outline-none"
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
                className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-green-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Target Phone Number</label>
              <input
                type="tel"
                value={formData.system_config?.phone_number || ''}
                onChange={(event) => setFormData((prev) => ({
                  ...prev,
                  system_config: { phone_number: event.target.value }
                }))}
                placeholder="+1234567890"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:border-green-500 focus:outline-none"
                required
              />
              <p className="mt-1 text-xs text-gray-500">
                Enter the destination number in E.164 format.
              </p>
            </div>

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
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-green-500 focus:outline-none"
              >
                <option value="during">Speak During Execution</option>
                <option value="after">Speak After Execution</option>
              </select>
              <p className="mt-2 text-xs text-gray-500">
                During: announce the handoff before switching. After: switch first.
              </p>
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
              className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <PhoneForwarded className="h-4 w-4" />}
              {functionData?.id ? 'Save Call Transfer' : 'Create Call Transfer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
