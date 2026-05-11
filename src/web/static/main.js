/**
 * 🏢 OFFICESIM — MAIN CONTROLLER (Post-Refactor)
 *
 * This file is now a thin orchestration layer. It owns:
 *   - TutorialController class
 *   - State orchestration (loadState, polling, phase routing)
 *   - Game controllers (startNewCareer, loadGame, handleLogout, etc.)
 *   - DOMContentLoaded event wiring
 *
 * All rendering lives in ui_render.js
 * Terminal parsing lives in terminal.js
 * Minigame bridge lives in minigame_bridge.js
 * DOM references live in ui_registry.js
 * Shared state lives in globals.js
 * API calls live in api.js
 */

// ============================================================================
// 🎓 TUTORIAL CONTROLLER
// ============================================================================

import { Globals } from './globals.js';
import { UI, initRegistry, initTutorialRegistry } from './ui_registry.js';
import { api } from './api.js';
import { appendLog, showBootSequence, updateScene, renderStats, renderSaveSlots, renderRoster } from './ui_render.js';
import { TerminalSession, handleTerminalCommand } from './terminal.js';
import { initMinigameBridge } from './minigame_bridge.js';
import { WorkMenu } from './work_menu.js';
import { DeckCreator } from './deck_creator.js';

class TutorialController {
    constructor() {
        this.steps = [
            {
                target: ".sidebar-left",
                text: "This is your vitals and skills panel. Keep an eye on your Energy and Stress—don't work too hard or HR will get concerned!",
                pos: "right"
            },
            {
                target: "#rosterList",
                text: "Your social network. Click a name to chat with them! Unlock more contacts at the watercooler or during meetings.",
                pos: "right"
            },
            {
                target: ".sidebar-right",
                text: "The Terminal Log tracks everything. Every event, conversation, and corporate directive appears here in real-time.",
                pos: "left"
            },
            {
                target: "#actionInput",
                text: "This is your main interface. Type intended actions or chat messages here. Use /help for a list of quick commands.",
                pos: "top"
            },
            {
                target: ".button-group",
                text: "These buttons provide quick access to core actions. Use them to Work, Socialize, or Slack Off when management isn't looking.",
                pos: "top"
            }
        ];
        this.currentStep = 0;
    }

    start(onboardingContext) {
        if (!UI.tutorial.overlay) return;
        this.onboarding = onboardingContext;
        UI.tutorial.overlay.classList.remove("hidden");
        this.currentStep = 0;
        this.showStep();
    }

    showStep() {
        const step = this.steps[this.currentStep];
        const targetEl = document.querySelector(step.target);

        // Remove old highlights
        document.querySelectorAll(".tutorial-highlight").forEach(el => {
            el.classList.remove("tutorial-highlight");
        });

        if (!targetEl) {
            console.warn("Tutorial target not found:", step.target);
            this.next();
            return;
        }

        // Apply highlight to target
        targetEl.classList.add("tutorial-highlight");
        targetEl.scrollIntoView({ behavior: "smooth", block: "nearest" });

        const card = UI.tutorial.card;
        const text = UI.tutorial.text;
        const count = UI.tutorial.stepCount;

        text.textContent = step.text;
        if (count) count.textContent = `${this.currentStep + 1} / ${this.steps.length}`;

        // Trigger enter animation
        card.classList.remove("step-enter");
        void card.offsetWidth; // Force reflow
        card.classList.add("step-enter");

        // Position card after a brief delay to allow layout to settle
        requestAnimationFrame(() => {
            const rect = targetEl.getBoundingClientRect();
            const cardRect = card.getBoundingClientRect();
            let top = 0, left = 0;
            const baseSize = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
            const offset = baseSize * 1.5;
            const margin = baseSize * 1.25;

            if (step.pos === "right") {
                top = rect.top + (rect.height / 2) - (cardRect.height / 2);
                left = rect.right + offset;
            } else if (step.pos === "left") {
                top = rect.top + (rect.height / 2) - (cardRect.height / 2);
                left = rect.left - cardRect.width - offset;
            } else if (step.pos === "top") {
                top = rect.top - cardRect.height - offset;
                left = rect.left + (rect.width / 2) - (cardRect.width / 2);
            }

            // Boundary checks
            top = Math.max(margin, Math.min(top, window.innerHeight - cardRect.height - margin));
            left = Math.max(margin, Math.min(left, window.innerWidth - cardRect.width - margin));

            card.style.top = `${top}px`;
            card.style.left = `${left}px`;

            // Position arrow (optional, keep simple for now)
            const arrow = card.querySelector(".tutorial-arrow");
            if (arrow) arrow.style.display = "none";
        });
    }

