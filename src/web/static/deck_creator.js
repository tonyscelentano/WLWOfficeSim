/**
 * 📊 OFFICESIM - DECK CREATOR MODULE
 * Satirical Pitch Deck generator (Mad Libs style).
 */

import { appendLog } from './ui_render.js';
import { WorkMenu } from './work_menu.js';

export const DeckCreator = {
    isOpen: false,
    
    themes: [
        { id: "techno", name: "Deep Techno Wizard Jargon", desc: "For when you don't want them to understand the lack of logic." },
        { id: "eli5", name: "ELI5 Nursery Pastel", desc: "So simple a toddler (or a CEO) could understand." },
        { id: "roi", name: "Ruthless Corporate ROI", desc: "Maximum aggression. Minimum soul." },
        { id: "dread", name: "Existential Dread Gray", desc: "A palette that reflects the true state of the quarterly projections." },
        { id: "space", name: "Billionaire Space-LARP", desc: "Shiny, chrome, and completely detached from Earth's gravity." }
    ],

    fonts: [
        { id: "comic", name: "Comic Sans (The 'I'm Fun!' Choice)" },
        { id: "brutal", name: "Brutalist Monospace" },
        { id: "caps", name: "Screaming All-Caps Corporate" },
        { id: "cursive", name: "Cursive 'Work-Life Balance' (Unreadable)" }
    ],

    init() {
        this.panel = document.getElementById("deckCreatorPanel");
        if (!this.panel) return;

        this.setupDropdowns();
        this.setupListeners();
    },

    setupDropdowns() {
        const themeSelect = document.getElementById("deckTheme");
        const fontSelect = document.getElementById("deckFont");

        if (themeSelect) {
            this.themes.forEach(t => {
                const opt = document.createElement("option");
                opt.value = t.id;
                opt.textContent = t.name;
                themeSelect.appendChild(opt);
            });
        }

        if (fontSelect) {
            this.fonts.forEach(f => {
                const opt = document.createElement("option");
                opt.value = f.id;
                opt.textContent = f.name;
                fontSelect.appendChild(opt);
            });
        }
    },

    setupListeners() {
        const closeBtn = this.panel.querySelector(".close-panel");
        const cancelBtn = document.getElementById("deckCancel");
        const submitBtn = document.getElementById("deckSubmit");

        if (closeBtn) closeBtn.addEventListener("click", () => this.close());
        if (cancelBtn) cancelBtn.addEventListener("click", () => this.close());
        
        if (submitBtn) {
            submitBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                this.generateDeck();
            });
        }

        // Picker Panel Close
        const picker = document.getElementById("deckPickerPanel");
        if (picker) {
            const pickerClose = picker.querySelector(".close-panel");
            if (pickerClose) pickerClose.addEventListener("click", () => this.close());
        }
    },


    savedDecks: JSON.parse(localStorage.getItem("officesim_decks") || "[]"),

    open() {
        this.isOpen = true;
        this.panel.classList.remove("hidden");
        // Reset inputs
        this.panel.querySelectorAll("input, textarea").forEach(i => i.value = "");
        appendLog("INITIALIZING_SLIDE_GENERATOR: Loading synergy assets...", "system", "DECK");
    },

    close() {
        this.isOpen = false;
        this.panel.classList.add("hidden");
        document.getElementById("deckPickerPanel").classList.add("hidden");
    },

    openPicker() {
        const picker = document.getElementById("deckPickerPanel");
        const list = document.getElementById("deckPickerList");
        if (!picker || !list) return;

        if (this.savedDecks.length === 0) {
            appendLog("ERROR: No authorized synergy decks found. Go create one.", "error", "SYSTEM");
            return;
        }

        list.innerHTML = "";
        this.savedDecks.forEach(deck => {
            const item = document.createElement("div");
            item.className = "menu-item";
            item.innerHTML = `
                <div style="display:flex; flex-direction:column;">
                    <span style="font-weight:800;">${deck.company}</span>
                    <span style="font-size:0.6rem; opacity:0.6;">Target: ${deck.noun}</span>
                </div>
            `;
            item.onclick = () => {
                this.close();
                if (typeof WorkMenu !== 'undefined') WorkMenu.startPresentation(deck);
            };
            list.appendChild(item);
        });

        picker.classList.remove("hidden");
    },

    saveDeck(data) {
        this.savedDecks.push({
            ...data,
            timestamp: new Date().toISOString(),
            id: Math.random().toString(36).substr(2, 9)
        });
        if (this.savedDecks.length > 8) this.savedDecks.shift();
        this.sync();
    },

    deleteDeck(id) {
        this.savedDecks = this.savedDecks.filter(d => d.id !== id);
        this.sync();
    },

    sync() {
        localStorage.setItem("officesim_decks", JSON.stringify(this.savedDecks));
    },

    generateDeck() {
        const data = {
            company: document.getElementById("deckCompany").value || "Globex Corp",
            verb: document.getElementById("deckVerb").value || "disrupt",
            noun: document.getElementById("deckNoun").value || "cloud",
            adjective: document.getElementById("deckAdj").value || "synergistic",
            theme: document.getElementById("deckTheme").value,
            font: document.getElementById("deckFont").value
        };

        const themeName = this.themes.find(t => t.id === data.theme)?.name;
        
        appendLog(`--- DECK GENERATED: ${data.company.toUpperCase()} ---`, "success-event", "DECK");
        appendLog(`Mission: To ${data.verb} the ${data.noun} market. Strategy: "${data.adjective}"`, "system", "DECK");
        
        this.saveDeck(data);
        appendLog("Deck saved to synergy vault. Ready for presentation.", "success-event", "SYSTEM");
        
        this.close();
    }
};

document.addEventListener("DOMContentLoaded", () => {
    setTimeout(() => DeckCreator.init(), 200);
    
    // Close picker on outside click
    document.addEventListener("click", (e) => {
        const picker = document.getElementById("deckPickerPanel");
        if (picker && !picker.classList.contains("hidden") && !picker.contains(e.target)) {
            picker.classList.add("hidden");
        }
    });
});

