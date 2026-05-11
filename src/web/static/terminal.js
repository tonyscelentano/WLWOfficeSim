/**
 * terminal.js — Terminal session state and command dispatcher.
 * Depends on: globals.js, ui_registry.js (UI), ui_render.js (appendLog)
 *
 * Owns:
 *   - TerminalSession: tracks social mode, current NPC, conversation context
 *   - handleTerminalCommand: slash-command parser (/help, /status, /clear, /chat)
 *   - showHelp: displays available commands in terminal log
 */

// ============================================================================
// 🔌 TERMINAL SESSION (Social Mode State Machine)
// ============================================================================

import { Globals } from './globals.js';
import { UI } from './ui_registry.js';
import { api } from './api.js';
import { appendLog } from './ui_render.js';
import { WorkMenu } from './work_menu.js';

export const TerminalSession = {
    mode: "work",               // "work" | "social"
    npc_id: null,
    npc_name: null,
    conversationId: null,       // future: multi-turn thread ID for LLM context

    enterSocialMode(npc_id, npc_name) {
        this.mode = "social";
        this.npc_id = npc_id;
        this.npc_name = npc_name;
        this.conversationId = `${npc_id}_${Date.now()}`;
    },

    exitSocialMode() {
        this.mode = "work";
        this.npc_id = null;
        this.npc_name = null;
        this.conversationId = null;
    },

    /** Call after every action response to sync terminal mode with scene context. */
    syncFromResult(result) {
        if (result && result.npc_id) {
            // Stay in or enter social mode if an NPC is involved
            if (this.npc_id !== result.npc_id) {
                this.enterSocialMode(result.npc_id, result.npc_name || result.npc_id);
            }
        } else if (this.mode === "social") {
            // Exit social mode if the action didn't involve an NPC
            this.exitSocialMode();
        }
    },

    /** Build the payload for /api/action based on current terminal context. */
    buildPayload(verb, input) {
        const payload = { verb, input };
        if (this.mode === "social" && this.npc_id) {
            payload.npc_id = this.npc_id;
            if (this.conversationId) {
                payload.conversation_id = this.conversationId;
            }
        }
        return payload;
    },

    /** Resolve what verb/payload a bare Enter keypress should submit. */
    resolveDefaultAction(input) {
        if (this.mode === "social") {
            return { verb: "socialize", extra: { npc_id: this.npc_id } };
        }
        return { verb: "work", extra: {} };
    }
};


// ============================================================================
// ⌨️ TERMINAL COMMAND DISPATCHER
// ============================================================================

function showHelp() {
    appendLog("--- [ TERMINAL ACCESS GRANTED ] ---", "success-event", "HELP");
    appendLog("<b>/help</b> - Display authorized command protocols", "system", "HELP");
    appendLog("<b>/status</b> - Diagnostic report of current vital signs", "system", "HELP");
    appendLog("<b>/clear</b> - Purge terminal buffer (cosmetic)", "system", "HELP");
    appendLog("<b>/chat &lt;message&gt;</b> - Send a chat message to current NPC", "system", "HELP");
    appendLog("<b>work</b> - Access the Assignment Task Router", "system", "HELP");
    appendLog("<b>socialize</b> - Initiate interpersonal networking", "system", "HELP");
    appendLog("<b>learn</b> - Access corporate training modules", "system", "HELP");
}

/**
 * Parse terminal input for slash-commands and built-in keywords.
 * Returns true if the command was handled (caller should clear input and stop).
 */
export function handleTerminalCommand(input) {
    const cmd = input.toLowerCase();
    if (cmd === "/help") {
        showHelp();
        return true;
    }
    if (cmd === "/status") {
        appendLog(`NAME: ${UI.stats.name.textContent} | DEPT: ${UI.stats.dept.textContent}`, "system", "DIAG");
        appendLog(`XP: ${UI.stats.xp.textContent} | REP: ${UI.stats.rep.textContent}`, "system", "DIAG");
        if (TerminalSession.mode === "social") {
            appendLog(`CHAT: ${TerminalSession.npc_name || "Unknown"} (${TerminalSession.npc_id})`, "system", "DIAG");
        }
        return true;
    }
    if (cmd === "/clear") {
        UI.display.log.innerHTML = "";
        appendLog("Terminal buffer purged.", "system", "KERN");
        return true;
    }
    if (cmd === "work") {
        if (typeof WorkMenu !== 'undefined') WorkMenu.open();
        return true;
    }
    return false;
}
