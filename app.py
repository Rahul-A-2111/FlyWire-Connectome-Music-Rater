import os
import json
import queue
import threading
from flask import Flask, request, Response, render_template_string, jsonify
from flask_cors import CORS
from judge_engine import evaluate_song_with_fly

app = Flask(__name__, static_folder='static')
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Fly Connectome Music Rater — 1930s Noir Edition</title>
<!-- Tailwind CSS -->
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<!-- Google Fonts -->
<link href="https://fonts.googleapis.com" rel="preconnect"/>
<link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/>
<link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700;900&family=Playfair+Display:ital,wght@0,600;0,800;1,600&family=Courier+Prime:ital,wght@0,400;0,700;1,400&family=Special+Elite&family=Bebas+Neue&family=Bricolage+Grotesque:wght@400;600;700&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<script>
    tailwind.config = {
      darkMode: "class",
      theme: {
        extend: {
          colors: {
            noir: {
              950: '#070b14',
              900: '#0a1020',
              850: '#111a30',
              800: '#1a2745',
              700: '#28375c',
              gold: '#d4af37',
              creme: '#f4ece1',
              aged: '#c8bfae',
              amber: '#f59e0b',
              sepia: '#e4d3b6'
            }
          },
          fontFamily: {
            cinzel: ['"Cinzel Decorative"', 'serif'],
            playfair: ['"Playfair Display"', 'serif'],
            mono: ['"Courier Prime"', 'monospace'],
            vintage: ['"Special Elite"', 'cursive']
          }
        }
      }
    }
  </script>
<style>
    body {
      background-color: #04122e;
      color: #f4ece1;
      overflow-x: hidden;
    }

    .film-vignette {
      box-shadow: inset 0 0 130px rgba(1, 13, 41, 0.95), inset 0 0 220px rgba(0, 0, 0, 0.9);
      pointer-events: none;
    }

    .spotlight-radial {
      background: radial-gradient(ellipse at 50% 10%, rgba(212, 175, 55, 0.18) 0%, rgba(244, 236, 225, 0.05) 40%, transparent 75%);
    }

    @keyframes rubber-hose-idle {
      0%, 100% { transform: translateY(0px) rotate(0deg); }
      25% { transform: translateY(-5px) rotate(-1deg); }
      50% { transform: translateY(0px) rotate(0deg); }
      75% { transform: translateY(-3px) rotate(1deg); }
    }
    .animate-rubber-bob {
      animation: rubber-hose-idle 2.8s infinite ease-in-out;
    }

    @keyframes gold-pulse {
      0%, 100% { box-shadow: 0 0 15px rgba(212, 175, 55, 0.4); }
      50% { box-shadow: 0 0 30px rgba(212, 175, 55, 0.85); }
    }
    .btn-gold-pulse {
      animation: gold-pulse 1.8s infinite ease-in-out;
    }

    .striped-bar {
      background-image: repeating-linear-gradient(
        -45deg,
        rgba(212, 175, 55, 0.9),
        rgba(212, 175, 55, 0.9) 12px,
        rgba(244, 236, 225, 0.85) 12px,
        rgba(244, 236, 225, 0.85) 24px
      );
      background-size: 34px 34px;
      animation: barberpole 0.9s linear infinite;
    }
    @keyframes barberpole {
      from { background-position: 0 0; }
      to { background-position: 34px 0; }
    }

    @keyframes flash-pop {
      0% { filter: brightness(2) contrast(150%); }
      100% { filter: brightness(1) contrast(100%); }
    }
    .film-flash {
      animation: flash-pop 0.4s ease-out;
    }
  </style>
</head>
<body class="relative min-h-screen flex flex-col justify-between selection:bg-noir-gold selection:text-noir-950 font-playfair">

<div class="fixed inset-0 film-vignette z-40 pointer-events-none"></div>
<div class="fixed inset-0 spotlight-radial z-0 pointer-events-none"></div>

<!-- FLOATING TOAST -->
<div class="fixed top-3 left-1/2 -translate-x-1/2 z-50 pointer-events-none opacity-0 transition-all duration-500 transform -translate-y-4" id="reset-toast">
<div class="flex items-center gap-3 px-5 py-2 rounded-full bg-noir-900/95 border border-noir-gold/80 shadow-2xl backdrop-blur-md">
<span class="inline-block w-2 h-2 rounded-full bg-noir-gold animate-ping"></span>
<span class="font-mono text-[11px] tracking-wider text-noir-creme uppercase font-bold">RECEPTORS ZEROED • READY FOR NEW TRACK</span>
</div>
</div>

