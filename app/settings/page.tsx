'use client';

import Link from 'next/link';
import {
    Bot, BookOpen, Phone, PhoneCall, History, MessageSquare,
    BarChart3, Settings, Key, Sparkles,
    User, CreditCard, Bell, Shield, Webhook
} from 'lucide-react';
import { useToast } from '../../components/ToastProvider';

export default function SettingsPage() {
    const { showToast } = useToast();

    return (
        <div className="min-h-screen bg-gray-50" style={{ fontFamily: 'Inter, system-ui, sans-serif' }}>
            <main>
                <div className="max-w-4xl mx-auto">
                    <div className="flex items-center gap-3 mb-8">
                        <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                            <Settings className="w-5 h-5 text-gray-600" />
                        </div>
                        <h1 className="text-2xl font-semibold text-gray-900">Settings</h1>
                    </div>

                    <div className="space-y-4">
                        <button
                            onClick={() => showToast('Account settings - Coming soon!', 'info')}
                            className="w-full flex items-center gap-4 p-4 bg-white rounded-xl border border-gray-200 hover:border-gray-300 transition-all text-left"
                        >
                            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                                <User className="w-5 h-5 text-blue-600" />
                            </div>
                            <div className="flex-1">
                                <h3 className="font-medium text-gray-900">Account</h3>
                                <p className="text-sm text-gray-500">Manage your profile and preferences</p>
                            </div>
                        </button>

                        <button
                            onClick={() => showToast('Billing settings - Coming soon!', 'info')}
                            className="w-full flex items-center gap-4 p-4 bg-white rounded-xl border border-gray-200 hover:border-gray-300 transition-all text-left"
                        >
                            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                                <CreditCard className="w-5 h-5 text-green-600" />
                            </div>
                            <div className="flex-1">
                                <h3 className="font-medium text-gray-900">Billing</h3>
                                <p className="text-sm text-gray-500">Manage payment methods and invoices</p>
                            </div>
                        </button>

                        <button
                            onClick={() => showToast('Notification settings - Coming soon!', 'info')}
                            className="w-full flex items-center gap-4 p-4 bg-white rounded-xl border border-gray-200 hover:border-gray-300 transition-all text-left"
                        >
                            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                                <Bell className="w-5 h-5 text-purple-600" />
                            </div>
                            <div className="flex-1">
                                <h3 className="font-medium text-gray-900">Notifications</h3>
                                <p className="text-sm text-gray-500">Configure alert preferences</p>
                            </div>
                        </button>

                        <button
                            onClick={() => showToast('Security settings - Coming soon!', 'info')}
                            className="w-full flex items-center gap-4 p-4 bg-white rounded-xl border border-gray-200 hover:border-gray-300 transition-all text-left"
                        >
                            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
                                <Shield className="w-5 h-5 text-red-600" />
                            </div>
                            <div className="flex-1">
                                <h3 className="font-medium text-gray-900">Security</h3>
                                <p className="text-sm text-gray-500">Manage passwords and 2FA</p>
                            </div>
                        </button>

                        <button
                            onClick={() => showToast('Integrations - Coming soon!', 'info')}
                            className="w-full flex items-center gap-4 p-4 bg-white rounded-xl border border-gray-200 hover:border-gray-300 transition-all text-left"
                        >
                            <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                                <Webhook className="w-5 h-5 text-orange-600" />
                            </div>
                            <div className="flex-1">
                                <h3 className="font-medium text-gray-900">Integrations</h3>
                                <p className="text-sm text-gray-500">Connect with CRM and other tools</p>
                            </div>
                        </button>
                    </div>
                </div>
            </main>
        </div>
    );
}