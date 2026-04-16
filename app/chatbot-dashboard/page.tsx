'use client';

import { Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { Copy, Download, Minus, Plus, RefreshCw, Smartphone } from 'lucide-react';

type Tab = 'general' | 'appearance' | 'behavior' | 'embed';
type ChatMode = 'webhook' | 'agent';
type IconKey = 'message' | 'spark' | 'bolt' | 'bot';
type PreviewMode = 'mobile' | 'web';
type FontFamilyKey = 'Inter' | 'Poppins' | 'Manrope' | 'Montserrat' | 'Lora';

type QuickReply = { id: number; icon: string; text: string };
type PropertyCard = {
  id: number;
  title: string;
  subtitle: string;
  price: string;
  imageUrl: string;
};
type Message = { id: number; text: string; user: boolean; properties?: PropertyCard[] };
type ParsedWebhook = { message: string; properties: PropertyCard[] };
type AgentSummary = {
  id: number;
  name: string;
  display_name?: string | null;
  welcome_message?: string | null;
  webhook_url?: string | null;
  custom_params?: Record<string, unknown>;
};
type ChatHistoryEntry = { role: 'user' | 'assistant'; content: string };

type Config = {
  chatMode: ChatMode;
  agentId: number | null;
  apiBaseUrl: string;
  webhookUrl: string;
  companyName: string;
  welcomeMessage: string;
  inputPlaceholder: string;
  sendLabel: string;
  launcherLabel: string;
  launcherIcon: IconKey;
  launcherIconUrl: string;
  headerIcon: IconKey;
  headerIconUrl: string;
  userMessageIcon: IconKey;
  userMessageIconUrl: string;
  aiMessageIcon: IconKey;
  aiMessageIconUrl: string;
  fontSize: number;
  fontFamily: FontFamilyKey;
  launcherSize: number;
  launcherRadius: number;
  widgetRadius: number;
  lineHeight: number;
  borderWidth: number;
  position: 'left' | 'right';
  bottom: string;
  autoOpen: boolean;
  colors: {
    primary: string;
    chatBackground: string;
    sendMessage: string;
    aiMessage: string;
    brandA: string;
    brandB: string;
    surface: string;
    botBubble: string;
    userBubble: string;
    page: string;
    text: string;
  };
  quickReplies: QuickReply[];
};

export const STORAGE_KEY = 'oyik_chatbot_dashboard_config_v1';

const ICONS: Record<IconKey, string> = {
  message:
    '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v8Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  spark:
    '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="m12 2 1.8 4.7L18.5 8 13.8 9.3 12 14l-1.8-4.7L5.5 8l4.7-1.3L12 2Zm7 11 1 2.6L22.6 16 20 16.7 19 19.3 18 16.7 15.4 16l2.6-.7L19 13Zm-14 2 1.2 3L9 19l-2.8.8L5 22.8l-1.2-3L1 19l2.8-.8L5 15Z" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  bolt:
    '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  bot:
    '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2v3M7 10h10a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2Zm-2 3H3m18 0h-2M9 14h.01M15 14h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
};

const FONT_FAMILY_OPTIONS: { key: FontFamilyKey; label: string; value: string }[] = [
  { key: 'Inter', label: 'Inter', value: 'Inter, Segoe UI, sans-serif' },
  { key: 'Poppins', label: 'Poppins', value: 'Poppins, Segoe UI, sans-serif' },
  { key: 'Manrope', label: 'Manrope', value: 'Manrope, Segoe UI, sans-serif' },
  { key: 'Montserrat', label: 'Montserrat', value: 'Montserrat, Segoe UI, sans-serif' },
  { key: 'Lora', label: 'Lora', value: 'Lora, Georgia, serif' },
];

export const initialConfig: Config = {
  chatMode: 'webhook',
  agentId: null,
  apiBaseUrl: '',
  webhookUrl: 'https://oyik.cloud/webhook/a05f977e-05e7-461d-a8a3-70f9c7c05025/chat',
  companyName: 'Ariya Property',
  welcomeMessage: 'Hello! Welcome to Ariya Property Services. How can I help you today?',
  inputPlaceholder: 'Type your message...',
  sendLabel: 'Send',
  launcherLabel: 'Chat',
  launcherIcon: 'message',
  launcherIconUrl: '',
  headerIcon: 'bot',
  headerIconUrl: '',
  userMessageIcon: 'spark',
  userMessageIconUrl: '',
  aiMessageIcon: 'bot',
  aiMessageIconUrl: '',
  fontSize: 14,
  fontFamily: 'Inter',
  launcherSize: 68,
  launcherRadius: 20,
  widgetRadius: 22,
  lineHeight: 1.4,
  borderWidth: 1,
  position: 'right',
  bottom: '28px',
  autoOpen: false,
  colors: {
    primary: '#ff6b35',
    chatBackground: '#171c36',
    sendMessage: '#ff6b35',
    aiMessage: 'rgba(255,255,255,0.12)',
    brandA: '#ff6b35',
    brandB: '#ff6b35',
    surface: '#171c36',
    botBubble: 'rgba(255,255,255,0.12)',
    userBubble: '#ff6b35',
    page: '#eef3ff',
    text: '#ffffff',
  },
  quickReplies: [
    { id: 1, icon: 'Rent', text: 'I want to rent a property' },
    { id: 2, icon: 'Buy', text: 'I want to buy a property' },
  ],
};

function tryParseJson(raw: string): unknown | null {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function pickString(...values: unknown[]): string {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) return value.trim();
    if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  }
  return '';
}

function normalizeProperties(input: unknown): PropertyCard[] {
  if (!Array.isArray(input)) return [];

  return input
    .map((row, index) => {
      const data = row && typeof row === 'object' ? (row as Record<string, unknown>) : {};

      const bed = pickString(data.bedrooms, data.beds, data.bhk, data.bed);
      const bath = pickString(data.bathrooms, data.baths, data.bath);
      const bedBath = [bed ? `${bed} bed` : '', bath ? `${bath} bath` : ''].filter(Boolean).join(', ');

      const title = pickString(data.title, data.name, data.property_name, data.propertyTitle, data.project_name, 'Property');
      const subtitle = pickString(
        data.subtitle,
        data.description,
        data.summary,
        bedBath,
        data.location,
        data.address,
        data.locality,
      );

      const rawPrice = data.price;
      let price = pickString(data.priceText, data.price_text, data.display_price, data.rent, data.amount, data.cost, rawPrice);
      if (typeof rawPrice === 'number' && Number.isFinite(rawPrice) && !String(price).includes('₹')) {
        price = `₹${new Intl.NumberFormat('en-IN').format(rawPrice)}`;
      }

      let imageUrl = pickString(data.imageUrl, data.image_url, data.image, data.public_url, data.publicUrl, data.thumbnail, data.photo);
      if (!imageUrl && Array.isArray(data.media) && data.media.length > 0) {
        const media = data.media[0];
        if (typeof media === 'string') imageUrl = media;
        if (media && typeof media === 'object') {
          imageUrl = pickString(
            imageUrl,
            (media as Record<string, unknown>).url,
            (media as Record<string, unknown>).image_url,
            (media as Record<string, unknown>).src,
          );
        }
      }

      return {
        id: Date.now() + index,
        title,
        subtitle,
        price,
        imageUrl,
      };
    })
    .filter((p) => p.title || p.subtitle || p.price || p.imageUrl)
    .slice(0, 10);
}

function parseWebhookPayload(raw: string): ParsedWebhook {
  const fallback = 'Thanks for your message.';
  const trimmed = raw.trim();
  const parsedRaw = tryParseJson(trimmed);
  if (!parsedRaw || typeof parsedRaw !== 'object') {
    return { message: trimmed || fallback, properties: [] };
  }

  const root = parsedRaw as Record<string, unknown>;
  let payload: Record<string, unknown> = root;
  if ('output' in root) {
    const output = root.output;
    if (typeof output === 'string') {
      const nested = tryParseJson(output);
      if (nested && typeof nested === 'object') payload = nested as Record<string, unknown>;
      else payload = { message: output };
    } else if (output && typeof output === 'object') {
      payload = output as Record<string, unknown>;
    }
  }

  const message = pickString(payload.message, payload.response, payload.reply, payload.text) || fallback;
  const properties = normalizeProperties(payload.properties ?? root.properties);
  return { message, properties };
}

function normalizeChatMode(value: unknown): ChatMode {
  return value === 'agent' ? 'agent' : 'webhook';
}

function normalizeAgentId(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value) && value > 0) return value;
  if (typeof value === 'string') {
    const parsed = Number.parseInt(value, 10);
    if (Number.isFinite(parsed) && parsed > 0) return parsed;
  }
  return null;
}

function normalizeApiBaseUrl(raw?: string): string {
  const value = (raw || '').trim();
  if (value) return value.replace(/\/$/, '');
  if (typeof window !== 'undefined') return window.location.origin;
  return '';
}

function serializeConfig(config: Config): string {
  return JSON.stringify(config);
}

function storageKeyForAgent(agentId: number | null): string {
  return agentId ? `${STORAGE_KEY}_agent_${agentId}` : STORAGE_KEY;
}

export function mergeConfig(base: Config, saved?: Partial<Config> | null): Config {
  const next = saved ?? {};
  return {
    ...base,
    ...next,
    chatMode: normalizeChatMode(next.chatMode ?? base.chatMode),
    agentId: normalizeAgentId(next.agentId ?? base.agentId),
    apiBaseUrl: normalizeApiBaseUrl(
      typeof next.apiBaseUrl === 'string' ? next.apiBaseUrl : base.apiBaseUrl,
    ),
    webhookUrl: typeof next.webhookUrl === 'string' && next.webhookUrl.trim() ? next.webhookUrl.trim() : base.webhookUrl,
    companyName: typeof next.companyName === 'string' && next.companyName.trim() ? next.companyName : base.companyName,
    welcomeMessage: typeof next.welcomeMessage === 'string' ? next.welcomeMessage : base.welcomeMessage,
    inputPlaceholder: typeof next.inputPlaceholder === 'string' && next.inputPlaceholder.trim() ? next.inputPlaceholder : base.inputPlaceholder,
    sendLabel: typeof next.sendLabel === 'string' && next.sendLabel.trim() ? next.sendLabel : base.sendLabel,
    launcherLabel: typeof next.launcherLabel === 'string' && next.launcherLabel.trim() ? next.launcherLabel : base.launcherLabel,
    bottom: typeof next.bottom === 'string' && next.bottom.trim() ? next.bottom : base.bottom,
    colors: {
      ...base.colors,
      ...(next.colors ?? {}),
    },
    quickReplies: Array.isArray(next.quickReplies) && next.quickReplies.length > 0
      ? next.quickReplies
      : base.quickReplies,
  };
}

function readStoredConfig(agentId: number | null): Partial<Config> | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(storageKeyForAgent(agentId));
    if (!raw) return null;
    return JSON.parse(raw) as Partial<Config>;
  } catch {
    return null;
  }
}

function buildAgentChatEndpoint(config: Pick<Config, 'agentId' | 'apiBaseUrl'>): string {
  const agentId = normalizeAgentId(config.agentId);
  if (!agentId) return '';
  return `${normalizeApiBaseUrl(config.apiBaseUrl)}/api/agents/${agentId}/test-chat`;
}

