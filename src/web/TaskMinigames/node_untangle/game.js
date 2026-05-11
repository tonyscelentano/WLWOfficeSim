// node_untangle: scaffolding only.
// Real gameplay (planar-graph drag-to-untangle) lands later.

(function () {
  "use strict";

  const taskLabel = document.getElementById("task_label");
  const progressBar = document.getElementById("progress_bar");

  Minigame.init({
    name: "node_untangle",
    onStart: function (task) {
      taskLabel.textContent = task.task_title || "(unspecified task)";
      // Fake progress to demonstrate the channel works.
      let p = 0;
      const id = setInterval(function () {
        p += 0.05;
        if (p >= 1) { clearInterval(id); return; }
        progressBar.style.width = (p * 100).toFixed(0) + "%";
        Minigame.progress(p);
      }, 250);
    },
    onAbort: function () {
      // Parent cancelled; surrender without scoring.
      progressBar.style.width = "0%";
    },
  });

  document.getElementById("btn_partial").addEventListener("click", function () {
    Minigame.complete({ score: 0.55, telemetry: { stub: true } });
  });
  document.getElementById("btn_success").addEventListener("click", function () {
    Minigame.complete({ score: 0.85, telemetry: { stub: true } });
  });
})();
