'use client';

import { usePathname } from 'next/navigation';
import { ToastProvider } from '../../components/ToastProvider';
import Sidebar from './Sidebar';

export default function AppWrapper({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const isLoginPage = pathname === '/login';
    const isChatPage =
        pathname === '/chat' ||
        pathname === '/chat-preview' ||
        pathname === '/chatbot-dashboard';
    const isAgentPage = pathname.startsWith('/agent/');

    if (isLoginPage || isChatPage || isAgentPage) {
        return (
            <ToastProvider>
                {children}
            </ToastProvider>
        );
    }

    return (
        <ToastProvider>
            <div className="h-screen flex overflow-hidden bg-gray-50">
                <Sidebar />
                <main className="flex-1 overflow-y-auto min-w-0">
                    {children}
                </main>
            </div>
        </ToastProvider>
    );
}
