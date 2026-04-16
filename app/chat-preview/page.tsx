'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { buildEmbed, initialConfig, mergeConfig, STORAGE_KEY } from '../chatbot-dashboard/page';

export default function ChatPreviewPage() {
    const [embedHtml, setEmbedHtml] = useState(() => buildEmbed(initialConfig));
    const [status, setStatus] = useState('Showing latest saved chat config');

    const srcDoc = useMemo(
        () =>
            `<!doctype html><html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" /><title>Chat Preview</title><style>html,body{margin:0;height:100%;background:linear-gradient(180deg,#f8faff,#eef3ff);font-family:Inter,Segoe UI,sans-serif;}body{min-height:100vh;}</style></head><body>${embedHtml}</body></html>`,
        [embedHtml],
    );

    const loadPreview = useCallback(() => {
        try {
            const raw = window.localStorage.getItem(STORAGE_KEY);
            if (!raw) {
                setEmbedHtml(buildEmbed(initialConfig));
                setStatus('Showing default chat config');
                return;
            }

            const saved = JSON.parse(raw);
            const config = mergeConfig(initialConfig, saved);
            setEmbedHtml(buildEmbed(config));
            setStatus('Showing latest saved chat config');
        } catch {
            setEmbedHtml(buildEmbed(initialConfig));
            setStatus('Saved config was invalid, using defaults');
        }
    }, []);

    useEffect(() => {
        loadPreview();

        const handleStorage = (event: StorageEvent) => {
            if (event.key && event.key !== STORAGE_KEY) return;
            loadPreview();
        };

        window.addEventListener('storage', handleStorage);
        return () => window.removeEventListener('storage', handleStorage);
    }, [loadPreview]);

    return (
        <main className="min-h-screen bg-[linear-gradient(180deg,#f8faff,#eef3ff)] p-6">
            <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Chat Preview</p>
                    <h1 className="text-xl font-semibold text-slate-900">Live Widget Preview</h1>
                    <p className="text-sm text-slate-500">{status}</p>
                </div>
                <button
                    type="button"
                    onClick={loadPreview}
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                    <RefreshCw className="h-4 w-4" />
                    Refresh Preview
                </button>
            </div>

            <div className="mx-auto mt-6 max-w-6xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.08)]">
                <iframe
                    title="Chat Preview"
                    srcDoc={srcDoc}
                    className="h-[calc(100vh-170px)] min-h-[720px] w-full border-0"
                />
            </div>
        </main>
    );
}
