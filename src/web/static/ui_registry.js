/**
 * ui_registry.js — DOM safety layer and UI element registry.
 * Provides a null-safe proxy for all UI elements used across modules.
 */

// ============================================================================
// 🛡️ UI REGISTRY (DOM SAFETY LAYER)
// ============================================================================

export const UI = {
    // Core Panels
    panels: {
        menu:        null,
        application: null,
        onboarding:  null,
        game:        null,
        minigame:    null
    },
    // Interaction
    forms: {
        application: null,
        answer:      null,
        action:      null,
        nimKey:      null
    },
    // Output
    display: {
        scene:           null,
        onboardingScene: null,
        sceneCaption:    null,
        log:             null,
        question:        null,
        saveSlots:       null,
        roster:          null
    },
    // Stats & Vitals
    stats: {
        name:   null, title: null, dept: null,
        day:    null, money: null, rep:  null, xp: null,
        energy: { val: null, bar: null },
        stress: { val: null, bar: null },
        skills: null
    },
    // Controls
    btns: {
        newCareer:      null,
        logout:         null,
        submitApp:      null,
        submitAnswer:   null,
        closeMinigame:  null
    },
    config: {
        nimApiKey: null,
        nimKeyStatus: null
    },
    tutorial: {}
};


export function initRegistry() {
    const map = (id) => {
        const el = document.getElementById(id);
        if (!el) {
            console.warn(`[UI Registry] Missing Element: #${id}`);
            return {
                classList: { add: () => {}, remove: () => {}, contains: () => false },
                style: {},
                addEventListener: () => {},
                appendChild: () => {},
                innerHTML: "", textContent: "", value: "", focus: () => {}
            };
        }
        return el;
    };

    // Map Panels
    UI.panels.menu             = map("menuPanel");
    UI.panels.application      = map("applicationPanel");
    UI.panels.onboarding       = map("onboardingPanel");
    UI.panels.onboardingPacket = map("onboardingPacketPanel");
    UI.panels.game             = map("gamePanel");
    UI.panels.minigame         = map("minigamePanel");

    // Map Forms
    UI.forms.application = map("applicationForm");
    UI.forms.answer      = map("answerInput");
    UI.forms.action      = map("actionInput");
    UI.forms.nimKey      = map("nimKeyForm");

    // Map Display
    UI.display.scene           = map("scene");
    UI.display.onboardingScene = map("onboardingScene");
    UI.display.log             = map("terminalLog");
    UI.display.question        = map("question");
    UI.display.saveSlots       = map("saveSlotsList");
    UI.display.roster          = map("rosterList");

    // Map Stats
    UI.stats.name       = map("playerName");
    UI.stats.title      = map("playerTitle");
    UI.stats.dept       = map("playerDept");
    UI.stats.day        = map("statDay");
    UI.stats.money      = map("statMoney");
    UI.stats.rep        = map("statRep");
    UI.stats.xp         = map("statXp");
    UI.stats.energy.val = map("valEnergy");
    UI.stats.energy.bar = map("barEnergy");
    UI.stats.stress.val = map("valStress");
    UI.stats.stress.bar = map("barStress");
    UI.stats.skills     = map("skillsList");

    // Map Buttons
    UI.btns.newCareer     = map("newCareerBtn");
    UI.btns.logout        = map("logoutBtn");
    UI.btns.submitApp     = map("applicationSubmitBtn");
    UI.btns.submitAnswer  = map("answerBtn");
    UI.btns.beginCareer   = map("beginCareerBtn");
    UI.btns.tutorialNext  = map("tutorialNextBtn");
    UI.btns.closeMinigame = map("closeMinigameBtn");

    // Map Config
    UI.config.nimApiKey    = map("nimApiKey");
    UI.config.nimKeyStatus = map("nimKeyStatus");
}

export function initTutorialRegistry() {
    UI.tutorial.overlay   = document.getElementById("tutorialOverlay");
    UI.tutorial.card      = document.getElementById("tutorialCard");
    UI.tutorial.text      = document.getElementById("tutorialText");
    UI.tutorial.stepCount = document.getElementById("tutorialStepCount");
}
