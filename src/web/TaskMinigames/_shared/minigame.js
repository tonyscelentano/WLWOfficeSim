// Shared iframe ↔ parent helper.
// Every minigame imports this and calls Minigame.init / Minigame.complete.
// The parent (static/index.html) listens for these messages and forwards
// the result to the engine via /api/action.

(function (global) {
  "use strict";

  const state = {
    name: null,
    started: false,
    completed: false,
    task: null,
    onStart: null,
    onAbort: null,
  };

  function post(type, payload) {
    if (typeof window === "undefined" || !window.parent) return;
    window.parent.postMessage(Object.assign({ type, name: state.name }, payload || {}), "*");
  }

  function init(opts) {
    if (!opts || !opts.name) {
      throw new Error("Minigame.init requires { name }");
    }
    state.name = opts.name;
    state.onStart = opts.onStart || null;
    state.onAbort = opts.onAbort || null;

    window.addEventListener("message", function (ev) {
      const msg = ev.data || {};
      if (msg.type === "parent:start" && !state.started) {
        state.started = true;
        state.task = { task_id: msg.task_id, task_title: msg.task_title, difficulty: msg.difficulty };
        if (state.onStart) state.onStart(state.task);
      } else if (msg.type === "parent:abort") {
        if (state.onAbort) state.onAbort();
      }
    });

    post("minigame:ready", {});
  }

  function progress(p) {
    if (state.completed) return;
    post("minigame:progress", { progress: clamp01(p) });
  }

  function complete(result) {
    if (state.completed) return;
    state.completed = true;
    const score = clamp01(result && result.score);
    const outcome = (result && result.outcome) || scoreToOutcome(score);
    const telemetry = (result && result.telemetry) || {};
    post("minigame:complete", { score, outcome, telemetry });
  }

  function scoreToOutcome(score) {
    // Default fallback curve. Per-game logic should override by passing `outcome` directly.
    if (score >= 0.95) return "legendary";
    if (score >= 0.70) return "success";
    if (score >= 0.40) return "partial";
    return "dumpster_fire";
  }

  function clamp01(n) {
    n = Number(n);
    if (!isFinite(n)) return 0;
    return Math.max(0, Math.min(1, n));
  }

  global.Minigame = { init, progress, complete };
})(window);
