let state = {
    npcs: [],
    personas: [],
    scenes: [],
    pfps: [],
    departments: [],
    selectedNpcId: null
};

// DOM Elements
const els = {
    list: document.getElementById('npcList'),
    btnNew: document.getElementById('btnNewNpc'),
    btnSave: document.getElementById('btnSave'),
    editor: document.getElementById('editorContent'),
    empty: document.getElementById('emptyState'),
    
    inId: document.getElementById('inId'),
    inName: document.getElementById('inName'),
    inRole: document.getElementById('inRole'),
    inDept: document.getElementById('inDept'),
    inDesc: document.getElementById('inDesc'),
    
    inReportsTo: document.getElementById('inReportsTo'),
    inArchetype: document.getElementById('inArchetype'),
    selPillar: document.getElementById('selPillar'),
    selPath: document.getElementById('selPath'),
    inCluster: document.getElementById('inCluster'),
    inAmbition: document.getElementById('inAmbition'),
    inBaseTrust: document.getElementById('inBaseTrust'),
    inBaseRivalry: document.getElementById('inBaseRivalry'),
    inInfluenceWeight: document.getElementById('inInfluenceWeight'),
    inInfluenceScope: document.getElementById('inInfluenceScope'),
    inAccessTags: document.getElementById('inAccessTags'),
    inCommStyle: document.getElementById('inCommStyle'),
    inSocialCurrency: document.getElementById('inSocialCurrency'),
    
    selScene: document.getElementById('selScene'),
    selPfp: document.getElementById('selPfp'),
    scenePreview: document.getElementById('scenePreview'),
    pfpPreview: document.getElementById('pfpPreview'),
    inWatercoolerSeed: document.getElementById('inWatercoolerSeed'),
    
    inTone: document.getElementById('inTone'),
    inExamples: document.getElementById('inExamples')
};

// Initialize
async function init() {
    try {
        const res = await fetch('/api/data');
        const data = await res.json();
        
        state.npcs = data.npcs;
        state.personas = data.personas;
        state.scenes = ["", ...data.scenes];
        state.pfps = ["", ...data.pfps];
        state.departments = data.departments || [];
        
        populateDropdowns();
        renderRoster();
    } catch (e) {
        console.error("Failed to load data:", e);
        alert("Failed to load data. Is the server running?");
    }
}

function populateDropdowns() {
    els.selScene.innerHTML = state.scenes.map(s => `<option value="${s}">${s || '-- None --'}</option>`).join('');
    els.selPfp.innerHTML = state.pfps.map(p => `<option value="${p}">${p || '-- None --'}</option>`).join('');
    
    const deptOptions = state.departments.map(d => `<option value="${d.id}">${d.name}</option>`).join('');
    els.inDept.innerHTML = deptOptions;
    els.inCluster.innerHTML = deptOptions;
}

function renderRoster() {
    els.list.innerHTML = state.npcs.map(npc => `
        <li class="${state.selectedNpcId === npc.id ? 'selected' : ''}" onclick="selectNpc('${npc.id}')">
            <strong>${npc.name || npc.id}</strong>
            <span>${npc.role || 'Unknown'}</span>
        </li>
    `).join('');
}

function selectNpc(id) {
    // Save current before switching
    saveCurrentToState();
    
    state.selectedNpcId = id;
    renderRoster();
    
    const npc = state.npcs.find(n => n.id === id);
    const persona = state.personas.find(p => p.id === id) || { id: id, tone: '', examples: [] };
    
    if (npc) {
        els.editor.classList.remove('hidden');
        els.empty.classList.add('hidden');
        
        els.inId.value = npc.id || '';
        els.inName.value = npc.name || '';
        els.inRole.value = npc.role || '';
        els.inDept.value = npc.department || '';
        els.inDesc.value = npc.description || '';
        
        els.inReportsTo.value = npc.reports_to || '';
        els.inArchetype.value = npc.archetype || '';
        els.selPillar.value = npc.pillar || 'technical';
        els.selPath.value = npc.path || 'middle';
        els.inCluster.value = npc.cluster || '';
        els.inAmbition.value = npc.ambition || 0;
        els.inBaseTrust.value = npc.base_trust || 50;
        els.inBaseRivalry.value = npc.base_rivalry || 0;
        els.inInfluenceWeight.value = npc.influence_weight || 0;
        els.inInfluenceScope.value = npc.influence_scope ? npc.influence_scope.join(', ') : '';
        els.inAccessTags.value = npc.access_tags ? npc.access_tags.join(', ') : '';
        els.inCommStyle.value = npc.communication_style || '';
        els.inSocialCurrency.value = npc.social_currency || '';
        
        els.selScene.value = npc.watercooler_scene || '';
        els.selPfp.value = npc.pfp || '';
        els.inWatercoolerSeed.value = npc.watercooler_seed || '';
        
        updatePreviews();
        
        els.inTone.value = persona.tone ? persona.tone.trim() : '';
        els.inExamples.value = persona.examples ? persona.examples.join('\n') : '';
    }
}

