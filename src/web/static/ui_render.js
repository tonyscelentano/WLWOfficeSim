/**
 * ui_render.js — All DOM rendering functions.
 * Depends on: globals.js (currentSceneSrc, seenHRWarnings), ui_registry.js (UI)
 *
 * CANONICAL render layer. All render functions live here; no duplicates elsewhere.
 */

// ============================================================================
// 🎨 UI RENDERING
// ============================================================================

import { Globals } from './globals.js';
import { UI } from './ui_registry.js';
import { loadGame, submitAction } from './main.js';

function formatTime() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function appendLog(line, type = "system", source = "System") {
    const div = document.createElement("div");
    div.className = `log-entry ${type}`;
    div.innerHTML = `
        <div class="log-meta">
            <span class="log-time">[${formatTime()}]</span>
            <span class="log-source">${source}</span>
        </div>
        <div class="log-content">${line}</div>
    `;
    UI.display.log.appendChild(div);
    requestAnimationFrame(() => {
        UI.display.log.scrollTop = UI.display.log.scrollHeight;
    });
}

export function showBootSequence(onboarding) {
    const lines = [
        { t: "OFFICESIM KERNEL v4.0.2 SECURE BOOT...", s: "CORE" },
        { t: "Mounting neural-link interface... [OK]", s: "SYS" },
        { t: "Validating corporate loyalty contract... [OK]", s: "LEGAL" },
        { t: "Scanning employee aptitude profile...", s: "HR" },
        { t: "VERDICT: " + (onboarding?.flavor || "Candidate accepted. Welcome to the machine."), s: "VERDICT", type: "success-event" },
        { t: "Assigned Role: " + (onboarding?.role || "Junior Backend Dev"), s: "ASSIGN", type: "system" },
        { t: "Assigned Dept: " + (onboarding?.pillar || "Technical") + "." + (onboarding?.path || "middle") + "." + (onboarding?.cluster || "backend"), s: "ASSIGN", type: "system" },
        { t: "Proceeding to cubicle 4F-12. Please do not stop to talk to the interns.", s: "NAV", type: "system" }
    ];
    let delay = 300;
    lines.forEach(line => {
        setTimeout(() => appendLog(line.t, line.type || "system", line.s), delay);
        delay += Math.random() * 600 + 400;
    });

    setTimeout(() => {
        updateScene(UI.display.scene, "/assets/scenes/User_Workdesk_Generic.jpeg");
        appendLog("Location: OFFICE_FLOOR_4 / CUBICLE_12", "system", "NAV");
        appendLog("The monitor hums with existential dread. Your inbox is already at 42 unread messages.", "system", "SIGHT");
        appendLog("Welcome to your new life. Type 'work' to begin the cycle.", "success-event", "SYSTEM");
    }, delay + 1000);
}

export const SCENE_MAP = {
    "SCENE_DESK": "/assets/scenes/User_Workdesk_Generic.jpeg",
    "SCENE_DESK_SUCCESS": "/assets/scenes/User_Workdesk_ClientOutcome-Good.jpeg",
    "SCENE_DESK_FAIL": "/assets/scenes/User_Workdesk_ClientOutcome-Bad.jpeg",
    "SCENE_RACKS_ON_FIRE": "/assets/scenes/Server-Room_RacksOnFire.jpeg",
    "SCENE_WATERCOOLER": "/assets/scenes/Watercooler_Personnel_Generic-Coworker.jpeg",
    "SCENE_RECOVER": "/assets/scenes/User_Workdesk_Generic_InboxSpam.jpeg",
    "SCENE_SLACKING": "/assets/scenes/SlackingOff_PolyesterSuitPaulie.jpeg",
    "SCENE_IT_BASEMENT": "/assets/scenes/IT-Basement_Bored-Technician.jpeg",
    "SCENE_GREMLINS": "/assets/scenes/IT-Basement_Literal-Gremlins-GoneWild.jpeg",
    "SCENE_HR_OFFICE": "/assets/scenes/HR-Office_Generic1.jpeg",
    "SCENE_INTERVIEW": "/assets/scenes/1_NewGameInterview.jpeg",
    "SCENE_INTERVIEW_HIRED": "/assets/scenes/1_NewGameInterview_Hired.jpeg",
    "SCENE_ALLHANDS_1": "/assets/scenes/Generic_AllHands_Meeting.jpeg",
    "SCENE_ALLHANDS_2": "/assets/scenes/Generic_AllHands_Meeting_2.jpeg",
    "SCENE_ALLHANDS_CATS": "/assets/scenes/Generic_AllHands_Meeting_LiterallyCats.jpeg",
    "SCENE_WEBCAM": "/assets/scenes/WebcamConference_Coworkers.jpeg",
    "SCENE_SERVER_ROOM": "/assets/scenes/Server-Room_Generic_PersonnelWorkers.jpeg",
    "SCENE_MEETING_1": "/assets/scenes/MeetingRoom_PitchDeck_Generic.jpeg",
    "SCENE_MEETING_2": "/assets/scenes/MeetingRoom_PitchDeck_Generic2.jpeg",
    "SCENE_MEETING_SHODAN": "/assets/scenes/MeetingRoom_PitchDeck_SHODAN.jpeg",
    "SCENE_MEETING_CATS": "/assets/scenes/MeetingRoom_PitchDeck_TunaCats.jpeg",
    "SCENE_MEETING_ANIME": "/assets/scenes/MeetingRoom_PitchDeck_AnimeWaifu-Avatar.jpeg",
    "SCENE_MEETING_EYE": "/assets/scenes/MeetingRoom_PitchDeck_IlluminatiEye.jpeg",
    "SCENE_MEETING_VLM": "/assets/scenes/MeetingRoom_PitchDeck_VLM-Classifier.jpeg",
};