function buildChatHistory(messages: Message[]): ChatHistoryEntry[] {
  return messages
    .filter((message) => typeof message.text === 'string' && message.text.trim())
    .map((message) => ({
      role: message.user ? 'user' : 'assistant',
      content: message.text,
    }));
}

function parseAgentChatPayload(raw: string): ParsedWebhook {
  const fallback = 'Thanks for your message.';
  const trimmed = raw.trim();
  const parsed = tryParseJson(trimmed);
  if (!parsed || typeof parsed !== 'object') {
    return { message: trimmed || fallback, properties: [] };
  }

  const payload = parsed as Record<string, unknown>;
  return {
    message: pickString(payload.reply, payload.message, payload.response, payload.text) || fallback,
    properties: normalizeProperties(payload.properties),
  };
}

function iconSvg(icon: IconKey): string {
  return ICONS[icon];
}

function iconOrImage(icon: IconKey, imageUrl?: string): string {
  const url = (imageUrl || '').trim();
  if (url) {
    return `<img src="${url.replace(/"/g, '&quot;')}" alt="icon" style="width:100%;height:100%;object-fit:contain;border-radius:6px" />`;
  }
  return iconSvg(icon);
}

function fontValue(fontKey: FontFamilyKey): string {
  return FONT_FAMILY_OPTIONS.find((f) => f.key === fontKey)?.value || FONT_FAMILY_OPTIONS[0].value;
}

