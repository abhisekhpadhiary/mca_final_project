(function () {
  'use strict';

  let examId = null;
  let startTime = null;
  let endTime = null;
  let timerInterval = null;
  let submitted = false; // This flag prevents the repetitive popup loop
  
  let currentQ = 0;
  let totalQs = 0;

  /* ─── Init ─────────────────────────────────────────────────────────── */
  function init(eid, end, start) {
    examId = eid;
    endTime = new Date(end);
    startTime = new Date(start);
    totalQs = document.querySelectorAll('.nptel-q-block').length;
    
    requestFullscreen();
    attachProctorListeners();
    
    if (Date.now() < startTime) {
      startLobbyTimer();
    } else {
      startTimer();
    }
  }

  /* ─── Lobby Timer (Waiting Room) ───────────────────────────────────── */
  function startLobbyTimer() {
    const lobbyDisplay = document.getElementById('lobby-timer');
    
    const lobbyInterval = setInterval(() => {
      const diff = startTime - Date.now();
      
      if (diff <= 0) {
        clearInterval(lobbyInterval);
        document.getElementById('exam-lobby').style.display = 'none';
        document.getElementById('active-exam-ui').style.display = 'block';
        startTimer(); 
        return;
      }
      
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      if(lobbyDisplay) {
        lobbyDisplay.textContent = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
      }
    }, 1000);
  }

  /* ─── Exam Timer ───────────────────────────────────────────────────── */
  function startTimer() {
    const display = document.getElementById('timer-display');

    function tick() {
      const remaining = endTime - Date.now();

      if (remaining <= 0) {
        if (display) display.textContent = '00:00';
        clearInterval(timerInterval);
        if (!submitted) {
          submitAnswers(false);
        }
        return;
      }

      const mins = Math.floor(remaining / 60000);
      const secs = Math.floor((remaining % 60000) / 1000);
      const formatted = `${String(mins).padStart(2,'0')}:${String(secs).padStart(2,'0')}`;

      if (display) {
        display.textContent = formatted;
        display.className = 'time-left' + (remaining < 60000 ? ' danger' : remaining < 300000 ? ' warning' : '');
      }
    }

    tick();
    timerInterval = setInterval(tick, 1000);
  }

  /* ─── Fullscreen & Proctoring ──────────────────────────────────────── */
  function requestFullscreen() {
    const el = document.documentElement;
    const req = el.requestFullscreen || el.webkitRequestFullscreen || el.mozRequestFullScreen || el.msRequestFullscreen;
    if (req) req.call(el).catch(() => {});
  }

  function isFullscreen() {
    return !!(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement);
  }

  function attachProctorListeners() {

    document.addEventListener('visibilitychange', () => { 
      if (document.hidden && !submitted) {
          triggerAutoSubmit('Tab switch detected'); 
      }
    });

    const fsEvents = ['fullscreenchange', 'webkitfullscreenchange', 'mozfullscreenchange', 'MSFullscreenChange'];
    fsEvents.forEach(evt => document.addEventListener(evt, () => {
      if (!isFullscreen() && !submitted) {
          triggerAutoSubmit('Fullscreen exited');
      }
    }));

    // 🔥 ADD BELOW

  window.addEventListener("resize", () => {
    if (!submitted) {
      // More reliable check
      if (!isFullscreen()) {
        triggerAutoSubmit("Fullscreen exited / Window resized");
      }
    }
  });

    window.addEventListener("blur", () => {
      if (!submitted) {
        triggerAutoSubmit("Window lost focus");
      }
    });
  }

  function triggerAutoSubmit(reason) {
    if (submitted) return; // Guard clause to prevent infinite alert loops
    submitted = true;
    clearInterval(timerInterval);
    
    // Create a visual overlay instead of an alert() to avoid focus-loss loops
    const overlay = document.createElement('div');
    overlay.style.cssText = `position:fixed;inset:0;z-index:9999;background:rgba(239,68,68,0.97);display:flex;flex-direction:column;align-items:center;justify-content:center;color:#fff;text-align:center;padding:2rem;`;
    overlay.innerHTML = `<div style="font-size:48px;margin-bottom:1rem;">⚠️</div><h2>Exam Auto-Submitted</h2><p>Reason: <strong>${reason}</strong></p>`;
    document.body.appendChild(overlay);

    // Give the user 1.5 seconds to read the reason before redirecting
    setTimeout(() => { submitAnswers(true); }, 1500);
  }

  function submitAnswers(autoSubmit) {
    // Ensure we mark it as submitted to stop any background timers/alerts
    submitted = true;
    clearInterval(timerInterval);

    const answers = {};
    document.querySelectorAll('.nptel-q-block').forEach((block, idx) => {
      const checked = block.querySelector(`input[name="q${idx}"]:checked`);
      if (checked) answers[idx] = checked.value;
    });

    fetch(`/student/submit/${examId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers, auto_submit: autoSubmit }),
    }).then(() => { window.location.href = '/student/grades'; })
      .catch(() => { window.location.href = '/student/grades'; });
  }

  function manualSubmit() {
    if (submitted || !confirm('Are you sure you want to submit?')) return;
    submitAnswers(false);
  }

  window.ProctorExam = {
    init,
    manualSubmit,
    goToQuestion: function(idx) {
      const currentBlock = document.getElementById(`q-block-${currentQ}`);
      if (currentBlock) currentBlock.style.display = 'none';
      const pal = document.getElementById(`pal-${currentQ}`);
      if (pal && pal.classList.contains('status-not-visited')) pal.className = 'palette-item status-not-answered';
      currentQ = idx;
      const nextBlock = document.getElementById(`q-block-${currentQ}`);
      if (nextBlock) nextBlock.style.display = 'block';
    },
    nextQuestion: function() { if (currentQ < totalQs - 1) this.goToQuestion(currentQ + 1); },
    prevQuestion: function() { if (currentQ > 0) this.goToQuestion(currentQ - 1); },
    updatePalette: function(idx, status) {
      const pal = document.getElementById(`pal-${idx}`);
      if (pal) pal.className = `palette-item status-${status}`;
    },
    markForReview: function() { this.updatePalette(currentQ, 'review'); this.nextQuestion(); },
    clearResponse: function() {
      document.getElementsByName(`q${currentQ}`).forEach(r => r.checked = false);
      this.updatePalette(currentQ, 'not-answered');
    }
  };
})();

/* ─── EXAMINER DASHBOARD LOGIC ─── */
window.ExaminerDashboard = {
    init: function(status) {
        this.filterExams(status);
    },

    filterExams: function(status) {
        document.querySelectorAll('.filter-card').forEach(card => card.classList.remove('active'));
        const activeCard = document.getElementById('card-' + status);
        if (activeCard) activeCard.classList.add('active');

        const titleMap = {
            'live': 'Live Exams (Currently In-Progress)',
            'upcoming': 'Upcoming Scheduled Exams',
            'completed': 'Completed Exam Records'
        };
        const titleEl = document.getElementById('table-title');
        if (titleEl) titleEl.innerText = titleMap[status] || 'Exams';

        const allRows = document.querySelectorAll('.exam-item-row');
        allRows.forEach(row => {
            const isMatch = row.getAttribute('data-status') === status;
            if (row.classList.contains('exam-details-row')) {
                row.style.display = 'none';
                const id = row.id.split('-')[1];
                const chevron = document.getElementById('chevron-' + id);
                if (chevron) chevron.style.transform = 'rotate(0deg)';
            } else {
                row.style.display = isMatch ? 'table-row' : 'none';
            }
        });
    },

    toggleDetails: function(id) {
        const detailsRow = document.getElementById(id);
        const examId = id.split('-')[1];
        const chevron = document.getElementById('chevron-' + examId);
        
        if (detailsRow) {
            const isHidden = detailsRow.style.display === 'none';
            detailsRow.style.display = isHidden ? 'table-row' : 'none';
            if (chevron) chevron.style.transform = isHidden ? 'rotate(90deg)' : 'rotate(0deg)';
        }
    }
};

/* ─── PROFILE & UI LOGIC ─── */
function toggleProfileMenu(event) {
    event.stopPropagation();
    const menu = document.getElementById('new-profile-menu');
    if (menu) menu.classList.toggle('show-menu');
}

window.addEventListener('click', function(e) {
    const menu = document.getElementById('new-profile-menu');
    if (menu && menu.classList.contains('show-menu')) menu.classList.remove('show-menu');
});

/* ─── CONTEXT-AWARE EXAM SECURITY ─── */

// 1. Disable Right-Click during Exam
document.addEventListener('contextmenu', (e) => {
    const activeUI = document.getElementById('active-exam-ui');
    if (activeUI && activeUI.style.display !== 'none') {
        e.preventDefault();
    }
});

// 2. Disable Meta Keys & Ctrl Shortcuts during Exam
document.addEventListener('keydown', (e) => {
    const activeUI = document.getElementById('active-exam-ui');
    if (activeUI && activeUI.style.display !== 'none') {
        const isBlockedKey = e.key === 'Meta' || e.key === 'OS' || e.keyCode === 123;
        const isBlockedShortcut = e.ctrlKey || e.metaKey;

        if (isBlockedKey || isBlockedShortcut) {
            e.preventDefault();
        }
    }
});