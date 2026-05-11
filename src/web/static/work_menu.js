/**
 * 🛠️ OFFICESIM - WORK MODULE
 * Handles the "Work" action sub-menu and specialized work-related scenes.
 */

import { UI } from './ui_registry.js';
import { api } from './api.js';
import { appendLog, updateScene } from './ui_render.js';
import { DeckCreator } from './deck_creator.js';

import { TerminalSession } from './terminal.js';

export const WorkMenu = {
    isOpen: false,
    
    init() {
        this.menu = document.getElementById("workMenu");
        this.btn = document.getElementById("workBtn");
        
        if (!this.btn || !this.menu) return;

        this.btn.addEventListener("click", (e) => {
            e.stopPropagation();
            this.toggle();
        });

        document.addEventListener("click", (e) => {
            if (this.isOpen && !this.menu.contains(e.target)) {
                this.close();
            }
        });

        this.setupListeners();
    },

    toggle() {
        this.isOpen ? this.close() : this.open();
    },

    open() {
        this.isOpen = true;
        this.menu.classList.remove("hidden");
        
        // Position it above the button
        const rect = this.btn.getBoundingClientRect();
        const baseSize = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
        this.menu.style.position = "fixed";
        this.menu.style.bottom = `${window.innerHeight - rect.top + (baseSize * 0.75)}px`;
        this.menu.style.left = `${rect.left}px`;
    },

    close() {
        this.isOpen = false;
        this.menu.classList.add("hidden");
    },

    setupListeners() {
        this.menu.querySelectorAll(".menu-item").forEach(item => {
            item.addEventListener("click", (e) => {
                e.stopPropagation(); // Prevent bubbling to document (which closes pickers)
                const action = item.dataset.workAction;
                this.handleAction(action);
                this.close();
            });
        });
    },


    async handleAction(action) {
        console.log(`[WorkModule] Executing: ${action}`);
        
        switch(action) {
            case "meeting":
                this.attendMeeting();
                break;
            case "it":
                this.visitIT();
                break;
            case "pitch_new":
                this.startPitchMadLibs();
                break;
            case "pitch_existing":
                this.pitchExisting();
                break;
            case "server_room":
                this.visitServerRoom();
                break;
            default:
                appendLog(`Error: Work action '${action}' not implemented.`, "error", "CORE");
        }
    },

    // --- Action Implementations ---

    async attendMeeting() {


        const scenes = [
            "/assets/scenes/Generic_AllHands_Meeting.jpeg",
            "/assets/scenes/Generic_AllHands_Meeting_2.jpeg",
            "/assets/scenes/Generic_AllHands_Meeting_LiterallyCats.jpeg",
            "/assets/scenes/WebcamConference_Coworkers.jpeg"
        ];
        const randomScene = scenes[Math.floor(Math.random() * scenes.length)];
        
        appendLog("Entering the Synchronized Alignment Chamber. Coffee levels: Minimal.", "system", "NAV");
        updateScene(UI.display.scene, randomScene);
        
        const outcomes = [
            { text: "The VP spoke for 45 minutes about 'The Future of Cloud'. You fell asleep with your eyes open.", energy: -10, stress: 5 },
            { text: "Someone brought donuts. You secured the last chocolate glazed. A major political victory.", energy: 10, stress: -5 },
            { text: "The presentation was entirely in Comic Sans. You felt your soul slowly eroding.", energy: -15, stress: 15 },
            { text: "You were asked for your opinion. You said 'Leveraging AI' and everyone nodded solemnly.", energy: -5, stress: 10 },
            { text: "The meeting could have been an email. You spent the time drawing a very detailed cat.", energy: -5, stress: -5 }
        ];

        const result = outcomes[Math.floor(Math.random() * outcomes.length)];

        setTimeout(() => {
            appendLog(`[MEETING RESULT]: ${result.text}`, "success-event", "SYSTEM");
            if (window.updateVitals) {
                window.updateVitals(result.energy, result.stress);
                appendLog(`VITAL_ADJUSTMENT: Energy ${result.energy} | Stress ${result.stress > 0 ? '+' : ''}${result.stress}`, "system", "DIAG");
            }
        }, 4000);
    },


    async visitIT() {
        appendLog("Descending to the IT basement. The smell of ozone and unwashed hoodies intensifies.", "system", "NAV");
        const response = await api("/api/action", { verb: "visit_it" });
        if (response.result) {
            updateScene(UI.display.scene, response.result.scene);
            appendLog(`${response.result.flavor}`, "system", "IT");
            TerminalSession.syncFromResult(response.result);
        }
    },

    visitServerRoom() {
        appendLog("Entering the Server Vault. Thousands of cooling fans scream in unison.", "system", "NAV");
        updateScene(UI.display.scene, "/assets/scenes/Server-Room_Generic_PersonnelWorkers.jpeg");
    },

    pitchExisting() {
        if (typeof DeckCreator !== 'undefined') {
            DeckCreator.openPicker();
        } else {
            appendLog("ERROR: Deck Creator not available.", "error", "SYSTEM");
        }
    },

    async startPresentation(deck) {
        const scenes = [
            "/assets/scenes/MeetingRoom_PitchDeck_Generic.jpeg",
            "/assets/scenes/MeetingRoom_PitchDeck_Generic2.jpeg",
            "/assets/scenes/MeetingRoom_PitchDeck_SHODAN.jpeg",
            "/assets/scenes/MeetingRoom_PitchDeck_TunaCats.jpeg",
            "/assets/scenes/MeetingRoom_PitchDeck_AnimeWaifu-Avatar.jpeg",
            "/assets/scenes/MeetingRoom_PitchDeck_IlluminatiEye.jpeg",
            "/assets/scenes/MeetingRoom_PitchDeck_VLM-Classifier.jpeg"
        ];
        const randomScene = scenes[Math.floor(Math.random() * scenes.length)];
        
        appendLog(`--- [ PRESENTING: ${deck.company} ] ---`, "success-event", "PITCH");
        appendLog(`STRATEGY: ${deck.verb} the ${deck.noun} sector.`, "system", "PITCH");
        appendLog(`SYNERGY: "${deck.adjective}"`, "system", "PITCH");
        
        updateScene(UI.display.scene, randomScene);

        // Fetch LLM Assessment from Backend
        const response = await api("/api/pitch/evaluate", deck);
        
        if (response.error) {
            // HR Intervention / Blocker
            updateScene(UI.display.scene, "/assets/scenes/HR-Office_Generic1.jpeg");
            
            const hrMessages = [
                "HR has flagged your current presence as a 'liability event'. Please vacate the meeting room.",
                "Your vitals are non-compliant with the Employee Wellness Act of 2024. This pitch is terminated.",
                "Management has noticed you are vibrating. Please report to the recovery sector immediately.",
                "This meeting room has been remotely locked by HR. Your badge access has been throttled."
            ];
            const randomMsg = hrMessages[Math.floor(Math.random() * hrMessages.length)];
            
            appendLog(`[!] HR INTERVENTION: ${randomMsg}`, "fail-event", "HR");
            return; // Terminate presentation flow
        }

        const result = response.result || { 
            flavor: "The boardroom was remarkably quiet. Even the water cooler stopped bubbling.",
            energy_delta: -20,
            stress_delta: 10,
            outcome: "partial"
        };


        setTimeout(() => {
            const status = (result.outcome === "success") ? "success-event" : "fail-event";
            appendLog(`[OUTCOME]: ${result.flavor}`, status, "PITCH");
            
            // ACTUAL STAT MODIFICATION
            if (window.updateVitals) {
                window.updateVitals(result.energy_delta, result.stress_delta);
                appendLog(`VITAL_ADJUSTMENT: Energy ${result.energy_delta} | Stress +${result.stress_delta}`, "system", "DIAG");
            }
            
            // Auto-delete deck after use
            if (typeof DeckCreator !== 'undefined') DeckCreator.deleteDeck(deck.id);
            
            appendLog(`SYNERGY_ASSET_EXHAUSTED: Deck '${deck.company}' purged from buffer.`, "system", "KERN");
        }, 3500);
    },




    startPitchMadLibs() {
        if (typeof DeckCreator !== 'undefined') {
            DeckCreator.open();
        } else {
            appendLog("Deck Creator module not initialized.", "error", "SYSTEM");
        }
    }

};

// Initialize once the main script is ready
document.addEventListener("DOMContentLoaded", () => {
    // Wait a tiny bit to ensure UI registry is populated
    setTimeout(() => WorkMenu.init(), 100);
});