function imageCandidates(raw?: string): string[] {
  const value = (raw || '').trim();
  if (!value) return [];

  const stripProtocol = (url: string) => url.replace(/^https?:\/\//i, '');
  const bareInput = stripProtocol(value);
  const hostPart = bareInput.split('/')[0] || '';
  const hostWithoutPort = hostPart.split(':')[0] || '';
  const isIpv4 = (() => {
    const parts = hostWithoutPort.split('.');
    if (parts.length !== 4) return false;
    return parts.every((part) => /^\d{1,3}$/.test(part) && Number(part) >= 0 && Number(part) <= 255);
  })();
  const hasCustomPort = /:\d+$/.test(hostPart);

  let primary = value;
  if (primary.startsWith('//')) primary = `https:${primary}`;
  if (!/^https?:\/\//i.test(primary)) {
    primary = isIpv4 || hasCustomPort ? `http://${primary}` : `https://${primary}`;
  }

  const toProxy = (url: string) =>
    `https://images.weserv.nl/?url=${encodeURIComponent(stripProtocol(url))}&w=640&h=360&fit=cover`;

  if (isIpv4 || hasCustomPort) {
    const httpSource = `http://${stripProtocol(primary)}`;
    return [...new Set([toProxy(httpSource), toProxy(primary)])];
  }
  return [...new Set([primary, toProxy(primary)])];
}

export function buildEmbed(config: Config): string {
  const payload = JSON.stringify(
    {
      ...config,
      chatMode: normalizeChatMode(config.chatMode),
      agentId: normalizeAgentId(config.agentId),
      apiBaseUrl: normalizeApiBaseUrl(config.apiBaseUrl),
      fontFamilyCss: fontValue(config.fontFamily),
      launcherIconHtml: iconOrImage(config.launcherIcon, config.launcherIconUrl),
      headerIconHtml: iconOrImage(config.headerIcon, config.headerIconUrl),
      userMessageIconHtml: iconOrImage(config.userMessageIcon, config.userMessageIconUrl),
      aiMessageIconHtml: iconOrImage(config.aiMessageIcon, config.aiMessageIconUrl),
    },
    null,
    2,
  ).replace(/</g, '\\u003c');

  return `<script>
    (function () {
      var cfg = ${payload};
      var root = document.getElementById('lk-chat');
      if (!root) {
        root = document.createElement('div');
        root.id = 'lk-chat';
        document.body.appendChild(root);
      }

      var fallbackLauncherSvg = '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v8Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
      var state = {
        open: !!cfg.autoOpen,
        typing: false,
        sessionId: 's_' + Date.now() + '_' + Math.random().toString(36).slice(2, 10),
        messages: [{ id: 1, text: cfg.welcomeMessage, user: false, properties: [] }],
      };

      function ensureThemeStyles() {
        if (document.getElementById('lk-chat-theme')) return;
        var style = document.createElement('style');
        style.id = 'lk-chat-theme';
        style.textContent = [
          '#lk-chat{position:relative;z-index:9998;}',
          '#lk-chat .lk-widget{backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);transition:opacity .2s ease,transform .2s ease;}',
          '#lk-chat .lk-msgs{scrollbar-width:thin;scrollbar-color:rgba(255,255,255,.28) transparent;}',
          '#lk-chat .lk-msgs::-webkit-scrollbar{width:6px;}',
          '#lk-chat .lk-msgs::-webkit-scrollbar-thumb{background:rgba(255,255,255,.28);border-radius:999px;}',
          '#lk-chat .lk-bubble{box-shadow:inset 0 0 0 1px rgba(255,255,255,.03);}',
          '#lk-chat .lk-input{outline:none;}',
          '#lk-chat .lk-input:focus{box-shadow:0 0 0 2px rgba(255,255,255,.22);}',
          '#lk-chat .lk-send{transition:filter .2s ease,transform .16s ease;}',
          '#lk-chat .lk-send:hover{filter:brightness(1.04);}',
          '#lk-chat .lk-send:active{transform:translateY(1px);}',
          '#lk-chat .lk-close{transition:background .2s ease,transform .16s ease;}',
          '#lk-chat .lk-close:hover{background:rgba(255,255,255,.3);}',
          '#lk-chat .lk-close:active{transform:scale(.97);}',
          '#lk-chat .lk-quick{transition:background .2s ease,border-color .2s ease;}',
          '#lk-chat .lk-quick:hover{background:rgba(255,255,255,.13);border-color:rgba(255,255,255,.35);}',
          '#lk-chat .lk-launcher{transition:transform .18s ease,box-shadow .2s ease;}',
          '#lk-chat .lk-launcher:hover{transform:translateY(-1px);box-shadow:0 16px 30px rgba(0,0,0,.28);}',
          '#lk-chat .lk-typing{display:inline-flex;align-items:center;gap:5px;padding:6px 8px;margin-left:2px;}',
          '#lk-chat .lk-typing span{width:6px;height:6px;border-radius:999px;background:rgba(255,255,255,.8);display:inline-block;animation:lkDot 1.2s infinite ease-in-out;}',
          '#lk-chat .lk-typing span:nth-child(2){animation-delay:.15s;}',
          '#lk-chat .lk-typing span:nth-child(3){animation-delay:.3s;}',
          '#lk-chat .lk-powered{font-size:11px;color:rgba(255,255,255,.68);text-align:center;padding:0 0 8px;letter-spacing:.01em;}',
          '#lk-chat .lk-powered a{color:inherit;text-decoration:none;cursor:pointer;}',
          '#lk-chat .lk-powered a:hover{text-decoration:underline;color:#ffffff;}',
          '@keyframes lkDot{0%,80%,100%{transform:translateY(0);opacity:.35;}40%{transform:translateY(-4px);opacity:1;}}',
          '@media (max-width:900px){#lk-chat .lk-widget{width:min(360px,calc(100vw - 18px)) !important;height:min(72vh,560px) !important;bottom:86px !important;}}',
          '@media (max-width:640px){#lk-chat .lk-widget{left:10px !important;right:10px !important;width:auto !important;max-width:none !important;height:min(78vh,620px) !important;bottom:84px !important;border-radius:18px !important;}#lk-chat .lk-launcher{right:12px !important;left:auto !important;bottom:max(12px,env(safe-area-inset-bottom)) !important;}}',
          '@media (max-width:420px){#lk-chat .lk-widget{left:0 !important;right:0 !important;bottom:0 !important;height:100vh !important;border-radius:0 !important;max-width:none !important;}#lk-chat .lk-inputbar{padding-bottom:calc(10px + env(safe-area-inset-bottom)) !important;}}',
        ].join('');
        document.head.appendChild(style);
      }

      function applyStyles(el, styles) {
        Object.keys(styles).forEach(function (key) {
          el.style[key] = styles[key];
        });
        return el;
      }

      function parseJson(raw) {
        try {
          return JSON.parse(raw);
        } catch (error) {
          return null;
        }
      }

      function pick() {
        for (var i = 0; i < arguments.length; i += 1) {
          var val = arguments[i];
          if (typeof val === 'string' && val.trim()) return val.trim();
          if (typeof val === 'number' && Number.isFinite(val)) return String(val);
        }
        return '';
      }

      function normalizeProperties(list) {
        if (!Array.isArray(list)) return [];
        return list
          .map(function (item, idx) {
            var row = item && typeof item === 'object' ? item : {};
            var bed = pick(row.bedrooms, row.beds, row.bhk, row.bed);
            var bath = pick(row.bathrooms, row.baths, row.bath);
            var bedBath = [bed ? bed + ' bed' : '', bath ? bath + ' bath' : ''].filter(Boolean).join(', ');
            var rawPrice = row.price;
            var price = pick(row.priceText, row.price_text, row.display_price, row.rent, row.amount, row.cost, rawPrice);
            if (typeof rawPrice === 'number' && Number.isFinite(rawPrice) && String(price).indexOf('\\u20B9') === -1) {
              price = '\\u20B9' + new Intl.NumberFormat('en-IN').format(rawPrice);
            }

            var imageUrl = pick(row.imageUrl, row.image_url, row.image, row.public_url, row.publicUrl, row.thumbnail, row.photo);
            if (!imageUrl && Array.isArray(row.media) && row.media.length > 0) {
              var first = row.media[0];
              if (typeof first === 'string') imageUrl = first;
              if (first && typeof first === 'object') {
                imageUrl = pick(imageUrl, first.url, first.image_url, first.src);
              }
            }

            return {
              id: Date.now() + idx,
              title: pick(row.title, row.name, row.property_name, row.propertyTitle, row.project_name, 'Property'),
              subtitle: pick(row.subtitle, row.description, row.summary, bedBath, row.location, row.address, row.locality),
              price: price,
              imageUrl: imageUrl,
            };
          })
          .filter(function (card) {
            return card.title || card.subtitle || card.price || card.imageUrl;
          })
          .slice(0, 10);
      }

      function parseWebhook(raw) {
        var fallback = 'Thanks for your message.';
        var text = (raw || '').trim();
        var parsedRoot = parseJson(text);
        if (!parsedRoot || typeof parsedRoot !== 'object') {
          return { message: text || fallback, properties: [] };
        }

        var payloadNode = parsedRoot;
        if (Object.prototype.hasOwnProperty.call(parsedRoot, 'output')) {
          var output = parsedRoot.output;
          if (typeof output === 'string') {
            var nested = parseJson(output);
            payloadNode = nested && typeof nested === 'object' ? nested : { message: output };
          } else if (output && typeof output === 'object') {
            payloadNode = output;
          }
        }

        return {
          message: pick(payloadNode.message, payloadNode.response, payloadNode.reply, payloadNode.text) || fallback,
          properties: normalizeProperties(payloadNode.properties || parsedRoot.properties),
        };
      }

      function buildHistory() {
        return state.messages
          .filter(function (message) {
            return message && typeof message.text === 'string' && message.text.trim();
          })
          .map(function (message) {
            return {
              role: message.user ? 'user' : 'assistant',
              content: message.text,
            };
          });
      }

      function normalizedApiBaseUrl() {
        var raw = (cfg.apiBaseUrl || '').trim();
        if (raw) return raw.replace(/\\/$/, '');
        return window.location.origin;
      }

      function agentEndpoint() {
        if (!cfg.agentId) return '';
        return normalizedApiBaseUrl() + '/api/agents/' + cfg.agentId + '/test-chat';
      }

      function parseAgentResponse(raw) {
        var fallback = 'Thanks for your message.';
        var text = (raw || '').trim();
        var parsed = parseJson(text);
        if (!parsed || typeof parsed !== 'object') {
          return { message: text || fallback, properties: [] };
        }

        return {
          message: pick(parsed.reply, parsed.message, parsed.response, parsed.text) || fallback,
          properties: normalizeProperties(parsed.properties),
        };
      }

      function launcherPosition() {
        if (cfg.position === 'left') return { left: '20px', right: 'auto' };
        return { left: 'auto', right: '20px' };
      }

      function ensureGlyphSize(host) {
        var iconEl = host.querySelector('svg, img');
        if (!iconEl) {
          host.textContent = 'C';
          host.style.fontSize = '14px';
          host.style.fontWeight = '700';
          host.style.lineHeight = '1';
          host.style.alignItems = 'center';
          host.style.justifyContent = 'center';
          return;
        }
        iconEl.style.width = '100%';
        iconEl.style.height = '100%';
        iconEl.style.display = 'block';
        iconEl.style.objectFit = 'contain';
      }

      function createIconBadge(iconHtml, size, background, extraStyles) {
        var badge = applyStyles(
          document.createElement('span'),
          Object.assign(
            {
              width: size + 'px',
              height: size + 'px',
              minWidth: size + 'px',
              borderRadius: '999px',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              background: background || 'rgba(255,255,255,.12)',
              overflow: 'hidden',
            },
            extraStyles || {},
          ),
        );
        badge.innerHTML = iconHtml || fallbackLauncherSvg;
        ensureGlyphSize(badge);
        return badge;
      }

      function imageCandidates(raw) {
        var value = (raw || '').trim();
        if (!value) return [];

        function stripProtocol(url) {
          var lower = url.toLowerCase();
          if (lower.indexOf('https://') === 0) return url.slice(8);
          if (lower.indexOf('http://') === 0) return url.slice(7);
          return url;
        }

        function isIpv4(host) {
          var parts = host.split('.');
          if (parts.length !== 4) return false;
          for (var i = 0; i < parts.length; i += 1) {
            var p = parts[i];
            if (!p || p.length > 3) return false;
            if (!/^\\d+$/.test(p)) return false;
            var n = Number(p);
            if (!Number.isFinite(n) || n < 0 || n > 255) return false;
          }
          return true;
        }

        var bareInput = stripProtocol(value);
        var hostPart = bareInput.split('/')[0] || '';
        var hostWithoutPort = hostPart.split(':')[0] || '';
        var isIpv4Host = isIpv4(hostWithoutPort);
        var hasCustomPort = /:\\d+$/.test(hostPart);

        var primary = value;
        if (primary.indexOf('//') === 0) primary = 'https:' + primary;
        var low = primary.toLowerCase();
        if (!(low.indexOf('https://') === 0 || low.indexOf('http://') === 0)) {
          primary = isIpv4Host || hasCustomPort ? 'http://' + primary : 'https://' + primary;
        }

        function toProxy(url) {
          return 'https://images.weserv.nl/?url=' + encodeURIComponent(stripProtocol(url)) + '&w=640&h=360&fit=cover';
        }

        if (isIpv4Host || hasCustomPort) {
          var httpSource = 'http://' + stripProtocol(primary);
          var first = toProxy(httpSource);
          var second = toProxy(primary);
          return first === second ? [first] : [first, second];
        }

        var proxy = toProxy(primary);
        return primary === proxy ? [primary] : [primary, proxy];
      }

      function addPropertyRail(container, properties) {
        if (!properties || !properties.length) return;

        var rail = applyStyles(document.createElement('div'), {
          display: 'flex',
          gap: '10px',
          overflowX: 'auto',
          padding: '2px 2px 6px',
          scrollbarWidth: 'thin',
        });

        properties.forEach(function (property) {
          var card = applyStyles(document.createElement('article'), {
            minWidth: '168px',
            maxWidth: '168px',
            background: '#ffffff',
            borderRadius: '14px',
            overflow: 'hidden',
            boxShadow: 'inset 0 0 0 1px rgba(15,23,42,0.08)',
          });

          var imageWrap = applyStyles(document.createElement('div'), {
            height: '96px',
            background: '#e2e8f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          });

          if (property.imageUrl) {
            var image = document.createElement('img');
            var candidates = imageCandidates(property.imageUrl);
            image.src = candidates[0] || '';
            image.alt = property.title || 'Property';
            image.loading = 'lazy';
            applyStyles(image, { width: '100%', height: '100%', objectFit: 'cover' });
            if (candidates.length > 1) {
              image.onerror = function () {
                if (image.src === candidates[0]) {
                  image.src = candidates[1];
                  return;
                }
                imageWrap.innerHTML = '<span style="font-size:12px;color:#64748b;">No image</span>';
              };
            } else {
              image.onerror = function () {
                imageWrap.innerHTML = '<span style="font-size:12px;color:#64748b;">No image</span>';
              };
            }
            imageWrap.appendChild(image);
          } else {
            var placeholder = document.createElement('span');
            placeholder.textContent = 'No image';
            applyStyles(placeholder, { fontSize: '12px', color: '#64748b' });
            imageWrap.appendChild(placeholder);
          }

          var body = applyStyles(document.createElement('div'), {
            padding: '8px 9px 9px',
            color: '#0f172a',
          });

          var title = document.createElement('p');
          title.textContent = property.title || 'Property';
          applyStyles(title, { margin: '0', fontSize: '12px', fontWeight: '700', lineHeight: '1.35' });
          body.appendChild(title);

          if (property.subtitle) {
            var subtitle = document.createElement('p');
            subtitle.textContent = property.subtitle;
            applyStyles(subtitle, { margin: '5px 0 0', fontSize: '11px', lineHeight: '1.3', color: '#475569' });
            body.appendChild(subtitle);
          }

          if (property.price) {
            var price = document.createElement('p');
            price.textContent = property.price;
            applyStyles(price, { margin: '7px 0 0', fontSize: '20px', fontWeight: '800', letterSpacing: '-0.02em' });
            body.appendChild(price);
          }

          card.appendChild(imageWrap);
          card.appendChild(body);
          rail.appendChild(card);
        });

        container.appendChild(rail);
      }

      function renderMessages(box) {
        box.innerHTML = '';

        state.messages.forEach(function (message) {
          var block = applyStyles(document.createElement('div'), {
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          });

          var row = applyStyles(document.createElement('div'), {
            display: 'flex',
            justifyContent: message.user ? 'flex-end' : 'flex-start',
            alignItems: 'flex-end',
            gap: '8px',
          });

          if (!message.user) {
            row.appendChild(
              createIconBadge(cfg.aiMessageIconHtml, 28, 'rgba(255,255,255,.12)', {
                color: '#fff',
                flexShrink: '0',
                marginBottom: '2px',
              }),
            );
          }

          var bubble = document.createElement('div');
          bubble.className = 'lk-bubble ' + (message.user ? 'is-user' : 'is-bot');
          bubble.textContent = message.text;
          applyStyles(bubble, {
            maxWidth: '84%',
            padding: '9px 11px',
            borderRadius: '12px',
            color: cfg.colors.text,
            lineHeight: String(cfg.lineHeight),
            background: message.user ? cfg.colors.userBubble : cfg.colors.botBubble,
            fontSize: cfg.fontSize + 'px',
          });
          row.appendChild(bubble);

          if (message.user) {
            row.appendChild(
              createIconBadge(cfg.userMessageIconHtml, 28, 'rgba(255,255,255,.12)', {
                color: '#fff',
                flexShrink: '0',
                marginBottom: '2px',
              }),
            );
          }

          block.appendChild(row);

          if (!message.user && Array.isArray(message.properties) && message.properties.length > 0) {
            addPropertyRail(block, message.properties);
          }

          box.appendChild(block);
        });

        if (state.messages.length < 3 && Array.isArray(cfg.quickReplies)) {
          var quickWrap = applyStyles(document.createElement('div'), {
            display: 'flex',
            flexWrap: 'wrap',
            gap: '8px',
          });

          cfg.quickReplies.forEach(function (quick) {
            var quickButton = document.createElement('button');
            quickButton.className = 'lk-quick';
            quickButton.textContent = quick.icon + ' ' + quick.text;
            applyStyles(quickButton, {
              border: '1px solid rgba(255,255,255,.2)',
              background: 'rgba(255,255,255,.08)',
              color: '#fff',
              borderRadius: '999px',
              padding: '7px 10px',
              cursor: 'pointer',
              fontSize: '12px',
            });
            quickButton.onclick = function () {
              send(quick.text);
            };
            quickWrap.appendChild(quickButton);
          });
          box.appendChild(quickWrap);
        }

        if (state.typing) {
          var typing = document.createElement('div');
          typing.className = 'lk-typing';
          typing.innerHTML = '<span></span><span></span><span></span>';
          box.appendChild(typing);
        }

        box.scrollTop = box.scrollHeight;
      }

      async function send(forcedValue) {
        var input = document.getElementById('lk-inp');
        var text = (forcedValue || (input ? input.value : '') || '').trim();
        if (!text) return;

        state.messages.push({ id: Date.now(), text: text, user: true, properties: [] });
        if (input) input.value = '';
        state.typing = true;
        render();
        var typingSince = Date.now();

        try {
          var useAgentRuntime = cfg.chatMode === 'agent' && !!cfg.agentId;
          var response = await fetch(useAgentRuntime ? agentEndpoint() : cfg.webhookUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(
              useAgentRuntime
                ? {
                    message: text,
                    history: buildHistory(),
                  }
                : {
                    message: text,
                    timestamp: new Date().toISOString(),
                    sessionId: state.sessionId,
                  }
            ),
          });
          var raw = await response.text();
          var parsed = useAgentRuntime ? parseAgentResponse(raw) : parseWebhook(raw);
          state.messages.push({
            id: Date.now() + 1,
            text: parsed.message,
            user: false,
            properties: parsed.properties,
          });
        } catch (error) {
          state.messages.push({
            id: Date.now() + 1,
            text: cfg.chatMode === 'agent' ? 'Agent chat is not reachable.' : 'Webhook not reachable.',
            user: false,
            properties: [],
          });
        } finally {
          var wait = 550 - (Date.now() - typingSince);
          if (wait > 0) {
            await new Promise(function (resolve) {
              setTimeout(resolve, wait);
            });
          }
          state.typing = false;
          render();
        }
      }

      function render() {
        root.innerHTML = '';
        var position = launcherPosition();
        ensureThemeStyles();

        if (state.open) {
          var widget = applyStyles(document.createElement('div'), {
            position: 'fixed',
            left: position.left,
            right: position.right,
            bottom: '96px',
            width: '390px',
            maxWidth: 'calc(100vw - 24px)',
            height: '560px',
            maxHeight: 'calc(100vh - 108px)',
            borderRadius: cfg.widgetRadius + 'px',
            overflow: 'hidden',
            zIndex: '9999',
            background: cfg.colors.surface,
            border: cfg.borderWidth + 'px solid rgba(255,255,255,.16)',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 18px 34px rgba(0,0,0,.35)',
            fontFamily: cfg.fontFamilyCss,
            fontSize: cfg.fontSize + 'px',
          });
          widget.className = 'lk-widget';

          var head = applyStyles(document.createElement('div'), {
            padding: '12px 14px',
            color: cfg.colors.text,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: 'linear-gradient(135deg,' + cfg.colors.brandA + ',' + cfg.colors.brandB + ')',
          });
          head.className = 'lk-head';
          var headLeft = applyStyles(document.createElement('div'), {
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            minWidth: '0',
          });
          var headIcon = createIconBadge(cfg.headerIconHtml, 28, 'rgba(255,255,255,.22)', {
            color: '#fff',
            flexShrink: '0',
          });
          var title = document.createElement('strong');
          title.textContent = cfg.companyName;
          applyStyles(title, {
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          });
          var closeButton = document.createElement('button');
          closeButton.id = 'lk-close';
          closeButton.className = 'lk-close';
          closeButton.innerHTML = '&times;';
          applyStyles(closeButton, {
            border: 'none',
            background: 'rgba(255,255,255,.22)',
            color: '#fff',
            borderRadius: '999px',
            width: '28px',
            height: '28px',
            cursor: 'pointer',
            fontSize: '18px',
            lineHeight: '1',
          });
          headLeft.appendChild(headIcon);
          headLeft.appendChild(title);
          head.appendChild(headLeft);
          head.appendChild(closeButton);

          var messageBox = document.createElement('div');
          messageBox.id = 'lk-msgs';
          messageBox.className = 'lk-msgs';
          applyStyles(messageBox, {
            flex: '1',
            overflowY: 'auto',
            padding: '10px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          });

          var inputBar = applyStyles(document.createElement('div'), {
            display: 'flex',
            gap: '7px',
            borderTop: '1px solid rgba(255,255,255,.14)',
            padding: '9px 9px 7px',
          });
          inputBar.className = 'lk-inputbar';
          var input = document.createElement('input');
          input.id = 'lk-inp';
          input.className = 'lk-input';
          input.placeholder = cfg.inputPlaceholder;
          applyStyles(input, {
            flex: '1',
            border: 'none',
            borderRadius: '9px',
            padding: '9px 10px',
            fontSize: '13px',
          });
          var sendButton = document.createElement('button');
          sendButton.id = 'lk-send';
          sendButton.className = 'lk-send';
          sendButton.textContent = cfg.sendLabel;
          applyStyles(sendButton, {
            border: 'none',
            background: cfg.colors.brandA,
            color: '#fff',
            borderRadius: '9px',
            padding: '9px 12px',
            cursor: 'pointer',
            fontSize: '13px',
          });
          inputBar.appendChild(input);
          inputBar.appendChild(sendButton);

          widget.appendChild(head);
          widget.appendChild(messageBox);
          widget.appendChild(inputBar);
          var poweredBy = document.createElement('div');
          poweredBy.className = 'lk-powered';
          var poweredByLink = document.createElement('a');
          poweredByLink.href = 'https://oyik.ai';
          poweredByLink.target = '_blank';
          poweredByLink.rel = 'noopener noreferrer';
          poweredByLink.textContent = 'Powered By Oyik.AI';
          poweredBy.appendChild(poweredByLink);
          widget.appendChild(poweredBy);
          root.appendChild(widget);

          renderMessages(messageBox);
          closeButton.onclick = function () {
            state.open = false;
            render();
          };
          sendButton.onclick = function () {
            send();
          };
          input.onkeydown = function (event) {
            if (event.key === 'Enter') send();
          };
        }

        if (!state.open) {
          var launcher = document.createElement('button');
          launcher.className = 'lk-launcher';
          applyStyles(launcher, {
            position: 'fixed',
            left: position.left,
            right: position.right,
            bottom: cfg.bottom,
            width: cfg.launcherSize + 'px',
            height: cfg.launcherSize + 'px',
            border: 'none',
            borderRadius: cfg.launcherRadius + 'px',
            color: '#fff',
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '3px',
            zIndex: '9998',
            background: 'linear-gradient(135deg,' + cfg.colors.brandA + ',' + cfg.colors.brandB + ')',
            boxShadow: '0 12px 24px rgba(0,0,0,.24)',
          });

          var iconWrap = createIconBadge(cfg.launcherIconHtml, 20, 'transparent', {
            color: '#fff',
            borderRadius: '0',
          });
          iconWrap.className = 'lk-launcher-icon';

          var label = document.createElement('span');
          label.className = 'lk-launcher-label';
          label.textContent = cfg.launcherLabel;
          applyStyles(label, { fontSize: '10px', fontWeight: '600' });

          launcher.appendChild(iconWrap);
          launcher.appendChild(label);
          launcher.onclick = function () {
            state.open = true;
            render();
          };
          root.appendChild(launcher);
        }
      }

      render();
    })();
</script>`;
}

function IconPreview({ icon, imageUrl, className }: { icon: IconKey; imageUrl?: string; className?: string }) {
  if (imageUrl?.trim()) {
    return (
      <span className={`icon-svg ${className ?? ''}`}>
        <img src={imageUrl} alt="icon" />
      </span>
    );
  }
  return <span className={`icon-svg ${className ?? ''}`} dangerouslySetInnerHTML={{ __html: ICONS[icon] }} />;
}

function ColorPickerField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="color-field">
      <label>{label}</label>
      <div className="color-row">
        <button
          type="button"
          className="color-swatch"
          style={{ background: value }}
          onClick={() => setOpen((v) => !v)}
          aria-label={`${label} color`}
        />
        <input value={value} onChange={(e) => onChange(e.target.value)} />
      </div>
      {open && (
        <div className="color-pop">
          <input type="color" value={value} onChange={(e) => onChange(e.target.value)} />
        </div>
      )}
    </div>
  );
}

