import os
import sys
import json
import logging
import http.server
import socketserver
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from core.voice import (
    interview_opening_prompt,
    interview_followup_prompt,
    interview_evaluation_prompt,
    task_evaluation_prompt,
    social_evaluation_prompt,
    _load_voice_pack,
    VOICE_FILE
)

try:
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    OpenAI = None

import tomllib
# Note: Using 'tomli_w' would be better for writing but we want zero-dep.
# We'll use a simple dictionary-based update and rewrite for the surgical edits.

MOCK_DATA = {
    "application": {
        "name": "Tony",
        "age": "32",
        "preferred_role": "Backend Architect",
        "work_history": "10 years of fighting with databases and legacy code. Once saved a production server with a well-placed regex."
    },
    "transcript": [
        {"role": "interviewer", "content": "Welcome. If this office were a small disaster with snacks, would you fix the thing, sell the thing, or turn it into a meeting?"},
        {"role": "user", "content": "I'd automate the fixing and then turn the snacks into a spreadsheet."}
    ],
    "task": {
        "id": "email_triage",
        "title": "Email Triage",
        "required_skill": "engineering",
        "evaluation_hint": "Focus on their prioritization logic and whether they sound burned out."
    },
    "npc": {
        "id": "alex_lead",
        "name": "Alex",
        "role": "Lead Engineer",
        "description": "A dry, code-obsessed lead who values efficiency above all.",
        "communication_style": "terse",
        "prompt_templates": {"general": "You are reviewing a PR with the player."}
    },
    "archetype": {
        "id": "chaotic_genius",
        "outcome_hints": "Be impressed by clever hacks, annoyed by boilerplate."
    },
    "player": {
        "skills": {"engineering": 7, "communication": 3, "politics": 1},
        "reputation": 50,
        "stress": 20
    }
}

PORT = 9991

class StructuredPromptHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode())
        elif self.path == '/api/load':
            with open(VOICE_FILE, 'rb') as f:
                data = tomllib.load(f)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
        else:
            self.send_error(404)

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        if self.path == '/api/save-field':
            # Surgical field update
            data = json.loads(post_data)
            self.update_voice_field(data['path'], data['value'])
            _load_voice_pack.cache_clear()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Saved")
                
        elif self.path == '/api/test':
            data = json.loads(post_data)
            _load_voice_pack.cache_clear()
            
            prompt = ""
            user_input = ""
            type_id = data.get('type')
            
            if type_id == 'opening':
                prompt = interview_opening_prompt(MOCK_DATA["application"])
            elif type_id == 'followup':
                prompt = interview_followup_prompt(MOCK_DATA["transcript"], MOCK_DATA["application"])
            elif type_id == 'eval':
                prompt = interview_evaluation_prompt(MOCK_DATA["transcript"], MOCK_DATA["application"])
                transcript_text = "\n".join([f"{t['role'].capitalize()}: {t['content']}" for t in MOCK_DATA["transcript"]])
                user_input = f"Interview Transcript:\n{transcript_text}"
            elif type_id == 'task':
                prompt = task_evaluation_prompt(MOCK_DATA["task"], 5)
                user_input = data.get('input', "I refactored the entire system while drinking cold coffee.")
            elif type_id == 'social':
                # Map selected NPC
                npc_id = data.get('npc_id', 'alex_lead')
                pack = _load_voice_pack()
                # We need to find the NPC data from the game's actual data to be realistic
                # For this tool, we'll just mock the shift
                custom_npc = dict(MOCK_DATA["npc"])
                custom_npc["id"] = npc_id
                prompt = social_evaluation_prompt(custom_npc, MOCK_DATA["archetype"], MOCK_DATA["player"], data.get('input', "I think we should ship it."))
            
            response_data = {"prompt": prompt, "user_input": user_input}
            if data.get('execute'):
                response_data["response"] = self.run_llm(prompt, user_input)
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode())

    def update_voice_field(self, path, value):
        # We'll use a crude but effective way to update the TOML without a writer lib
        # for a developer tool. We'll load, mutate dict, and write back as "clean" as possible.
        with open(VOICE_FILE, 'rb') as f:
            full_data = tomllib.load(f)
        
        # Path format: "global.tone" or "npc_personas.0.tone"
        parts = path.split('.')
        ref = full_data
        for part in parts[:-1]:
            if part.isdigit():
                ref = ref[int(part)]
            else:
                ref = ref[part]
        
        last_key = parts[-1]
        ref[last_key] = value

        # Manual TOML generation (very basic, but works for our schema)
        lines = []
        # Global
        lines.append("[global]")
        lines.append(f'tone = """\n{full_data["global"]["tone"].strip()}\n"""\n')
        
        # Interview
        lines.append("[interview]")
        lines.append(f'opening_question = "{full_data["interview"]["opening_question"]}"\n')
        
        # NPCs
        for npc in full_data.get("npc_personas", []):
            lines.append("[[npc_personas]]")
            lines.append(f'id = "{npc["id"]}"')
            lines.append(f'tone = """\n{npc["tone"].strip()}\n"""')
            ex_list = ", ".join(f'"{ex}"' for ex in npc.get("examples", []))
            lines.append(f'examples = [{ex_list}]\n')
            
        # Archetypes
        for arch in full_data.get("archetype_personas", []):
            lines.append("[[archetype_personas]]")
            lines.append(f'id = "{arch["id"]}"')
            lines.append(f'tone = """\n{arch["tone"].strip()}\n"""\n')

        with open(VOICE_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

    def run_llm(self, prompt, user_input):
        api_key = os.environ.get("NVIDIA_API_KEY", os.environ.get("NIM_API_KEY"))
        if not api_key or OpenAI is None: return "[API Key Missing]"
        try:
            client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
            messages = [{"role": "system", "content": prompt}]
            if user_input: messages.append({"role": "user", "content": user_input})
            completion = client.chat.completions.create(model="nvidia/nemotron-3-nano-30b-a3b", messages=messages, temperature=0.8, max_tokens=1024)
            return completion.choices[0].message.content
        except Exception as e: return f"[LLM Error: {str(e)}]"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>OfficeSim Prompt Laboratory</title>
    <style>
        :root { --bg: #1e1e1e; --panel: #252526; --border: #333; --text: #ccc; --accent: #007acc; --highlight: #569cd6; --fallback: #ce9178; --llm: #b5cea8; }
        body { font-family: 'Segoe UI', sans-serif; margin: 0; background: var(--bg); color: var(--text); display: flex; height: 100vh; overflow: hidden; }
        
        .sidebar { width: 450px; border-right: 1px solid var(--border); display: flex; flex-direction: column; background: var(--panel); overflow-y: auto; }
        .main { flex: 1; display: flex; flex-direction: column; overflow-y: auto; padding: 20px; gap: 20px; }
        
        .section-header { background: #333; padding: 10px 15px; font-size: 0.8em; font-weight: bold; text-transform: uppercase; color: #888; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; }
        .field-group { padding: 15px; border-bottom: 1px solid var(--border); }
        .field-label { font-size: 0.85em; margin-bottom: 8px; color: var(--highlight); display: block; }
        .fallback-tag { background: #443; color: #da0; padding: 2px 6px; font-size: 0.7em; border-radius: 3px; margin-left: 5px; }
        .llm-tag { background: #343; color: #4ec9b0; padding: 2px 6px; font-size: 0.7em; border-radius: 3px; margin-left: 5px; }
        
        textarea { width: 100%; background: #111; color: #ddd; border: 1px solid #444; padding: 8px; font-family: 'Consolas', monospace; font-size: 13px; border-radius: 4px; box-sizing: border-box; resize: vertical; min-height: 60px; }
        input[type="text"] { width: 100%; background: #111; color: #ddd; border: 1px solid #444; padding: 8px; border-radius: 4px; box-sizing: border-box; }
        
        button { background: var(--accent); color: white; border: none; padding: 6px 12px; cursor: pointer; border-radius: 3px; font-size: 0.9em; transition: 0.2s; }
        button:hover { background: #008be5; }
        
        .tab-btn { background: transparent; color: #888; border: none; padding: 10px; cursor: pointer; border-bottom: 2px solid transparent; }
        .tab-btn.active { color: var(--highlight); border-bottom-color: var(--highlight); }
        
        .output-container { background: #111; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
        .output-header { background: #2d2d2d; padding: 8px 15px; font-size: 0.75em; color: #aaa; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .output-content { padding: 15px; font-family: 'Consolas', monospace; font-size: 13px; white-space: pre-wrap; line-height: 1.5; }
        
        .pill { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 0.75em; background: #444; margin-right: 5px; cursor: pointer; }
        .pill.selected { background: var(--accent); color: white; }
        
        .save-btn { font-size: 0.7em; padding: 2px 8px; opacity: 0; transition: 0.3s; }
        .field-group:hover .save-btn { opacity: 1; }
        
        .loading-overlay { position: fixed; top:0; left:0; right:0; bottom:0; background: rgba(0,0,0,0.5); display: none; justify-content: center; align-items: center; z-index: 1000; }
    </style>
</head>
<body>
    <div id="loading" class="loading-overlay"><span>Running LLM...</span></div>

    <div class="sidebar">
        <div class="section-header">Global Satire Config</div>
        <div class="field-group">
            <span class="field-label">OFFICE TONE <span class="llm-tag">Used by all prompts</span> <button class="save-btn" onclick="saveField('global.tone')">Save</button></span>
            <textarea id="field-global-tone" oninput="markDirty(this)"></textarea>
        </div>

        <div class="section-header">Recruitment (Onboarding)</div>
        <div class="field-group">
            <span class="field-label">INTERVIEW OPENING <span class="fallback-tag">Fallback Preset</span> <button class="save-btn" onclick="saveField('interview.opening_question')">Save</button></span>
            <input type="text" id="field-interview-opening" oninput="markDirty(this)">
        </div>

        <div class="section-header">Persona Surgical Edits</div>
        <div id="persona-list" style="padding: 10px;">
            <!-- Populated via JS -->
        </div>
        <div id="persona-editor" class="field-group" style="border-top: 1px solid #444; display: none;">
            <span class="field-label">PERSONA TONE <span class="llm-tag">LLM Context</span> <button id="persona-save-btn" class="save-btn">Save</button></span>
            <textarea id="field-persona-tone" oninput="markDirty(this)" style="min-height: 150px;"></textarea>
        </div>
    </div>

    <div class="main">
        <div style="display: flex; gap: 10px; align-items: center;">
            <h2 style="margin:0;">Laboratory Console</h2>
            <div style="margin-left: auto; display: flex; gap: 5px;">
                <button class="tab-btn active" onclick="setScenario('opening', this)">Interview Start</button>
                <button class="tab-btn" onclick="setScenario('followup', this)">Follow-up</button>
                <button class="tab-btn" onclick="setScenario('eval', this)">Sort/Eval</button>
                <button class="tab-btn" onclick="setScenario('task', this)">Task</button>
                <button class="tab-btn" onclick="setScenario('social', this)">Social</button>
            </div>
        </div>

        <div id="test-controls" style="background: #2d2d2d; padding: 15px; border-radius: 6px; display: flex; gap: 15px; align-items: center;">
            <div id="social-npc-selector" style="display:none;">
                <span class="label">Target NPC:</span>
                <select id="test-npc-id" style="background:#111; color:white; border:1px solid #444; padding:5px;"></select>
            </div>
            <div id="task-input-container" style="display:none; flex:1;">
                <input type="text" id="test-player-input" placeholder="Type player response/action here..." style="background:#111; color:white; border:1px solid #444; padding:8px; width:100%;">
            </div>
            <button onclick="generatePreview()">Generate Prompt</button>
            <button onclick="executeLLM()" style="background: #28a745;">Run Test</button>
        </div>

        <div class="output-container">
            <div class="output-header">GENERATED SYSTEM PROMPT <span style="color: var(--highlight)">Segment: voice.py logic + toml content</span></div>
            <div id="out-prompt" class="output-content" style="color: var(--fallback)">Select a scenario and click Generate.</div>
        </div>

        <div id="out-user-container" class="output-container" style="display:none;">
            <div class="output-header">USER / TRANSCRIPT CONTEXT</div>
            <div id="out-user" class="output-content" style="color: #9cdcfe"></div>
        </div>

        <div class="output-container">
            <div class="output-header">LLM INFERENCE <span style="color: var(--llm)">Model: nvidia/nemotron-3-nano-30b-a3b</span></div>
            <div id="out-llm" class="output-content" style="color: var(--llm); min-height: 100px;">Execute a test to see results.</div>
        </div>
    </div>

    <script>
        let currentScenario = 'opening';
        let voiceData = {};
        let selectedPersonaIdx = -1;

        async function init() {
            const resp = await fetch('/api/load');
            voiceData = await resp.json();
            
            document.getElementById('field-global-tone').value = voiceData.global.tone;
            document.getElementById('field-interview-opening').value = voiceData.interview.opening_question;
            
            renderPersonaList();
            renderNPCSelector();
        }

        function renderPersonaList() {
            const list = document.getElementById('persona-list');
            list.innerHTML = '';
            voiceData.npc_personas.forEach((npc, idx) => {
                const p = document.createElement('span');
                p.className = 'pill' + (selectedPersonaIdx === idx ? ' selected' : '');
                p.innerText = npc.id;
                p.onclick = () => selectPersona(idx);
                list.appendChild(p);
            });
        }
        
        function renderNPCSelector() {
            const sel = document.getElementById('test-npc-id');
            sel.innerHTML = '';
            voiceData.npc_personas.forEach(npc => {
                const opt = document.createElement('option');
                opt.value = npc.id;
                opt.innerText = npc.id;
                sel.appendChild(opt);
            });
        }

        function selectPersona(idx) {
            selectedPersonaIdx = idx;
            renderPersonaList();
            const editor = document.getElementById('persona-editor');
            editor.style.display = 'block';
            document.getElementById('field-persona-tone').value = voiceData.npc_personas[idx].tone;
            document.getElementById('persona-save-btn').onclick = () => saveField(`npc_personas.${idx}.tone`);
            document.getElementById('field-persona-tone').style.borderColor = '#444';
        }

        function setScenario(type, btn) {
            currentScenario = type;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            document.getElementById('social-npc-selector').style.display = type === 'social' ? 'block' : 'none';
            document.getElementById('task-input-container').style.display = (type === 'task' || type === 'social') ? 'block' : 'none';
        }

        function markDirty(el) {
            el.style.borderColor = '#007acc';
        }

        async function saveField(path) {
            let val = "";
            if (path === 'global.tone') val = document.getElementById('field-global-tone').value;
            else if (path === 'interview.opening_question') val = document.getElementById('field-interview-opening').value;
            else if (path.includes('npc_personas')) val = document.getElementById('field-persona-tone').value;

            const resp = await fetch('/api/save-field', {
                method: 'POST',
                body: JSON.stringify({ path, value: val })
            });
            
            if (resp.ok) {
                // Flash success
                const elId = path === 'global.tone' ? 'field-global-tone' : 
                             (path === 'interview.opening_question' ? 'field-interview-opening' : 'field-persona-tone');
                const el = document.getElementById(elId);
                el.style.borderColor = '#4ec9b0';
                setTimeout(() => el.style.borderColor = '#444', 1000);
                
                // Refresh local data
                const loadResp = await fetch('/api/load');
                voiceData = await loadResp.json();
            }
        }

        async function generatePreview(execute = false) {
            const loader = document.getElementById('loading');
            if (execute) loader.style.display = 'flex';
            
            const payload = {
                type: currentScenario,
                npc_id: document.getElementById('test-npc-id').value,
                input: document.getElementById('test-player-input').value,
                execute: execute
            };
            
            const resp = await fetch('/api/test', {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            const data = await resp.json();
            
            document.getElementById('out-prompt').innerText = data.prompt;
            if (data.user_input) {
                document.getElementById('out-user-container').style.display = 'block';
                document.getElementById('out-user').innerText = data.user_input;
            } else {
                document.getElementById('out-user-container').style.display = 'none';
            }
            
            if (execute) {
                document.getElementById('out-llm').innerText = data.response;
                loader.style.display = 'none';
            }
        }

        function executeLLM() {
            generatePreview(true);
        }

        init();
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    print(f"Starting OfficeSim Structured Prompt Lab on http://localhost:{PORT}")
    with socketserver.TCPServer(("", PORT), StructuredPromptHandler) as httpd:
        httpd.serve_forever()
