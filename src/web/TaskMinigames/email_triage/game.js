const EMAILS = [
    { sender: "HR - Darren", subject: "Mandatory Wellness Seminar", body: "Please attend the 4-hour seminar on avoiding burnout by working more efficiently." },
    { sender: "IT Helpdesk", subject: "Password Expiring", body: "Your password will expire in 4 minutes. Please change it to something with 3 emojis." },
    { sender: "Alex (Lead)", subject: "Quick Sync?", body: "Got a minute to talk about the project? I've invited 14 other people just in case." },
    { sender: "No-Reply", subject: "Jira: [BUG-999] Everything is broken", body: "Priority: Critical. Assigned to: You. Description: It just doesn't feel right." },
    { sender: "CEO Office", subject: "Exciting News!", body: "We are pleased to announce a 0.2% increase in coffee quality. No raises this year." },
    { sender: "Maya (CSM)", subject: "Client is screaming", body: "The client noticed a typo in a comment. They are threatening to leave. Please fix." },
    { sender: "Slack Bot", subject: "New Login", body: "Someone logged into your account from a toaster in Siberia. Was this you?" },
    { sender: "Facilities", subject: "The Microwave", body: "Whoever put fish in the microwave is banned from the building for 48 hours." }
];

let triagedCount = 0;
let stress = 0;
let currentEmail = null;
let gameActive = false;

function init() {
    Minigame.init({
        name: 'email_triage',
        onStart: () => {
            gameActive = true;
            document.getElementById('overlay').classList.add('hidden');
            nextEmail();
        }
    });

    document.addEventListener('keydown', (e) => {
        if (!gameActive) return;
        if (e.key.toLowerCase() === 'a') triage('delete');
        if (e.key.toLowerCase() === 's') triage('archive');
        if (e.key.toLowerCase() === 'd') triage('forward');
    });

    document.getElementById('overlay').addEventListener('click', () => {
        if (!gameActive) {
            gameActive = true;
            document.getElementById('overlay').classList.add('hidden');
            nextEmail();
        }
    });
}

function nextEmail() {
    if (triagedCount >= 20) {
        finish(true);
        return;
    }

    const email = EMAILS[Math.floor(Math.random() * EMAILS.length)];
    currentEmail = email;
    
    const card = document.getElementById('email-card');
    card.className = 'card'; // Reset classes
    document.getElementById('sender').textContent = `From: ${email.sender}`;
    document.getElementById('subject').textContent = `Subject: ${email.subject}`;
    document.getElementById('body').textContent = email.body;
}

function triage(action) {
    if (!gameActive) return;

    const card = document.getElementById('email-card');
    if (action === 'delete') card.classList.add('swipe-left');
    if (action === 'archive') card.classList.add('swipe-up');
    if (action === 'forward') card.classList.add('swipe-right');

    triagedCount++;
    document.getElementById('count').textContent = triagedCount;
    
    // Random stress spikes
    if (Math.random() > 0.7) {
        stress = Math.min(100, stress + 10);
        document.getElementById('stress').textContent = stress;
        if (stress >= 100) finish(false);
    }

    Minigame.progress(triagedCount / 20);

    setTimeout(nextEmail, 200);
}

function finish(success) {
    gameActive = false;
    const overlay = document.getElementById('overlay');
    const title = document.getElementById('overlay-title');
    const subtitle = document.getElementById('overlay-subtitle');

    overlay.classList.remove('hidden');
    
    if (success) {
        title.textContent = "INBOX ZERO ACHIEVED";
        subtitle.textContent = "For the next 5 minutes, at least.";
        Minigame.complete({
            score: 1.0,
            outcome: 'success',
            telemetry: { triaged: triagedCount, stress }
        });
    } else {
        title.textContent = "SYSTEM OVERLOAD";
        subtitle.textContent = "Your brain has been archived.";
        Minigame.complete({
            score: triagedCount / 20,
            outcome: 'dumpster_fire',
            telemetry: { triaged: triagedCount, stress: 100 }
        });
    }
}

window.onload = init;