function IconSelector({
  value,
  onChange,
}: {
  value: IconKey;
  onChange: (icon: IconKey) => void;
}) {
  return (
    <div className="icons">
      {(['message', 'spark', 'bolt', 'bot'] as IconKey[]).map((icon) => (
        <button key={icon} className={value === icon ? 'pick active' : 'pick'} onClick={() => onChange(icon)} type="button" aria-label={`icon-${icon}`}>
          <IconPreview icon={icon} />
        </button>
      ))}
    </div>
  );
}

function MobilePreview({ config, mode }: { config: Config; mode: PreviewMode }) {
  const [open, setOpen] = useState(config.autoOpen);
  const [typing, setTyping] = useState(false);
  const [input, setInput] = useState('');
  const [sessionId] = useState(() => `preview_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`);
  const [messages, setMessages] = useState<Message[]>([{ id: 1, text: config.welcomeMessage, user: false }]);
  const parsedBottom = Number.parseInt(config.bottom.replace('px', ''), 10);
  const bottomOffset = Number.isFinite(parsedBottom) ? `${parsedBottom}px` : config.bottom;

  const launcherPos = useMemo(() => {
    if (mode === 'mobile') {
      return { left: 'auto', right: '20px', bottom: bottomOffset, transform: 'none' };
    }
    const left = config.position === 'left' ? '20px' : 'auto';
    const right = config.position === 'right' ? '20px' : 'auto';
    return { left, right, bottom: bottomOffset, transform: 'none' };
  }, [bottomOffset, config.position, mode]);

  const widgetAlignStyle = useMemo(() => {
    if (mode !== 'web') return {};
    if (config.position === 'left') {
      return { left: mode === 'web' ? '16px' : '10px', right: 'auto' };
    }
    return { right: mode === 'web' ? '16px' : '10px', left: 'auto' };
  }, [config.position, mode]);

  useEffect(() => {
    setOpen(config.autoOpen);
  }, [config.autoOpen]);

  useEffect(() => {
    setMessages((prev) => {
      const nextGreeting: Message = { id: 1, text: config.welcomeMessage, user: false, properties: [] };
      if (!prev.length) return [nextGreeting];
      if (!prev[0].user) {
        return [{ ...prev[0], text: config.welcomeMessage, properties: [] }, ...prev.slice(1)];
      }
      return [nextGreeting, ...prev];
    });
  }, [config.welcomeMessage]);

  useEffect(() => {
    setTyping(false);
    setInput('');
    setMessages([{ id: 1, text: config.welcomeMessage, user: false, properties: [] }]);
  }, [config.agentId, config.chatMode, config.webhookUrl]);

  const send = async (forced?: string) => {
    const text = (forced ?? input).trim();
    if (!text) return;
    setMessages((p) => [...p, { id: Date.now(), text, user: true, properties: [] }]);
    setInput('');
    setTyping(true);
    const typingSince = Date.now();
    try {
      const useAgentRuntime = config.chatMode === 'agent' && normalizeAgentId(config.agentId);
      const endpoint = useAgentRuntime ? buildAgentChatEndpoint(config) : config.webhookUrl;
      const body = useAgentRuntime
        ? { message: text, history: buildChatHistory(messages) }
        : { message: text, timestamp: new Date().toISOString(), sessionId };
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const raw = await res.text();
      const parsed = useAgentRuntime ? parseAgentChatPayload(raw) : parseWebhookPayload(raw);
      setMessages((p) => [...p, { id: Date.now() + 1, text: parsed.message, user: false, properties: parsed.properties }]);
    } catch {
      setMessages((p) => [
        ...p,
        {
          id: Date.now() + 1,
          text: config.chatMode === 'agent' ? 'Agent chat is not reachable.' : 'Webhook not reachable.',
          user: false,
          properties: [],
        },
      ]);
    } finally {
      const wait = 550 - (Date.now() - typingSince);
      if (wait > 0) await new Promise((resolve) => setTimeout(resolve, wait));
      setTyping(false);
    }
  };

  return (
    <div className="phone-wrap" style={{ background: config.colors.page }}>
        <div className={mode === 'mobile' ? 'device-shell mobile' : 'device-shell web'}>
        {mode === 'mobile' ? (
          !open && (
            <>
              <div className="statusbar"><span>9:41</span><span className="status-icons">5G 87%</span></div>
              <div className="notch" />
            </>
          )
        ) : (
          <div className="browser-bar"><span /><span /><span /><p>oyik.ai</p></div>
        )}
        <div className="screen">
          <div className={`landing ${mode}`}>
            <div className="landing-header">
              <div className="landing-logo">Oyik.ai Real Estate</div>
              <button>Find Homes</button>
            </div>
            <div className="landing-hero">
              <h3>Discover your next property in minutes</h3>
              <p>Search verified homes, compare prices, and chat instantly with our assistant.</p>
            </div>
            <div className="landing-grid">
              <div className="house-card">
                <img src="https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1000&q=80" alt="Luxury Villa" />
                <p>Luxury Villa · Dubai Hills</p>
              </div>
              <div className="house-card">
                <img src="https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1000&q=80" alt="Family Apartment" />
                <p>Family Apartment · Business Bay</p>
              </div>
              <div className="house-card">
                <img src="https://images.unsplash.com/photo-1568605114967-8130f3a36994?auto=format&fit=crop&w=1000&q=80" alt="Townhouse" />
                <p>Townhouse · JVC</p>
              </div>
            </div>
          </div>

          {open && (
            <div
              className={`widget ${mode} ${open ? 'open' : ''}`}
              style={{
                ...widgetAlignStyle,
                borderRadius: config.widgetRadius,
                borderWidth: config.borderWidth,
                background: config.colors.chatBackground,
                fontFamily: fontValue(config.fontFamily),
                fontSize: `${config.fontSize}px`,
              }}
            >
              <div className="widget-head" style={{ background: config.colors.primary }}>
                <div className="head-left">
                  <span className="avatar head-avatar">
                    <IconPreview icon={config.headerIcon} imageUrl={config.headerIconUrl} className="mini" />
                  </span>
                  <strong>{config.companyName}</strong>
                </div>
                <button onClick={() => setOpen(false)} aria-label="Minimize chat">
                  <Minus size={14} />
                </button>
              </div>

              <div className="widget-body">
                {messages.map((m) => (
                  <div className="message-block" key={m.id}>
                    <div className={`row ${m.user ? 'u' : 'b'}`}>
                      {!m.user && (
                        <span className="avatar">
                          <IconPreview icon={config.aiMessageIcon} imageUrl={config.aiMessageIconUrl} className="msg-icon" />
                        </span>
                      )}
                      <div className="bubble" style={{ lineHeight: config.lineHeight, fontSize: `${config.fontSize}px`, color: config.colors.text, background: m.user ? config.colors.sendMessage : config.colors.aiMessage }}>
                        {m.text}
                      </div>
                      {m.user && (
                        <span className="avatar user">
                          <IconPreview icon={config.userMessageIcon} imageUrl={config.userMessageIconUrl} className="msg-icon" />
                        </span>
                      )}
                    </div>
                    {!m.user && !!m.properties?.length && (
                      <div className="property-rail">
                        {m.properties.map((property) => (
                          <article className="property-card" key={`${m.id}_${property.id}`}>
                            <div className="property-image">
                              {property.imageUrl ? (
                                <img
                                  src={imageCandidates(property.imageUrl)[0]}
                                  data-fallback={imageCandidates(property.imageUrl)[1] || ''}
                                  alt={property.title || 'Property'}
                                  onError={(event) => {
                                    const target = event.currentTarget;
                                    const fallback = target.getAttribute('data-fallback');
                                    if (fallback && target.src !== fallback) {
                                      target.src = fallback;
                                      return;
                                    }
                                    target.style.display = 'none';
                                    const parent = target.parentElement;
                                    if (parent && !parent.querySelector('.no-image')) {
                                      const placeholder = document.createElement('span');
                                      placeholder.className = 'no-image';
                                      placeholder.textContent = 'No image';
                                      parent.appendChild(placeholder);
                                    }
                                  }}
                                />
                              ) : (
                                <span>No image</span>
                              )}
                            </div>
                            <div className="property-content">
                              <p className="property-title">{property.title || 'Property'}</p>
                              {property.subtitle && <p className="property-subtitle">{property.subtitle}</p>}
                              {property.price && <p className="property-price">{property.price}</p>}
                            </div>
                          </article>
                        ))}
                      </div>
                    )}
                  </div>
                ))}

                {messages.length < 3 && (
                  <div className="quick-wrap">
                    {config.quickReplies.map((q) => (
                      <button key={q.id} onClick={() => send(q.text)}>
                        {q.icon} {q.text}
                      </button>
                    ))}
                  </div>
                )}

                {typing && (
                  <div className="typing typing-dots" aria-label="Typing">
                    <span />
                    <span />
                    <span />
                  </div>
                )}
              </div>

              <div className="widget-input">
                <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && send()} placeholder={config.inputPlaceholder} />
                <button onClick={() => send()} style={{ background: config.colors.primary }}>{config.sendLabel}</button>
              </div>
              <div className="powered-by">
                <a href="https://oyik.ai" target="_blank" rel="noreferrer">
                  Powered By Oyik.AI
                </a>
              </div>
            </div>
          )}

          {!open && (
            <button className={`launcher ${mode}`} style={{ ...launcherPos, width: config.launcherSize, height: config.launcherSize, borderRadius: config.launcherRadius, background: config.colors.primary }} onClick={() => setOpen((v) => !v)}>
              <IconPreview icon={config.launcherIcon} imageUrl={config.launcherIconUrl} />
              <span>{config.launcherLabel}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function ChatbotDashboardPageContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const requestedAgentId = normalizeAgentId(searchParams.get('agentId'));
  const [tab, setTab] = useState<Tab>('general');
  const [previewMode, setPreviewMode] = useState<PreviewMode>('mobile');
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(requestedAgentId);
  const [agents, setAgents] = useState<AgentSummary[]>([]);
  const [agentLoading, setAgentLoading] = useState(false);
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [config, setConfig] = useState<Config>(() =>
    mergeConfig(initialConfig, {
      agentId: requestedAgentId,
      chatMode: requestedAgentId ? 'agent' : initialConfig.chatMode,
      apiBaseUrl: normalizeApiBaseUrl(initialConfig.apiBaseUrl),
    }),
  );
  const [draft, setDraft] = useState<QuickReply>({ id: 0, icon: 'Ask', text: '' });
  const [lastSavedSignature, setLastSavedSignature] = useState('');
  const didHydrateSavedState = useRef(false);

  const embed = useMemo(() => buildEmbed(config), [config]);
  const selectedAgent = useMemo(
    () => agents.find((agent) => agent.id === selectedAgentId) ?? null,
    [agents, selectedAgentId],
  );

  useEffect(() => {
    setSelectedAgentId(requestedAgentId);
  }, [requestedAgentId]);

  useEffect(() => {
    let cancelled = false;

    const loadAgents = async () => {
      try {
        const response = await fetch('/api/agents/');
        if (!response.ok) return;
        const data = (await response.json()) as AgentSummary[];
        if (!cancelled) {
          setAgents(Array.isArray(data) ? data : []);
        }
      } catch {
        if (!cancelled) {
          setAgents([]);
        }
      }
    };

    void loadAgents();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadConfig = async () => {
      const localDraft = readStoredConfig(selectedAgentId);

      if (!selectedAgentId) {
        const nextConfig = mergeConfig(initialConfig, {
          ...(localDraft ?? {}),
          agentId: null,
          chatMode: 'webhook',
          apiBaseUrl: normalizeApiBaseUrl((localDraft?.apiBaseUrl as string | undefined) || initialConfig.apiBaseUrl),
        });
        setConfig(nextConfig);
        setLastSavedSignature(serializeConfig(nextConfig));
        setSaveState('idle');
        return;
      }

      setAgentLoading(true);
      try {
        const response = await fetch(`/api/agents/${selectedAgentId}`);
        if (!response.ok) throw new Error('Failed to load agent');

        const agent = (await response.json()) as AgentSummary;
        if (cancelled) return;

        const customParams =
          agent.custom_params && typeof agent.custom_params === 'object'
            ? (agent.custom_params as Record<string, unknown>)
            : {};
        const savedWidget =
          customParams.chat_widget && typeof customParams.chat_widget === 'object'
            ? (customParams.chat_widget as Partial<Config>)
            : null;

        const baseConfig = mergeConfig(initialConfig, {
          agentId: agent.id,
          chatMode: 'agent',
          apiBaseUrl: normalizeApiBaseUrl(initialConfig.apiBaseUrl),
          companyName: agent.display_name || agent.name || initialConfig.companyName,
          welcomeMessage: pickString(
            savedWidget?.welcomeMessage,
            agent.welcome_message,
            initialConfig.welcomeMessage,
          ),
          webhookUrl:
            typeof agent.webhook_url === 'string' && agent.webhook_url.trim()
              ? agent.webhook_url.trim()
              : initialConfig.webhookUrl,
        });

        const localMerged = mergeConfig(baseConfig, localDraft);
        const finalConfig = mergeConfig(localMerged, savedWidget);
        const nextConfig = mergeConfig(finalConfig, {
          agentId: agent.id,
          chatMode: savedWidget?.chatMode ? normalizeChatMode(savedWidget.chatMode) : 'agent',
          apiBaseUrl: normalizeApiBaseUrl(finalConfig.apiBaseUrl),
        });
        setConfig(nextConfig);
        setLastSavedSignature(serializeConfig(nextConfig));
        setSaveState('idle');
      } catch {
        if (!cancelled) {
          const fallbackConfig = mergeConfig(initialConfig, {
            ...(localDraft ?? {}),
            agentId: selectedAgentId,
            chatMode: 'agent',
            apiBaseUrl: normalizeApiBaseUrl((localDraft?.apiBaseUrl as string | undefined) || initialConfig.apiBaseUrl),
          });
          setConfig(fallbackConfig);
          setLastSavedSignature(serializeConfig(fallbackConfig));
          setSaveState('error');
        }
      } finally {
        if (!cancelled) {
          setAgentLoading(false);
        }
      }
    };

    void loadConfig();

    return () => {
      cancelled = true;
    };
  }, [selectedAgentId]);

  useEffect(() => {
    if (!lastSavedSignature) return;
    if (!didHydrateSavedState.current) {
      didHydrateSavedState.current = true;
      return;
    }
    if (saveState === 'saving') return;
    if (serializeConfig(config) !== lastSavedSignature) {
      setSaveState('idle');
    }
  }, [config, lastSavedSignature, saveState]);

  const updateAgentSelection = (nextAgentId: number | null) => {
    const nextParams = new URLSearchParams(searchParams.toString());
    if (nextAgentId) nextParams.set('agentId', String(nextAgentId));
    else nextParams.delete('agentId');
    const target = nextParams.toString() ? `${pathname}?${nextParams.toString()}` : pathname;
    router.replace(target);
  };

  const addReply = () => {
    if (!draft.text.trim()) return;
    setConfig((p) => ({ ...p, quickReplies: [...p.quickReplies, { ...draft, id: Date.now() }] }));
    setDraft({ id: 0, icon: 'Ask', text: '' });
  };

  const bottomOffsetValue = Number.parseInt(config.bottom.replace('px', ''), 10) || 0;
  const setBottomOffset = (value: number) => {
    const next = Math.max(0, value);
    setConfig((p) => ({ ...p, bottom: `${next}px` }));
  };

  const setPrimaryColor = (value: string) =>
    setConfig((p) => ({
      ...p,
      colors: { ...p.colors, primary: value, brandA: value, brandB: value },
    }));

  const setChatBackground = (value: string) =>
    setConfig((p) => ({
      ...p,
      colors: { ...p.colors, chatBackground: value, surface: value },
    }));

  const setUserMessageColor = (value: string) =>
    setConfig((p) => ({
      ...p,
      colors: { ...p.colors, sendMessage: value, userBubble: value },
    }));

  const setAiMessageColor = (value: string) =>
    setConfig((p) => ({
      ...p,
      colors: { ...p.colors, aiMessage: value, botBubble: value },
    }));

  const copyEmbed = async () => {
    await navigator.clipboard.writeText(embed);
    alert('Embed HTML copied.');
  };

  const downloadEmbed = () => {
    const blob = new Blob([embed], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'chatbot-widget-embed.html';
    a.click();
    URL.revokeObjectURL(url);
  };

  const openLocalEmbedTest = () => {
    const html = `<!doctype html><html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" /><title>Embed Test</title><style>html,body{margin:0;min-height:100%;font-family:Inter,Segoe UI,sans-serif;background:linear-gradient(180deg,#f8faff,#eef3ff);}body{min-height:100vh;}main{min-height:100vh;padding:24px;display:flex;align-items:flex-start;justify-content:flex-start;background:radial-gradient(circle at top left,rgba(79,70,229,.08),transparent 38%),linear-gradient(180deg,#f8faff,#eef3ff);}section{max-width:720px;color:#0f172a;}h1{margin:0 0 8px;font-size:28px;}p{margin:0;color:#475569;line-height:1.5;}</style></head><body><main><section><h1>Local Embed Test</h1><p>This page uses the same generated embed code from the builder so you can validate the real copy-paste output.</p></section></main>${embed}</body></html>`;
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const win = window.open(url, '_blank', 'noopener,noreferrer');
    if (!win) {
      URL.revokeObjectURL(url);
      alert('Pop-up blocked. Please allow pop-ups for this site.');
      return;
    }
    window.setTimeout(() => URL.revokeObjectURL(url), 60000);
  };

  const saveConfig = async () => {
    const nextConfig = mergeConfig(config, {
      agentId: selectedAgentId,
      chatMode: config.chatMode === 'agent' && selectedAgentId ? 'agent' : config.chatMode,
      apiBaseUrl: normalizeApiBaseUrl(config.apiBaseUrl),
    });

    setSaveState('saving');
    try {
      window.localStorage.setItem(storageKeyForAgent(selectedAgentId), JSON.stringify(nextConfig));
      if (storageKeyForAgent(selectedAgentId) !== STORAGE_KEY) {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextConfig));
      }

      if (selectedAgentId) {
        const response = await fetch(`/api/agents/${selectedAgentId}`);
        if (!response.ok) throw new Error('Failed to reload agent before saving');
        const agent = (await response.json()) as AgentSummary;
        const currentCustomParams =
          agent.custom_params && typeof agent.custom_params === 'object'
            ? (agent.custom_params as Record<string, unknown>)
            : {};

        const patchResponse = await fetch(`/api/agents/${selectedAgentId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            webhook_url: nextConfig.chatMode === 'webhook' ? nextConfig.webhookUrl.trim() : undefined,
            custom_params: {
              ...currentCustomParams,
              chat_widget: nextConfig,
            },
          }),
        });

        if (!patchResponse.ok) {
          const detail = await patchResponse.text();
          throw new Error(detail || 'Failed to save agent chat settings');
        }
      }

      setConfig(nextConfig);
      setLastSavedSignature(serializeConfig(nextConfig));
      setSaveState('saved');
    } catch {
      setSaveState('error');
    }
  };

  const resetConfig = () => {
    setConfig(
      mergeConfig(initialConfig, {
        chatMode: selectedAgentId ? 'agent' : 'webhook',
        agentId: selectedAgentId,
        apiBaseUrl: normalizeApiBaseUrl(config.apiBaseUrl),
        companyName: selectedAgent?.display_name || selectedAgent?.name || initialConfig.companyName,
        welcomeMessage: selectedAgent?.welcome_message || initialConfig.welcomeMessage,
        webhookUrl: config.webhookUrl,
      }),
    );
    setSaveState('idle');
  };

  const isDirty = lastSavedSignature ? serializeConfig(config) !== lastSavedSignature : true;
  const saveButtonLabel =
    saveState === 'saving' ? 'Saving...' : saveState === 'saved' && !isDirty ? 'Saved' : saveState === 'error' ? 'Retry Save' : 'Save';
  const saveButtonClass = [
    'save-btn',
    saveState === 'saving' ? 'saving' : '',
    saveState === 'saved' && !isDirty ? 'saved' : '',
    saveState === 'error' ? 'error' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className="chatbot-dashboard root">
      <header className="head">
        <div className="brand-head">
          <div className="brand-mark">O</div>
          <div>
            <p className="kicker">OYIK.AI</p>
            <h1>{selectedAgent ? `${selectedAgent.display_name || selectedAgent.name} Chat Builder` : 'Custom Chat Builder'}</h1>
          </div>
        </div>
        <div className="head-actions">
          <button className={saveButtonClass} onClick={() => void saveConfig()} disabled={agentLoading || saveState === 'saving'}>
            {saveButtonLabel}
          </button>
          <button onClick={resetConfig}><RefreshCw size={14} /> Reset</button>
          <button onClick={copyEmbed}><Copy size={14} /> Copy Embed</button>
          <button onClick={downloadEmbed}><Download size={14} /> Download</button>
        </div>
      </header>

      <div className="layout">
        <aside className="left">
          <div className="tabs">
            <button className={tab === 'general' ? 'active' : ''} onClick={() => setTab('general')}>General</button>
            <button className={tab === 'appearance' ? 'active' : ''} onClick={() => setTab('appearance')}>Appearance</button>
            <button className={tab === 'behavior' ? 'active' : ''} onClick={() => setTab('behavior')}>Behavior</button>
            <button className={tab === 'embed' ? 'active' : ''} onClick={() => setTab('embed')}>Embed</button>
          </div>

          {tab === 'general' && (
            <div className="panel">
              <h3>Agent Link</h3>
              <label>Connected Agent</label>
              <select
                value={selectedAgentId ?? ''}
                onChange={(e) => {
                  const nextId = normalizeAgentId(e.target.value);
                  updateAgentSelection(nextId);
                }}
              >
                <option value="">Standalone widget</option>
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.display_name || agent.name}
                  </option>
                ))}
              </select>
              <p>Linking an agent lets the widget use the same prompt and tools as your built-in test chat.</p>

              <h3>Chat Engine</h3>
              <label>Mode</label>
              <select
                value={config.chatMode}
                onChange={(e) =>
                  setConfig((p) => ({
                    ...p,
                    chatMode: normalizeChatMode(e.target.value),
                    agentId: normalizeChatMode(e.target.value) === 'agent' ? selectedAgentId : p.agentId,
                    apiBaseUrl: normalizeApiBaseUrl(p.apiBaseUrl),
                  }))
                }
              >
                <option value="webhook">External webhook</option>
                <option value="agent" disabled={!selectedAgentId}>Linked agent runtime</option>
              </select>

              {config.chatMode === 'agent' ? (
                <>
                  <label>API Base URL</label>
                  <input
                    placeholder="https://oyik.info"
                    value={config.apiBaseUrl}
                    onChange={(e) => setConfig((p) => ({ ...p, apiBaseUrl: e.target.value }))}
                  />
                  <p>{buildAgentChatEndpoint(config) || 'Select an agent to build the runtime endpoint.'}</p>
                </>
              ) : (
                <>
                  <label>Webhook URL</label>
                  <input value={config.webhookUrl} onChange={(e) => setConfig((p) => ({ ...p, webhookUrl: e.target.value }))} />
                </>
              )}

              <h3>Text Content</h3>
              <label>Company Name</label>
              <input value={config.companyName} onChange={(e) => setConfig((p) => ({ ...p, companyName: e.target.value }))} />
              <label>Welcome Message</label>
              <textarea
                rows={4}
                className="welcome-textarea"
                value={config.welcomeMessage}
                onChange={(e) => setConfig((p) => ({ ...p, welcomeMessage: e.target.value }))}
              />
              <label>Input Placeholder</label>
              <input value={config.inputPlaceholder} onChange={(e) => setConfig((p) => ({ ...p, inputPlaceholder: e.target.value }))} />
              <label>Send Button Text</label>
              <input value={config.sendLabel} onChange={(e) => setConfig((p) => ({ ...p, sendLabel: e.target.value }))} />
            </div>
          )}

          {tab === 'appearance' && (
            <div className="panel">
              <h3>Launcher Icon</h3>
              <IconSelector value={config.launcherIcon} onChange={(icon) => setConfig((p) => ({ ...p, launcherIcon: icon }))} />
              <label>Launcher Icon URL</label>
              <input
                placeholder="https://example.com/icon.png"
                value={config.launcherIconUrl}
                onChange={(e) => setConfig((p) => ({ ...p, launcherIconUrl: e.target.value }))}
              />

              <h3>Message Icons</h3>
              <label>Top Header Icon</label>
              <IconSelector value={config.headerIcon} onChange={(icon) => setConfig((p) => ({ ...p, headerIcon: icon }))} />
              <label>Top Header Icon URL</label>
              <input
                placeholder="https://example.com/header-icon.png"
                value={config.headerIconUrl}
                onChange={(e) => setConfig((p) => ({ ...p, headerIconUrl: e.target.value }))}
              />
              <label>User Message Icon</label>
              <IconSelector value={config.userMessageIcon} onChange={(icon) => setConfig((p) => ({ ...p, userMessageIcon: icon }))} />
              <label>User Message Icon URL</label>
              <input
                placeholder="https://example.com/user-icon.png"
                value={config.userMessageIconUrl}
                onChange={(e) => setConfig((p) => ({ ...p, userMessageIconUrl: e.target.value }))}
              />
              <label>AI Message Icon</label>
              <IconSelector value={config.aiMessageIcon} onChange={(icon) => setConfig((p) => ({ ...p, aiMessageIcon: icon }))} />
              <label>AI Message Icon URL</label>
              <input
                placeholder="https://example.com/ai-icon.png"
                value={config.aiMessageIconUrl}
                onChange={(e) => setConfig((p) => ({ ...p, aiMessageIconUrl: e.target.value }))}
              />

              <h3>Colors</h3>
              <ColorPickerField label="Header + Send Button" value={config.colors.primary} onChange={setPrimaryColor} />
              <ColorPickerField label="Chat Background" value={config.colors.chatBackground} onChange={setChatBackground} />
              <ColorPickerField label="User Message Color" value={config.colors.sendMessage} onChange={setUserMessageColor} />
              <ColorPickerField label="AI Message Color" value={config.colors.aiMessage} onChange={setAiMessageColor} />

              <h3>Typography</h3>
              <label>Font Size</label>
              <div className="stepper">
                <button type="button" onClick={() => setConfig((p) => ({ ...p, fontSize: Math.max(11, p.fontSize - 1) }))}><Minus size={14} /></button>
                <input
                  type="number"
                  min={11}
                  max={22}
                  value={config.fontSize}
                  onChange={(e) => setConfig((p) => ({ ...p, fontSize: Number(e.target.value || 14) }))}
                />
                <button type="button" onClick={() => setConfig((p) => ({ ...p, fontSize: Math.min(22, p.fontSize + 1) }))}><Plus size={14} /></button>
              </div>
              <label>Font Family</label>
              <select value={config.fontFamily} onChange={(e) => setConfig((p) => ({ ...p, fontFamily: e.target.value as FontFamilyKey }))}>
                {FONT_FAMILY_OPTIONS.map((font) => (
                  <option key={font.key} value={font.key}>{font.label}</option>
                ))}
              </select>
            </div>
          )}

          {tab === 'behavior' && (
            <div className="panel">
              <h3>Widget Controls</h3>
              <label>Launcher Label</label>
              <input value={config.launcherLabel} onChange={(e) => setConfig((p) => ({ ...p, launcherLabel: e.target.value }))} />
              <label>Launcher Size</label>
              <input type="number" min={44} max={100} value={config.launcherSize} onChange={(e) => setConfig((p) => ({ ...p, launcherSize: Number(e.target.value || 68) }))} />
              <label>Launcher Radius</label>
              <input type="number" min={8} max={36} value={config.launcherRadius} onChange={(e) => setConfig((p) => ({ ...p, launcherRadius: Number(e.target.value || 20) }))} />
              <label>Widget Side</label>
              <select value={config.position} onChange={(e) => setConfig((p) => ({ ...p, position: e.target.value as Config['position'] }))}>
                <option value="left">Left</option>
                <option value="right">Right</option>
              </select>
              <label>Bottom Offset</label>
              <div className="stepper">
                <button type="button" onClick={() => setBottomOffset(bottomOffsetValue - 4)}><Minus size={14} /></button>
                <input type="number" min={0} value={bottomOffsetValue} onChange={(e) => setBottomOffset(Number(e.target.value || 0))} />
                <button type="button" onClick={() => setBottomOffset(bottomOffsetValue + 4)}><Plus size={14} /></button>
              </div>
              <label className="checkbox"><input type="checkbox" checked={config.autoOpen} onChange={(e) => setConfig((p) => ({ ...p, autoOpen: e.target.checked }))} /> Auto-open widget</label>
              <h3>Quick Replies</h3>
              {config.quickReplies.map((q) => (
                <div className="reply" key={q.id}>
                  <span>{q.icon}</span>
                  <span>{q.text}</span>
                  <button onClick={() => setConfig((p) => ({ ...p, quickReplies: p.quickReplies.filter((r) => r.id !== q.id) }))}>x</button>
                </div>
              ))}
              <div className="reply-add">
                <input value={draft.icon} onChange={(e) => setDraft((p) => ({ ...p, icon: e.target.value }))} placeholder="Icon" />
                <input value={draft.text} onChange={(e) => setDraft((p) => ({ ...p, text: e.target.value }))} placeholder="Line text" />
                <button onClick={addReply}><Plus size={14} /></button>
              </div>
            </div>
          )}

          {tab === 'embed' && (
            <div className="panel">
              <h3>Embed Code</h3>
              <p>Hostinger-friendly: wrapped and ready to paste.</p>
              <textarea rows={15} readOnly wrap="soft" className="embed-code" value={embed} />
              <div className="inline">
                <button onClick={copyEmbed}><Copy size={14} /> Copy Embed</button>
                <button onClick={downloadEmbed}><Download size={14} /> Download</button>
                <button onClick={openLocalEmbedTest}>Open Local Test</button>
              </div>
            </div>
          )}
        </aside>

        <section className="right">
          <div className="preview-top">
            <div className="preview-title"><Smartphone size={16} /> {previewMode === 'mobile' ? 'Mobile Preview' : 'Web Preview'}</div>
            <div className="preview-switch">
              <button className={previewMode === 'mobile' ? 'active' : ''} onClick={() => setPreviewMode('mobile')}>Mobile</button>
              <button className={previewMode === 'web' ? 'active' : ''} onClick={() => setPreviewMode('web')}>Web</button>
            </div>
          </div>
          <MobilePreview config={config} mode={previewMode} />
        </section>
      </div>

      <style jsx global>{`
        .chatbot-dashboard.root{height:100vh;overflow:hidden;display:flex;flex-direction:column;background:linear-gradient(180deg,#f8faff,#eef3ff);color:#0f172a;padding:16px;font-family:Inter,Segoe UI,sans-serif}
        .chatbot-dashboard .head{display:flex;justify-content:space-between;gap:10px;align-items:center;background:#fff;border:1px solid #dbe5f6;border-radius:14px;padding:14px 16px;margin-bottom:12px}
        .chatbot-dashboard .brand-head{display:flex;align-items:center;gap:10px;min-width:0}
        .chatbot-dashboard .brand-mark{width:38px;height:38px;border-radius:12px;display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#1d4ed8,#4f46e5);color:#fff;font-weight:800;font-size:16px;box-shadow:0 8px 18px rgba(37,99,235,.3)}
        .chatbot-dashboard .kicker{margin:0;font-size:12px;letter-spacing:.05em;color:#4f46e5;text-transform:uppercase}
        .chatbot-dashboard .head h1{margin:2px 0 0;font-size:20px;line-height:1.1}
        .chatbot-dashboard .head-actions{display:flex;gap:8px}
        .chatbot-dashboard .head-actions button{border:1px solid #d2def4;background:#fff;border-radius:10px;padding:8px 10px;cursor:pointer;display:inline-flex;gap:6px;align-items:center}
        .chatbot-dashboard .head-actions .save-btn{background:#0f172a;border-color:#0f172a;color:#fff;transition:background .22s ease,border-color .22s ease,box-shadow .22s ease,transform .18s ease}
        .chatbot-dashboard .head-actions .save-btn:hover:not(:disabled){transform:translateY(-1px);box-shadow:0 10px 24px rgba(15,23,42,.18)}
        .chatbot-dashboard .head-actions .save-btn:disabled{cursor:not-allowed;opacity:.9}
        .chatbot-dashboard .head-actions .save-btn.saving{background:#1d4ed8;border-color:#1d4ed8;box-shadow:0 0 0 4px rgba(37,99,235,.12)}
        .chatbot-dashboard .head-actions .save-btn.saved{background:#16a34a;border-color:#16a34a;box-shadow:0 0 0 4px rgba(34,197,94,.14)}
        .chatbot-dashboard .head-actions .save-btn.error{background:#dc2626;border-color:#dc2626;box-shadow:0 0 0 4px rgba(220,38,38,.12)}
        .chatbot-dashboard .layout{display:grid;grid-template-columns:minmax(340px,440px) minmax(0,1fr);gap:12px;flex:1;min-height:0;overflow:hidden}
        .chatbot-dashboard .left{background:#fff;border:1px solid #dbe5f6;border-radius:14px;overflow:hidden;display:grid;grid-template-rows:auto 1fr;min-height:0}
        .chatbot-dashboard .tabs{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;padding:10px;border-bottom:1px solid #e6ecf8}
        .chatbot-dashboard .tabs button{border:1px solid #dbe5f6;background:#f7f9ff;color:#334155;border-radius:9px;padding:8px 6px;font-size:12px;cursor:pointer}
        .chatbot-dashboard .tabs button.active{background:#eef2ff;border-color:#c7d2fe;color:#312e81;font-weight:600}
        .chatbot-dashboard .panel{overflow:auto;padding:12px;display:grid;gap:8px;align-content:start;min-height:0}
        .chatbot-dashboard .panel h3{margin:6px 0 4px;font-size:15px}
        .chatbot-dashboard .panel p{margin:0 0 8px;color:#64748b;font-size:13px}
        .chatbot-dashboard .panel label{color:#475569;font-size:12px}
        .chatbot-dashboard .panel input,.chatbot-dashboard .panel textarea,.chatbot-dashboard .panel select{width:100%;border:1px solid #d8e2f3;border-radius:10px;padding:10px;font-size:14px}
        .chatbot-dashboard .panel textarea.welcome-textarea{min-height:104px;height:104px;max-height:104px;line-height:1.45;resize:none;overflow-y:auto}
        .chatbot-dashboard .panel textarea.welcome-textarea::-webkit-scrollbar{width:6px}
        .chatbot-dashboard .panel textarea.welcome-textarea::-webkit-scrollbar-thumb{background:#cbd5e1;border-radius:999px}
        .chatbot-dashboard .inline{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
        .chatbot-dashboard .embed-code{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;font-size:12px;line-height:1.45;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;resize:vertical}
        .chatbot-dashboard .inline button,.chatbot-dashboard .panel>button{border:1px solid #d2def4;background:#fff;border-radius:10px;padding:8px 10px;cursor:pointer;display:inline-flex;gap:6px;align-items:center;width:fit-content}
        .chatbot-dashboard .icons{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
        .chatbot-dashboard .pick{border:1px solid #dbe5f6;background:#f8fbff;border-radius:10px;padding:10px;display:flex;align-items:center;justify-content:center;cursor:pointer}
        .chatbot-dashboard .pick.active{border-color:#a5b4fc;background:#eef2ff;color:#312e81;font-weight:600}
        .chatbot-dashboard .icon-svg{width:20px;height:20px;display:inline-flex;color:currentColor}
        .chatbot-dashboard .icon-svg svg{width:100%;height:100%}
        .chatbot-dashboard .icon-svg img{width:100%;height:100%;object-fit:cover;border-radius:6px}
        .chatbot-dashboard .color-field{display:grid;gap:6px;position:relative}
        .chatbot-dashboard .color-row{display:grid;grid-template-columns:40px 1fr;gap:8px}
        .chatbot-dashboard .color-swatch{border:1px solid #d1dbef;border-radius:8px;cursor:pointer}
        .chatbot-dashboard .color-pop{position:absolute;top:58px;left:0;background:#fff;border:1px solid #d8e2f3;border-radius:10px;padding:8px;z-index:12;box-shadow:0 10px 24px rgba(15,23,42,.16)}
        .chatbot-dashboard .color-pop input{width:64px;height:38px;border:none;padding:0;background:transparent}
        .chatbot-dashboard .stepper{display:grid;grid-template-columns:38px 1fr 38px;gap:8px}
        .chatbot-dashboard .stepper button{border:1px solid #d1dbef;background:#f8fbff;border-radius:10px;display:inline-flex;align-items:center;justify-content:center;cursor:pointer}
        .chatbot-dashboard .checkbox{display:flex;gap:8px;align-items:center;font-size:13px}
        .chatbot-dashboard .checkbox input{width:auto}
        .chatbot-dashboard .reply{border:1px solid #dbe5f6;background:#f8fbff;border-radius:10px;padding:8px 10px;display:grid;grid-template-columns:auto 1fr auto;gap:8px;align-items:center}
        .chatbot-dashboard .reply button{border:1px solid #d1dbef;background:#fff;border-radius:8px;cursor:pointer;padding:2px 8px}
        .chatbot-dashboard .reply-add{display:grid;grid-template-columns:74px 1fr 42px;gap:8px}
        .chatbot-dashboard .reply-add button{border:1px solid #d1dbef;background:#eef2ff;border-radius:10px;color:#312e81;cursor:pointer;display:inline-flex;align-items:center;justify-content:center}
        .chatbot-dashboard .right{background:#fff;border:1px solid #dbe5f6;border-radius:14px;padding:12px;display:grid;grid-template-rows:auto 1fr;gap:10px;min-height:0;overflow:hidden}
        .chatbot-dashboard .preview-top{display:flex;justify-content:space-between;align-items:center;gap:10px}
        .chatbot-dashboard .preview-title{font-size:14px;color:#1e293b;display:inline-flex;gap:8px;align-items:center;font-weight:600}
        .chatbot-dashboard .preview-switch{display:inline-flex;border:1px solid #d3def3;border-radius:10px;background:#f8faff;padding:3px}
        .chatbot-dashboard .preview-switch button{border:none;background:transparent;padding:6px 10px;font-size:12px;border-radius:8px;color:#475569;cursor:pointer}
        .chatbot-dashboard .preview-switch button.active{background:#e9efff;color:#1e3a8a;font-weight:700}
        .chatbot-dashboard .phone-wrap{border:1px solid #d7e2f4;border-radius:12px;height:100%;min-height:0;display:flex;align-items:center;justify-content:center;padding:14px;overflow:hidden}
        .chatbot-dashboard .device-shell{position:relative;box-shadow:0 18px 38px rgba(15,23,42,.24);overflow:hidden;background:#0f172a}
        .chatbot-dashboard .device-shell.mobile{width:334px;height:684px;max-height:100%;border-radius:42px;padding:11px;background:linear-gradient(165deg,#0f172a,#0b132e);box-shadow:0 26px 50px rgba(2,6,23,.35),inset 0 0 0 1px rgba(255,255,255,.06)}
        .chatbot-dashboard .device-shell.web{width:100%;height:100%;border-radius:18px;padding:0}
        .chatbot-dashboard .statusbar{position:absolute;top:12px;left:18px;right:18px;z-index:6;color:#e2e8f0;font-size:11px;display:flex;justify-content:space-between;pointer-events:none}
        .chatbot-dashboard .status-icons{font-weight:600;letter-spacing:.02em}
        .chatbot-dashboard .notch{position:absolute;top:12px;left:50%;transform:translateX(-50%);width:126px;height:25px;border-radius:999px;background:#050a18;z-index:5;box-shadow:inset 0 -2px 4px rgba(255,255,255,.04)}
        .chatbot-dashboard .browser-bar{height:36px;background:#e2e8f0;display:flex;align-items:center;gap:7px;padding:0 12px;position:relative}
        .chatbot-dashboard .browser-bar span{width:8px;height:8px;border-radius:50%;background:#94a3b8}
        .chatbot-dashboard .browser-bar p{position:absolute;left:50%;transform:translateX(-50%);margin:0;font-size:12px;color:#334155;font-weight:600}
        .chatbot-dashboard .screen{width:100%;height:100%;border-radius:31px;overflow:hidden;position:relative;background:#f2f6ff}
        .chatbot-dashboard .device-shell.web .screen{border-radius:0 0 18px 18px;height:calc(100% - 36px)}
        .chatbot-dashboard .landing{position:absolute;inset:0;display:flex;flex-direction:column;background:linear-gradient(180deg,#ffffff,#eff5ff);padding:14px;gap:10px}
        .chatbot-dashboard .landing.mobile{padding-top:28px}
        .chatbot-dashboard .landing-header{display:flex;justify-content:space-between;align-items:center}
        .chatbot-dashboard .landing-logo{font-size:14px;font-weight:800;color:#1e3a8a}
        .chatbot-dashboard .landing-header button{border:none;background:#1d4ed8;color:#fff;border-radius:10px;padding:7px 11px;font-size:12px}
        .chatbot-dashboard .landing-hero{background:#e0ebff;border-radius:14px;padding:12px}
        .chatbot-dashboard .landing-hero h3{margin:0;font-size:16px;color:#0f172a}
        .chatbot-dashboard .landing-hero p{margin:6px 0 0;font-size:12px;color:#475569}
        .chatbot-dashboard .landing-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:9px}
        .chatbot-dashboard .house-card{background:#fff;border-radius:12px;overflow:hidden;box-shadow:inset 0 0 0 1px #dbe7ff}
        .chatbot-dashboard .house-card img{display:block;width:100%;height:82px;object-fit:cover}
        .chatbot-dashboard .house-card p{margin:8px;font-size:11px;color:#334155;line-height:1.3}
        .chatbot-dashboard .widget{position:absolute;border-style:solid;border-color:rgba(255,255,255,.16);overflow:hidden;display:flex;flex-direction:column;box-shadow:0 16px 32px rgba(2,6,23,.32)}
        .chatbot-dashboard .widget.mobile{right:10px;left:auto;bottom:92px;width:min(308px,calc(100% - 20px));height:min(520px,calc(100% - 132px))}
        .chatbot-dashboard .widget.mobile.open{inset:0;width:100%;height:100%;border-radius:0 !important;border-width:0 !important;box-shadow:none}
        .chatbot-dashboard .widget.web{right:16px;left:auto;bottom:14px;width:min(280px,calc(100% - 24px));height:calc(100% - 28px)}
        .chatbot-dashboard .widget.web .widget-head{padding:10px 11px;font-size:13px}
        .chatbot-dashboard .widget.web .widget-head button{padding:3px 7px;font-size:11px}
        .chatbot-dashboard .widget.web .widget-body{padding:8px;gap:7px}
        .chatbot-dashboard .widget.web .bubble{max-width:88%;padding:8px 9px;font-size:12px;border-radius:10px}
        .chatbot-dashboard .widget.web .quick-wrap button{padding:6px 8px;font-size:11px}
        .chatbot-dashboard .widget.web .property-card{min-width:146px;max-width:146px}
        .chatbot-dashboard .widget.web .property-image{height:84px}
        .chatbot-dashboard .widget.web .property-title{font-size:11px}
        .chatbot-dashboard .widget.web .property-subtitle{font-size:10px}
        .chatbot-dashboard .widget.web .property-price{font-size:16px}
        .chatbot-dashboard .widget.web .widget-input{gap:6px;padding:7px}
        .chatbot-dashboard .widget.web .widget-input input{padding:8px 9px;font-size:12px}
        .chatbot-dashboard .widget.web .widget-input button{padding:8px 10px;font-size:12px}
        .chatbot-dashboard .widget.mobile.open .widget-head{padding:12px 14px}
        .chatbot-dashboard .widget.mobile.open .widget-body{padding:10px}
        .chatbot-dashboard .widget.mobile.open .bubble{font-size:13px}
        .chatbot-dashboard .launcher.web .icon-svg{width:18px;height:18px}
        .chatbot-dashboard .launcher.web span{font-size:9px}
        .chatbot-dashboard .widget-head{padding:12px 14px;color:#fff;display:flex;justify-content:space-between;align-items:center}
        .chatbot-dashboard .head-left{display:flex;align-items:center;gap:8px;min-width:0}
        .chatbot-dashboard .head-left strong{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .chatbot-dashboard .avatar{width:22px;height:22px;border-radius:999px;background:rgba(255,255,255,.18);display:inline-flex;align-items:center;justify-content:center;flex:0 0 auto}
        .chatbot-dashboard .avatar.user{background:rgba(255,255,255,.14)}
        .chatbot-dashboard .head-avatar{width:24px;height:24px}
        .chatbot-dashboard .icon-svg.mini,.chatbot-dashboard .icon-svg.msg-icon{width:14px;height:14px}
        .chatbot-dashboard .widget-head button{border:none;background:rgba(255,255,255,.24);color:#fff;border-radius:9px;padding:4px 8px;cursor:pointer}
        .chatbot-dashboard .widget-body{flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:8px}
        .chatbot-dashboard .widget-body::-webkit-scrollbar{width:6px}
        .chatbot-dashboard .widget-body::-webkit-scrollbar-thumb{background:rgba(255,255,255,.22);border-radius:6px}
        .chatbot-dashboard .message-block{display:flex;flex-direction:column;gap:8px}
        .chatbot-dashboard .row{display:flex;align-items:flex-end;gap:6px}
        .chatbot-dashboard .row.u{justify-content:flex-end}
        .chatbot-dashboard .row.b{justify-content:flex-start}
        .chatbot-dashboard .bubble{max-width:84%;border-radius:12px;padding:9px 11px;font-size:14px}
        .chatbot-dashboard .property-rail{display:flex;gap:10px;overflow-x:auto;padding:2px 2px 6px;scrollbar-width:thin}
        .chatbot-dashboard .property-rail::-webkit-scrollbar{height:6px}
        .chatbot-dashboard .property-rail::-webkit-scrollbar-thumb{background:rgba(255,255,255,.25);border-radius:6px}
        .chatbot-dashboard .property-card{min-width:168px;max-width:168px;background:#fff;border-radius:14px;overflow:hidden;box-shadow:inset 0 0 0 1px rgba(15,23,42,.08)}
        .chatbot-dashboard .property-image{height:96px;background:#e2e8f0;display:flex;align-items:center;justify-content:center}
        .chatbot-dashboard .property-image img{width:100%;height:100%;object-fit:cover}
        .chatbot-dashboard .property-image span{font-size:12px;color:#64748b}
        .chatbot-dashboard .property-content{padding:8px 9px 9px;color:#0f172a}
        .chatbot-dashboard .property-title{margin:0;font-size:12px;font-weight:700;line-height:1.35}
        .chatbot-dashboard .property-subtitle{margin:5px 0 0;font-size:11px;line-height:1.3;color:#475569}
        .chatbot-dashboard .property-price{margin:7px 0 0;font-size:20px;font-weight:800;letter-spacing:-.02em}
        .chatbot-dashboard .quick-wrap{display:flex;flex-wrap:wrap;gap:8px}
        .chatbot-dashboard .quick-wrap button{border:1px solid rgba(255,255,255,.2);background:rgba(255,255,255,.08);color:#fff;border-radius:999px;padding:7px 10px;font-size:12px;cursor:pointer}
        .chatbot-dashboard .typing{color:rgba(255,255,255,.74);font-size:12px}
        .chatbot-dashboard .typing-dots{display:inline-flex;align-items:center;gap:5px;padding:6px 8px}
        .chatbot-dashboard .typing-dots span{width:6px;height:6px;border-radius:999px;background:rgba(255,255,255,.82);display:inline-block;animation:chatTypingDot 1.2s infinite ease-in-out}
        .chatbot-dashboard .typing-dots span:nth-child(2){animation-delay:.15s}
        .chatbot-dashboard .typing-dots span:nth-child(3){animation-delay:.3s}
        @keyframes chatTypingDot{0%,80%,100%{transform:translateY(0);opacity:.35}40%{transform:translateY(-4px);opacity:1}}
        .chatbot-dashboard .widget-input{display:flex;gap:7px;border-top:1px solid rgba(255,255,255,.14);padding:9px}
        .chatbot-dashboard .widget-input input{flex:1;border:none;border-radius:9px;padding:9px 10px;font-size:13px}
        .chatbot-dashboard .widget-input button{border:none;border-radius:9px;padding:9px 12px;cursor:pointer;color:#fff;background:#ff6b35;font-size:13px}
        .chatbot-dashboard .powered-by{font-size:11px;color:rgba(255,255,255,.68);text-align:center;padding:0 0 8px;letter-spacing:.01em}
        .chatbot-dashboard .powered-by a{color:inherit;text-decoration:none}
        .chatbot-dashboard .powered-by a:hover{text-decoration:underline;color:#fff}
        .chatbot-dashboard .widget.web .powered-by{font-size:10px;padding:0 0 6px}
        .chatbot-dashboard .launcher{position:absolute;border:none;color:#fff;cursor:pointer;display:inline-flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;box-shadow:0 12px 24px rgba(0,0,0,.24);z-index:3}
        .chatbot-dashboard .launcher span{font-size:10px;font-weight:600}
        @media (max-width:1100px){
          .chatbot-dashboard .layout{grid-template-columns:1fr}
          .chatbot-dashboard .left{max-height:360px}
        }
        @media (max-width:760px){
          .chatbot-dashboard.root{padding:10px}
          .chatbot-dashboard .head{flex-direction:column;align-items:flex-start}
          .chatbot-dashboard .head-actions{width:100%;display:grid;grid-template-columns:1fr 1fr 1fr}
          .chatbot-dashboard .tabs{grid-template-columns:1fr 1fr}
          .chatbot-dashboard .device-shell.mobile{width:302px;height:618px}
          .chatbot-dashboard .landing-grid{grid-template-columns:1fr 1fr}
          .chatbot-dashboard .widget.mobile{width:min(280px,calc(100% - 16px));height:min(452px,calc(100% - 124px))}
        }
      `}</style>
    </div>
  );
}

export default function ChatbotDashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-[#eef3ff] text-sm text-slate-600">
          Loading chat builder...
        </div>
      }
    >
      <ChatbotDashboardPageContent />
    </Suspense>
  );
}