function saveCurrentToState() {
    if (!state.selectedNpcId) return;
    
    let npc = state.npcs.find(n => n.id === state.selectedNpcId);
    if (!npc) return; // Should not happen
    
    const newId = els.inId.value.trim();
    if (newId && newId !== state.selectedNpcId) {
        // ID changed. We must update persona ID as well
        let p = state.personas.find(p => p.id === state.selectedNpcId);
        if (p) p.id = newId;
        state.selectedNpcId = newId;
    }
    
    npc.id = state.selectedNpcId;
    npc.name = els.inName.value;
    npc.role = els.inRole.value;
    npc.department = els.inDept.value;
    npc.description = els.inDesc.value;
    
    npc.reports_to = els.inReportsTo.value;
    npc.archetype = els.inArchetype.value;
    npc.pillar = els.selPillar.value;
    npc.path = els.selPath.value;
    npc.cluster = els.inCluster.value;
    npc.ambition = parseInt(els.inAmbition.value) || 0;
    npc.base_trust = parseInt(els.inBaseTrust.value) || 50;
    npc.base_rivalry = parseInt(els.inBaseRivalry.value) || 0;
    npc.influence_weight = parseInt(els.inInfluenceWeight.value) || 0;
    
    const scopeStr = els.inInfluenceScope.value;
    npc.influence_scope = scopeStr ? scopeStr.split(',').map(s => s.trim()).filter(s => s) : [];
    
    const tagsStr = els.inAccessTags.value;
    npc.access_tags = tagsStr ? tagsStr.split(',').map(s => s.trim()).filter(s => s) : [];
    
    npc.communication_style = els.inCommStyle.value;
    npc.social_currency = els.inSocialCurrency.value;
    
    npc.watercooler_scene = els.selScene.value;
    npc.watercooler_seed = els.inWatercoolerSeed.value;
    npc.pfp = els.selPfp.value;
    
    // Persona
    let persona = state.personas.find(p => p.id === state.selectedNpcId);
    const tone = els.inTone.value;
    const examplesStr = els.inExamples.value.trim();
    const examples = examplesStr ? examplesStr.split('\n').filter(e => e.trim()) : [];
    
    if (tone || examples.length > 0) {
        if (!persona) {
            persona = { id: state.selectedNpcId };
            state.personas.push(persona);
        }
        persona.tone = `\n${tone}\n`; // TOML multiline formatting preference
        persona.examples = examples;
    }
}

function updatePreviews() {
    const scene = els.selScene.value;
    const pfp = els.selPfp.value;
    
    els.scenePreview.style.backgroundImage = scene ? `url('/assets/Scenes/${scene}')` : 'none';
    els.pfpPreview.style.backgroundImage = pfp ? `url('/assets/PFPs/${pfp}')` : 'none';
}

// Events
els.selScene.addEventListener('change', updatePreviews);
els.selPfp.addEventListener('change', updatePreviews);

els.btnNew.addEventListener('click', () => {
    saveCurrentToState();
    const newId = 'new_npc_' + Date.now();
    state.npcs.push({
        id: newId,
        name: 'New NPC',
        role: 'Role',
        department: 'department',
        reports_to: 'manager',
        archetype: 'operator',
        ambition: 5,
        base_trust: 50,
        base_rivalry: 0,
        influence_weight: 5,
        influence_scope: ['department'],
        communication_style: 'casual',
        pillar: 'technical',
        path: 'middle',
        cluster: 'backend',
        social_currency: 'currency',
        access_tags: ['tag1']
    });
    selectNpc(newId);
});

els.btnSave.addEventListener('click', async () => {
    saveCurrentToState();
    
    // Clean up empty fields to avoid TOML clutter
    const cleanNpcs = state.npcs.map(n => {
        let clean = { ...n };
        if (!clean.watercooler_scene) delete clean.watercooler_scene;
        if (!clean.pfp) delete clean.pfp;
        if (!clean.watercooler_seed) delete clean.watercooler_seed;
        return clean;
    });

    try {
        const res = await fetch('/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                npcs: cleanNpcs,
                personas: state.personas
            })
        });
        
        if (res.ok) {
            alert('Saved successfully!');
            renderRoster(); // In case names changed
        } else {
            const err = await res.text();
            alert('Error saving: ' + err);
        }
    } catch (e) {
        alert('Network error saving data.');
    }
});

// Boot
init();