    next() {
        this.currentStep++;
        if (this.currentStep < this.steps.length) {
            this.showStep();
        } else {
            this.finish();
        }
    }

    async finish() {
        UI.tutorial.overlay.classList.add("hidden");
        document.querySelectorAll(".tutorial-highlight").forEach(el => {
            el.classList.remove("tutorial-highlight");
        });

        // Notify backend to persist tutorial completion
        await api("/api/tutorial/finish");

        appendLog("Tutorial completed. You are now authorized to perform work duties.", "success-event", "SYSTEM");
        showBootSequence(this.onboarding);
    }
}

const Tutorial = new TutorialController();

const NIM_KEY_STORAGE_KEY = "officesim:nvidia-nim-api-key";


// ============================================================================
// 🔄 STATE ORCHESTRATION
// ============================================================================

export async function loadState() {
    const data = await api("/api/state", null, "GET");
    if (data.error) return;

    const wasGameHidden = UI.panels.game.classList.contains("hidden");

    // Toggle Visibility
    UI.panels.menu.classList.toggle("hidden", data.phase !== "menu");
    UI.panels.application.classList.toggle("hidden", data.phase !== "application");
    UI.panels.onboarding.classList.toggle("hidden", data.phase !== "onboarding");
    UI.panels.onboardingPacket.classList.toggle("hidden", data.phase !== "result");
    UI.panels.game.classList.toggle("hidden", data.phase !== "game");

    if (data.phase !== "game") {
        TerminalSession.exitSocialMode();
    }

    if (data.phase === "menu") {
        renderSaveSlots(data.saves || []);
        stopPolling();
    } else if (data.phase === "application") {
        const app = data.application || {};
        document.getElementById("appName").value = app.name || "";
        document.getElementById("appAge").value = app.age || "";
        document.getElementById("appWorkHistory").value = app.work_history || "";
        document.getElementById("appPreferredRole").value = app.preferred_role || "";
        document.getElementById("appName").focus();
    } else if (data.phase === "onboarding") {
        UI.display.question.textContent = data.question || "Loading...";
        updateScene(UI.display.onboardingScene, data.scene || "");
    } else if (data.phase === "result") {
        const onboard = data.onboarding || {};
        document.getElementById("resultFlavor").textContent = onboard.flavor || "You're hired.";
        document.getElementById("resultRole").textContent = onboard.role || "Employee";
        document.getElementById("resultDept").textContent = `${onboard.pillar}.${onboard.path}.${onboard.cluster}`;
        stopPolling();
    } else if (data.phase === "game") {
        const logCount = UI.display.log && UI.display.log.children ? UI.display.log.children.length : 0;
        const isFirstLoad = wasGameHidden || logCount === 0;
        renderStats(data.state);
        renderRoster(data.state);
        updateScene(UI.display.scene, data.scene || "");
        startPolling();
        if (isFirstLoad) {
            UI.display.log.innerHTML = "";
            if (data.is_load) {
                appendLog("You clock back into work.", "success-event", "SYSTEM");
            } else if (data.state && !data.state.tutorial_done) {
                Tutorial.start(data.onboarding);
            } else {
                showBootSequence(data.onboarding);
            }
        }
    }
}

let eventSource = null;

export function startPolling() {
    if (eventSource) return;
    eventSource = new EventSource("/api/stream");
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.phase === "game" && !data.error && data.state) {
            renderStats(data.state);
        }
    };
    eventSource.onerror = (err) => {
        console.error("SSE Connection Error. Retrying...");
    };
}