<!-- HEADER (Compact viewport spacing) -->
<header class="relative z-30 pt-4 pb-1 text-center px-4 max-w-4xl mx-auto w-full">
<div class="inline-flex items-center gap-2 px-3 py-0.5 rounded-full border border-noir-700 bg-noir-900/85 shadow mb-1">
<span class="w-1.5 h-1.5 rounded-full bg-noir-gold animate-ping"></span>
<span class="font-mono text-[10px] tracking-[0.2em] text-noir-aged uppercase">Drosophila Biosonic Sound Laboratories</span>
</div>
<h1 class="font-cinzel text-2xl sm:text-3xl md:text-4xl font-black tracking-wide text-noir-creme uppercase leading-tight">
  WELCOME TO FLY CONNECTOME <span class="text-transparent bg-clip-text bg-gradient-to-r from-noir-gold via-amber-200 to-noir-gold">MUSIC RATER</span>
</h1>
<p class="font-vintage text-[11px] sm:text-xs tracking-widest text-noir-aged mt-1 uppercase">
  GET READY FOR THE MUSIC CONNOISSEUR FLY TO JUDGE YOUR TASTE IN MUSIC
</p>
</header>

<!-- MAIN STAGE -->
<main class="relative z-20 flex-1 flex flex-col items-center justify-center px-4 w-full max-w-2xl mx-auto py-1">
<div class="relative w-full transition-all duration-500 ease-out transform" id="hero-frame-container">
<div class="relative p-2.5 rounded-2xl bg-gradient-to-b from-noir-850 via-noir-900 to-noir-950 border-2 border-noir-700 shadow-2xl">

<!-- VIEWPORT -->
<div class="relative overflow-hidden rounded-xl aspect-[16/10] bg-noir-950 flex items-center justify-center border border-noir-700 shadow-inner" id="media-viewport">
  
  <!-- STATE 1: Hero Image Frame -->
  <div class="absolute inset-0 transition-opacity duration-500 opacity-100 flex items-center justify-center" id="view-hero-image">
    <img alt="Lord Drosophila" class="w-full h-full object-cover filter contrast-110 sepia-[0.15] brightness-95 animate-rubber-bob" id="hero-fly-img" src="/static/fly_hero.png" onerror="this.onerror=null; this.src='https://lh3.googleusercontent.com/aida/AEtjO1Wo4SrTXHjt7XLcJwhiWS43VcBER2LCMbKK-mFqqSX5Qjb0bDibGsHsrpxxGPMfEr1x0J_SZ9v37-eQWC5UcPf4VDzvxGloi2VN-u8RgFF792e95Cni7u6Rs-levQ6pvF0liRsbkeCaxKixoG6r7PMjsWkrK97nriqdzvCEsjLz9iXYnVK5Rl4s_8Fy9q_RbnTDCLcnNKjKVfs-FXDJgLZ9CiAK_fdZR_UUju9P8T9ad92eEqNX0pVV6Ds';"/>
    <div class="absolute bottom-2 left-3 right-3 flex justify-between items-end pointer-events-none">
      <span class="font-cinzel text-[11px] text-noir-creme bg-noir-900/90 px-2.5 py-0.5 rounded border border-noir-700">SUBJECT: LORD DROSOPHILA, ESQ.</span>
      <span class="font-mono text-[9px] text-noir-gold tracking-widest bg-noir-950/90 px-2 py-0.5 rounded border border-noir-700/80" id="hero-audit-status">STATUS: IDLE</span>
    </div>
  </div>

  <!-- STATE 4: MP4 Reaction Video Viewport (Hidden initially) -->
  <div class="absolute inset-0 opacity-0 pointer-events-none transition-all duration-500 flex items-center justify-center bg-noir-950 z-20" id="view-video-player">
    <video class="w-full h-full object-cover" id="flyVideo" muted controls>
        <source id="videoSource" src="" type="video/mp4">
    </video>
  </div>

  <!-- STATE 3: "SEE RESULTS" POPUP OVERLAY (Hidden initially) -->
  <div class="absolute inset-0 z-30 flex items-center justify-center bg-noir-950/80 backdrop-blur-sm opacity-0 pointer-events-none transition-all duration-300 transform scale-90" id="reveal-popup">
    <div class="text-center p-5 border-2 border-noir-gold/90 rounded-xl bg-noir-900/95 shadow-2xl max-w-xs w-full mx-3">
      <div class="text-[10px] font-mono tracking-widest text-noir-aged mb-1">BRAIN SCAN COMPLETE</div>
      <div class="text-xl font-cinzel text-noir-gold font-bold mb-2">★ NEURAL VERDICT READY ★</div>
      <button class="w-full py-3 px-5 rounded-lg font-cinzel text-xs font-black tracking-widest uppercase bg-gradient-to-r from-noir-gold via-amber-200 to-noir-gold text-noir-950 shadow-xl hover:brightness-110 active:scale-95 transition-all btn-gold-pulse cursor-pointer" id="btn-see-results">
        SEE RESULTS ➔
      </button>
    </div>
  </div>

