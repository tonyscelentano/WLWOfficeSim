/**
 * globals.js — Shared mutable state for OfficeSim frontend.
 * Must load before all other OfficeSim scripts.
 */

export const Globals = {
    currentSceneSrc: "",
    isOffline: false,
    seenHRWarnings: new Set(),
    currentMinigameContext: "work"
};
