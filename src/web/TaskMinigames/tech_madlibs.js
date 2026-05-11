// ============================================================================
// 🎮 MINIGAME: TECH MAD LIBS
// ============================================================================
// A modular minigame component that renders an IDE-style code block with 
// missing variables. The player must select the correct jargon to "fix" it.
// ============================================================================

window.TechMadlibs = {
    render: function(containerElement, onCompleteCallback) {
        // Define the HTML structure for the minigame
        containerElement.innerHTML = `
            <div class="madlibs-wrapper">
                <div class="madlibs-instructions">
                    <span class="warning">CRITICAL ALERT:</span> Production is down! Fill in the missing architecture components to fix the deploy script.
                </div>
                
                <div class="madlibs-ide">
                    <div class="ide-header">
                        <span class="ide-dot red"></span>
                        <span class="ide-dot yellow"></span>
                        <span class="ide-dot green"></span>
                        <span class="ide-title">deploy_script_0x4A.ts</span>
                    </div>
                    <div class="ide-body">
                        <span class="kw">async function</span> <span class="func">deployToProd</span>() {<br>
                        &nbsp;&nbsp;<span class="kw">try</span> {<br>
                        &nbsp;&nbsp;&nbsp;&nbsp;<span class="kw">await</span> 
                        <select id="ml_1" class="ml-select">
                            <option value="" disabled selected>--target--</option>
                            <option value="the Kubernetes cluster">Kubernetes</option>
                            <option value="the legacy mainframe">Legacy Mainframe</option>
                            <option value="the production database">Prod DB</option>
                        </select>.<span class="func">restart</span>();<br><br>
                        
                        &nbsp;&nbsp;&nbsp;&nbsp;console.<span class="func">log</span>(<span class="str">"Services are currently: "</span> + 
                        <input type="text" id="ml_2" placeholder="status..." class="ml-input" autocomplete="off" />);<br><br>
                        
                        &nbsp;&nbsp;} <span class="kw">catch</span> (err) {<br>
                        &nbsp;&nbsp;&nbsp;&nbsp;<span class="func">trigger_</span><select id="ml_3" class="ml-select">
                            <option value="" disabled selected>--fallback--</option>
                            <option value="blame_game">blame_game</option>
                            <option value="rollback">rollback</option>
                            <option value="resume_update">update_resume</option>
                        </select>();<br>
                        &nbsp;&nbsp;}<br>
                        }
                    </div>
                </div>

                <div style="text-align: right; margin-top: 20px;">
                    <button id="ml_submit" class="primary">Push to Prod 🚀</button>
                </div>
            </div>
        `;

        // Bind the submit event
        document.getElementById('ml_submit').addEventListener('click', () => {
            const val1 = document.getElementById('ml_1').value;
            const val2 = document.getElementById('ml_2').value.trim();
            const val3 = document.getElementById('ml_3').value;
            
            // Simple validation
            if (!val1 || !val2 || !val3) {
                alert("The linter is failing. Fill out all missing fields before pushing!");
                return;
            }

            // Construct the natural language narrative based on their choices.
            // This string gets passed back to the engine's LLM to evaluate the task outcome!
            const narrative = `I forcefully restarted ${val1}, reported that the services were '${val2}', and set the fallback protocol to ${val3}.`;
            
            // Pass the generated sentence back to the main UI
            onCompleteCallback(narrative);
        });
    }
};