</div>
</div>
</div>

<!-- INPUT CONSOLE BAR -->
<div class="w-full max-w-2xl mt-3 relative z-30">
  <div class="relative transition-all duration-500" id="chat-bar-container">
    <label class="group relative flex items-center justify-between w-full p-2 pl-4 pr-2 rounded-full bg-noir-900/95 border-2 border-noir-700 hover:border-noir-gold shadow-xl backdrop-blur-md cursor-pointer transition-all" for="audio-file-input">
      <div class="flex items-center gap-3 flex-1 overflow-hidden">
        <span class="material-symbols-outlined text-noir-gold text-xl">mic</span>
        <span class="font-playfair italic text-xs text-noir-aged truncate group-hover:text-noir-creme" id="chat-bar-placeholder">
          Drag and drop your track or click to upload audio (.mp3, .wav)...
        </span>
      </div>
      <input accept="audio/*" class="sr-only" id="audio-file-input" type="file"/>
      <button class="shrink-0 ml-2 w-9 h-9 rounded-full bg-gradient-to-br from-noir-gold via-amber-400 to-amber-600 text-noir-950 flex items-center justify-center font-bold shadow hover:scale-105 active:scale-95 transition-all cursor-pointer" type="button">
        <span class="material-symbols-outlined font-black text-xl">arrow_upward</span>
      </button>
    </label>
  </div>

  <!-- RETRO SCANNING CONSOLE -->
  <div class="hidden opacity-0 transform translate-y-2 transition-all duration-500 p-4 rounded-xl bg-noir-900/95 border-2 border-noir-gold/70 shadow-xl backdrop-blur-md" id="loading-card">
    <div class="flex items-center justify-between mb-2">
      <div class="flex items-center gap-2">
        <span class="inline-block w-2.5 h-2.5 rounded-full bg-noir-gold animate-ping"></span>
        <span class="font-cinzel text-xs font-bold tracking-wider text-noir-creme">CONNECTOME SCANNER ACTIVE</span>
      </div>
      <span class="font-mono text-xs text-noir-gold font-bold" id="loading-percentage">0%</span>
    </div>
    <div class="font-mono text-[11px] text-noir-sepia italic mb-2 truncate" id="loading-step-text">
      1. Converting Audio Stream...
    </div>
    <div class="w-full bg-noir-950 h-3 rounded-full overflow-hidden border border-noir-700 p-[1px]">
      <div class="h-full striped-bar rounded-full w-0 transition-all duration-150 ease-out" id="progress-bar-fill"></div>
    </div>
  </div>
</div>
</main>

<!-- METRICS SLIDE-UP DASHBOARD -->
<div class="fixed inset-x-0 bottom-0 z-50 transform translate-y-full transition-transform duration-700 ease-out max-h-[85vh] overflow-y-auto px-4 pb-6 pt-3 bg-noir-950/98 border-t-2 border-noir-gold/90 shadow-2xl backdrop-blur-xl" id="metrics-dashboard">
<div class="flex flex-col items-center justify-center mb-3">
<div class="w-12 h-1 rounded-full bg-noir-700 mb-1"></div>
<div class="font-mono text-[9px] text-noir-gold tracking-widest uppercase">✦ CONNECTOME FINAL RATING TICKET ✦</div>
</div>

<div class="max-w-3xl mx-auto">
<div class="p-4 rounded-xl bg-gradient-to-r from-noir-900 via-noir-850 to-noir-900 border border-noir-gold/50 shadow-xl flex flex-col md:flex-row items-center justify-between gap-4 mb-4">
<div>
  <div class="flex items-center gap-2 mb-1">
    <span class="font-mono text-[10px] text-noir-aged border border-noir-700 bg-noir-950 px-2 py-0.5 rounded" id="metrics-track-title">TRACK: Audio Track</span>
    <span class="font-mono text-[10px] font-bold text-noir-950 bg-noir-gold px-2.5 py-0.5 rounded-full" id="metrics-rank-badge">RANK S+</span>
  </div>
  <h2 class="font-cinzel text-xl sm:text-2xl font-black text-noir-creme" id="metrics-verdict-title">THE FLY IS OFFICIALLY GROOVING!</h2>
  <p class="font-vintage text-xs text-noir-sepia mt-1 italic" id="metrics-verdict-comment">"Ah, sheer perfection! Antennal micro-hairs vibrating in complete harmonic resonance."</p>
