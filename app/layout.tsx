import type { Metadata } from 'next';
import './globals.css';
import AppWrapper from './components/AppWrapper';

export const metadata: Metadata = {
    title: 'Oyik Voice & Chat AI',
    description: 'Build and deploy AI voice and chat agents',
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body className="bg-gray-50">
                <AppWrapper>{children}</AppWrapper>
            </body>
        </html>
    );
}
