'use client';

import { useToast } from '../../components/ToastProvider';

export default function KnowledgeBasePage() {
    const { showToast } = useToast();

    return (
        <div className="min-h-screen bg-gray-50" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
            {/* Main Content */}
            <main className="flex flex-col bg-gray-50 min-w-0">
                {/* Header */}
                <header className="bg-white border-b border-gray-200 px-4 md:px-6 py-3 md:py-4">
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 md:gap-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 md:gap-4">
                                <h1 className="text-lg md:text-xl font-semibold text-gray-900">Knowledge Base</h1>
                            </div>
                        </div>

                        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3">
                            {/* Upload Button */}
                            <button
                                onClick={() => showToast('File upload coming soon!', 'info')}
                                className="flex items-center justify-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors"
                            >
                                <span>Upload Documents</span>
                            </button>
                        </div>
                    </div>
                </header>

                {/* Content */}
                <div className="flex-1 p-6 overflow-auto">
                    <div className="bg-white rounded-xl border border-gray-200 p-8">
                        <div className="text-center py-12">
                            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-400">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                    <polyline points="14 2 14 8 20 8"></polyline>
                                    <line x1="16" y1="13" x2="8" y2="13"></line>
                                    <line x1="16" y1="17" x2="8" y2="17"></line>
                                    <polyline points="10 9 9 9 8 9"></polyline>
                                </svg>
                            </div>
                            <h2 className="text-lg font-medium text-gray-900 mb-2">No Documents Yet</h2>
                            <p className="text-gray-500 mb-6">Upload documents to enhance your agents with knowledge</p>

                            <div className="flex justify-center gap-4">
                                <button
                                    onClick={() => showToast('File upload coming soon!', 'info')}
                                    className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
                                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                        <polyline points="17 8 12 3 7 8"></polyline>
                                        <line x1="12" y1="3" x2="12" y2="15"></line>
                                    </svg>
                                    Upload Documents
                                </button>
                            </div>
                        </div>

                        <div className="mt-8 p-4 bg-blue-50 rounded-lg">
                            <h3 className="text-sm font-medium text-blue-900 mb-2">Supported Formats</h3>
                            <p className="text-sm text-blue-700">PDF, DOCX, TXT, MD - Max 10MB per file</p>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}