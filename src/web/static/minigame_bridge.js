/**
 * minigame_bridge.js — Minigame launch, vitals sync, and iframe postMessage bridge.
 * Depends on: globals.js (currentMinigameContext), ui_registry.js (UI),
 *             ui_render.js (appendLog, renderStats), api.js (api)
 */

// ============================================================================
// 🧩 MINIGAME ENGINE
// ============================================================================

import { api } from './api.js';
import { appendLog, renderStats } from './ui_render.js';
import { Globals } from './globals.js';
import { UI } from './ui_registry.js';
import { stopPolling, startPolling, loadState, submitAction } from './main.js';

window.updateVitals = async function(energyDelta, stressDelta) {
    // 1. Optimistic UI update for immediate feedback
    let energyText = UI.stats.energy.val.textContent;
    let stressText = UI.stats.stress.val.textContent;

    let energy = parseInt(energyText.split("/")[0]) || 0;
    let stress = parseInt(stressText.split("/")[0]) || 0;

    energy = Math.max(0, Math.min(100, energy + energyDelta));
    stress = Math.max(0, Math.min(100, stress + stressDelta));

    UI.stats.energy.val.textContent = `${energy} / 100`;
    UI.stats.energy.bar.style.width = `${energy}%`;
    UI.stats.stress.val.textContent = `${stress} / 100`;
    UI.stats.stress.bar.style.width = `${stress}%`;

    // Visual feedback
    if (energyDelta < 0) UI.stats.energy.val.classList.add("bad-impact");
    else if (energyDelta > 0) UI.stats.energy.val.classList.add("good-impact");
    if (stressDelta > 0) UI.stats.stress.val.classList.add("bad-impact");
    else if (stressDelta < 0) UI.stats.stress.val.classList.add("good-impact");

    setTimeout(() => {
        UI.stats.energy.val.classList.remove("bad-impact", "good-impact");
        UI.stats.stress.val.classList.remove("bad-impact", "good-impact");
    }, 1000);

    // 2. Persist to server
    const data = await api("/api/player/vitals", { energy: energyDelta, stress: stressDelta });
    if (!data.error && data.state) {
        renderStats(data.state);
    }
};

window.showMinigame = function(title, type, context = "work") {
    Globals.currentMinigameContext = context;
    const titleEl = document.getElementById("minigameTitle");
    const container = document.getElementById("minigameContainer");
    if (titleEl) titleEl.textContent = title;
    if (container) {
        container.innerHTML = `<iframe src="/minigames/${type}/" id="minigame_frame" style="width:100%;height:650px;border:none;"></iframe>`;
    }
    UI.panels.minigame.classList.remove("hidden");
    stopPolling();
};

export function initMinigameBridge() {
    window.addEventListener("message", (event) => {
        const msg = event.data;
        if (!msg || !msg.type) return;

        if (msg.type === "vitals:update") {
            if (window.updateVitals) {
                window.updateVitals(msg.energy || 0, msg.stress || 0);
            }
            return;
        }

        if (msg.type === "minigame:ready") {
            const frame = document.getElementById("minigame_frame");
            const title = document.getElementById("minigameTitle")?.textContent || "Task";
            if (frame) frame.contentWindow.postMessage({ type: "parent:start", task_title: title }, "*");
        } else if (msg.type === "minigame:complete") {
            UI.panels.minigame.classList.add("hidden");
            startPolling();
            appendLog(`Task Completed: ${msg.outcome.toUpperCase()}`, "success-event", "SYSTEM");

            // Only trigger backend finalization if this was a WORK task.
            // Slacking rewards are already handled via real-time vitals:update messages.
            if (Globals.currentMinigameContext === "work") {
                submitAction("work", { outcome: msg.outcome });
            } else {
                loadState();
            }
        }
    });
}
