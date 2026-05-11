// drive_archaeology: scaffolding only.
// Real gameplay (recursive folder navigation, decoy files, time pressure) lands later.

(function () {
  "use strict";

  const STUB_FOLDERS = [
    "📁 Old Strategy Decks (DO NOT DELETE)",
    "📁 Q2 Reorg — Final Final v3",
    "📁 Misc",
    "📁 Shared with team@ (read-only)",
    "📁 Marketing handoff (2019)",
    "📄 FY24_Q3_FINAL_v6_USE_THIS_ONE.xlsx",
    "📄 FY24_Q3_FINAL_v7_USE_THIS_ONE — Copy.xlsx",
    "📄 budget_template (1).xlsx",
  ];

  const taskLabel = document.getElementById("task_label");
  const progressBar = document.getElementById("progress_bar");
  const folderList = document.getElementById("folder_list");

  STUB_FOLDERS.forEach(function (label) {
    const li = document.createElement("li");
    li.textContent = label;
    folderList.appendChild(li);
  });

  Minigame.init({
    name: "drive_archaeology",
    onStart: function (task) {
      taskLabel.textContent = task.task_title || "(unspecified task)";
    },
    onAbort: function () {
      progressBar.style.width = "0%";
    },
  });

  document.getElementById("btn_partial").addEventListener("click", function () {
    Minigame.complete({ score: 0.45, telemetry: { stub: true, gave_up: true } });
  });
  document.getElementById("btn_success").addEventListener("click", function () {
    Minigame.complete({ score: 0.90, telemetry: { stub: true, found_it: true } });
  });
})();
