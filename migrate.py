import tomllib
import json

WATERCOOLER_CONTEXTS = {
    "sam_coworker": {
        "scene": "Watercooler_Personnel_Generic-Coworker.jpeg",
        "seed": "Sam is telling a meandering story about his weekend that somehow transitioned into expense report complaints.",
    },
    "root_devops_cat": {
        "scene": "Watercooler_Personnel_Generic-DevOpsCat.jpeg",
        "seed": "Root is perched on the water jug, maintaining unblinking eye contact while emitting a low, judgmental purr.",
    },
    "diane_gossip": {
        "scene": "Watercooler_Personnel_Generic-GossipGirls.jpeg",
        "seed": "Diane and her inner circle are exchanging meaningful glances. The social ledger is being updated.",
    },
    "nina_hr": {
        "scene": "Watercooler_Personnel_Generic-HR.jpeg",
        "seed": "Nina is by the watercooler. She has seen six CEOs come and go, and knows exactly how many pens you have taken.",
    },
    "iris_it": {
        "scene": "Watercooler_Personnel_Generic-IT.jpeg",
        "seed": "Iris is attempting to unravel a cat5 cable while glaring at the water cooler's power supply.",
    },
    "alex_lead": {
        "scene": "Watercooler_Personnel_Generic-MiddleManagement.jpeg",
        "seed": "Alex is standing near the watercooler, visibly calculating the ROI of human interaction and finding it lacking.",
    },
    "robo_janitor": {
        "scene": "Watercooler_Personnel_RoboJanitor.jpeg",
        "seed": "The Robo-Janitor hums cheerfully, scrubbing a mysterious stain near the water jug.",
    },
    "tom_finance": {
        "scene": "Watercooler_Personnel_Tom-Lee.jpeg",
        "seed": "Tom is reviewing a spreadsheet on his phone while waiting for his cup to fill.",
    },
    "chen_ux": {
        "scene": "Watercooler_Personnel_ChenWei.jpeg",
        "seed": "Chen Wei is staring at the water cooler's push-button mechanism with deep UX disgust.",
    },
    "pam_reception": {
        "scene": "Watercooler_Personnel_Generic-PamMartinez.jpeg",
        "seed": "Pam is taking a quick break, but her eyes are still tracking everyone who walks by.",
    },
    "carlos_investor": {
        "scene": "Watercooler_Personnel_Generic-InvestorCarlos.jpeg",
        "seed": "Carlos is standing near the cooler, wearing a suit that costs more than your salary.",
    },
    "hr_lady": {
        "scene": "Watercooler_Personnel_Generic-HRLady.jpeg",
        "seed": "The HR Lady is ensuring the water cups are compliant with current corporate wellness initiatives.",
    },
    "matt_sales": {
        "scene": "Watercooler_Personnel_Generic-MatthewJacobs.jpeg",
        "seed": "Matthew is practicing his golf swing next to the watercooler while speaking loudly into a headset.",
    },
    "tony_it": {
        "scene": "Watercooler_Personnel_Generic-TonySalvatore.jpeg",
        "seed": "Tony is dismantling the watercooler's internal thermostat for 'philosophical reasons'.",
    },
    "timothy_intern": {
        "scene": "Watercooler_Personnel_Generic-TimothyLarps.jpeg",
        "seed": "Timothy is holding a reusable bamboo cup and looking at the watercooler like it's a piece of performance art.",
    },
    "hany_pm": {
        "scene": "Watercooler_Personnel_Generic-HanyDefault.jpeg",
        "seed": "Hany is leaning against the wall, checking her watch with a smile that says she knows you're going to help her.",
    },
    "keith_bro": {
        "scene": "Watercooler_Personnel_Generic-KeithAdams.jpeg",
        "seed": "Keith is doing single-arm pushups next to the watercooler while waiting for the filtration light to turn green.",
    }
}

import tomli_w

with open('src/data/npcs.toml', 'rb') as f:
    data = tomllib.load(f)

for npc in data.get('npcs', []):
    npc_id = npc.get('id')
    if npc_id in WATERCOOLER_CONTEXTS:
        npc['watercooler_scene'] = WATERCOOLER_CONTEXTS[npc_id]['scene']
        npc['watercooler_seed'] = WATERCOOLER_CONTEXTS[npc_id]['seed']

with open('src/data/npcs.toml', 'wb') as f:
    tomli_w.dump(data, f)
