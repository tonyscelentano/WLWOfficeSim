/**
 * Meeting Dodge: The 5:00 PM Exit
 * A survival game about dodging office distractions.
 */

const canvas = document.getElementById('game-canvas');
const ctx = canvas.getContext('2d');

let gameActive = false;
let startTime = 0;
const DURATION = 30000; // 30 seconds to win

const player = {
    x: 50,
    y: 200,
    size: 20,
    speed: 5,
    color: '#38bdf8'
};

let obstacles = [];
const OBSTACLE_TYPES = [
    { text: "MEETING?", color: "#ef4444" },
    { text: "URGENT!!", color: "#f59e0b" },
    { text: "SLACK", color: "#a855f7" },
    { text: "KPIs", color: "#ef4444" },
    { text: "SYNC", color: "#10b981" }
];

const keys = {};

function init() {
    Minigame.init({
        name: 'meeting_dodge',
        onStart: start
    });

    document.getElementById('start-btn').addEventListener('click', start);
    window.addEventListener('keydown', e => keys[e.code] = true);
    window.addEventListener('keyup', e => keys[e.code] = false);

    drawPlaceholder();
}

function start() {
    gameActive = true;
    startTime = Date.now();
    obstacles = [];
    player.x = 50;
    player.y = 200;
    document.getElementById('overlay').classList.add('hidden');
    requestAnimationFrame(loop);
}

function spawnObstacle() {
    const type = OBSTACLE_TYPES[Math.floor(Math.random() * OBSTACLE_TYPES.length)];
    obstacles.push({
        x: canvas.width + 100,
        y: Math.random() * (canvas.height - 40) + 20,
        text: type.text,
        color: type.color,
        speed: 3 + Math.random() * 4
    });
}

function loop() {
    if (!gameActive) return;

    const elapsed = Date.now() - startTime;
    const remaining = Math.max(0, DURATION - elapsed);
    
    document.getElementById('timer').textContent = `TIME UNTIL EXIT: ${(remaining/1000).toFixed(1)}s`;
    Minigame.progress(elapsed / DURATION);

    if (remaining === 0) {
        finish(true);
        return;
    }

    // Update Player
    if (keys['ArrowUp'] && player.y > 0) player.y -= player.speed;
    if (keys['ArrowDown'] && player.y < canvas.height - player.size) player.y += player.speed;
    if (keys['ArrowLeft'] && player.x > 0) player.x -= player.speed;
    if (keys['ArrowRight'] && player.x < canvas.width - player.size) player.x += player.speed;

    // Spawn Obstacles
    if (Math.random() < 0.05 + (elapsed / DURATION) * 0.1) {
        spawnObstacle();
    }

    // Update Obstacles
    obstacles.forEach((obs, index) => {
        obs.x -= obs.speed;
        
        // Collision detection
        const dist = Math.hypot(player.x - obs.x, player.y - obs.y);
        if (dist < 40) { // Simple bounding box for text
            finish(false);
        }

        if (obs.x < -200) obstacles.splice(index, 1);
    });

    draw();
    requestAnimationFrame(loop);
}

function draw() {
    ctx.fillStyle = '#020617';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw Player (as a little person or dot)
    ctx.fillStyle = player.color;
    ctx.font = '20px Arial';
    ctx.fillText('🏃', player.x, player.y + 20);

    // Draw Obstacles
    obstacles.forEach(obs => {
        ctx.fillStyle = obs.color;
        ctx.font = 'bold 16px "JetBrains Mono"';
        ctx.fillText(obs.text, obs.x, obs.y);
        
        // Shadow/Glow
        ctx.shadowBlur = 10;
        ctx.shadowColor = obs.color;
    });
    ctx.shadowBlur = 0;
}

function drawPlaceholder() {
    ctx.fillStyle = '#020617';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
}

function finish(success) {
    gameActive = false;
    const overlay = document.getElementById('overlay');
    const content = document.getElementById('overlay-content');
    overlay.classList.remove('hidden');

    if (success) {
        content.innerHTML = `
            <h1>OFFICE ESCAPED</h1>
            <p>You made it out before the 5:15 PM meeting!</p>
            <button onclick="location.reload()">REPLAY</button>
        `;
        Minigame.complete({
            score: 1.0,
            outcome: 'legendary',
            telemetry: { time: DURATION }
        });
    } else {
        content.innerHTML = `
            <h1>TRAPPED</h1>
            <p>"Hey, do you have a quick sec?"</p>
            <button onclick="location.reload()">TRY AGAIN</button>
        `;
        Minigame.complete({
            score: 0.5,
            outcome: 'partial',
            telemetry: { time: Date.now() - startTime }
        });
    }
}

init();