export function updateScene(imgElement, newSrc) {
    if (!newSrc || !imgElement) return;
    
    // Resolve semantic ID if present
    const resolvedSrc = SCENE_MAP[newSrc] || (newSrc.startsWith('/') ? newSrc : `/assets/scenes/${newSrc}`);

    if (Globals.currentSceneSrc === resolvedSrc) return;
    Globals.currentSceneSrc = resolvedSrc;
    imgElement.classList.add("fade-out");
    setTimeout(() => {
        imgElement.src = resolvedSrc;
        imgElement.onload = () => imgElement.classList.remove("fade-out");
    }, 400);
}

export function renderStats(s) {
    if (!s) return;
    UI.stats.name.textContent  = s.name || "Employee";
    UI.stats.title.textContent = s.title || "Junior Dev";
    UI.stats.dept.textContent  = s.department || "Dept";
    UI.stats.day.textContent   = s.day || 1;
    UI.stats.money.textContent = `$${s.money || 0}`;
    UI.stats.rep.textContent   = s.reputation || 0;
    UI.stats.xp.textContent    = s.xp || 0;

    // Update Avatar Initial
    const avatar = document.querySelector(".player-avatar");
    if (avatar) avatar.textContent = (s.name || "T")[0].toUpperCase();

    const e  = Math.max(0, Math.min(100, s.energy || 0));
    const st = Math.max(0, Math.min(100, s.stress || 0));
    UI.stats.energy.val.textContent = `${e} / 100`;
    UI.stats.energy.bar.style.width = `${e}%`;
    UI.stats.stress.val.textContent = `${st} / 100`;
    UI.stats.stress.bar.style.width = `${st}%`;

    // Burnout visuals
    if (e <= 5) UI.stats.energy.bar.classList.add("burnout");
    else        UI.stats.energy.bar.classList.remove("burnout");
    if (st >= 95) UI.stats.stress.bar.classList.add("burnout");
    else          UI.stats.stress.bar.classList.remove("burnout");

    // Day change resets session-local HR warning cache
    if (s.day > (parseInt(UI.stats.day.textContent) || 0)) {
        Globals.seenHRWarnings.clear();
    }

    // HR Warning interception
    if (s.hr_warnings) {
        s.hr_warnings.forEach(msg => {
            if (!Globals.seenHRWarnings.has(msg)) {
                appendLog(`[!] HR WARNING: ${msg}`, "fail-event", "HR");
                Globals.seenHRWarnings.add(msg);
            }
        });
    }

    UI.stats.skills.innerHTML = "";
    for (const [k, v] of Object.entries(s.skills || {})) {
        const li = document.createElement("li");
        li.className = "skill-item";
        li.innerHTML = `<span class="skill-name">${k.charAt(0).toUpperCase() + k.slice(1)}</span> <span class="skill-value">${v}</span>`;
        UI.stats.skills.appendChild(li);
    }
}


export function renderRoster(state) {
    if (!state) return;

    const relEntries = state.relationships
        ? Object.entries(state.relationships).filter(([, rel]) => rel && rel.name !== "Unknown")
        : [];

    UI.display.roster.innerHTML = "";
    if (relEntries.length === 0) {
        UI.display.roster.innerHTML = `<li class="roster-item"><div class="roster-info"><span class="roster-name" style="color:#666;">No network contacts unlocked.</span><span class="roster-role" style="color:#555;">Get to the watercooler!</span></div></li>`;
        return;
    }

    relEntries.forEach(([keyNpcId, rel]) => {
        const npcId = rel.npc_id || keyNpcId;
        const li = document.createElement("li");
        li.className = "roster-item";
        li.dataset.npcId = npcId;
        li.dataset.npcName = (rel.name || "").toLowerCase();
        
        let avatarContent = "";
        if (rel.pfp) {
            avatarContent = `<img src="/assets/PFPs/${rel.pfp}" alt="${rel.name}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">`;
        } else {
            avatarContent = rel.name.substring(0, 1).toUpperCase();
        }

        li.innerHTML = `
            <div class="roster-avatar">
                ${avatarContent}
                <div class="status-dot online"></div>
            </div>
            <div class="roster-info"><span class="roster-name">${rel.name}</span><span class="roster-role">${rel.role}</span></div>
        `;
        li.addEventListener("click", () => {
            // Directly initiate a socialize action targeting this specific NPC
            submitAction("socialize", { npc_id: npcId });
        });
        UI.display.roster.appendChild(li);
    });
}


export function renderSaveSlots(saves) {
    UI.display.saveSlots.innerHTML = "";
    if (!saves || saves.length === 0) {
        UI.display.saveSlots.innerHTML = `<p class="muted" style="text-align: center; padding: 20px;">No employee files found.</p>`;
        return;
    }

    saves.forEach(save => {
        const li = document.createElement("li");
        li.className = "roster-item";
        const meta = save.meta || {};
        const app  = meta.application || {};
        const name = app.name || `Slot ${save.slot}`;
        const role = app.preferred_role || "Unknown Role";
        const date = save.saved_at ? new Date(save.saved_at).toLocaleString() : "Unknown";

        li.innerHTML = `
            <div class="roster-info" style="flex: 1;">
                <span class="roster-name" style="font-size: 1.1rem;">${name}</span>
                <span class="roster-role">${role} • ${date}</span>
            </div>
            <button class="primary load-btn" style="flex: 0; padding: 8px 20px;">Load</button>
        `;
        li.querySelector(".load-btn").addEventListener("click", () => loadGame(save.slot));
        UI.display.saveSlots.appendChild(li);
    });
}
