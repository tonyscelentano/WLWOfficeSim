# TaskMinigames

Click-based browser minigames satirizing daily workflow tasks. Each minigame is a self-contained static page embedded in the main UI via an `<iframe>`.

## Layout

```
TaskMinigames/
├── _shared/
│   ├── minigame.css     # baseline styling so games look at home in the iframe
│   └── minigame.js      # postMessage helper (reportComplete, ready handshake)
├── tetris/              # "Clear the Backlog"
├── email_triage/        # "Inbox Zero"
├── meeting_dodge/       # "The 5:00 PM Exit"
├── node_untangle/       # "Graph Cleanup"
├── drive_archaeology/   # "Legacy Search"
└── README.md
```

One folder per minigame. Each must expose `index.html` as its entry point. The web server routes `/minigames/<folder>/` to that folder.

## iframe ↔ parent contract

The parent page embeds a minigame as:

```html
<iframe src="/minigames/tetris/" id="minigame_frame"></iframe>
```

The minigame communicates with the parent exclusively via `window.postMessage`. **Direct DOM access across the iframe boundary is forbidden** so games stay swappable.

### Messages the minigame sends

| `type` | Payload | When |
|---|---|---|
| `minigame:ready` | `{name: str}` | Once the game has loaded and is interactive. |
| `minigame:complete` | `{score: 0..1, outcome: "dumpster_fire"|"partial"|"success"|"legendary", telemetry: dict}` | Player finishes (or gives up). |
| `vitals:update` | `{energy: int, stress: int}` | Real-time stat adjustments (e.g., during Tetris). |

### Messages the parent sends

| `type` | Payload | When |
|---|---|---|
| `parent:start` | `{task_id, task_title, difficulty: 1..5}` | After receiving `minigame:ready`. |

## Status

**Production-Ready.** The core suite of 5 minigames is integrated into the `minigame_bridge.js` logic and linked to player vitals persistence.
