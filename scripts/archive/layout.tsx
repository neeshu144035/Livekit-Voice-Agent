import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
    title: 'LiveKit SaaS Dashboard',
    description: 'Manage your AI voice agents',
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body>{children}</body>
        </html>
    );
}