</div>
<div class="shrink-0 text-center px-4 py-3 rounded-lg bg-noir-950 border border-noir-gold shadow min-w-[140px]">
  <div class="font-mono text-[9px] tracking-widest text-noir-aged uppercase">AFFINITY SCORE</div>
  <div class="font-cinzel text-3xl font-black text-transparent bg-clip-text bg-gradient-to-b from-noir-gold to-amber-200" id="metrics-affinity-score">98.4</div>
  <div class="font-mono text-[10px] text-noir-gold font-bold">/ 100 MAXIMUM BUZZ</div>
</div>
</div>

<div class="grid grid-cols-2 sm:grid-cols-5 gap-2.5 mb-6">
  <div class="p-3 rounded-lg bg-noir-900/90 border border-noir-700/80">
    <div class="text-[9px] font-mono text-noir-aged uppercase mb-0.5">JO-AB RESONANCE</div>
    <div class="font-cinzel text-lg font-bold text-noir-creme" id="metric-organ">99%</div>
    <div class="w-full bg-noir-950 h-1 rounded-full mt-1 overflow-hidden"><div class="bg-noir-gold h-full w-[99%]" id="bar-organ"></div></div>
  </div>
  <div class="p-3 rounded-lg bg-noir-900/90 border border-noir-700/80">
    <div class="text-[9px] font-mono text-noir-aged uppercase mb-0.5">COURTSHIP PULSE</div>
    <div class="font-cinzel text-lg font-bold text-noir-creme" id="metric-courtship">97%</div>
    <div class="w-full bg-noir-950 h-1 rounded-full mt-1 overflow-hidden"><div class="bg-noir-gold h-full w-[97%]" id="bar-courtship"></div></div>
  </div>
  <div class="p-3 rounded-lg bg-noir-900/90 border border-noir-700/80">
    <div class="text-[9px] font-mono text-noir-aged uppercase mb-0.5">FLIGHT MOTOR</div>
    <div class="font-cinzel text-lg font-bold text-noir-creme" id="metric-flight">94%</div>
    <div class="w-full bg-noir-950 h-1 rounded-full mt-1 overflow-hidden"><div class="bg-amber-400 h-full w-[94%]" id="bar-flight"></div></div>
  </div>
  <div class="p-3 rounded-lg bg-noir-900/90 border border-noir-700/80">
    <div class="text-[9px] font-mono text-noir-aged uppercase mb-0.5">SWATTER ESCAPE</div>
    <div class="font-cinzel text-lg font-bold text-rose-400" id="metric-threat">02%</div>
    <div class="w-full bg-noir-950 h-1 rounded-full mt-1 overflow-hidden"><div class="bg-rose-500 h-full w-[2%]" id="bar-threat"></div></div>
  </div>
  <div class="p-3 rounded-lg bg-noir-900/90 border border-noir-700/80 col-span-2 sm:col-span-1">
    <div class="text-[9px] font-mono text-noir-aged uppercase mb-0.5">DOPAMINE SURGE</div>
    <div class="font-cinzel text-lg font-bold text-emerald-400" id="metric-dopamine">+3.8x</div>
    <div class="w-full bg-noir-950 h-1 rounded-full mt-1 overflow-hidden"><div class="bg-emerald-400 h-full w-[96%]" id="bar-dopamine"></div></div>
  </div>
</div>

<div class="text-center pt-1">
  <button class="px-6 py-3 rounded-lg font-cinzel text-xs font-black tracking-widest uppercase bg-gradient-to-r from-noir-850 via-noir-800 to-noir-850 text-noir-gold border border-noir-gold hover:bg-noir-gold hover:text-noir-950 transition-all cursor-pointer" id="btn-reset-app">
    ✦ CHOOSE NEW SONG FOR RATING ✦
  </button>
</div>
</div>
</div>

<footer class="relative z-20 py-2 text-center text-[10px] font-mono text-noir-aged/60 border-t border-noir-850 bg-noir-950/85 px-4">
  DROSOPHILA MELANOGASTER AUDIT ENGINE • CONNECTOME ATLAS 4.8.19
