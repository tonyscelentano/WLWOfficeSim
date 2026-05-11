/**
 * Tetris: Project Pile-up
 * A corporate-themed Tetris implementation for OfficeSim.
 */

const COLS = 10;
const ROWS = 20;
const BLOCK_SIZE = 30;

const COLORS = {
    'I': '#06b6d4',
    'J': '#3b82f6',
    'L': '#f59e0b',
    'O': '#eab308',
    'S': '#22c55e',
    'T': '#a855f7',
    'Z': '#ef4444'
};

const SHAPES = {
    'I': [[0,0,0,0], [1,1,1,1], [0,0,0,0], [0,0,0,0]],
    'J': [[1,0,0], [1,1,1], [0,0,0]],
    'L': [[0,0,1], [1,1,1], [0,0,0]],
    'O': [[1,1], [1,1]],
    'S': [[0,1,1], [1,1,0], [0,0,0]],
    'T': [[0,1,0], [1,1,1], [0,0,0]],
    'Z': [[1,1,0], [0,1,1], [0,0,0]]
};

class Game {
    constructor() {
        this.canvas = document.getElementById('game-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.nextCanvas = document.getElementById('next-canvas');
        this.nextCtx = this.nextCanvas.getContext('2d');
        
        this.grid = this.createGrid();
        this.score = 0;
        this.lines = 0;
        this.level = 1;
        this.gameOver = false;
        this.paused = true;
        
        this.currentPiece = null;
        this.nextPiece = null;
        
        this.dropCounter = 0;
        this.dropInterval = 1000;
        this.lastTime = 0;
        
        this.init();
    }

    init() {
        this.reset();
        
        // Listen for keyboard
        document.addEventListener('keydown', (e) => {
            if (this.gameOver) {
                this.reset();
                this.start();
                return;
            }
            
            if (this.paused && !this.gameOver) {
                this.start();
                return;
            }

            if (e.key === 'ArrowLeft') this.movePiece(-1, 0);
            if (e.key === 'ArrowRight') this.movePiece(1, 0);
            if (e.key === 'ArrowDown') this.drop();
            if (e.key === 'ArrowUp') this.rotate();
            if (e.key === ' ') this.hardDrop();
        });

        // Minigame Handshake
        Minigame.init({
            name: 'tetris',
            onStart: (task) => {
                document.getElementById('task-name').textContent = task.task_title;
                this.level = task.difficulty || 1;
                this.dropInterval = Math.max(100, 1000 - (this.level - 1) * 100);
                this.start();
            },
            onAbort: () => {
                this.paused = true;
            }
        });

        this.drawPlaceholder();
    }

    createGrid() {
        return Array.from({ length: ROWS }, () => Array(COLS).fill(0));
    }

    reset() {
        this.grid = this.createGrid();
        this.score = 0;
        this.lines = 0;
        this.gameOver = false;
        this.paused = true;
        this.updateStats();
        this.nextPiece = this.getRandomPiece();
        this.spawnPiece();
        document.getElementById('overlay').classList.remove('hidden');
        document.getElementById('overlay-title').textContent = 'PROJECT PILE-UP';
        document.getElementById('overlay-subtitle').textContent = 'Press any key to start';
    }

    start() {
        this.paused = false;
        document.getElementById('overlay').classList.add('hidden');
        requestAnimationFrame(this.update.bind(this));
    }

    getRandomPiece() {
        const types = Object.keys(SHAPES);
        const type = types[Math.floor(Math.random() * types.length)];
        return {
            type,
            shape: SHAPES[type],
            pos: { x: 0, y: 0 },
            color: COLORS[type]
        };
    }

    spawnPiece() {
        this.currentPiece = this.nextPiece;
        this.nextPiece = this.getRandomPiece();
        this.currentPiece.pos = {
            x: Math.floor(COLS / 2) - Math.floor(this.currentPiece.shape[0].length / 2),
            y: 0
        };

        if (this.collide()) {
            this.handleGameOver();
        }
        
        this.drawNext();
    }

    collide() {
        const { shape, pos } = this.currentPiece;
        for (let y = 0; y < shape.length; y++) {
            for (let x = 0; x < shape[y].length; x++) {
                if (shape[y][x] !== 0) {
                    const newX = pos.x + x;
                    const newY = pos.y + y;
                    if (newX < 0 || newX >= COLS || newY >= ROWS || (newY >= 0 && this.grid[newY][newX] !== 0)) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    movePiece(dx, dy) {
        this.currentPiece.pos.x += dx;
        this.currentPiece.pos.y += dy;
        if (this.collide()) {
            this.currentPiece.pos.x -= dx;
            this.currentPiece.pos.y -= dy;
            return false;
        }
        return true;
    }

    rotate() {
        const originalShape = this.currentPiece.shape;
        const n = originalShape.length;
        const newShape = Array.from({ length: n }, () => Array(n).fill(0));
        
        for (let y = 0; y < n; y++) {
            for (let x = 0; x < n; x++) {
                newShape[x][n - 1 - y] = originalShape[y][x];
            }
        }
        
        const oldShape = this.currentPiece.shape;
        this.currentPiece.shape = newShape;
        
        // Wall kick basic
        let offset = 1;
        while (this.collide()) {
            this.currentPiece.pos.x += offset;
            offset = -(offset + (offset > 0 ? 1 : -1));
            if (Math.abs(offset) > originalShape[0].length) {
                this.currentPiece.shape = oldShape;
                this.currentPiece.pos.x -= offset; // Reset pos if still colliding
                return;
            }
        }
    }

    drop() {
        if (!this.movePiece(0, 1)) {
            this.freeze();
            this.clearLines();
            this.spawnPiece();
        }
        this.dropCounter = 0;
    }

    hardDrop() {
        while (this.movePiece(0, 1)) {
            this.score += 2;
        }
        this.freeze();
        this.clearLines();
        this.spawnPiece();
        this.updateStats();
    }

    freeze() {
        const { shape, pos, color } = this.currentPiece;
        shape.forEach((row, y) => {
            row.forEach((value, x) => {
                if (value !== 0) {
                    const gridY = pos.y + y;
                    if (gridY >= 0) {
                        this.grid[gridY][pos.x + x] = color;
                    }
                }
            });
        });
    }

    clearLines() {
        let linesCleared = 0;
        for (let y = ROWS - 1; y >= 0; y--) {
            if (this.grid[y].every(cell => cell !== 0)) {
                this.grid.splice(y, 1);
                this.grid.unshift(Array(COLS).fill(0));
                linesCleared++;
                y++;
            }
        }
        
        if (linesCleared > 0) {
            this.lines += linesCleared;
            const points = [0, 100, 300, 500, 800];
            this.score += points[linesCleared] * this.level;
            this.updateStats();

            // Real-time Rewards
            const energyGain = linesCleared * 2;
            const stressLoss = -linesCleared * 3;
            
            this.showFeedback(`+${energyGain} Energy`, '#22c55e');
            this.showFeedback(`${stressLoss} Stress`, '#38bdf8', 30);
            
            window.parent.postMessage({ 
                type: 'vitals:update', 
                energy: energyGain, 
                stress: stressLoss 
            }, '*');
            
            // Report progress to parent
            Minigame.progress(Math.min(1, this.lines / 10)); // Goal: clear 10 lines
            
            if (this.lines >= 10) {
                this.handleWin();
            }
        }
    }

    showFeedback(text, color, yOffset = 0) {
        const board = document.getElementById('board-container');
        const el = document.createElement('div');
        el.className = 'floating-text';
        el.textContent = text;
        el.style.color = color;
        el.style.left = '50%';
        el.style.top = `${50 + yOffset}%`;
        el.style.transform = 'translateX(-50%)';
        board.appendChild(el);
        setTimeout(() => el.remove(), 1000);
    }


    updateStats() {
        document.getElementById('score').textContent = this.score;
        document.getElementById('lines').textContent = this.lines;
    }

    handleGameOver() {
        this.gameOver = true;
        this.paused = true;
        document.getElementById('overlay').classList.remove('hidden');
        document.getElementById('overlay-title').textContent = 'DEADLINE MISSED';
        document.getElementById('overlay-subtitle').textContent = 'Project Overload. Try again?';
        
        Minigame.complete({
            score: this.lines / 10,
            outcome: 'dumpster_fire',
            telemetry: { lines: this.lines, score: this.score, reason: 'overflow' }
        });
    }

    handleWin() {
        this.gameOver = true;
        this.paused = true;
        document.getElementById('overlay').classList.remove('hidden');
        document.getElementById('overlay-title').textContent = 'PROJECT SHIPPED';
        document.getElementById('overlay-subtitle').textContent = 'Incredible workflow efficiency!';

        // Big Win Rewards
        window.parent.postMessage({ 
            type: 'vitals:update', 
            energy: 20, 
            stress: -30 
        }, '*');
        
        Minigame.complete({
            score: 1.0,
            outcome: 'legendary',
            telemetry: { lines: this.lines, score: this.score, reason: 'quota_met' }
        });
    }


    update(time = 0) {
        if (this.paused) return;
        
        const deltaTime = time - this.lastTime;
        this.lastTime = time;
        
        this.dropCounter += deltaTime;
        if (this.dropCounter > this.dropInterval) {
            this.drop();
        }
        
        this.draw();
        requestAnimationFrame(this.update.bind(this));
    }

    draw() {
        // Clear background
        this.ctx.fillStyle = '#020617';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw grid
        this.drawGrid();
        
        // Draw piece
        if (this.currentPiece) {
            this.drawPiece(this.ctx, this.currentPiece);
            this.drawGhost();
        }
    }

    drawGrid() {
        this.grid.forEach((row, y) => {
            row.forEach((color, x) => {
                if (color !== 0) {
                    this.drawBlock(this.ctx, x, y, color);
                }
            });
        });
        
        // Draw grid lines (subtle)
        this.ctx.strokeStyle = 'rgba(255,255,255,0.03)';
        for (let x = 0; x <= COLS; x++) {
            this.ctx.beginPath();
            this.ctx.moveTo(x * BLOCK_SIZE, 0);
            this.ctx.lineTo(x * BLOCK_SIZE, ROWS * BLOCK_SIZE);
            this.ctx.stroke();
        }
        for (let y = 0; y <= ROWS; y++) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y * BLOCK_SIZE);
            this.ctx.lineTo(COLS * BLOCK_SIZE, y * BLOCK_SIZE);
            this.ctx.stroke();
        }
    }

    drawPiece(ctx, piece, offset = { x: 0, y: 0 }, scale = 1) {
        const size = BLOCK_SIZE * scale;
        piece.shape.forEach((row, y) => {
            row.forEach((value, x) => {
                if (value !== 0) {
                    this.drawBlock(ctx, piece.pos.x + x + offset.x, piece.pos.y + y + offset.y, piece.color, scale);
                }
            });
        });
    }

    drawBlock(ctx, x, y, color, scale = 1) {
        const size = BLOCK_SIZE * scale;
        ctx.fillStyle = color;
        ctx.fillRect(x * size, y * size, size, size);
        
        // Add highlight
        ctx.fillStyle = 'rgba(255,255,255,0.2)';
        ctx.fillRect(x * size, y * size, size, size / 4);
        ctx.fillRect(x * size, y * size, size / 4, size);
        
        // Add shadow
        ctx.fillStyle = 'rgba(0,0,0,0.2)';
        ctx.fillRect(x * size, (y + 1) * size - size / 4, size, size / 4);
        ctx.fillRect((x + 1) * size - size / 4, y * size, size / 4, size);
        
        // Border
        ctx.strokeStyle = 'rgba(0,0,0,0.3)';
        ctx.strokeRect(x * size, y * size, size, size);
    }

    drawGhost() {
        const ghost = JSON.parse(JSON.stringify(this.currentPiece));
        while (true) {
            ghost.pos.y++;
            if (this.collideGhost(ghost)) {
                ghost.pos.y--;
                break;
            }
        }
        
        // Draw ghost with transparency
        this.ctx.globalAlpha = 0.2;
        this.drawPiece(this.ctx, ghost);
        this.ctx.globalAlpha = 1.0;
    }

    collideGhost(ghost) {
        const { shape, pos } = ghost;
        for (let y = 0; y < shape.length; y++) {
            for (let x = 0; x < shape[y].length; x++) {
                if (shape[y][x] !== 0) {
                    const newX = pos.x + x;
                    const newY = pos.y + y;
                    if (newX < 0 || newX >= COLS || newY >= ROWS || (newY >= 0 && this.grid[newY][newX] !== 0)) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    drawNext() {
        this.nextCtx.fillStyle = '#0f172a';
        this.nextCtx.fillRect(0, 0, this.nextCanvas.width, this.nextCanvas.height);
        
        const piece = this.nextPiece;
        const scale = 20 / BLOCK_SIZE;
        const offsetX = (this.nextCanvas.width / 20 - piece.shape[0].length) / 2;
        const offsetY = (this.nextCanvas.height / 20 - piece.shape.length) / 2;
        
        piece.shape.forEach((row, y) => {
            row.forEach((value, x) => {
                if (value !== 0) {
                    this.drawBlock(this.nextCtx, x + offsetX, y + offsetY, piece.color, scale);
                }
            });
        });
    }

    drawPlaceholder() {
        this.draw();
        this.drawNext();
    }
}

// Start the game
window.addEventListener('load', () => {
    new Game();
});