export function stopPolling() {
    if (eventSource) { 
        eventSource.close(); 
        eventSource = null; 
    }
    // Also clear old interval if it somehow exists
    if (typeof pollInterval !== "undefined" && pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}


// ============================================================================
// 🎮 GAME CONTROLLERS
// ============================================================================

export async function startNewCareer() {
    if (!await syncNimKeyFromMenu()) return;
    const data = await api("/api/new-career");
    if (!data.error) loadState();
}

export async function loadGame(slot) {
    if (!await syncNimKeyFromMenu()) return;
    const data = await api("/api/load", { slot });
    if (!data.error) loadState();
}

export async function handleLogout() {
    const data = await api("/api/logout");
    if (data.error) {
        if (confirm("Server unresponsive. Force return to menu?")) location.reload();
    } else {
        loadState();
    }
}

async function submitApplication(e) {
    e.preventDefault();
    UI.btns.submitApp.disabled = true;
    const data = await api("/api/application/submit", {
        name: document.getElementById("appName").value.trim(),
        age: document.getElementById("appAge").value.trim(),
        work_history: document.getElementById("appWorkHistory").value.trim(),
        preferred_role: document.getElementById("appPreferredRole").value.trim()
    });
    UI.btns.submitApp.disabled = false;
    if (!data.error) loadState();
}

async function submitAnswer() {
    const answer = UI.forms.answer.value.trim();
    if (!answer) return;
    appendLog(answer, "user", "Candidate");
    UI.forms.answer.value = "";
    const data = await api("/api/onboarding/answer", { answer });
    if (!data.error) loadState();
}

async function beginCareer() {
    const data = await api("/api/onboarding/confirm");
    if (!data.error) loadState();
}

function setNimKeyStatus(message, isConfigured = false) {
    UI.config.nimKeyStatus.textContent = message;
    UI.config.nimKeyStatus.classList.toggle("configured", isConfigured);
}

function readNimKeyFromMenu() {
    return UI.config.nimApiKey.value.trim();
}

async function syncNimKeyFromMenu() {
    const apiKey = readNimKeyFromMenu();
    localStorage.setItem(NIM_KEY_STORAGE_KEY, apiKey);

    const data = await api("/api/config/nim-key", { api_key: apiKey });
    if (data.error) {
        setNimKeyStatus(data.error, false);
        return false;
    }

    setNimKeyStatus(
        data.configured ? "NIM key configured for this session." : "NIM key not configured. Local fallback mode will be used.",
        Boolean(data.configured),
    );
    return true;
}

async function saveNimKey(e) {
    e.preventDefault();
    await syncNimKeyFromMenu();
}

function restoreNimKey() {
    const saved = localStorage.getItem(NIM_KEY_STORAGE_KEY) || "";
    UI.config.nimApiKey.value = saved;
    setNimKeyStatus(
        saved ? "NIM key saved in this browser. It will be sent when you start or load." : "NIM key not configured.",
        Boolean(saved),
    );
}


export async function submitAction(verb, extraData = {}) {
    const input = UI.forms.action.value.trim();
    appendLog(`[${verb.toUpperCase()}] ${input || "..."}`, "user", "Player");
    UI.forms.action.disabled = true;

    // Use TerminalSession to base our payload (handles conversation_id and default npc_id)
    const payload = TerminalSession.buildPayload(verb, input);
    Object.assign(payload, extraData);

    if (payload.new_encounter) {
        delete payload.npc_id;
        delete payload.conversation_id;
        delete payload.new_encounter; // Don't send internal flag to backend
    }

    const data = await api("/api/action", payload);

    UI.forms.action.value = "";
    UI.forms.action.disabled = false;
    UI.forms.action.focus();

    if (data.error) {
        // HR Intervention Visual
        updateScene(UI.display.scene, "/assets/scenes/HR-Office_Generic1.jpeg");
        return;
    }

    if (data.result) {
        appendLog(data.result.flavor, data.result.outcome === "success" ? "success-event" : "system", data.result.outcome.toUpperCase());
        renderStats(data.state);
        renderRoster(data.state);
        updateScene(UI.display.scene, data.result.scene || "");

        // Sync terminal session with scene context
        TerminalSession.syncFromResult(data.result);

        // Minigame Trigger
        if (data.result.minigame && window.showMinigame) {
            setTimeout(() => {
                window.showMinigame(data.result.minigame.toUpperCase(), data.result.minigame, verb);
            }, 1000);
        }
    }
}

// ============================================================================
// 🚀 INITIALIZATION
// ============================================================================

document.addEventListener("DOMContentLoaded", () => {
    initRegistry();
    initTutorialRegistry();

    // Attach Listeners — Buttons
    UI.btns.newCareer.addEventListener("click", startNewCareer);
    UI.btns.logout.addEventListener("click", handleLogout);
    UI.btns.submitAnswer.addEventListener("click", submitAnswer);
    UI.btns.beginCareer.addEventListener("click", beginCareer);
    UI.btns.tutorialNext.addEventListener("click", () => Tutorial.next());

    UI.btns.closeMinigame.addEventListener("click", () => {
        UI.panels.minigame.classList.add("hidden");
        startPolling();
    });

    // Forms
    UI.forms.application.addEventListener("submit", submitApplication);
    UI.forms.nimKey.addEventListener("submit", saveNimKey);
    UI.forms.answer.addEventListener("keypress", (e) => { if (e.key === "Enter") submitAnswer(); });

    // Terminal Input — keypress dispatcher
    UI.forms.action.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            const input = UI.forms.action.value.trim();
            if (!input) return;

            // Slash commands and built-in keywords
            if (handleTerminalCommand(input)) {
                UI.forms.action.value = "";
                return;
            }

            // Debug minigame shortcuts
            const text = input.toLowerCase();
            if (text === "debug tetris") { UI.forms.action.value = ""; window.showMinigame("Clear the Backlog", "tetris"); return; }
            if (text === "debug triage") { UI.forms.action.value = ""; window.showMinigame("Inbox Zero", "email_triage"); return; }

            // Explicit /chat command
            if (text.startsWith("/chat ")) {
                let msg = input.substring(6).trim();
                let targetNpc = TerminalSession.npc_id;

                // Support "/chat with [Name] [msg]"
                if (msg.toLowerCase().startsWith("with ")) {
                    const parts = msg.substring(5).split(" ");
                    const potentialName = parts[0];
                    // Resolve roster names to canonical npc_id from DOM dataset.
                    const rosterItems = Array.from(UI.display.roster.querySelectorAll(".roster-item"));
                    const lower = potentialName.toLowerCase();
                    const match = rosterItems.find(item => {
                        const name = (item.dataset.npcName || "").toLowerCase();
                        return name.startsWith(lower) || name.includes(lower);
                    });
                    targetNpc = match?.dataset?.npcId || potentialName;
                    msg = parts.slice(1).join(" ");
                }

                UI.forms.action.value = msg;
                submitAction("socialize", targetNpc ? { npc_id: targetNpc } : {});
                return;
            }

            // Default action based on terminal session mode
            const resolved = TerminalSession.resolveDefaultAction(input);
            submitAction(resolved.verb, resolved.extra);
        }
    });

    // Quick-action verb buttons
    document.querySelectorAll("button[data-verb]").forEach(btn => {
        btn.addEventListener("click", () => {
            if (btn.dataset.verb === "socialize") {
                const isNew = TerminalSession.mode !== "social";
                submitAction("socialize", isNew ? { new_encounter: true } : {});
            } else {
                submitAction(btn.dataset.verb);
            }
        });
    });

    // Debug Menu Logic
    const debugBtn = document.getElementById("debugMenuBtn");
    const debugMenu = document.getElementById("minigameMenu");

    if (debugBtn && debugMenu) {
        debugBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const isHidden = debugMenu.classList.toggle("hidden");
            if (!isHidden) {
                const rect = debugBtn.getBoundingClientRect();
                const baseSize = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
                debugMenu.style.position = "fixed";
                debugMenu.style.bottom = `${window.innerHeight - rect.top + (baseSize * 0.75)}px`;
                debugMenu.style.left = `${rect.left}px`;
            }
        });

        document.addEventListener("click", (e) => {
            if (!debugMenu.contains(e.target) && e.target !== debugBtn) {
                debugMenu.classList.add("hidden");
            }
        });

        const gameTitles = {
            "tetris": "Clear the Backlog",
            "email_triage": "Inbox Zero",
            "meeting_dodge": "The 5:00 PM Exit",
            "node_untangle": "Graph Cleanup",
            "drive_archaeology": "Legacy Search"
        };

        debugMenu.querySelectorAll(".menu-item").forEach(item => {
            item.addEventListener("click", () => {
                const game = item.dataset.game;
                const title = gameTitles[game] || "Task";
                window.showMinigame(title, game);
                debugMenu.classList.add("hidden");
            });
        });
    }

    // Initialize minigame postMessage bridge
    initMinigameBridge();
    restoreNimKey();

    // Initial Load
    loadState();
});