</footer>

<!-- SCRIPT ENGINE -->
<script>
window.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('audio-file-input');
    const chatBarContainer = document.getElementById('chat-bar-container');
    const chatBarPlaceholder = document.getElementById('chat-bar-placeholder');

    const heroFrameContainer = document.getElementById('hero-frame-container');
    const viewHeroImage = document.getElementById('view-hero-image');
    const heroAuditStatus = document.getElementById('hero-audit-status');

    const loadingCard = document.getElementById('loading-card');
    const loadingPercentage = document.getElementById('loading-percentage');
    const loadingStepText = document.getElementById('loading-step-text');
    const progressBarFill = document.getElementById('progress-bar-fill');

    const revealPopup = document.getElementById('reveal-popup');
    const btnSeeResults = document.getElementById('btn-see-results');

    const viewVideoPlayer = document.getElementById('view-video-player');
    const flyVideo = document.getElementById('flyVideo');
    const videoSource = document.getElementById('videoSource');

    const metricsDashboard = document.getElementById('metrics-dashboard');
    const btnResetApp = document.getElementById('btn-reset-app');
    const resetToast = document.getElementById('reset-toast');

    let evalData = null;
    let toastTimer = null;

    // FULL RESET TO INITIAL STATE
    function resetToPristine(showToast = true) {
        metricsDashboard.classList.remove('translate-y-0');
        metricsDashboard.classList.add('translate-y-full');

        // Hide Video Viewport & Reset Video Player
        viewVideoPlayer.classList.add('opacity-0', 'pointer-events-none');
        viewVideoPlayer.classList.remove('opacity-100');
        flyVideo.pause();
        flyVideo.currentTime = 0;

        // Restore Hero Image
        viewHeroImage.classList.remove('opacity-0');
        viewHeroImage.classList.add('opacity-100');
        heroAuditStatus.textContent = "STATUS: IDLE";

        // CRITICAL FIX: Explicitly Hide Reveal Popup Modal
        revealPopup.classList.add('opacity-0', 'scale-90', 'pointer-events-none');
        revealPopup.classList.remove('opacity-100', 'scale-100');

        // Hide Loading Card
        loadingCard.classList.add('hidden', 'opacity-0', 'translate-y-2');
        progressBarFill.style.width = '0%';
        loadingPercentage.textContent = '0%';

        // Restore Chat Bar Input
        chatBarPlaceholder.textContent = "Drag and drop your track or click to upload audio (.mp3, .wav)...";
        fileInput.value = '';
        chatBarContainer.classList.remove('hidden', 'opacity-0', 'scale-95');

        if (showToast && resetToast) {
            clearTimeout(toastTimer);
            resetToast.classList.remove('opacity-0', '-translate-y-4');
            resetToast.classList.add('opacity-100', 'translate-y-0');
            toastTimer = setTimeout(() => {
                resetToast.classList.remove('opacity-100', 'translate-y-0');
                resetToast.classList.add('opacity-0', '-translate-y-4');
            }, 2500);
        }
    }

    btnResetApp.addEventListener('click', () => resetToPristine(true));

    fileInput.addEventListener('change', async (e) => {
        if (!e.target.files[0]) return;
        const file = e.target.files[0];

        chatBarPlaceholder.textContent = file.name;
        chatBarContainer.classList.add('opacity-0', 'scale-95');

        setTimeout(() => {
            chatBarContainer.classList.add('hidden');
            loadingCard.classList.remove('hidden');
            void loadingCard.offsetWidth;
            loadingCard.classList.remove('opacity-0', 'translate-y-2');
        }, 280);

        const formData = new FormData();
        formData.append('song', file);

        try {
            const uploadRes = await fetch('/upload', { method: 'POST', body: formData });
            const uploadData = await uploadRes.json();

            const eventSource = new EventSource(`/stream_judge/${uploadData.filename}`);
            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.stage) loadingStepText.textContent = data.stage;
                if (data.progress !== undefined) {
                    progressBarFill.style.width = data.progress + '%';
                    loadingPercentage.textContent = data.progress + '%';
                }

                if (data.result) {
                    eventSource.close();
                    evalData = data;

                    loadingCard.classList.add('opacity-0');
                    setTimeout(() => loadingCard.classList.add('hidden'), 300);

                    // Reveal Popup Modal
                    revealPopup.classList.remove('pointer-events-none', 'opacity-0', 'scale-90');
                    revealPopup.classList.add('opacity-100', 'scale-100');
                }
            };
        } catch (err) {
            alert('Scan Error: ' + err.message);
            resetToPristine(false);
        }
    });

    // 1. CLICK "SEE RESULTS" -> HIDE POPUP COMPLETELY & PLAY VIDEO
    btnSeeResults.addEventListener('click', () => {
        // CRITICAL FIX: Hide popup modal completely before video starts
        revealPopup.classList.add('opacity-0', 'scale-90', 'pointer-events-none');
        revealPopup.classList.remove('opacity-100', 'scale-100');

        heroFrameContainer.classList.add('film-flash');
        viewHeroImage.classList.add('opacity-0');

        // Assign video source
        videoSource.src = evalData.result === "GOOD" ? "/static/fly_good.mp4" : "/static/fly_bad.mp4";

        viewVideoPlayer.classList.remove('pointer-events-none', 'opacity-0');
        viewVideoPlayer.classList.add('opacity-100');

        flyVideo.load();
        flyVideo.play();
    });

    // 2. WHEN VIDEO ENDS -> SLIDE UP METRICS DASHBOARD
    flyVideo.addEventListener('ended', () => {
        populateDashboard(evalData);

        metricsDashboard.classList.remove('translate-y-full');
        metricsDashboard.classList.add('translate-y-0');
    });

    function populateDashboard(data) {
        document.getElementById('metrics-affinity-score').textContent = data.score;

        const rankBadge = document.getElementById('metrics-rank-badge');
        const verdictTitle = document.getElementById('metrics-verdict-title');
        const verdictComment = document.getElementById('metrics-verdict-comment');

        if (data.result === "GOOD") {
            rankBadge.textContent = "RANK S+ // MAXIMUM BUZZ";
            verdictTitle.textContent = "THE FLY IS OFFICIALLY GROOVING!";
            verdictComment.textContent = "“Ah, sheer perfection! Antennal micro-hairs vibrating in complete harmonic resonance.”";
        } else {
            rankBadge.textContent = "RANK F // SWATTER ESCAPE";
            verdictTitle.textContent = "THE FLY IS IN UTTER AGONY!";
            verdictComment.textContent = "“Preposterous din! Unendurable screeching across non-harmonic spectrums. Giant Fiber escape circuits activated.”";
        }

        document.getElementById('metric-organ').textContent = Math.round(data.courtship_sync) + "%";
        document.getElementById('bar-organ').style.width = Math.round(data.courtship_sync) + "%";

        document.getElementById('metric-courtship').textContent = Math.round(data.courtship_sync * 0.95) + "%";
        document.getElementById('bar-courtship').style.width = Math.round(data.courtship_sync * 0.95) + "%";

        document.getElementById('metric-flight').textContent = Math.round(data.flight_motor) + "%";
        document.getElementById('bar-flight').style.width = Math.round(data.flight_motor) + "%";

        const threatPct = Math.round(data.threat_coefficient * 100);
        document.getElementById('metric-threat').textContent = threatPct + "%";
        document.getElementById('bar-threat').style.width = threatPct + "%";

        document.getElementById('metric-dopamine').textContent = "+" + (data.dopamine_surge / 20).toFixed(1) + "x";
        document.getElementById('bar-dopamine').style.width = Math.round(data.dopamine_surge) + "%";
    }
});
</script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload():
    if 'song' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['song']
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    return jsonify({"filename": file.filename})

@app.route('/stream_judge/<filename>')
def stream_judge(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    def generate():
        msg_queue = queue.Queue()

        def callback(data_dict):
            msg_queue.put(data_dict)

        result_holder = {}

        def run_eval():
            try:
                res = evaluate_song_with_fly(file_path, progress_callback=callback)
                result_holder['data'] = res
            except Exception as e:
                result_holder['error'] = str(e)
            finally:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
                msg_queue.put(None)

        thread = threading.Thread(target=run_eval)
        thread.start()

        while True:
            msg = msg_queue.get()
            if msg is None:
                break
            yield f"data: {json.dumps(msg)}\n\n"

        if 'data' in result_holder:
            yield f"data: {json.dumps(result_holder['data'])}\n\n"
        else:
            yield f"data: {json.dumps({'result': 'BAD', 'score': 0, 'error': result_holder.get('error', 'Failed')})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    print("Starting Fly Connectome Noir Web App on http://127.0.0.1:5000 ...")
    app.run(host='0.0.0.0', port=5000, debug=True)