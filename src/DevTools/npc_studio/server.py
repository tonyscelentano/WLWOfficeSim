import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import tomllib
import tomli_w

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "src" / "data"
ASSETS_DIR = PROJECT_ROOT / "src" / "web" / "assets"
SCENES_DIR = ASSETS_DIR / "Scenes"
PFPS_DIR = ASSETS_DIR / "PFPs"

class StudioHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

    def do_GET(self):
        if self.path == "/api/data":
            try:
                # Load NPCs
                with open(DATA_DIR / "npcs.toml", "rb") as f:
                    npcs_data = tomllib.load(f)
                
                # Load Voices
                with open(DATA_DIR / "voices.toml", "rb") as f:
                    voices_data = tomllib.load(f)
                
                # Load Factions (for Departments/Clusters)
                with open(DATA_DIR / "factions.toml", "rb") as f:
                    factions_data = tomllib.load(f)
                
                departments = []
                pillars = factions_data.get("pillars", {})
                for p_id, p_data in pillars.items():
                    paths = p_data.get("paths", {})
                    for path_id, path_data in paths.items():
                        clusters = path_data.get("clusters", {})
                        for c_id, c_data in clusters.items():
                            departments.append({"id": c_id, "name": c_data.get("name", c_id)})
                
                # Load assets
                scenes = []
                if SCENES_DIR.exists():
                    scenes = [f.name for f in SCENES_DIR.iterdir() if f.is_file() and f.name.endswith(('.jpeg', '.jpg', '.png'))]
                
                pfps = []
                if PFPS_DIR.exists():
                    pfps = [f.name for f in PFPS_DIR.iterdir() if f.is_file() and f.name.endswith(('.jpeg', '.jpg', '.png'))]

                response = {
                    "npcs": npcs_data.get("npcs", []),
                    "personas": voices_data.get("npc_personas", []),
                    "scenes": scenes,
                    "pfps": pfps,
                    "departments": departments
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.send_error(500, f"Server Error: {str(e)}")
            return
        
        if self.path.startswith("/assets/"):
            file_path = ASSETS_DIR / self.path.split("/assets/")[1]
            if file_path.exists() and file_path.is_file():
                # determine content type based on extension
                ext = file_path.suffix.lower()
                content_type = 'image/jpeg' if ext in ('.jpg', '.jpeg') else 'image/png' if ext == '.png' else 'application/octet-stream'
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "File Not Found")
                return
        
        # Fallback to serving static files
        super().do_GET()

    def do_POST(self):
        if self.path == "/api/save":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode())
                updated_npcs = data.get("npcs", [])
                updated_personas = data.get("personas", [])

                # Save NPCs
                with open(DATA_DIR / "npcs.toml", "rb") as f:
                    full_npcs = tomllib.load(f)
                full_npcs["npcs"] = updated_npcs
                with open(DATA_DIR / "npcs.toml", "wb") as f:
                    tomli_w.dump(full_npcs, f)

                # Save Voices
                with open(DATA_DIR / "voices.toml", "rb") as f:
                    full_voices = tomllib.load(f)
                full_voices["npc_personas"] = updated_personas
                with open(DATA_DIR / "voices.toml", "wb") as f:
                    tomli_w.dump(full_voices, f)

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode())
            except Exception as e:
                self.send_error(500, f"Error saving: {str(e)}")
            return
        
        self.send_error(404, "Not Found")

if __name__ == "__main__":
    PORT = 8001
    server = HTTPServer(('', PORT), StudioHandler)
    print(f"NPC Studio running on http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()