'use client';

import { createContext, useContext, useState, useCallback } from 'react';
import { Check, AlertCircle, Info, X } from 'lucide-react';

interface Toast {
    id: string;
    message: string;
    type: 'success' | 'error' | 'info';
}

interface ToastContextType {
    showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const showToast = useCallback((message: string, type: 'success' | 'error' | 'info' = 'info') => {
        const id = Date.now().toString();
        setToasts(prev => [...prev, { id, message, type }]);
        
        setTimeout(() => {
            setToasts(prev => prev.filter(t => t.id !== id));
        }, 3000);
    }, []);

    return (
        <ToastContext.Provider value={{ showToast }}>
            {children}
            <div className="fixed bottom-4 right-4 z-50 space-y-2">
                {toasts.map(toast => (
                    <div
                        key={toast.id}
                        className={`flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-sm font-medium animate-in slide-in-from-right ${
                            toast.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' :
                            toast.type === 'error' ? 'bg-red-50 text-red-800 border border-red-200' :
                            'bg-blue-50 text-blue-800 border border-blue-200'
                        }`}
                    >
                        {toast.type === 'success' && <Check className="w-4 h-4" />}
                        {toast.type === 'error' && <AlertCircle className="w-4 h-4" />}
                        {toast.type === 'info' && <Info className="w-4 h-4" />}
                        {toast.message}
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
}

export function useToast() {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within ToastProvider');
    }
    return context;
}