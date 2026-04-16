'use client';

import { usePathname } from 'next/navigation';
import { ToastProvider } from '../../components/ToastProvider';
import Sidebar from '../../components/Sidebar';

export default function AppWrapper({ children }: { children: React.ReactNode }) {
    const pathname = usePathname();
    const isLoginPage = pathname === '/login';
    const isChatPage =
        pathname === '/chat' ||
        pathname === '/chat-preview' ||
        pathname === '/chatbot-dashboard';
    const isAgentPage = pathname.startsWith('/agent/');
    const isMainDashboard = pathname === '/';

    if (isLoginPage || isChatPage || isAgentPage || isMainDashboard) {
        return (
            <ToastProvider>
                {children}
            </ToastProvider>
        );
    }

    return (
        <ToastProvider>
            <Sidebar />
            <div className="lg:ml-60 min-h-screen">
                <div className="p-6">
                    {children}
                </div>
            </div>
        </ToastProvider>
    );
}
