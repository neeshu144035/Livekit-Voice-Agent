'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';
import { AlertCircle, X } from 'lucide-react';

interface LLMStatus {
  quota_errors: Array<{
    agent_id: number;
    agent_name: string;
    llm_model: string;
    error: string;
    timestamp: string;
  }>;
  models_in_use: string[];
  has_quota_error: boolean;
}

export default function LLMStatusBanner() {
  const [status, setStatus] = useState<LLMStatus | null>(null);
  const [isVisible, setIsVisible] = useState(true);
  const [isLoading, setIsLoading] = useState(true);

  const fetchStatus = async () => {
    try {
      const res = await axios.get('/api/system/llm-status');
      setStatus(res.data);
    } catch (err) {
      console.error('Failed to fetch LLM status:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    // Check every 30 seconds
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  if (isLoading || !status || !status.has_quota_error || !isVisible) {
    return null;
  }

  // Get unique models with errors
  const errorModels = [...new Set(status.quota_errors.map(e => e.llm_model))];
  const modelNames = errorModels.map(model => {
    if (model.includes('gpt')) return 'OpenAI';
    if (model.includes('moonshot')) return 'Moonshot';
    if (model.includes('kimi')) return 'Kimi';
    return model;
  }).join(', ');

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-red-50 border-t border-red-200 px-4 py-3 z-50">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-red-800">
              Insufficient balance in {modelNames}
            </p>
            <p className="text-xs text-red-600 mt-0.5">
              AI responses may fail. Please check your billing settings or switch to a different model.
            </p>
          </div>
        </div>
        <button
          onClick={() => setIsVisible(false)}
          className="p-1 text-red-400 hover:text-red-600 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
