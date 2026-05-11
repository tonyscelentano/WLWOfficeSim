/**
 * api.js — Unified API wrapper with offline detection.
 * Depends on: globals.js (isOffline), ui_render.js (appendLog — runtime ref only)
 */

// ============================================================================
// 📡 API COMMUNICATION
// ============================================================================

import { Globals } from './globals.js';
import { appendLog } from './ui_render.js';

export async function api(path, body, method = "POST") {
    try {
        const options = {
            method: method,
            headers: { "Content-Type": "application/json" }
        };
        if (method === "POST") options.body = JSON.stringify(body || {});

        const res = await fetch(path, options);

        // Handle application-level errors (HR blocks, state conflicts)
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            const msg = errorData.error || `HTTP ${res.status}`;

            if (res.status === 403 || res.status === 409) {
                appendLog(msg, "error", "HR / AUTH");
                return { error: msg };
            }
            throw new Error(msg);
        }

        const data = await res.json();
        if (data.error) appendLog(data.error, "error", "API Error");

        if (Globals.isOffline) {
            Globals.isOffline = false;
            appendLog("Connection restored.", "success-event", "Network");
        }
        return data;
    } catch (err) {
        if (!Globals.isOffline) {
            Globals.isOffline = true;
            appendLog(`Connection lost: ${err.message}`, "error", "Network");
        }
        return { error: "Connection lost." };
    }
}
