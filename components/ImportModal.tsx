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

    const handleImport = () => {
        if (!selectedFile) {
            showToast('Please select a file first', 'error');
            return;
        }
        
        showToast(`Importing ${selectedFile.name}...`, 'info');
        setTimeout(() => {
            showToast('Import completed successfully!', 'success');
            onClose();
            setSelectedFile(null);
        }, 2000);
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