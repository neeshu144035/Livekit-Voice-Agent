# LiveKit Telephony & SIP Trunk Setup Guide

This guide explains how to connect your Twilio phone number to your self-hosted LiveKit Voice Agent using SIP Trunking.

## Prerequisites
1.  **A Twilio Account**: You need a paid Twilio account to use Elastic SIP Trunking.
2.  **LiveKit Server IP**: Your server's public IP address (Current: `13.135.81.172`).
3.  **LiveKit SIP Port**: Default is `5060`.

---

## Step 1: Purchase a Twilio Phone Number
1.  Go to **Twilio Console** → **Phone Numbers** → **Manage** → **Buy a Number**.
2.  Purchase a number that supports **Voice**.
3.  Note the number in E.164 format (e.g., `+1234567890`).

---

## Step 2: Create a Twilio Elastic SIP Trunk
1.  Go to **Elastic SIP Trunking** → **Manage** → **Trunks**.
2.  Click **Create new SIP Trunk**.
3.  **Friendly Name**: e.g., `LiveKit-Voice-Trunk`.

### Configuration Sections:

#### A. Origination (Inbound Calls - From Twilio to LiveKit)
This tells Twilio where to send calls when someone dials your number.
1.  Go to the **Origination** tab.
2.  Click **Add new Origination URI**.
3.  **SIP URI**: `sip:13.135.81.172:5060`
4.  **Priority/Weight**: Set both to `10`.
5.  Click **Add**.

#### B. Termination (Outbound Calls - From LiveKit to Twilio)
This allows your agent to call OUT to real phone numbers.
1.  Go to the **Termination** tab.
2.  **Termination SIP URI**: Choose a unique "localized" URI, e.g., `oyik.pstn.twilio.com`.
    *   **CRITICAL**: This must be a domain ending in `.pstn.twilio.com`. Do NOT use an IP address or a friendly name here.
3.  **Authentication**: We recommend **IP Access Control List** for simplicity.
    *   Create a new IP ACL.
    *   Name: `LiveKit-Server`.
    *   IP Address: `13.135.81.172`.
4.  (Optional) If you prefer username/password, create a **Credential List** instead.

#### C. Numbers
1.  Go to the **Numbers** tab in the trunk.
2.  Click **Add a Number** and select the number you bought in Step 1.

---

## Step 3: Add the Number to Your Dashboard
Now, register this number in your LiveKit Dashboard so it knows how to route the calls.

1.  Click **Add Number** on the Phone Numbers page.
2.  **Phone Number**: The number you bought (e.g., `+1234567890`).
3.  **Termination URI**: The URI you created in Step 2.B (e.g., `yourcompany.pstn.twilio.com`).
4.  **SIP Credentials**: 
    *   If using **IP Access Control**, leave Username and Password **blank**.
    *   If using **Credential List**, enter the username and password you created.
5.  **Inbound Agent**: Select which agent (e.g., Sarah) should answer when this number is called.
6.  Click **Add Phone Number**.

---

## Step 4: Verification & Debugging
1.  **Inbound**: Call your Twilio number from your mobile. You should see logs in the `voice-agent` container and the agent should pick up.
2.  **Outbound**: Use the "Call Out" button on the dashboard. Enter your mobile number. The agent should call you.

### Common Issues:
*   **Silence**: Ensure your `voice-agent` has valid LLM API keys.
*   **403 Forbidden**: Usually means the IP Access Control List in Twilio doesn't match your server's public IP.
*   **No Ringing**: Ensure port `5060` (SIP) and `10000-20000` (RTP) are open in your server firewall.
