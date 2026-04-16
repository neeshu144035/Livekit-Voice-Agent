'use client';

import { useState } from 'react';
import { Copy, X, Loader2 } from 'lucide-react';

interface DuplicateAgentModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: (newName: string) => Promise<void>;
    originalAgentName: string;
    isLoading?: boolean;
}

export default function DuplicateAgentModal({
    isOpen,
    onClose,
    onConfirm,
    originalAgentName,
    isLoading = false
}: DuplicateAgentModalProps) {
    const [newName, setNewName] = useState('');

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (newName.trim()) {
            await onConfirm(newName.trim());
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[1000] p-4">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-2">
                        <Copy className="w-5 h-5 text-gray-700" />
                        <h2 className="text-lg font-semibold text-gray-900">
                            Duplicate Agent
                        </h2>
                    </div>
                    <button
                        onClick={onClose}
                        disabled={isLoading}
                        className="p-1 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
                    >
                        <X className="w-5 h-5 text-gray-500" />
                    </button>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            New Agent Name
                        </label>
                        <input
                            type="text"
                            value={newName}
                            onChange={(e) => setNewName(e.target.value)}
                            placeholder="Enter agent name..."
                            disabled={isLoading}
                            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                            autoFocus
                        />
                        <p className="text-xs text-gray-500 mt-2">
                            This will create a new agent with all settings copied from "{originalAgentName}"
                        </p>
                    </div>

                    <div className="flex gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            disabled={isLoading}
                            className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={!newName.trim() || isLoading}
                            className="flex-1 px-4 py-2.5 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Duplicating...
                                </>
                            ) : (
                                <>
                                    <Copy className="w-4 h-4" />
                                    Duplicate
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
