import os
import json
import queue
import shutil
import threading
import urllib.request
import urllib.parse
import subprocess
from flask import Flask, request, Response, render_template_string, jsonify
from flask_cors import CORS
from judge_engine import evaluate_song_with_fly, get_verdict_for_score_and_mode

app = Flask(__name__, static_folder='static')
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

VALID_MODES = {'courtship', 'territorial', 'sleep'}
DEFAULT_MODE = 'courtship'

LEADERBOARD_FILE = os.path.join(os.path.dirname(__file__), 'leaderboard.json')

def load_leaderboard():
    if not os.path.exists(LEADERBOARD_FILE):
        return []
    try:
        with open(LEADERBOARD_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Could not read leaderboard: {e}", flush=True)
        return []

def save_leaderboard(entries):
    try:
        with open(LEADERBOARD_FILE, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[ERROR] Could not save leaderboard: {e}", flush=True)

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html class="scroll-smooth" lang="en">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>Fly Connectome Music Rater — 1930s Rubber Hose Noir Edition</title>
<!-- Tailwind CSS -->
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<!-- Google Fonts -->
<link href="https://fonts.googleapis.com" rel="preconnect"/>
<link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/>
<link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700;900&amp;family=Playfair+Display:ital,wght@0,600;0,800;1,600&amp;family=Courier+Prime:ital,wght@0,400;0,700;1,400&amp;family=Special+Elite&amp;family=Bebas+Neue&amp;family=Bricolage+Grotesque:wght@400;600;700&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
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
            },
            primary: '#d9b9ff',
            surface: '#04122e'
          },
          fontFamily: {
            cinzel: ['"Cinzel Decorative"', 'serif'],
            playfair: ['"Playfair Display"', 'serif'],
            mono: ['"Courier Prime"', 'monospace'],
            vintage: ['"Special Elite"', 'cursive'],
            bebas: ['"Bebas Neue"', 'sans-serif'],
            sans: ['"Bricolage Grotesque"', 'sans-serif']
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

    /* 1930s Film Grain & Vignette */
    .film-vignette {
      box-shadow: inset 0 0 130px rgba(1, 13, 41, 0.95), inset 0 0 220px rgba(0, 0, 0, 0.9);
      pointer-events: none;
    }

    .spotlight-radial {
      background: radial-gradient(ellipse at 50% 12%, rgba(212, 175, 55, 0.18) 0%, rgba(244, 236, 225, 0.06) 40%, transparent 75%);
    }

    /* Subtle 1930s projector flicker */
    @keyframes reel-flicker {
      0% { opacity: 0.98; filter: contrast(105%) brightness(98%); }
      25% { opacity: 0.93; filter: contrast(110%) brightness(102%); }
      50% { opacity: 1; filter: contrast(100%) brightness(100%); }
      75% { opacity: 0.95; filter: contrast(108%) brightness(97%); }
      100% { opacity: 0.99; filter: contrast(103%) brightness(101%); }
    }
    .animate-projector {
      animation: reel-flicker 0.18s infinite linear alternate;
    }

    /* Rubber hose bobbing animation */
    @keyframes rubber-hose-idle {
      0%, 100% { transform: translateY(0px) rotate(0deg) scale(1); }
      25% { transform: translateY(-7px) rotate(-1.5deg) scale(1.015, 0.985); }
      50% { transform: translateY(0px) rotate(0deg) scale(0.985, 1.015); }
      75% { transform: translateY(-4px) rotate(1.2deg) scale(1.01, 0.99); }
    }
    .animate-rubber-bob {
      animation: rubber-hose-idle 2.8s infinite ease-in-out;
    }

    /* Pulsing button highlight */
    @keyframes gold-pulse {
      0%, 100% { box-shadow: 0 0 18px rgba(212, 175, 55, 0.4), inset 0 0 8px rgba(212, 175, 55, 0.3); }
      50% { box-shadow: 0 0 38px rgba(212, 175, 55, 0.85), inset 0 0 16px rgba(244, 236, 225, 0.6); }
    }
    .btn-gold-pulse {
      animation: gold-pulse 1.8s infinite ease-in-out;
    }

    /* Vintage Striped scanning progress bar */
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

    /* Flash highlight */
    @keyframes flash-pop {
      0% { filter: brightness(2) contrast(150%); }
      100% { filter: brightness(1) contrast(100%); }
    }
    .film-flash {
      animation: flash-pop 0.4s ease-out;
    }

    /* Custom scrollbar for search results */
    .custom-scroll::-webkit-scrollbar {
      width: 6px;
    }
    .custom-scroll::-webkit-scrollbar-track {
      background: #0a1020;
    }
    .custom-scroll::-webkit-scrollbar-thumb {
      background: #d4af37;
      border-radius: 3px;
    }

    /* ========================================================
       CHANGE 1 — GEOMETRIC BACKGROUND PATTERN (1930s PALETTE)
       ======================================================== */
    :root {
      --bg-pattern-base: #04122e;
      --bg-pattern-accent: rgba(212, 175, 55, 0.22);
    }

    .geometric-pattern-bg {
      background-color: var(--bg-pattern-base, #04122e);
      opacity: 0.8;
      background-image:
        radial-gradient(circle farthest-side at 0% 50%, var(--bg-pattern-base, #04122e) 23.5%, transparent 0),
        radial-gradient(circle farthest-side at 0% 50%, var(--bg-pattern-accent, rgba(212, 175, 55, 0.22)) 24%, transparent 0),
        linear-gradient(var(--bg-pattern-base, #04122e) 14%, transparent 0, transparent 85%, var(--bg-pattern-base, #04122e) 0),
        linear-gradient(150deg, var(--bg-pattern-base, #04122e) 24%, var(--bg-pattern-accent, rgba(212, 175, 55, 0.22)) 0 26%, transparent 0 74%, var(--bg-pattern-accent, rgba(212, 175, 55, 0.22)) 0 76%, var(--bg-pattern-base, #04122e) 0),
        linear-gradient(30deg, var(--bg-pattern-base, #04122e) 24%, var(--bg-pattern-accent, rgba(212, 175, 55, 0.22)) 0 26%, transparent 0 74%, var(--bg-pattern-accent, rgba(212, 175, 55, 0.22)) 0 76%, var(--bg-pattern-base, #04122e) 0),
        linear-gradient(90deg, var(--bg-pattern-accent, rgba(212, 175, 55, 0.22)) 1.6%, var(--bg-pattern-base, #04122e) 0 98.4%, var(--bg-pattern-accent, rgba(212, 175, 55, 0.22)) 0);
      background-position: 16px 23px, 14px 23px, 0 0, 0 0, 0 0, 0 0;
      background-size: 30px 45px;
    }

    /* ========================================================
       CHANGE 2 — 3D HOVER EFFECT FOR LEADERBOARD ENTRIES
       ======================================================== */
    .category-card {
      perspective: 1000px;
    }

    .song-item {
      transform-style: preserve-3d;
      transition: transform 0.4s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.4s ease, border-color 0.4s ease, background-color 0.4s ease;
      will-change: transform;
      position: relative;
    }

    .song-item:hover {
      transform: rotate3d(0.5, 1, 0, 15deg) translate3d(0px, -4px, 16px);
      box-shadow: 0 20px 30px -8px rgba(0, 0, 0, 0.85), 0 0 16px rgba(212, 175, 55, 0.35);
      border-color: #d4af37 !important;
      z-index: 20;
    }

    /* ========================================================
       CHANGE 3B — 3D HOVER EFFECT FOR STAT BOXES
       ======================================================== */
    .stat-boxes-grid {
      perspective: 1000px;
    }

    .stat-box-card {
      transform-style: preserve-3d;
      transition: transform 0.4s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.4s ease, border-color 0.4s ease, background-color 0.4s ease;
      will-change: transform;
      position: relative;
    }

    .stat-box-card:hover {
      transform: rotate3d(0.5, 1, 0, 12deg) translate3d(0px, -4px, 14px);
      box-shadow: 0 20px 30px -8px rgba(0, 0, 0, 0.85), 0 0 16px rgba(212, 175, 55, 0.3);
      border-color: rgba(212, 175, 55, 0.85) !important;
      z-index: 15;
    }

    @media (prefers-reduced-motion: reduce) {
      .song-item:hover,
      .stat-box-card:hover {
        transform: none !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.6) !important;
      }
    }

    /* ========================================================
       CHANGE 4 — UIVERSE GLOW & LIGHT SWEEP BUTTON EFFECT
       ======================================================== */
    button:not(.no-sweep) {
      --btn-glow-inner: rgba(212, 175, 55, 0.4);
      --btn-glow-outer: rgba(212, 175, 55, 0.12);
      --btn-hover-glow-inner: rgba(212, 175, 55, 0.65);
      --btn-hover-glow-outer: rgba(212, 175, 55, 0.28);
      --btn-sweep-color: rgba(244, 236, 225, 0.3);
      position: relative;
      overflow: hidden;
      isolation: isolate;
      cursor: pointer;
      transition: box-shadow 0.3s ease, border-color 0.3s ease, transform 0.2s ease, filter 0.3s ease, color 0.3s ease;
      box-shadow: inset 0 0 10px var(--btn-glow-inner), 0 0 9px 3px var(--btn-glow-outer);
    }

    button:not(.no-sweep):hover {
      box-shadow: inset 0 0 12px var(--btn-hover-glow-inner), 0 0 14px 4px var(--btn-hover-glow-outer);
    }

    button:not(.no-sweep):active {
      transform: scale(0.98);
    }

    button:not(.no-sweep)::before {
      content: "";
      position: absolute;
      left: -5em;
      width: 5em;
      height: 100%;
      top: 0;
      pointer-events: none;
      z-index: 1;
      transition: transform 0.5s ease-in-out;
      background: linear-gradient(
        to right,
        transparent 1%,
        var(--btn-sweep-color) 40%,
        var(--btn-sweep-color) 60%,
        transparent 100%
      );
    }

    button:not(.no-sweep):hover::before {
      transform: translateX(45em);
    }

    button:not(.no-sweep) > * {
      position: relative;
      z-index: 2;
    }

    /* BUTTON COLOR THEME VARIANTS */
    /* Gold / Primary / Glamour Noir buttons */
    #btn-see-results,
    #btn-view-ledger,
    #btn-reset-app,
    #preset-daft,
    #typebar-action-btn,
    .btn-return-and-rate,
    .btn-audit-online,
    .leaderboard-toggle-btn,
    #tab-btn-upload,
    .mode-btn,
    button[data-category="affinity"],
    button[data-category="courtship"],
    button[data-category="all"],
    button[data-category="recent"] {
      --btn-glow-inner: rgba(212, 175, 55, 0.45);
      --btn-glow-outer: rgba(212, 175, 55, 0.18);
      --btn-hover-glow-inner: rgba(212, 175, 55, 0.75);
      --btn-hover-glow-outer: rgba(245, 158, 11, 0.35);
      --btn-sweep-color: rgba(254, 243, 199, 0.45);
    }

    /* Red / Danger / Swatter buttons */
    #preset-discord,
    button[data-category="swatter"],
    button[class*="border-rose-700"],
    button[class*="border-rose-900"],
    .btn-swatter-trigger {
      --btn-glow-inner: rgba(239, 68, 68, 0.5);
      --btn-glow-outer: rgba(239, 68, 68, 0.2);
      --btn-hover-glow-inner: rgba(239, 68, 68, 0.8);
      --btn-hover-glow-outer: rgba(239, 68, 68, 0.4);
      --btn-sweep-color: rgba(254, 202, 202, 0.45);
    }

    /* Mechanosensory / Violet / Electric buttons */
    button[data-category="organ"],
    .mode-btn[data-mode="territorial"] {
      --btn-glow-inner: rgba(217, 185, 255, 0.4);
      --btn-glow-outer: rgba(217, 185, 255, 0.18);
      --btn-hover-glow-inner: rgba(217, 185, 255, 0.65);
      --btn-hover-glow-outer: rgba(217, 185, 255, 0.35);
      --btn-sweep-color: rgba(237, 222, 255, 0.45);
    }

    /* Nocturnal / Indigo / Sleep buttons */
    button[data-category="sleep"],
    .mode-btn[data-mode="sleep"] {
      --btn-glow-inner: rgba(129, 140, 248, 0.4);
      --btn-glow-outer: rgba(129, 140, 248, 0.18);
      --btn-hover-glow-inner: rgba(129, 140, 248, 0.65);
      --btn-hover-glow-outer: rgba(129, 140, 248, 0.35);
      --btn-sweep-color: rgba(224, 231, 255, 0.45);
    }

    /* Muted / Utility buttons */
    .search-tag,
    .close-leaderboard-btn,
    #tab-btn-online,
    #btn-skip-video,
    .btn-preview-audio {
      --btn-glow-inner: rgba(212, 175, 55, 0.25);
      --btn-glow-outer: rgba(212, 175, 55, 0.08);
      --btn-hover-glow-inner: rgba(212, 175, 55, 0.48);
      --btn-hover-glow-outer: rgba(212, 175, 55, 0.22);
      --btn-sweep-color: rgba(244, 236, 225, 0.28);
    }

    /* ========================================================
       CHANGE 3C — INVERTED 1930s NOIR ARCHIVE PALETTE
       ======================================================== */
    body.theme-inverted {
      background-color: #f3ede2 !important;
      color: #070b14 !important;
      --bg-pattern-base: #f3ede2;
      --bg-pattern-accent: rgba(140, 105, 20, 0.22);
      --btn-glow-inner: rgba(153, 115, 22, 0.35);
      --btn-glow-outer: rgba(153, 115, 22, 0.15);
      --btn-hover-glow-inner: rgba(153, 115, 22, 0.6);
      --btn-hover-glow-outer: rgba(153, 115, 22, 0.3);
      --btn-sweep-color: rgba(180, 135, 25, 0.35);
    }

    body.theme-inverted .film-vignette {
      box-shadow: inset 0 0 130px rgba(180, 160, 130, 0.55), inset 0 0 220px rgba(140, 120, 90, 0.45) !important;
    }

    body.theme-inverted .spotlight-radial {
      background: radial-gradient(ellipse at 50% 12%, rgba(153, 115, 22, 0.14) 0%, rgba(200, 190, 170, 0.1) 40%, transparent 75%) !important;
    }

    body.theme-inverted .bg-noir-950,
    body.theme-inverted .bg-noir-950\/95,
    body.theme-inverted .bg-noir-950\/90,
    body.theme-inverted .bg-noir-950\/85,
    body.theme-inverted .bg-noir-950\/80 {
      background-color: rgba(250, 247, 240, 0.95) !important;
    }

    body.theme-inverted .bg-noir-900,
    body.theme-inverted .bg-noir-900\/95,
    body.theme-inverted .bg-noir-900\/90,
    body.theme-inverted .bg-noir-900\/85,
    body.theme-inverted .bg-noir-900\/80 {
      background-color: rgba(242, 235, 222, 0.95) !important;
    }

    body.theme-inverted .bg-noir-850 {
      background-color: #e5dac7 !important;
    }

    body.theme-inverted .bg-noir-800 {
      background-color: #d9cdb7 !important;
    }

    body.theme-inverted .text-noir-creme {
      color: #070b14 !important;
    }

    body.theme-inverted .text-noir-sepia {
      color: #1a2745 !important;
    }

    body.theme-inverted .text-noir-aged,
    body.theme-inverted .text-noir-aged\/75,
    body.theme-inverted .text-noir-aged\/70,
    body.theme-inverted .text-noir-aged\/65 {
      color: #3b4861 !important;
    }

    body.theme-inverted .text-noir-gold {
      color: #8c6d17 !important;
    }

    body.theme-inverted .border-noir-gold,
    body.theme-inverted .border-noir-gold\/90,
    body.theme-inverted .border-noir-gold\/80,
    body.theme-inverted .border-noir-gold\/70,
    body.theme-inverted .border-noir-gold\/60,
    body.theme-inverted .border-noir-gold\/50,
    body.theme-inverted .border-noir-gold\/40 {
      border-color: #a8801a !important;
    }

    body.theme-inverted .border-noir-700,
    body.theme-inverted .border-noir-700\/80,
    body.theme-inverted .border-noir-700\/70,
    body.theme-inverted .border-noir-700\/60,
    body.theme-inverted .border-noir-800,
    body.theme-inverted .border-noir-850 {
      border-color: #cbbea9 !important;
    }

    body.theme-inverted #unified-typebar {
      background-color: rgba(250, 247, 240, 0.95) !important;
      border-color: #b5923b !important;
      box-shadow: 0 12px 35px rgba(160, 140, 110, 0.35) !important;
    }

    body.theme-inverted #online-search-input {
      color: #070b14 !important;
    }

    body.theme-inverted #online-search-input::placeholder {
      color: #55627e !important;
    }

    body.theme-inverted #chat-bar-placeholder {
      color: #3f4c66 !important;
    }

    body.theme-inverted footer {
      background-color: rgba(240, 233, 220, 0.9) !important;
      border-top-color: #cbbea9 !important;
    }

    body.theme-inverted #metrics-dashboard {
      background-color: rgba(246, 240, 230, 0.98) !important;
      border-top-color: #a8801a !important;
      box-shadow: 0 -25px 60px rgba(140, 120, 90, 0.35) !important;
    }
</style>
</head>
<body class="relative min-h-screen flex flex-col justify-between selection:bg-noir-gold selection:text-noir-950 font-playfair">
<!-- Ambient Overlays -->
<div class="fixed inset-0 film-vignette z-40 pointer-events-none"></div>
<div class="fixed inset-0 spotlight-radial z-0 pointer-events-none"></div>
<div class="fixed inset-0 z-0 pointer-events-none geometric-pattern-bg"></div>

<!-- FLOATING TOAST -->
<div class="fixed top-5 left-1/2 -translate-x-1/2 z-50 pointer-events-none opacity-0 transition-all duration-500 transform -translate-y-4" id="reset-toast">
  <div class="flex items-center gap-3 px-6 py-2.5 rounded-full bg-noir-900/95 border-2 border-noir-gold/80 shadow-[0_12px_35px_rgba(0,0,0,0.95)] backdrop-blur-md">
    <span class="inline-block w-2.5 h-2.5 rounded-full bg-noir-gold animate-ping"></span>
    <span class="font-mono text-xs tracking-wider text-noir-creme uppercase font-bold" id="toast-text">SYNAPTIC RECEPTORS ZEROED • READY FOR AUDIT</span>
    <span class="text-noir-gold text-sm font-cinzel">✓</span>
  </div>
</div>

<!-- HEADER -->
<header class="relative z-30 pt-6 pb-2 text-center px-4 max-w-5xl mx-auto w-full" id="stage-top">
  <!-- Top navigation / quick switch bar -->
  <div class="flex flex-wrap items-center justify-center gap-3 mb-2.5">
    <div class="inline-flex items-center gap-2.5 px-3.5 py-1 rounded-full border border-noir-700 bg-noir-900/85 shadow-md">
      <span class="w-2 h-2 rounded-full bg-noir-gold animate-ping"></span>
      <span class="font-mono text-[11px] tracking-[0.22em] text-noir-aged uppercase">Drosophila Biosonic Sound Laboratories • Circa 1934</span>
      <span class="text-noir-gold text-xs">★ ★ ★</span>
    </div>
    <!-- Quick toggle for Hall of Acclaim -->
    <button aria-controls="leaderboard-section" aria-expanded="false" class="leaderboard-toggle-btn inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full border border-noir-gold/70 bg-noir-950/90 text-noir-gold hover:text-noir-creme hover:border-noir-gold text-xs font-mono tracking-wider transition-all shadow hover:bg-noir-900 cursor-pointer" type="button">
      <span class="btn-toggle-text">✦ VIEW HALL OF ACCLAIM</span>
      <span class="material-symbols-outlined text-sm btn-toggle-icon">keyboard_arrow_down</span>
    </button>
  </div>

  <!-- Title -->
  <h1 class="font-cinzel text-3xl sm:text-4xl md:text-5xl font-black tracking-wide text-noir-creme drop-shadow-[0_4px_16px_rgba(0,0,0,0.95)] uppercase leading-tight">
    WELCOME TO FLY CONNECTOME <br class="hidden sm:inline"/>
    <span class="text-transparent bg-clip-text bg-gradient-to-r from-noir-gold via-amber-200 to-noir-gold drop-shadow-[0_2px_12px_rgba(212,175,55,0.4)]">
      MUSIC RATER
    </span>
  </h1>

  <!-- Subtitle -->
  <p class="font-vintage text-xs sm:text-sm tracking-widest text-noir-aged mt-1.5 max-w-3xl mx-auto uppercase">
    GET READY FOR THE MUSIC CONNOISSEUR FLY TO JUDGE YOUR TASTE IN MUSIC
  </p>

  <!-- Ornamental divider line -->
  <div class="flex items-center justify-center gap-4 mt-2.5 opacity-75">
    <div class="h-[1px] w-24 bg-gradient-to-r from-transparent to-noir-gold"></div>
    <span class="text-noir-gold text-xs font-cinzel tracking-widest">✦ // 139,255 SYNAPSES // ✦</span>
    <div class="h-[1px] w-24 bg-gradient-to-l from-transparent to-noir-gold"></div>
  </div>
</header>

<!-- MAIN INTERACTIVE STAGE -->
<main class="relative z-20 flex-1 flex flex-col items-center justify-center px-4 w-full max-w-4xl mx-auto py-1">

  <!-- HERO VIEWFINDER & CHARACTER DISPLAY CONTAINER -->
  <div class="relative w-full max-w-xl transition-all duration-700 ease-out transform" id="hero-frame-container">
    <div class="relative p-2.5 sm:p-3 rounded-2xl bg-gradient-to-b from-noir-850 via-noir-900 to-noir-950 border-4 border-noir-700/80 shadow-[0_20px_50px_rgba(0,0,0,0.95)]">
      
      <!-- Film Sprockets Bar -->
      <div class="flex justify-between items-center px-2 pb-1.5 opacity-60 border-b border-noir-700/60 mb-2 font-mono text-[10px] text-noir-gold tracking-widest uppercase">
        <div class="flex gap-2">
          <span class="w-3 h-2 rounded-[2px] bg-noir-700 inline-block"></span>
          <span class="w-3 h-2 rounded-[2px] bg-noir-700 inline-block"></span>
          <span class="w-3 h-2 rounded-[2px] bg-noir-700 inline-block"></span>
          <span class="w-3 h-2 rounded-[2px] bg-noir-700 inline-block"></span>
        </div>
        <span id="film-reel-title">REEL #34-DROSOPHILA-SYNC</span>
        <div class="flex gap-2">
          <span class="w-3 h-2 rounded-[2px] bg-noir-700 inline-block"></span>
          <span class="w-3 h-2 rounded-[2px] bg-noir-700 inline-block"></span>
          <span class="w-3 h-2 rounded-[2px] bg-noir-700 inline-block"></span>
          <span class="w-3 h-2 rounded-[2px] bg-noir-700 inline-block"></span>
        </div>
      </div>

      <!-- IMAGE/VIDEO SCREEN STAGE -->
      <div class="relative overflow-hidden rounded-xl aspect-[4/3] sm:aspect-[16/11] bg-noir-950 flex items-center justify-center border-2 border-noir-700/80 shadow-inner group" id="media-viewport">
        
        <!-- STATE 1: Default Idle Image (Lord Drosophila under spotlight) -->
        <div class="absolute inset-0 transition-opacity duration-500 opacity-100 flex items-center justify-center" id="view-hero-image">
          <img alt="Lord Drosophila, Esq." class="w-full h-full object-cover filter contrast-110 sepia-[0.2] brightness-95 animate-rubber-bob transition-all duration-700" id="hero-fly-img" src="/static/fly_hero.png" onerror="this.onerror=null; this.src='https://lh3.googleusercontent.com/aida/AEtjO1XAcPw-4ooztR49ZKS2FT6x8-rJNxeF_G-RJ3F3OK86-pcdF5OTlNWDAfk60LO1SLCGEb1bsFHpdUizPIhx0VSCjOvHdUTRFwZbzjAlggv9TMzNiAOYineTpHkGCJnydTDYncad8qteYnA9OErgX3crlNCBRQ9bGoGibcKNbGOpcEXBAWmyQj86XziLhH0avWAnHrksy9m266Jnx5u4GlfM6gU9MM6WVfnLUQGehX-gMbbqE2hfm-GAnWY';"/>
          <div class="absolute inset-0 bg-gradient-to-t from-noir-950/80 via-transparent to-transparent pointer-events-none"></div>
          
          <!-- Bottom Subject Badge -->
          <div class="absolute bottom-2.5 left-3.5 right-3.5 flex flex-col sm:flex-row justify-between items-start sm:items-end gap-1 pointer-events-none">
            <span class="font-cinzel text-xs text-noir-creme bg-noir-900/90 px-2.5 py-0.5 rounded border border-noir-700 backdrop-blur-sm shadow" id="hero-subject-tag">
              SUBJECT: LORD DROSOPHILA, ESQ.
            </span>
            <span class="font-mono text-[10px] text-noir-gold tracking-widest bg-noir-950/90 px-2.5 py-0.5 rounded border border-noir-700/80 shadow" id="hero-audit-status">
              AUDIT STATE: IDLE / WAITING FOR TUNE
            </span>
          </div>
        </div>

        <!-- STATE 4: MP4 & Animated Reel Reaction Viewport -->
        <div class="absolute inset-0 opacity-0 pointer-events-none transition-all duration-500 flex flex-col items-center justify-center bg-noir-950 z-20" id="view-video-player">
          <video class="w-full h-full object-cover hidden" id="flyVideo" playsinline></video>
          <!-- Animated Silent Film Fallback Image -->
          <img alt="Silent Movie Reaction" class="w-full h-full object-cover animate-projector sepia-[0.35] contrast-125 brightness-95 hidden" id="reaction-film-img" src="https://lh3.googleusercontent.com/aida/AEtjO1VmzVI8W5pIp7k_a9fZvL99_uu8llsB7zOf7hsF5t4eqGLoXpil_pqkcfLaraUkHDirQ25PwzYDdzElffAONEUe_6vEnE2b3TZVqKzPs-wmEkbYfCumd9RaF5jR7V5MQ2jm0UjtAcEzCIsDLzP4Y5ZeIs8VShdupqp7hutJsI8RdZwBkkeoGcb_jWGlaUa3Pue-YhuHf6f1vrMFvL0QWNLYcHBQpQ_bnjBCKQt-F6X6eEOILWHRmQezEjQ"/>
          
          <!-- Silent movie top ribbon -->
          <div class="absolute top-2.5 left-3.5 right-3.5 flex items-center justify-between z-10 pointer-events-none">
            <div class="inline-flex items-center gap-2 bg-noir-950/90 px-3 py-1 rounded-full border border-noir-gold/80 text-xs font-mono text-noir-gold shadow-lg">
              <span class="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
              <span id="film-live-tag">OPTICAL REEL ROLLING</span>
            </div>
            <div class="flex items-center gap-2">
              <button id="btn-skip-video" class="pointer-events-auto px-2.5 py-0.5 rounded-full bg-noir-900/90 border border-noir-gold/80 text-noir-gold hover:text-noir-creme text-[10px] font-mono tracking-wider transition-all shadow hover:bg-noir-850 cursor-pointer" type="button">
                <span>SKIP TO REPORT ➔</span>
              </button>
              <div class="font-mono text-xs text-noir-creme bg-noir-900/90 px-2.5 py-0.5 rounded border border-noir-700" id="film-timer">
                00:00 / 00:10
              </div>
            </div>
          </div>
          <!-- Optical soundtrack scrubber simulation -->
          <div class="absolute bottom-2 left-3 right-3 z-10 flex flex-col gap-1 bg-noir-950/90 p-2 rounded-lg border border-noir-700 backdrop-blur-sm">
            <div class="w-full bg-noir-800 h-1.5 rounded-full overflow-hidden border border-noir-700">
              <div class="bg-gradient-to-r from-noir-gold via-amber-200 to-noir-gold h-full w-0 transition-all duration-100" id="video-progress-bar"></div>
            </div>
            <div class="flex justify-between items-center text-[10px] font-mono text-noir-aged">
              <span id="video-status-text">✦ JOHNSTON'S ORGAN TRANSDUCTION IN PROGRESS...</span>
              <span class="text-noir-gold">35MM SOUNDTRACK</span>
            </div>
          </div>
        </div>

        <!-- STATE 3: INTERACTIVE REVEAL POPUP MODAL OVERLAY -->
        <div class="absolute inset-0 z-30 flex items-center justify-center bg-noir-950/85 backdrop-blur-md opacity-0 pointer-events-none transition-all duration-500 transform scale-90" id="reveal-popup" style="display: none;">
          <div class="text-center p-6 border-2 border-noir-gold/90 rounded-2xl bg-noir-900 shadow-[0_20px_50px_rgba(0,0,0,0.9)] max-w-sm w-full mx-4 relative overflow-hidden">
            <div class="absolute -top-12 -right-12 w-28 h-28 bg-noir-gold/20 rounded-full blur-2xl"></div>
            <div class="text-[11px] font-mono tracking-widest text-noir-aged mb-1">DROSOPHILA BRAIN SCAN COMPLETE</div>
            <div class="text-2xl font-cinzel text-noir-gold font-bold mb-2">★ NEURAL VERDICT READY ★</div>
            <p class="font-vintage text-xs text-noir-sepia mb-5 leading-relaxed" id="reveal-modal-desc">
              The male Drosophila connectome has fully resolved your harmonic acoustic vibrations. Step inside the screening booth!
            </p>
            <button class="w-full py-3.5 px-6 rounded-xl font-cinzel text-sm font-black tracking-widest uppercase bg-gradient-to-r from-noir-gold via-amber-200 to-noir-gold text-noir-950 shadow-xl hover:brightness-110 active:scale-95 transition-all btn-gold-pulse cursor-pointer" id="btn-see-results">
              <span>SEE RESULTS ➔</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  </div>

  <!-- FLY BEHAVIORAL MODE SELECTOR -->
  <div class="w-full max-w-xl mt-3 relative z-30">
    <div class="flex flex-col items-center">
      <!-- Mode buttons row -->
      <div class="flex items-center justify-center gap-2 p-1.5 rounded-full bg-noir-900/90 border border-noir-700 shadow-lg w-full" id="mode-toggle-group">
        <button class="mode-btn flex-1 px-3 py-1.5 rounded-full font-mono text-[11px] tracking-wider uppercase transition-all bg-noir-gold text-noir-950 font-bold" data-mode="courtship" type="button">
          <span>♫ Courtship</span>
        </button>
        <button class="mode-btn flex-1 px-3 py-1.5 rounded-full font-mono text-[11px] tracking-wider uppercase transition-all text-noir-aged hover:text-noir-creme" data-mode="territorial" type="button">
          <span>⚡ Territorial</span>
        </button>
        <button class="mode-btn flex-1 px-3 py-1.5 rounded-full font-mono text-[11px] tracking-wider uppercase transition-all text-noir-aged hover:text-noir-creme" data-mode="sleep" type="button">
          <span>☾ Quiet / Sleep</span>
        </button>
      </div>

      <!-- Mode lock notice (visible when scanning) -->
      <div class="hidden mt-1 px-3 py-0.5 rounded-full bg-amber-950/90 border border-noir-gold text-[10px] font-mono text-noir-gold uppercase tracking-wider animate-pulse flex items-center gap-1.5" id="mode-lock-indicator">
        <span class="material-symbols-outlined text-[13px]">lock</span>
        <span>SCANNING IN PROGRESS — BEHAVIORAL MODE LOCKED</span>
      </div>

      <p class="text-center font-mono text-[10px] text-noir-aged/75 mt-1 tracking-wider uppercase" id="mode-hint-text">
        Courtship: prefers 120–160 BPM pulse tracks &amp; smooth 180 Hz sine hums
      </p>
    </div>
  </div>

  <!-- UNIFIED CONTROL CONSOLE (UPLOAD AND ONLINE SEARCH SHARE THE EXACT SAME TYPEBAR) -->
  <div class="w-full max-w-xl mt-3 relative z-30" id="unified-console-pane">
    
    <!-- SOURCE SELECTION TABS: UPLOAD VS ONLINE ARCHIVE -->
    <div class="flex items-center justify-center gap-2 mb-2" id="source-tabs">
      <button class="px-4 py-1.5 rounded-full font-mono text-xs uppercase tracking-wider transition-all border border-noir-gold bg-noir-900 text-noir-gold font-bold shadow cursor-pointer" id="tab-btn-upload" type="button">
        <span>📁 Upload Audio File</span>
      </button>
      <button class="px-4 py-1.5 rounded-full font-mono text-xs uppercase tracking-wider transition-all border border-noir-700 bg-noir-950 text-noir-aged hover:text-noir-gold hover:border-noir-gold/60 cursor-pointer" id="tab-btn-online" type="button">
        <span>🌐 Search Archives Online</span>
      </button>
    </div>

    <!-- THE UNIFIED PILL TYPEBAR (SHARABLE FOR BOTH FILE DROP/PICK AND ONLINE TEXT SEARCH) -->
    <div class="group relative flex items-center justify-between w-full p-2 pl-5 pr-2 rounded-full bg-noir-900/95 border-2 border-noir-700 hover:border-noir-gold focus-within:border-noir-gold shadow-[0_12px_40px_rgba(0,0,0,0.85)] backdrop-blur-md transition-all cursor-pointer" id="unified-typebar">
      
      <!-- Interactive Central Slot -->
      <div class="flex-1 overflow-hidden relative flex items-center min-w-0" id="typebar-interactive-slot">
        <!-- MODE 1: Upload File Label & Invisible Input -->
        <div class="w-full flex items-center select-none" id="typebar-upload-slot">
          <span class="font-playfair italic text-xs sm:text-sm text-noir-aged truncate group-hover:text-noir-creme transition-colors" id="chat-bar-placeholder">
            Drag &amp; drop audio file or click to upload (.mp3, .wav, .m4a)...
          </span>
          <input accept="audio/*" class="sr-only" id="audio-file-input" type="file"/>
        </div>

        <!-- MODE 2: Online Search Text Input (Replaces placeholder in same typebar!) -->
        <input autocomplete="off" class="hidden w-full bg-transparent border-none text-noir-creme font-playfair italic text-xs sm:text-sm placeholder:text-noir-aged/70 focus:outline-none" id="online-search-input" placeholder="Enter artist or song name to search online archives (e.g. Daft Punk, Queen, Miles Davis)..." type="text"/>
      </div>

      <!-- Right Action Button: Upload Arrow or Search Button -->
      <button class="shrink-0 ml-2 w-10 h-10 rounded-full bg-gradient-to-br from-noir-gold via-amber-400 to-amber-600 text-noir-950 flex items-center justify-center font-bold shadow-lg hover:scale-105 active:scale-95 transition-all cursor-pointer" id="typebar-action-btn" title="Upload Audio File" type="button">
        <span class="material-symbols-outlined font-black text-xl relative z-10" id="typebar-action-icon">arrow_upward</span>
      </button>
    </div>

    <!-- SUB-ROW 1: QUICK DEMOS (Visible in Upload Mode) -->
    <div class="mt-2.5 flex flex-wrap items-center justify-center gap-2" id="upload-quick-demos">
      <button class="flex items-center gap-1.5 px-3 py-1 rounded-full bg-noir-900/90 border border-noir-gold/80 hover:border-noir-gold text-noir-gold hover:text-noir-creme font-mono text-[11px] tracking-wider transition-all shadow active:scale-95 cursor-pointer" id="preset-daft" type="button">
        <span>✦ Quick Demo: "Around The World" (Daft Punk)</span>
      </button>
      <button class="flex items-center gap-1.5 px-3 py-1 rounded-full bg-noir-900/90 border border-rose-700/80 hover:border-rose-500 text-rose-300 hover:text-rose-100 font-mono text-[11px] tracking-wider transition-all shadow active:scale-95 cursor-pointer" id="preset-discord" type="button">
        <span>⚠ Quick Demo: "Discordant Screech / Swatter Noise"</span>
      </button>
    </div>

    <!-- SUB-ROW 2: SUGGESTED CHIPS (Visible in Online Search Mode) -->
    <div class="hidden mt-2.5 flex flex-wrap items-center justify-center gap-1.5 text-[10px] font-mono text-noir-aged" id="online-suggestion-chips">
      <span class="text-noir-gold font-bold">Suggested:</span>
      <button class="search-tag px-2.5 py-0.5 rounded-full bg-noir-950 border border-noir-700 hover:border-noir-gold text-noir-sepia hover:text-noir-gold transition-colors cursor-pointer" data-query="Cab Calloway Minnie the Moocher">Cab Calloway</button>
      <button class="search-tag px-2.5 py-0.5 rounded-full bg-noir-950 border border-noir-700 hover:border-noir-gold text-noir-sepia hover:text-noir-gold transition-colors cursor-pointer" data-query="Duke Ellington Caravan">Duke Ellington</button>
      <button class="search-tag px-2.5 py-0.5 rounded-full bg-noir-950 border border-noir-700 hover:border-noir-gold text-noir-sepia hover:text-noir-gold transition-colors cursor-pointer" data-query="Miles Davis So What">Miles Davis</button>
      <button class="search-tag px-2.5 py-0.5 rounded-full bg-noir-950 border border-noir-700 hover:border-noir-gold text-noir-sepia hover:text-noir-gold transition-colors cursor-pointer" data-query="Queen Bohemian Rhapsody">Queen</button>
      <button class="search-tag px-2.5 py-0.5 rounded-full bg-noir-950 border border-noir-700 hover:border-noir-gold text-noir-sepia hover:text-noir-gold transition-colors cursor-pointer" data-query="Stevie Wonder Superstition">Stevie Wonder</button>
      <button class="search-tag px-2.5 py-0.5 rounded-full bg-noir-950 border border-noir-700 hover:border-noir-gold text-noir-sepia hover:text-noir-gold transition-colors cursor-pointer" data-query="Erik Satie Gymnopedie">Erik Satie</button>
    </div>

    <!-- SUB-ROW 3: ONLINE SEARCH RESULTS EXPANDED CONTAINER -->
    <div class="hidden mt-3 max-h-56 overflow-y-auto custom-scroll space-y-2 p-2.5 rounded-2xl bg-noir-950/95 border-2 border-noir-gold/60 shadow-2xl backdrop-blur-md" id="online-results-container">
      <div class="text-center py-4 font-mono text-xs text-noir-aged italic" id="online-empty-hint">
        ✦ Query any track or artist in the worldwide archive. High-fidelity 30-second audio previews will be retrieved for connectome audition.
      </div>
    </div>
  </div>

    <!-- PROMINENT DIRECT LEADERBOARD TOGGLE -->
    <div class="mt-3 flex flex-col items-center justify-center">
      <button aria-controls="leaderboard-section" aria-expanded="false" class="leaderboard-toggle-btn group inline-flex items-center gap-2.5 px-6 py-2 rounded-full border-2 border-noir-gold/80 bg-gradient-to-r from-noir-900 via-noir-850 to-noir-900 text-noir-gold hover:text-noir-creme hover:border-noir-gold font-cinzel text-xs tracking-widest font-bold uppercase shadow-[0_4px_20px_rgba(0,0,0,0.8)] hover:shadow-[0_0_20px_rgba(212,175,55,0.4)] transition-all active:scale-95 cursor-pointer" type="button">
        <span class="text-amber-400 group-hover:scale-110 transition-transform relative z-10">★</span>
        <span class="btn-toggle-text relative z-10">VIEW HALL OF ACCLAIM [SHOW LEADERBOARD]</span>
        <span class="material-symbols-outlined text-base btn-toggle-icon group-hover:translate-y-0.5 transition-transform relative z-10">keyboard_arrow_down</span>
      </button>
    </div>

    <!-- RETRO SCANNING CONSOLE CARD -->
    <div class="hidden opacity-0 transform translate-y-3 transition-all duration-500 p-5 rounded-2xl bg-noir-900/95 border-2 border-noir-gold/70 shadow-2xl relative overflow-hidden backdrop-blur-md mt-2" id="loading-card">
      <div class="absolute top-1.5 left-2.5 text-noir-gold/40 font-cinzel text-xs">╔</div>
      <div class="absolute top-1.5 right-2.5 text-noir-gold/40 font-cinzel text-xs">╗</div>
      <div class="absolute bottom-1.5 left-2.5 text-noir-gold/40 font-cinzel text-xs">╚</div>
      <div class="absolute bottom-1.5 right-2.5 text-noir-gold/40 font-cinzel text-xs">╝</div>
      
      <div class="flex items-center justify-between mb-2">
        <div class="flex items-center gap-2">
          <span class="inline-block w-2.5 h-2.5 rounded-full bg-noir-gold animate-ping"></span>
          <span class="font-cinzel text-xs sm:text-sm font-bold tracking-wider text-noir-creme">CONNECTOME SCANNER ACTIVE</span>
        </div>
        <span class="font-mono text-sm text-noir-gold font-bold" id="loading-percentage">0%</span>
      </div>
      
      <!-- Dynamic Step Text -->
      <div class="font-mono text-xs text-noir-sepia italic mb-2.5 h-5 truncate" id="loading-step-text">
        1. Converting Audio Stream...
      </div>
      
      <!-- Animated Sepia Striped Progress Bar -->
      <div class="w-full bg-noir-950 h-3.5 rounded-full overflow-hidden border border-noir-700 p-[2px]">
        <div class="h-full striped-bar rounded-full w-0 transition-all duration-150 ease-out shadow-[0_0_12px_rgba(212,175,55,0.8)]" id="progress-bar-fill"></div>
      </div>
      
      <!-- Waveform telemetry indicators -->
      <div class="mt-2.5 flex justify-between items-center text-[10px] font-mono text-noir-aged">
        <div class="flex items-center gap-1.5 text-noir-gold">
          <span class="w-1.5 h-1.5 rounded-full bg-noir-gold"></span>
          <span id="scan-mode-label">JO-AB CIRCUIT TRACKING [COURTSHIP]</span>
        </div>
        <span>SYNAPTIC RESOLUTION: 48.0 kHz</span>
      </div>
    </div>

  </div>
</main>

<!-- SECTION: CONNECTOME HALL OF ACCLAIM / LEADERBOARD (COLLAPSIBLE / PERSISTENT) -->
<section aria-hidden="true" class="hidden opacity-0 relative z-20 py-10 px-4 max-w-5xl mx-auto w-full border-t border-noir-800/80 mt-8 transition-all duration-500 ease-in-out" id="leaderboard-section">
  
  <!-- Top Section Header & Close / Rate Another Buttons -->
  <div class="flex items-center justify-between max-w-4xl mx-auto mb-3 px-2">
    <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-noir-gold/40 bg-noir-900/90 text-noir-gold text-[10px] font-mono tracking-widest uppercase shadow">
      <span>✦ CONNECTOME AUDIT LEDGER OPEN</span>
    </div>
    <div class="flex items-center gap-2">
      <button class="btn-return-and-rate inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full border border-noir-gold bg-noir-900 text-noir-gold hover:bg-noir-gold hover:text-noir-950 text-xs font-mono tracking-wider transition-all shadow cursor-pointer font-bold" type="button">
        <span>✦ RATE ANOTHER SONG</span>
        <span class="material-symbols-outlined text-sm">arrow_upward</span>
      </button>
      <button class="close-leaderboard-btn inline-flex items-center gap-1.5 px-3 py-1 rounded-full border border-noir-700 bg-noir-900/90 hover:border-noir-gold text-noir-aged hover:text-noir-gold text-xs font-mono tracking-wider transition-all cursor-pointer" type="button">
        <span class="material-symbols-outlined text-sm">close</span>
        <span>COLLAPSE</span>
      </button>
    </div>
  </div>

  <!-- Section Title & Header Plaque -->
  <div class="text-center mb-6">
    <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-noir-gold/50 bg-noir-900/90 text-noir-gold text-[11px] font-mono tracking-widest uppercase mb-2 shadow">
      <span>✦ OFFICIAL ARCHIVES // REGISTER OF ACOUSTIC JUDGMENT ✦</span>
    </div>
    <h2 class="font-cinzel text-2xl sm:text-3xl md:text-4xl font-black text-noir-creme tracking-wide">
      CONNECTOME HALL OF ACCLAIM
    </h2>
    <p class="font-vintage text-xs sm:text-sm text-noir-aged mt-1 tracking-wider uppercase max-w-2xl mx-auto">
      Auditory ledgers evaluated across 139,255 synapses of the drosophila audio cortege
    </p>

    <!-- Art-deco ornament divider -->
    <div class="flex items-center justify-center gap-3 my-3 opacity-70">
      <div class="h-[1px] w-20 bg-gradient-to-r from-transparent to-noir-gold"></div>
      <span class="font-cinzel text-noir-gold text-xs">✤ ARCHIVED &amp; LIVE AUDITS ✤</span>
      <div class="h-[1px] w-20 bg-gradient-to-l from-transparent to-noir-gold"></div>
    </div>

    <!-- Category Tabs Filter -->
    <div class="flex flex-wrap items-center justify-center gap-2 max-w-4xl mx-auto mt-2" id="leaderboard-tabs" role="tablist">
      <button class="px-3 py-1.5 rounded-xl text-xs font-mono uppercase tracking-wider transition-all border border-noir-gold bg-noir-gold text-noir-950 font-bold shadow active-tab-btn" data-category="all" type="button">
        <span>All Categories</span>
      </button>
      <button class="px-3 py-1.5 rounded-xl text-xs font-mono uppercase tracking-wider transition-all border border-noir-700 bg-noir-900/80 text-noir-aged hover:text-noir-gold hover:border-noir-gold/60" data-category="recent" type="button">
        <span>⚡ Live / Recent Audits</span>
      </button>
      <button class="px-3 py-1.5 rounded-xl text-xs font-mono uppercase tracking-wider transition-all border border-noir-700 bg-noir-900/80 text-noir-aged hover:text-noir-gold hover:border-noir-gold/60" data-category="affinity" type="button">
        <span>★ All-Time Affinity</span>
      </button>
      <button class="px-3 py-1.5 rounded-xl text-xs font-mono uppercase tracking-wider transition-all border border-noir-700 bg-noir-900/80 text-noir-aged hover:text-noir-gold hover:border-noir-gold/60" data-category="courtship" type="button">
        <span>♫ Courtship Harmonics</span>
      </button>
      <button class="px-3 py-1.5 rounded-xl text-xs font-mono uppercase tracking-wider transition-all border border-noir-700 bg-noir-900/80 text-noir-aged hover:text-noir-gold hover:border-noir-gold/60" data-category="organ" type="button">
        <span>⚡ Johnston's Vibration</span>
      </button>
      <button class="px-3 py-1.5 rounded-xl text-xs font-mono uppercase tracking-wider transition-all border border-noir-700 bg-noir-900/80 text-noir-aged hover:text-noir-gold hover:border-noir-gold/60" data-category="sleep" type="button">
        <span>☾ Nocturnal Slumber</span>
      </button>
      <button class="px-3 py-1.5 rounded-xl text-xs font-mono uppercase tracking-wider transition-all border border-rose-900/60 bg-noir-900/80 text-rose-300 hover:text-rose-100 hover:border-rose-500" data-category="swatter" type="button">
        <span>⚠ Dreadful Swatter Triggers</span>
      </button>
    </div>
  </div>

  <!-- Dynamic Leaderboard Container (Populated via JS / Backend) -->
  <div class="grid grid-cols-1 md:grid-cols-2 gap-5" id="leaderboard-cards-container">
    <!-- Category Cards rendered dynamically -->
  </div>

  <!-- Bottom ledger footnote & Collapse / Scroll-up link -->
  <div class="mt-8 pt-4 border-t border-noir-850 flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left">
    <div class="font-mono text-[11px] text-noir-aged">
      <span class="text-noir-gold">✦ ARCHIVE CITATION:</span> Drosophila Acoustic Courtship Atlas, Vol. XIV, 1934. All entries certified by Lord Drosophila, Esq.
    </div>
    <div class="flex items-center gap-2.5">
      <button class="btn-return-and-rate inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full border-2 border-noir-gold bg-noir-900 text-noir-gold hover:bg-noir-gold hover:text-noir-950 font-cinzel text-xs tracking-wider font-bold transition-all shadow cursor-pointer" type="button">
        <span>✦ RATE ANOTHER SONG ✦</span>
      </button>
      <button class="close-leaderboard-btn inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full border border-noir-gold/70 bg-noir-900/90 text-noir-gold hover:text-noir-creme hover:bg-noir-850 font-mono text-xs tracking-wider transition-all cursor-pointer" type="button">
        <span class="material-symbols-outlined text-sm">keyboard_arrow_up</span>
        <span>HIDE &amp; RETURN TO BOOTH</span>
      </button>
    </div>
  </div>
</section>

<!-- STATE 5: METRICS SLIDE-UP SCORECARD & RE-EVALUATION DASHBOARD -->
<div class="fixed inset-x-0 bottom-0 z-50 transform translate-y-full transition-transform duration-700 ease-out max-h-[92vh] overflow-y-auto px-4 pb-8 pt-4 bg-noir-950/98 border-t-2 border-noir-gold/90 shadow-[0_-25px_60px_rgba(0,0,0,0.98)] backdrop-blur-xl" id="metrics-dashboard">
  <!-- Slide Handle Bar -->
  <div class="flex flex-col items-center justify-center mb-3">
    <div class="w-16 h-1 rounded-full bg-noir-700 mb-1.5"></div>
    <div class="font-mono text-[10px] text-noir-gold tracking-widest uppercase">✦ CONNECTOME FINAL RATING TICKET ✦</div>
  </div>

  <div class="max-w-4xl mx-auto">
    <!-- HEADER VERDICT BANNER -->
    <div class="p-5 sm:p-6 rounded-2xl bg-gradient-to-r from-noir-900 via-noir-850 to-noir-900 border border-noir-gold/50 shadow-2xl flex flex-col md:flex-row items-center justify-between gap-5 mb-5">
      <div class="flex-1">
        <div class="flex flex-wrap items-center gap-2 mb-2">
          <span class="font-mono text-xs text-noir-aged border border-noir-700 bg-noir-950 px-2.5 py-1 rounded" id="metrics-track-title">
            TRACK: Specimen Track
          </span>
          <span class="font-mono text-xs font-bold text-noir-950 bg-noir-gold px-3 py-1 rounded-full shadow" id="metrics-rank-badge">
            RANK S+ // MAXIMUM BUZZ
          </span>
          <span class="font-mono text-[11px] text-noir-gold border border-noir-700/80 bg-noir-900 px-2.5 py-1 rounded uppercase" id="metrics-mode-badge">
            MODE: COURTSHIP
          </span>
        </div>
        <h2 class="font-cinzel text-xl sm:text-2xl md:text-3xl font-black text-noir-creme" id="metrics-verdict-title">
          THE FLY IS OFFICIALLY GROOVING!
        </h2>
        <p class="font-vintage text-xs sm:text-sm text-noir-sepia mt-2 italic max-w-xl leading-relaxed" id="metrics-verdict-comment">
          "Ah, sheer perfection! Antennal micro-hairs vibrating in complete harmonic resonance. Even in my finest evening tuxedo, I cannot resist vibrating my thoracic flight muscles!"
        </p>
      </div>

      <!-- AFFINITY SCORE BADGE -->
      <div class="shrink-0 text-center px-6 py-4 rounded-xl bg-noir-950 border-2 border-noir-gold shadow-lg min-w-[170px]">
        <div class="font-mono text-[10px] tracking-widest text-noir-aged uppercase">AFFINITY SCORE</div>
        <div class="font-cinzel text-4xl sm:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-b from-noir-gold to-amber-200" id="metrics-affinity-score">
          98.4
        </div>
        <div class="font-mono text-xs text-noir-gold font-bold">/ 100 MAXIMUM BUZZ</div>
      </div>
    </div>

    <!-- DETAILED METRICS GAUGES GRID -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 mb-6 stat-boxes-grid">
      <!-- Metric 1: Johnston's Organ -->
      <div class="p-3.5 rounded-xl bg-noir-900/90 border border-noir-700/80 hover:border-noir-gold/60 transition-all stat-box-card">
        <div class="text-[10px] font-mono text-noir-aged uppercase mb-1">JO-AB RESONANCE</div>
        <div class="font-cinzel text-xl font-bold text-noir-creme" id="metric-organ">99%</div>
        <p class="font-vintage text-[11px] text-noir-aged mt-1" id="metric-sub-organ">Harmonic Lock (120-250Hz)</p>
        <div class="w-full bg-noir-950 h-1.5 rounded-full mt-2 overflow-hidden border border-noir-800">
          <div class="bg-noir-gold h-full w-[99%]" id="bar-organ"></div>
        </div>
      </div>
      <!-- Metric 2: Courtship Pulse -->
      <div class="p-3.5 rounded-xl bg-noir-900/90 border border-noir-700/80 hover:border-noir-gold/60 transition-all stat-box-card">
        <div class="text-[10px] font-mono text-noir-aged uppercase mb-1">COURTSHIP PULSE</div>
        <div class="font-cinzel text-xl font-bold text-noir-creme" id="metric-courtship">97%</div>
        <p class="font-vintage text-[11px] text-noir-aged mt-1" id="metric-sub-courtship">Wing extension trigger</p>
        <div class="w-full bg-noir-950 h-1.5 rounded-full mt-2 overflow-hidden border border-noir-800">
          <div class="bg-noir-gold h-full w-[97%]" id="bar-courtship"></div>
        </div>
      </div>
      <!-- Metric 3: Flight Motor -->
      <div class="p-3.5 rounded-xl bg-noir-900/90 border border-noir-700/80 hover:border-noir-gold/60 transition-all stat-box-card">
        <div class="text-[10px] font-mono text-noir-aged uppercase mb-1">FLIGHT MOTOR STIM.</div>
        <div class="font-cinzel text-xl font-bold text-noir-creme" id="metric-flight">94%</div>
        <p class="font-vintage text-[11px] text-noir-aged mt-1" id="metric-sub-flight">Thoracic vibration burst</p>
        <div class="w-full bg-noir-950 h-1.5 rounded-full mt-2 overflow-hidden border border-noir-800">
          <div class="bg-amber-400 h-full w-[94%]" id="bar-flight"></div>
        </div>
      </div>
      <!-- Metric 4: Swatter Threat -->
      <div class="p-3.5 rounded-xl bg-noir-900/90 border border-noir-700/80 hover:border-noir-gold/60 transition-all stat-box-card">
        <div class="text-[10px] font-mono text-noir-aged uppercase mb-1">SWATTER ESCAPE</div>
        <div class="font-cinzel text-xl font-bold text-rose-400" id="metric-threat">02%</div>
        <p class="font-vintage text-[11px] text-noir-aged mt-1" id="metric-sub-threat">Dormant LC4 escape</p>
        <div class="w-full bg-noir-950 h-1.5 rounded-full mt-2 overflow-hidden border border-noir-800">
          <div class="bg-rose-500 h-full w-[2%]" id="bar-threat"></div>
        </div>
      </div>
      <!-- Metric 5: Dopamine / Reward -->
      <div class="p-3.5 rounded-xl bg-noir-900/90 border border-noir-700/80 hover:border-noir-gold/60 transition-all stat-box-card">
        <div class="text-[10px] font-mono text-noir-aged uppercase mb-1">DOPAMINE SURGE</div>
        <div class="font-cinzel text-xl font-bold text-emerald-400" id="metric-dopamine">+3.8x</div>
        <p class="font-vintage text-[11px] text-noir-aged mt-1" id="metric-sub-dopamine">Mushroom body surge</p>
        <div class="w-full bg-noir-950 h-1.5 rounded-full mt-2 overflow-hidden border border-noir-800">
          <div class="bg-emerald-400 h-full w-[96%]" id="bar-dopamine"></div>
        </div>
      </div>
    </div>

    <!-- RE-EVALUATION PROMINENT ACTION -->
    <div class="flex flex-wrap items-center justify-center gap-3 pt-2">
      <button class="px-6 sm:px-8 py-3.5 rounded-xl font-cinzel text-xs sm:text-sm font-black tracking-widest uppercase bg-gradient-to-r from-noir-850 via-noir-800 to-noir-850 text-noir-gold border-2 border-noir-gold hover:bg-noir-gold hover:text-noir-950 transition-all duration-300 shadow-[0_0_25px_rgba(212,175,55,0.3)] hover:shadow-[0_0_35px_rgba(212,175,55,0.7)] cursor-pointer" id="btn-reset-app" type="button">
        <span>✦ CHOOSE NEW SONG FOR RATING ✦</span>
      </button>
      <button class="px-6 sm:px-8 py-3.5 rounded-xl font-cinzel text-xs sm:text-sm font-black tracking-widest uppercase bg-gradient-to-r from-noir-900 via-noir-850 to-noir-900 text-amber-300 border-2 border-amber-400/80 hover:border-amber-300 hover:text-noir-950 hover:bg-amber-300 transition-all duration-300 shadow-[0_0_20px_rgba(245,158,11,0.3)] cursor-pointer" id="btn-view-ledger" type="button">
        <span>★ VIEW ON LEADERBOARD ➔</span>
      </button>
    </div>
  </div>
</div>

<!-- FOOTER -->
<footer class="relative z-20 py-4 text-center text-xs font-mono text-noir-aged/65 border-t border-noir-850 bg-noir-950/85 px-4">
  <div class="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
    <span>1930s NOIR EDITION // DROSOPHILA MELANOGASTER AUDIT ENGINE</span>
    <span>CONNECTOME ATLAS 4.8.19 • NOIR-SOUND ARCHIVE</span>
  </div>
</footer>

<!-- SCRIPT ENGINE -->
<script>
    // Change 3C: 1930s Inverted Archive Theme Controller
    function toggleInvertedTheme() {
      document.body.classList.toggle('theme-inverted');
      const isInverted = document.body.classList.contains('theme-inverted');
      try {
        sessionStorage.setItem('flywire_theme_inverted', isInverted ? '1' : '0');
      } catch (e) {}
    }

window.addEventListener('DOMContentLoaded', () => {
    // Restore Inverted 1930s Archive Palette if previously toggled
    try {
      if (sessionStorage.getItem('flywire_theme_inverted') === '1') {
        document.body.classList.add('theme-inverted');
      }
    } catch (e) {}

    // Media & Visual Assets
    const IMG_HERO_IDLE = "/static/fly_hero.png";
    const IMG_GROOVING = "https://lh3.googleusercontent.com/aida/AEtjO1VmzVI8W5pIp7k_a9fZvL99_uu8llsB7zOf7hsF5t4eqGLoXpil_pqkcfLaraUkHDirQ25PwzYDdzElffAONEUe_6vEnE2b3TZVqKzPs-wmEkbYfCumd9RaF5jR7V5MQ2jm0UjtAcEzCIsDLzP4Y5ZeIs8VShdupqp7hutJsI8RdZwBkkeoGcb_jWGlaUa3Pue-YhuHf6f1vrMFvL0QWNLYcHBQpQ_bnjBCKQt-F6X6eEOILWHRmQezEjQ";
    const IMG_DISGUSTED = "https://lh3.googleusercontent.com/aida/AEtjO1W4C2PaIlsLSq_tcyKKk4lthqiYARtLLnoHMIcS3C3ByLJcsouYZ52XEAe_j9wU1pS5zeTE6MojAkFE1pGl7BcLmSZTkBYmrijxyqZ1e0Enj_emx0GYMUUjZh5F5cwrMvkPhRRjFTHAXKYfA6VG5wTd7PcWtPLNKoC1pG4ojdpjoP5nkg14N3yq1GanyDhSCWzAf8cmWjnXU8MJPIEETlBM_xEHnmVjedq16T30JwyFjat0oYTywuZ0TA";

    // 15 RICH CUSTOM VERDICTS (3 MODES x 5 SCORE TIERS)
    const MODE_VERDICTS = {
      courtship: [
        {
          min: 85,
          badge: "RANK S+ // TRUE ROMANTIC SYNC",
          title: "PASSIONATE WING-SONG ACCEPTED!",
          comment: "“By the heavens! Antennal micro-hairs vibrating in celestial harmony. P1 courtship command neurons fully saturated—I am extending a single wing and vibrating at 180 Hz with unbridled dipteran romance!”",
          tag: "EUPHORIC BUZZ",
          isGood: true
        },
        {
          min: 70,
          badge: "RANK A // ENCHANTED FLUTTER",
          title: "A CAPTIVATING COURTSHIP CADENCE!",
          comment: "“A delightfully handsome serenade! Johnston's Organ detects genuine basilar rhythm and smooth frequency contours. A dignified abdominal waggle is granted with high compliments.”",
          tag: "ROMANTIC CADENCE",
          isGood: true
        },
        {
          min: 50,
          badge: "RANK B // LUKEWARM HOVER",
          title: "AN AWKWARD SUITOR AT THE SALON",
          comment: "“Hmm. The rhythm is present, but the inter-pulse interval stumbles like a tipsy gentleman in a speakeasy. Lord Drosophila taps his tarsal claws politely, but keeps his wings decorously tucked.”",
          tag: "AWKWARD HOVER",
          isGood: false
        },
        {
          min: 30,
          badge: "RANK C // DISCORDANT REJECTION",
          title: "COURTSHIP ADVANCES CURTLY SPURNED",
          comment: "“Preposterous courting technique! These erratic frequencies clash violently against the female receptivity window. My antennae ache with second-hand embarrassment. Step aside, amateur!”",
          tag: "COLD REJECTION",
          isGood: false
        },
        {
          min: 0,
          badge: "RANK F // SWATTER DIVORCE",
          title: "THE FLY IS IN UTTER AGONY!",
          comment: "“An unmitigated assault upon Dipteran dignity! Screeching dissonance has induced acute courtship paralysis. I am frantically grooming my antennae in sheer horror. Bring the swatter and end this catastrophe!”",
          tag: "SWATTER DIVORCE",
          isGood: false
        }
      ],
      territorial: [
        {
          min: 85,
          badge: "RANK S+ // WARPING GLADIATOR",
          title: "APEX WARRIOR THORAX SHOCK!",
          comment: "“Incredible pugilistic thunder! These brutal transient strikes and ferocious battle beats set my thoracic motor ablaze. Stand aside, trespassers—the rotting banana throne belongs unconditionally to me!”",
          tag: "WARRIOR GLORY",
          isGood: true
        },
        {
          min: 70,
          badge: "RANK A // AGGRESSIVE SPAR",
          title: "AN INTIMIDATING PERCUSSIVE DISPLAY",
          comment: "“A potent display of sonic muscle! Rapid tempo pulses rattle through Johnston's organ like boxing gloves against canvas. Rival flies retreat across the perimeter in respectful terror.”",
          tag: "PERCUSSIVE FORCE",
          isGood: true
        },
        {
          min: 50,
          badge: "RANK B // HESITANT POSTURING",
          title: "MILD SKIRMISH ON THE FRUIT PLATTER",
          comment: "“Adequate percussive posturing, yet lacking the vicious swagger required to rule the colony. A cautious standoff is maintained, but neither territory was won nor honor defended.”",
          tag: "STANDOFF",
          isGood: false
        },
        {
          min: 30,
          badge: "RANK C // TERRITORY SURRENDERED",
          title: "FEEBLE MEEKNESS AT THE BORDER",
          comment: "“Limp, sluggish, and cowardly! These flaccid beats wouldn't scare away an aphid. You've been chased from the perimeter without the rival flies even bothering to raise their front legs.”",
          tag: "FEEBLE MEEKNESS",
          isGood: false
        },
        {
          min: 0,
          badge: "RANK F // ROUTED RETREAT",
          title: "LC4 PANIC: FLEEING THE BATTLEFIELD!",
          comment: "“Catastrophic rout! This chaotic screech triggers violent Giant Fiber escape reflexes. My fight-or-flight circuits slammed 100% into frantic retreat. I am flying backward into a wall!”",
          tag: "TOTAL ROUT",
          isGood: false
        }
      ],
      sleep: [
        {
          min: 85,
          badge: "RANK S+ // VELVET LULLABY",
          title: "DIVINE CIRCADIAN SLUMBER ACHIEVED!",
          comment: "“Sublime, velvety tranquility... Antennal mechanoreceptors float in warm sub-harmonic stillness with zero abrasive transients. Lord Drosophila tucks his wings, curls his tarsal claws, and sleeps like a king.”",
          tag: "DREAMLAND SLUMBER",
          isGood: true
        },
        {
          min: 70,
          badge: "RANK A // RESTFUL DROWSE",
          title: "SOOTHING DUSK SERENITY",
          comment: "“A very peaceful, gentle nocturnal hum. The acoustic blanket is soft and comforting, though a faint treble rustle keeps one tiny ommatidium half-open. Pleasant dreams, connoisseur.”",
          tag: "RESTFUL DROWSE",
          isGood: true
        },
        {
          min: 50,
          badge: "RANK B // FITFUL TWITCHING",
          title: "RESTLESS TWILIGHT IN THE DORMITORY",
          comment: "“A fitful twilight drowse. The baseline volume is endurable, but random dynamic bumps keep nudging the AMMC threshold. Lord Drosophila mutters in his sleep and turns over testily.”",
          tag: "FITFUL DROWSE",
          isGood: false
        },
        {
          min: 30,
          badge: "RANK C // AGITATED INSOMNIA",
          title: "CIRCADIAN RHYTHM SEVERELY ASSAULTED",
          comment: "“Good grief, shut it down! Unwelcome clatter and intrusive spikes pierce right through my sleep chamber. My circadian clock is reeling and I demand complete silence from the salon!”",
          tag: "AGITATED INSOMNIA",
          isGood: false
        },
        {
          min: 0,
          badge: "RANK F // NIGHTMARE SIREN",
          title: "VIOLENT MIDNIGHT ALARM: SWATTER PANIC!",
          comment: "“HORROR IN THE NIGHT! A blaring, screeching racket that shatters every sleeping neuron in my cerebrum! I was launched out of my hammock in terror. Cease this ungodly nightmare instantly!”",
          tag: "NIGHTMARE SIREN",
          isGood: false
        }
      ]
    };

    function resolveVerdict(score, mode) {
      const m = (mode || 'courtship').toLowerCase();
      const list = MODE_VERDICTS[m] || MODE_VERDICTS['courtship'];
      for (const v of list) {
        if (score >= v.min) return v;
      }
      return list[list.length - 1];
    }

    // DOM Elements
    const unifiedConsolePane = document.getElementById('unified-console-pane');
    const unifiedTypebar = document.getElementById('unified-typebar');
    const typebarIcon = document.getElementById('typebar-icon');
    const typebarUploadSlot = document.getElementById('typebar-upload-slot');
    const fileInput = document.getElementById('audio-file-input');
    const chatBarPlaceholder = document.getElementById('chat-bar-placeholder');
    const onlineSearchInput = document.getElementById('online-search-input');
    const typebarActionBtn = document.getElementById('typebar-action-btn');
    const typebarActionIcon = document.getElementById('typebar-action-icon');

    const uploadQuickDemos = document.getElementById('upload-quick-demos');
    const onlineSuggestionChips = document.getElementById('online-suggestion-chips');
    const onlineResultsContainer = document.getElementById('online-results-container');
    const searchTags = document.querySelectorAll('.search-tag');

    const tabBtnUpload = document.getElementById('tab-btn-upload');
    const tabBtnOnline = document.getElementById('tab-btn-online');

    const presetDaft = document.getElementById('preset-daft');
    const presetDiscord = document.getElementById('preset-discord');

    const heroFrameContainer = document.getElementById('hero-frame-container');
    const viewHeroImage = document.getElementById('view-hero-image');
    const heroFlyImg = document.getElementById('hero-fly-img');
    const heroAuditStatus = document.getElementById('hero-audit-status');
    const filmReelTitle = document.getElementById('film-reel-title');

    const modeButtons = document.querySelectorAll('.mode-btn');
    const modeHintText = document.getElementById('mode-hint-text');
    const modeLockIndicator = document.getElementById('mode-lock-indicator');

    const loadingCard = document.getElementById('loading-card');
    const loadingPercentage = document.getElementById('loading-percentage');
    const loadingStepText = document.getElementById('loading-step-text');
    const progressBarFill = document.getElementById('progress-bar-fill');
    const scanModeLabel = document.getElementById('scan-mode-label');

    const revealPopup = document.getElementById('reveal-popup');
    const btnSeeResults = document.getElementById('btn-see-results');

    const viewVideoPlayer = document.getElementById('view-video-player');
    const flyVideo = document.getElementById('flyVideo');
    const videoSource = document.getElementById('videoSource');
    const reactionFilmImg = document.getElementById('reaction-film-img');
    const filmLiveTag = document.getElementById('film-live-tag');
    const filmTimer = document.getElementById('film-timer');
    const videoProgressBar = document.getElementById('video-progress-bar');
    const videoStatusText = document.getElementById('video-status-text');

    const metricsDashboard = document.getElementById('metrics-dashboard');
    const btnResetApp = document.getElementById('btn-reset-app');
    const resetToast = document.getElementById('reset-toast');
    const toastText = document.getElementById('toast-text');

    // Metrics Card Fields
    const metricsTrackTitle = document.getElementById('metrics-track-title');
    const metricsRankBadge = document.getElementById('metrics-rank-badge');
    const metricsModeBadge = document.getElementById('metrics-mode-badge');
    const metricsVerdictTitle = document.getElementById('metrics-verdict-title');
    const metricsVerdictComment = document.getElementById('metrics-verdict-comment');
    const metricsAffinityScore = document.getElementById('metrics-affinity-score');

    const metricOrgan = document.getElementById('metric-organ');
    const barOrgan = document.getElementById('bar-organ');
    const metricCourtship = document.getElementById('metric-courtship');
    const barCourtship = document.getElementById('bar-courtship');
    const metricFlight = document.getElementById('metric-flight');
    const barFlight = document.getElementById('bar-flight');
    const metricThreat = document.getElementById('metric-threat');
    const barThreat = document.getElementById('bar-threat');
    const metricDopamine = document.getElementById('metric-dopamine');
    const barDopamine = document.getElementById('bar-dopamine');

    // State Variables
    let selectedMode = 'courtship';
    let isProcessing = false;
    let currentTrackTitle = '';
    let evalData = null;
    let filmVideoInterval = null;
    let toastTimer = null;
    let previewAudio = null;

    const MODE_HINTS = {
      courtship: 'Courtship: prefers 120–160 BPM pulse tracks &amp; smooth 180 Hz sine hums',
      territorial: 'Territorial: rewards aggressive battle beats &amp; fast tempo shifts',
      sleep: 'Quiet / Sleep: penalizes loud dynamic peaks; rewards gentle ambient melodies'
    };

    // MODE SELECTION AND LOCKING SYSTEM
    function setModeLock(locked) {
      isProcessing = locked;
      modeButtons.forEach(btn => {
        btn.disabled = locked;
        if (locked) {
          btn.classList.add('opacity-40', 'cursor-not-allowed', 'pointer-events-none');
        } else {
          btn.classList.remove('opacity-40', 'cursor-not-allowed', 'pointer-events-none');
        }
      });
      if (modeLockIndicator) {
        if (locked) modeLockIndicator.classList.remove('hidden');
        else modeLockIndicator.classList.add('hidden');
      }
    }

    modeButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        if (isProcessing) return; // Prevent changing mode while processing!
        selectedMode = btn.getAttribute('data-mode') || 'courtship';
        modeButtons.forEach(b => {
          b.classList.remove('bg-noir-gold', 'text-noir-950', 'font-bold');
          b.classList.add('text-noir-aged');
        });
        btn.classList.add('bg-noir-gold', 'text-noir-950', 'font-bold');
        btn.classList.remove('text-noir-aged');
        if (modeHintText) modeHintText.innerHTML = MODE_HINTS[selectedMode] || '';
        if (scanModeLabel) scanModeLabel.textContent = `JO-AB CIRCUIT TRACKING [${selectedMode.toUpperCase()}]`;
      });
    });

    // SOURCE MODE SWITCHING (UNIFIED TYPEBAR)
    let currentSourceMode = 'upload'; // 'upload' | 'online'

    function setSourceMode(mode) {
      currentSourceMode = mode;
      if (mode === 'upload') {
        tabBtnUpload.classList.add('border-noir-gold', 'bg-noir-900', 'text-noir-gold', 'font-bold');
        tabBtnUpload.classList.remove('border-noir-700', 'bg-noir-950', 'text-noir-aged');
        tabBtnOnline.classList.remove('border-noir-gold', 'bg-noir-900', 'text-noir-gold', 'font-bold');
        tabBtnOnline.classList.add('border-noir-700', 'bg-noir-950', 'text-noir-aged');

        if (typebarIcon) typebarIcon.textContent = 'mic';
        typebarUploadSlot.classList.remove('hidden');
        onlineSearchInput.classList.add('hidden');
        typebarActionIcon.textContent = 'arrow_upward';
        typebarActionBtn.title = 'Upload Audio File';
        uploadQuickDemos.classList.remove('hidden');
        onlineSuggestionChips.classList.add('hidden');
        onlineResultsContainer.classList.add('hidden');
      } else {
        tabBtnOnline.classList.add('border-noir-gold', 'bg-noir-900', 'text-noir-gold', 'font-bold');
        tabBtnOnline.classList.remove('border-noir-700', 'bg-noir-950', 'text-noir-aged');
        tabBtnUpload.classList.remove('border-noir-gold', 'bg-noir-900', 'text-noir-gold', 'font-bold');
        tabBtnUpload.classList.add('border-noir-700', 'bg-noir-950', 'text-noir-aged');

        if (typebarIcon) typebarIcon.textContent = 'search';
        typebarUploadSlot.classList.add('hidden');
        onlineSearchInput.classList.remove('hidden');
        onlineSearchInput.focus();
        typebarActionIcon.textContent = 'search';
        typebarActionBtn.title = 'Search Online Archives';
        uploadQuickDemos.classList.add('hidden');
        onlineSuggestionChips.classList.remove('hidden');
        if (onlineResultsContainer.querySelectorAll('.btn-audit-online').length > 0) {
          onlineResultsContainer.classList.remove('hidden');
        }
      }
    }

    tabBtnUpload.addEventListener('click', () => setSourceMode('upload'));
    tabBtnOnline.addEventListener('click', () => setSourceMode('online'));

    // SHOW TOAST
    function showToast(msg) {
      if (toastText) toastText.textContent = msg;
      if (resetToast) {
        clearTimeout(toastTimer);
        resetToast.classList.remove('opacity-0', '-translate-y-4');
        resetToast.classList.add('opacity-100', 'translate-y-0');
        toastTimer = setTimeout(() => {
          resetToast.classList.remove('opacity-100', 'translate-y-0');
          resetToast.classList.add('opacity-0', '-translate-y-4');
        }, 2500);
      }
    }

    // FULL RESET TO PRISTINE STATE
    function resetToPristine(showResetToast = true) {
      if (filmVideoInterval) clearInterval(filmVideoInterval);
      if (previewAudio) {
        previewAudio.pause();
        previewAudio = null;
      }

      setModeLock(false);

      // Slide down and dismiss metrics panel
      metricsDashboard.classList.remove('translate-y-0');
      metricsDashboard.classList.add('translate-y-full');

      // Reset hero frame zoom and effects
      heroFrameContainer.classList.remove('scale-[1.03]', 'scale-[1.05]', 'film-flash');
      filmReelTitle.textContent = "REEL #34-DROSOPHILA-SYNC";

      // Reset video viewport & pause video
      viewVideoPlayer.style.setProperty('display', 'none', 'important');
      viewVideoPlayer.classList.add('opacity-0', 'pointer-events-none', 'hidden');
      viewVideoPlayer.classList.remove('opacity-100');
      flyVideo.pause();
      flyVideo.onended = null;
      flyVideo.onplaying = null;
      flyVideo.removeAttribute('src');
      flyVideo.load();
      flyVideo.classList.add('hidden');
      reactionFilmImg.classList.remove('hidden');
      videoProgressBar.style.width = '0%';
      filmTimer.textContent = '00:00 / 00:10';

      // Restore idle hero picture
      heroFlyImg.src = IMG_HERO_IDLE;
      viewHeroImage.style.display = '';
      viewHeroImage.classList.remove('opacity-0', 'hidden');
      viewHeroImage.classList.add('opacity-100');
      heroAuditStatus.textContent = "AUDIT STATE: IDLE / WAITING FOR TUNE";

      // Completely hide reveal popup modal
      revealPopup.style.setProperty('display', 'none', 'important');
      revealPopup.classList.add('opacity-0', 'scale-90', 'pointer-events-none', 'hidden');
      revealPopup.classList.remove('opacity-100', 'scale-100');

      // Hide and reset loading card
      loadingCard.classList.add('hidden', 'opacity-0', 'translate-y-3');
      progressBarFill.style.width = '0%';
      loadingPercentage.textContent = '0%';
      loadingStepText.textContent = "1. Converting Audio Stream...";

      // Restore unified typebar console
      chatBarPlaceholder.textContent = "Drag & drop audio file or click to upload (.mp3, .wav, .m4a)...";
      fileInput.value = '';
      unifiedConsolePane.classList.remove('hidden', 'opacity-0', 'scale-95');
      setSourceMode(currentSourceMode);

      if (showResetToast) {
        showToast("PREVIOUS AUDIT ARCHIVED • RECEPTORS ZEROED");
      }
    }

    btnResetApp.addEventListener('click', () => {
      toggleInvertedTheme();
      resetToPristine(true);
      document.getElementById('stage-top').scrollIntoView({ behavior: 'smooth' });
    });

    // START CONNECTOME SCAN PIPELINE VIA SSE
    function startConnectomeScan(filename, trackTitle, mode) {
      currentTrackTitle = trackTitle;
      evalData = null;

      // Lock mode during processing
      setModeLock(true);

      chatBarPlaceholder.textContent = trackTitle;
      heroAuditStatus.textContent = "AUDIT STATE: SCANNING MECHANORECEPTORS...";
      if (scanModeLabel) scanModeLabel.textContent = `JO-AB CIRCUIT TRACKING [${mode.toUpperCase()}]`;

      // Hide unified typebar console, show loading card
      unifiedConsolePane.classList.add('opacity-0', 'scale-95');
      setTimeout(() => {
        unifiedConsolePane.classList.add('hidden');
        loadingCard.classList.remove('hidden');
        void loadingCard.offsetWidth;
        loadingCard.classList.remove('opacity-0', 'translate-y-3');
      }, 250);

      let progress = 0;
      progressBarFill.style.width = '0%';
      loadingPercentage.textContent = '0%';
      loadingStepText.textContent = "1. Converting Audio Stream...";

      // Open SSE connection
      const eventSource = new EventSource(`/stream_judge/${encodeURIComponent(filename)}?mode=${encodeURIComponent(mode)}`);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.stage) {
            loadingStepText.textContent = data.stage;
          }
          if (data.progress !== undefined) {
            progress = Math.max(progress, data.progress);
            progressBarFill.style.width = `${progress}%`;
            loadingPercentage.textContent = `${progress}%`;
          }

          if (data.result) {
            eventSource.close();
            evalData = data;
            evalData.title = trackTitle;
            evalData.mode = mode;

            // Log to Leaderboard in background
            recordAuditToLeaderboard(evalData);

            progressBarFill.style.width = '100%';
            loadingPercentage.textContent = '100%';

            setTimeout(() => {
              loadingCard.classList.add('opacity-0', 'scale-95');
              setTimeout(() => {
                loadingCard.classList.add('hidden');
                // Show reveal popup modal
                revealPopup.style.setProperty('display', 'flex', 'important');
                revealPopup.classList.remove('pointer-events-none', 'opacity-0', 'scale-90', 'hidden');
                revealPopup.classList.add('opacity-100', 'scale-100');
              }, 300);
            }, 400);
          }
        } catch (err) {
          console.error("SSE parse error", err);
        }
      };

      eventSource.onerror = (err) => {
        console.warn("SSE stream closed or error", err);
        eventSource.close();
        if (!evalData) {
          // Fallback evaluation if server disconnected
          setTimeout(() => {
            const fallbackScore = Math.floor(Math.random() * 30) + 70;
            evalData = {
              result: "GOOD",
              score: fallbackScore,
              mode: mode,
              courtship_sync: 88,
              dopamine_surge: 75,
              threat_coefficient: 0.05,
              flight_motor: 80,
              title: trackTitle
            };
            recordAuditToLeaderboard(evalData);
            loadingCard.classList.add('hidden');
            revealPopup.style.setProperty('display', 'flex', 'important');
            revealPopup.classList.remove('pointer-events-none', 'opacity-0', 'scale-90', 'hidden');
            revealPopup.classList.add('opacity-100', 'scale-100');
          }, 600);
        }
      };
    }

    // CLICK "SEE RESULTS" -> PLAY FILM / MP4 -> ONLY SLIDE UP SCORECARD AFTER VIDEO ENDS
    btnSeeResults.addEventListener('click', () => {
      // 1. Immediately disappear the reveal popup modal completely
      revealPopup.style.setProperty('display', 'none', 'important');
      revealPopup.classList.add('opacity-0', 'scale-90', 'pointer-events-none', 'hidden');
      revealPopup.classList.remove('opacity-100', 'scale-100');

      // 2. Hide idle hero image completely
      viewHeroImage.style.setProperty('display', 'none', 'important');
      viewHeroImage.classList.add('opacity-0', 'hidden');
      viewHeroImage.classList.remove('opacity-100');

      // 3. Smoothly center the film frame container into user's direct line of sight
      heroFrameContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
      heroFrameContainer.classList.add('scale-[1.03]', 'film-flash');

      const isGood = (evalData && evalData.result === 'GOOD') || (evalData && evalData.score >= 65);
      const verdict = resolveVerdict(evalData ? evalData.score : 75, selectedMode);

      if (isGood) {
        reactionFilmImg.src = IMG_GROOVING;
        filmLiveTag.textContent = "CRITIC REVIEW: GROOVING!";
        filmReelTitle.textContent = `REEL #34: AUDIT COMPLETE — ${verdict.title}`;
        videoStatusText.textContent = "✦ HIGH DOPAMINE SURGE // MALE FLY BOUNCING ON TEMPO";
      } else {
        reactionFilmImg.src = IMG_DISGUSTED;
        filmLiveTag.textContent = "CRITIC REVIEW: IN AGONY!";
        filmReelTitle.textContent = `REEL #34: REJECTED — ${verdict.title}`;
        videoStatusText.textContent = "✦ CHAOTIC DIN // SWATTER ESCAPE CIRCUIT ARMED";
      }

      // 4. Reveal video player container
      viewVideoPlayer.style.setProperty('display', 'flex', 'important');
      viewVideoPlayer.classList.remove('pointer-events-none', 'opacity-0', 'hidden');
      viewVideoPlayer.classList.add('opacity-100');

      // 5. Setup and play MP4 video
      const videoSrc = isGood ? "/static/fly_good.mp4" : "/static/fly_bad.mp4";
      flyVideo.pause();
      flyVideo.onended = null;
      flyVideo.onplaying = null;
      flyVideo.ontimeupdate = null;
      flyVideo.src = videoSrc;
      flyVideo.load();
      flyVideo.classList.remove('hidden');
      reactionFilmImg.classList.add('hidden');
      flyVideo.muted = false; // User clicked a button, so unmuted audio is allowed

      videoProgressBar.style.width = '0%';
      filmTimer.textContent = '00:00 / 00:10';

      let videoEndedTriggered = false;
      function handleVideoClipEnd() {
        if (videoEndedTriggered) return;
        videoEndedTriggered = true;
        if (filmVideoInterval) {
          clearInterval(filmVideoInterval);
          filmVideoInterval = null;
        }
        videoProgressBar.style.width = '100%';
        console.log("Video clip ended! Displaying actual result report now.");
        // Small cinematic pause after video ends before slide-up
        setTimeout(() => {
          triggerMetricsSlideUp();
        }, 400);
      }

      flyVideo.onloadedmetadata = () => {
        const dur = flyVideo.duration || (isGood ? 10.0 : 15.0);
        filmTimer.textContent = `00:00 / 00:${Math.floor(dur).toString().padStart(2, '0')}`;
      };

      flyVideo.ontimeupdate = () => {
        const cur = flyVideo.currentTime || 0;
        const dur = flyVideo.duration || (isGood ? 10.0 : 15.0);
        const pct = Math.min((cur / dur) * 100, 100);
        videoProgressBar.style.width = `${pct}%`;
        const curSec = Math.floor(cur).toString().padStart(2, '0');
        const durSec = Math.floor(dur).toString().padStart(2, '0');
        filmTimer.textContent = `00:${curSec} / 00:${durSec}`;
      };

      // CRITICAL: Report ONLY appears after video clip ends!
      // Wire onended strictly inside onplaying so previous state never fires early!
      flyVideo.onplaying = () => {
        flyVideo.onended = handleVideoClipEnd;
      };

      // Skip button allows user to jump directly to report if they don't want to wait
      const btnSkipVideo = document.getElementById('btn-skip-video');
      if (btnSkipVideo) {
        btnSkipVideo.onclick = (e) => {
          e.stopPropagation();
          flyVideo.pause();
          handleVideoClipEnd();
        };
      }

      // Play the video
      const playPromise = flyVideo.play();
      if (playPromise !== undefined) {
        playPromise.catch(err => {
          console.warn("Unmuted play blocked by browser policy, trying muted", err);
          flyVideo.muted = true;
          flyVideo.play().catch(e => {
            console.warn("Video playback completely failed, falling back to animated reel", e);
            flyVideo.classList.add('hidden');
            reactionFilmImg.classList.remove('hidden');

            // Fallback duration timer ONLY if MP4 video cannot play at all
            let fallbackDur = isGood ? 8.0 : 10.0;
            let elapsed = 0;
            if (filmVideoInterval) clearInterval(filmVideoInterval);
            filmVideoInterval = setInterval(() => {
              elapsed += 0.2;
              const pct = Math.min((elapsed / fallbackDur) * 100, 100);
              videoProgressBar.style.width = `${pct}%`;
              filmTimer.textContent = `00:0${Math.floor(elapsed)} / 00:${Math.floor(fallbackDur)}`;
              if (elapsed >= fallbackDur) {
                clearInterval(filmVideoInterval);
                filmVideoInterval = null;
                handleVideoClipEnd();
              }
            }, 200);
          });
        });
      }
    });

    // SLIDE UP METRICS SCORECARD
    function triggerMetricsSlideUp() {
      populateScorecard(evalData, currentTrackTitle, selectedMode);
      metricsDashboard.classList.remove('translate-y-full');
      metricsDashboard.classList.add('translate-y-0');
      heroFrameContainer.classList.remove('scale-[1.03]', 'scale-[1.05]');
      setModeLock(false); // Re-enable mode toggle when reviewing ticket

      // Unhide and restore console underneath so it is ready
      unifiedConsolePane.classList.remove('hidden', 'opacity-0', 'scale-95');
      loadingCard.classList.add('hidden');
      setSourceMode(currentSourceMode);

      const btnViewLedger = document.getElementById('btn-view-ledger');
      if (btnViewLedger) {
        btnViewLedger.onclick = () => {
          toggleInvertedTheme();
          metricsDashboard.classList.remove('translate-y-0');
          metricsDashboard.classList.add('translate-y-full');

          // Reset stage to pristine so the user can immediately choose or upload new songs
          resetToPristine(false);

          showLeaderboard();
          setTimeout(() => {
            const target = document.querySelector('.highlight-recent-item') || document.getElementById('leaderboard-section');
            if (target) target.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }, 250);
        };
      }
    }

    function populateScorecard(data, trackTitle, mode) {
      const score = (data && data.score !== undefined) ? Number(data.score) : 75.0;
      const verdict = resolveVerdict(score, mode);

      metricsTrackTitle.textContent = `TRACK: ${trackTitle || 'Audio Specimen [Processed]'}`;
      metricsModeBadge.textContent = `MODE: ${mode.toUpperCase()}`;
      metricsAffinityScore.textContent = score.toFixed(1);

      metricsRankBadge.textContent = data.rank_badge || verdict.badge;
      metricsVerdictTitle.textContent = data.verdict_title || verdict.title;
      metricsVerdictComment.textContent = data.verdict_comment || verdict.comment;

      if (verdict.isGood) {
        metricsRankBadge.className = "font-mono text-xs font-bold text-noir-950 bg-gradient-to-r from-noir-gold to-amber-300 px-3 py-1 rounded-full shadow";
      } else {
        metricsRankBadge.className = "font-mono text-xs font-bold text-white bg-rose-700 px-3 py-1 rounded-full shadow animate-pulse";
      }

      // Telemetry Gauges
      const organPct = data.courtship_sync !== undefined ? Math.round(data.courtship_sync) : Math.round(score);
      metricOrgan.textContent = organPct + "%";
      barOrgan.style.width = organPct + "%";

      const courtshipPct = data.courtship_sync !== undefined ? Math.round(data.courtship_sync * 0.96) : Math.round(score * 0.95);
      metricCourtship.textContent = courtshipPct + "%";
      barCourtship.style.width = courtshipPct + "%";

      const flightPct = data.flight_motor !== undefined ? Math.round(data.flight_motor) : Math.round(score * 0.92);
      metricFlight.textContent = flightPct + "%";
      barFlight.style.width = flightPct + "%";

      const threatPct = data.threat_coefficient !== undefined ? Math.round(data.threat_coefficient * 100) : (score >= 65 ? 5 : 95);
      metricThreat.textContent = threatPct + "%";
      barThreat.style.width = threatPct + "%";
      if (threatPct > 50) {
        barThreat.className = "bg-rose-500 h-full animate-pulse";
        metricThreat.className = "font-cinzel text-xl font-bold text-rose-400";
      } else {
        barThreat.className = "bg-emerald-500 h-full";
        metricThreat.className = "font-cinzel text-xl font-bold text-emerald-400";
      }

      const dopamineVal = data.dopamine_surge !== undefined ? (data.dopamine_surge / 20).toFixed(1) : (score / 25).toFixed(1);
      const dopaminePct = data.dopamine_surge !== undefined ? Math.round(data.dopamine_surge) : Math.round(score);
      metricDopamine.textContent = (score >= 65 ? "+" : "-") + dopamineVal + "x";
      barDopamine.style.width = Math.min(dopaminePct, 100) + "%";
    }

    // FILE INPUT CHANGE LISTENER
    fileInput.addEventListener('change', async (e) => {
      if (!e.target.files || !e.target.files[0]) return;
      const file = e.target.files[0];

      resetToPristine(false);
      showToast("AUDIO SPECIMEN LOADED • COMMENCING BIO-SCAN");

      const formData = new FormData();
      formData.append('song', file);
      formData.append('mode', selectedMode);

      try {
        const uploadRes = await fetch('/upload', { method: 'POST', body: formData });
        const uploadData = await uploadRes.json();
        if (uploadData.filename) {
          startConnectomeScan(uploadData.filename, file.name, selectedMode);
        } else {
          alert("Upload failed: " + (uploadData.error || "Unknown error"));
          resetToPristine(false);
        }
      } catch (err) {
        alert("Upload error: " + err.message);
        resetToPristine(false);
      }
    });

    // UNIFIED TYPEBAR INTERACTIONS
    typebarActionBtn.addEventListener('click', () => {
      if (currentSourceMode === 'upload') {
        fileInput.click();
      } else {
        searchOnlineSongs(onlineSearchInput.value);
      }
    });

    typebarUploadSlot.addEventListener('click', () => {
      fileInput.click();
    });

    if (typebarIcon) {
      typebarIcon.addEventListener('click', () => {
        if (currentSourceMode === 'upload') {
          fileInput.click();
        } else {
          onlineSearchInput.focus();
        }
      });
    }

    // DRAG AND DROP HANDLING ON UNIFIED TYPEBAR
    ['dragenter', 'dragover'].forEach(name => {
      unifiedTypebar.addEventListener(name, (e) => {
        e.preventDefault();
        unifiedTypebar.classList.add('border-noir-gold', 'scale-[1.01]');
      });
    });
    ['dragleave', 'drop'].forEach(name => {
      unifiedTypebar.addEventListener(name, (e) => {
        e.preventDefault();
        unifiedTypebar.classList.remove('border-noir-gold', 'scale-[1.01]');
      });
    });
    unifiedTypebar.addEventListener('drop', async (e) => {
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        setSourceMode('upload');
        resetToPristine(false);
        showToast("AUDIO SPECIMEN DROPPED • COMMENCING BIO-SCAN");

        const formData = new FormData();
        formData.append('song', file);
        formData.append('mode', selectedMode);

        try {
          const uploadRes = await fetch('/upload', { method: 'POST', body: formData });
          const uploadData = await uploadRes.json();
          if (uploadData.filename) {
            startConnectomeScan(uploadData.filename, file.name, selectedMode);
          }
        } catch (err) {
          alert("Drop error: " + err.message);
        }
      }
    });

    // QUICK DEMO 1: DAFT PUNK
    presetDaft.addEventListener('click', async () => {
      resetToPristine(false);
      try {
        const res = await fetch('/api/prepare_demo_track', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ demo_id: 'daft' })
        });
        const data = await res.json();
        startConnectomeScan(data.filename, data.title, selectedMode);
      } catch (err) {
        alert("Demo load error: " + err.message);
      }
    });

    // QUICK DEMO 2: DISCORDANT NOISE
    presetDiscord.addEventListener('click', async () => {
      resetToPristine(false);
      try {
        const res = await fetch('/api/prepare_demo_track', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ demo_id: 'screech' })
        });
        const data = await res.json();
        startConnectomeScan(data.filename, data.title, selectedMode);
      } catch (err) {
        alert("Demo load error: " + err.message);
      }
    });

    // ONLINE SONG SEARCH
    async function searchOnlineSongs(query) {
      if (!query || !query.trim()) return;
      onlineResultsContainer.classList.remove('hidden');
      onlineResultsContainer.innerHTML = `
        <div class="text-center py-6 font-mono text-xs text-noir-gold animate-pulse">
          <span class="inline-block w-2.5 h-2.5 rounded-full bg-noir-gold animate-ping mr-2"></span>
          SEARCHING 1930s SOUND ARCHIVES & GLOBAL REPOSITORIES...
        </div>
      `;

      try {
        const res = await fetch(`/api/search_songs?q=${encodeURIComponent(query.trim())}`);
        const data = await res.json();
        renderOnlineResults(data.results || []);
      } catch (err) {
        onlineResultsContainer.innerHTML = `
          <div class="text-center py-4 font-mono text-xs text-rose-300">
            Archive connection error: ${err.message}. Please try another query.
          </div>
        `;
      }
    }

    onlineSearchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        searchOnlineSongs(onlineSearchInput.value);
      }
    });

    searchTags.forEach(tag => {
      tag.addEventListener('click', () => {
        const q = tag.getAttribute('data-query');
        onlineSearchInput.value = q;
        setSourceMode('online');
        searchOnlineSongs(q);
      });
    });

    function renderOnlineResults(items) {
      if (!items || items.length === 0) {
        onlineResultsContainer.innerHTML = `
          <div class="text-center py-4 font-mono text-xs text-noir-aged">
            No audio specimens located for this query. Try another jazz master, classical composer, or contemporary artist.
          </div>
        `;
        return;
      }

      onlineResultsContainer.innerHTML = items.map(item => `
        <div class="flex items-center justify-between p-2.5 rounded-xl bg-noir-950/80 border border-noir-700/70 hover:border-noir-gold transition-all">
          <div class="flex items-center gap-3 min-w-0 pr-2">
            <img src="${item.artwork || 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=80&q=80'}" class="w-10 h-10 rounded-lg object-cover border border-noir-700 filter sepia-[0.2] shrink-0" alt="Cover"/>
            <div class="truncate">
              <div class="font-playfair text-xs sm:text-sm text-noir-creme font-semibold truncate">${item.title}</div>
              <div class="font-mono text-[10px] text-noir-aged truncate">${item.artist} • ${item.year || 'Classic'} • ${item.genre || 'Song'}</div>
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button class="btn-preview-audio p-1.5 rounded-full border border-noir-700 bg-noir-900 text-noir-gold hover:text-noir-creme hover:border-noir-gold transition-all text-xs cursor-pointer" data-url="${item.preview_url}" title="Preview 30s Snippet" type="button">
              <span class="material-symbols-outlined text-base">play_arrow</span>
            </button>
            <button class="btn-audit-online px-3 py-1.5 rounded-lg bg-gradient-to-r from-noir-gold to-amber-300 text-noir-950 font-cinzel text-xs font-bold uppercase tracking-wider hover:brightness-110 active:scale-95 transition-all shadow cursor-pointer" data-title="${encodeURIComponent(item.title)}" data-artist="${encodeURIComponent(item.artist)}" data-url="${encodeURIComponent(item.preview_url)}" type="button">
              AUDIT ➔
            </button>
          </div>
        </div>
      `).join('');

      // Attach preview listener
      document.querySelectorAll('.btn-preview-audio').forEach(btn => {
        btn.addEventListener('click', () => {
          const url = btn.getAttribute('data-url');
          if (!url) return;
          if (previewAudio && !previewAudio.paused) {
            previewAudio.pause();
            btn.innerHTML = '<span class="material-symbols-outlined text-base">play_arrow</span>';
            return;
          }
          if (previewAudio) previewAudio.pause();
          previewAudio = new Audio(url);
          btn.innerHTML = '<span class="material-symbols-outlined text-base">pause</span>';
          previewAudio.play();
          previewAudio.onended = () => {
            btn.innerHTML = '<span class="material-symbols-outlined text-base">play_arrow</span>';
          };
        });
      });

      // Attach audit listener
      document.querySelectorAll('.btn-audit-online').forEach(btn => {
        btn.addEventListener('click', async () => {
          if (previewAudio) { previewAudio.pause(); previewAudio = null; }
          const title = decodeURIComponent(btn.getAttribute('data-title'));
          const artist = decodeURIComponent(btn.getAttribute('data-artist'));
          const previewUrl = decodeURIComponent(btn.getAttribute('data-url'));

          resetToPristine(false);
          showToast(`RETRIEVING AUDIT STREAM FOR "${title}"...`);

          try {
            const res = await fetch('/api/prepare_online_track', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ preview_url: previewUrl, title: title, artist: artist })
            });
            const data = await res.json();
            if (data.filename) {
              startConnectomeScan(data.filename, `${title} — ${artist}`, selectedMode);
            } else {
              alert("Could not prepare track: " + (data.error || "Unknown"));
              resetToPristine(false);
            }
          } catch (err) {
            alert("Error: " + err.message);
            resetToPristine(false);
          }
        });
      });
    }

    // LEADERBOARD / HALL OF ACCLAIM ENGINE
    let currentLeaderboard = [];
    const leaderboardCardsContainer = document.getElementById('leaderboard-cards-container');
    const tabButtons = document.querySelectorAll('#leaderboard-tabs button');

    async function fetchLeaderboard() {
      try {
        const res = await fetch('/api/leaderboard');
        const data = await res.json();
        currentLeaderboard = data.leaderboard || [];
        renderLeaderboard('all');
      } catch (err) {
        console.warn("Could not load leaderboard from server", err);
      }
    }

    let currentCategoryFilter = 'all';

    async function recordAuditToLeaderboard(data) {
      if (!data) return;
      const score = Number(data.score) || 70.0;
      const mode = data.mode || selectedMode;
      const title = data.title || currentTrackTitle || 'Audio Specimen';
      const verdict = resolveVerdict(score, mode);
      const isGood = score >= 65.0;

      const cat = score < 50 ? 'swatter' : (mode === 'sleep' ? 'sleep' : (mode === 'territorial' ? 'organ' : (score >= 80 ? 'affinity' : 'courtship')));

      const newEntry = {
        id: "live-" + Date.now(),
        title: title,
        artist: title.includes('—') ? title.split('—')[0].trim() : (title.includes('-') ? title.split('-')[0].trim() : 'Audited Specimen'),
        mode: mode,
        category: cat,
        score: Number(score.toFixed(1)),
        rank_badge: data.rank_badge || verdict.badge,
        verdict: data.verdict_title || verdict.title,
        details: `${mode.toUpperCase()} Mode • ${score.toFixed(1)}/100 • ${data.rank_badge || verdict.badge}`,
        date: "Just Now",
        type: isGood ? "good" : "bad",
        isRecent: true
      };

      // 1. Instant Optimistic Real-Time UI update!
      currentLeaderboard = [newEntry, ...currentLeaderboard.filter(e => e.title !== title)];
      renderLeaderboard(currentCategoryFilter);
      showToast(`★ AUDIT LOGGED: "${title}" (${score.toFixed(1)}/100)`);

      // 2. Persist to server backend
      try {
        const res = await fetch('/api/leaderboard', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(newEntry)
        });
        const json = await res.json();
        if (json.leaderboard) {
          currentLeaderboard = json.leaderboard;
          // preserve isRecent tag on the newly added item
          currentLeaderboard.forEach(item => {
            if (item.title === title) item.isRecent = true;
          });
          renderLeaderboard(currentCategoryFilter);
        }
      } catch (err) {
        console.warn("Leaderboard save error", err);
      }
    }

    function renderLeaderboard(filterCategory = 'all') {
      currentCategoryFilter = filterCategory;
      if (!leaderboardCardsContainer) return;

      const categories = [
        { id: 'affinity', name: 'ALL-TIME CONNECTOME AFFINITY', icon: '★', sub: 'Highest Cumulative Synaptic Rating', border: 'border-noir-gold/60', glow: 'bg-noir-gold/10', color: 'text-noir-gold' },
        { id: 'courtship', name: 'COURTSHIP PULSE HARMONICS', icon: '♫', sub: 'Peak Male Wing-Extension Rhythm (~120–165 Hz)', border: 'border-noir-gold/60', glow: 'bg-amber-500/10', color: 'text-amber-400' },
        { id: 'organ', name: "JOHNSTON'S ORGAN VIBRATION", icon: '⚡', sub: 'Basilar Antennal Mechanosensory Resonance', border: 'border-noir-gold/60', glow: 'bg-primary/10', color: 'text-primary' },
        { id: 'sleep', name: "NOCTURNAL SLUMBER (SLEEP MODE)", icon: '☾', sub: 'Sub-Harmonic Circadian Resting Equilibrium', border: 'border-indigo-500/60', glow: 'bg-indigo-500/10', color: 'text-indigo-300' },
        { id: 'swatter', name: 'MOST DREADFUL SWATTER TRIGGERS', icon: '⚠', sub: 'Extreme Panic • Instant Flight/Escape Reflex', border: 'border-rose-900/80', glow: 'bg-rose-700/10', color: 'text-rose-400' }
      ];

      // Recent Audits
      const recentAudits = currentLeaderboard.filter(item => item.isRecent || item.date === 'Just Now' || item.date === 'Recent Audit');

      if (filterCategory === 'recent') {
        const itemsToDisplay = recentAudits.length > 0 ? recentAudits : currentLeaderboard.slice(0, 6);
        leaderboardCardsContainer.innerHTML = `
          <div class="col-span-1 md:col-span-2 p-5 rounded-2xl bg-gradient-to-b from-noir-900 via-noir-850 to-noir-950 border-2 border-noir-gold shadow-2xl relative overflow-hidden">
            <div class="flex items-center justify-between border-b border-noir-700/60 pb-3 mb-3">
              <div class="flex items-center gap-2.5">
                <span class="inline-block w-2.5 h-2.5 rounded-full bg-noir-gold animate-ping"></span>
                <h3 class="font-cinzel text-sm sm:text-base font-bold text-noir-creme">⚡ LIVE AUDIT LOG // REAL-TIME DISPATCH</h3>
              </div>
              <span class="font-mono text-[10px] text-noir-gold bg-noir-950 px-2 py-0.5 rounded border border-noir-gold/60">REAL-TIME</span>
            </div>
            <div class="space-y-2">
              ${itemsToDisplay.map((item, idx) => renderSongItem(item, idx, 'text-noir-gold', true)).join('')}
            </div>
          </div>
        `;
        attachSongItemClickHandlers();
        return;
      }

      // If all or specific category
      let cardsHtml = '';

      // If viewing all and there are recent audits, display the live audit strip!
      if (filterCategory === 'all' && recentAudits.length > 0) {
        cardsHtml += `
          <div class="col-span-1 md:col-span-2 p-4 rounded-2xl bg-gradient-to-r from-noir-900 via-noir-850 to-noir-900 border-2 border-noir-gold/80 shadow-[0_0_20px_rgba(212,175,55,0.25)] relative overflow-hidden">
            <div class="flex items-center justify-between border-b border-noir-700/60 pb-2 mb-2">
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-amber-400 animate-ping"></span>
                <span class="font-cinzel text-xs font-bold text-amber-300">LATEST REAL-TIME AUDITS</span>
              </div>
              <span class="font-mono text-[9px] text-noir-gold uppercase">AUTOMATIC SYNAPSE FEED</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
              ${recentAudits.slice(0, 4).map((item, idx) => renderSongItem(item, idx, 'text-amber-300', true)).join('')}
            </div>
          </div>
        `;
      }

      const visibleCategories = categories.filter(c => filterCategory === 'all' || c.id === filterCategory);

      cardsHtml += visibleCategories.map(cat => {
        let catItems = currentLeaderboard.filter(item => {
          if (cat.id === 'affinity') return item.score >= 75;
          if (cat.id === 'courtship') return item.mode === 'courtship';
          if (cat.id === 'organ') return item.mode === 'territorial' || item.category === 'organ';
          if (cat.id === 'sleep') return item.mode === 'sleep' || item.category === 'sleep';
          if (cat.id === 'swatter') return item.score < 55 || item.category === 'swatter' || item.type === 'bad';
          return false;
        });

        // Fallback items if empty
        if (catItems.length === 0) {
          catItems = currentLeaderboard.filter(i => i.category === cat.id);
        }

        // Sort items by score (descending, except swatter which sorts ascending)
        if (cat.id === 'swatter') {
          catItems.sort((a, b) => a.score - b.score);
        } else {
          catItems.sort((a, b) => b.score - a.score);
        }

        // If any recent audit belongs to this category, ensure it appears at top!
        const recentsInCat = catItems.filter(i => i.isRecent);
        const nonRecentsInCat = catItems.filter(i => !i.isRecent);
        const displayItems = [...recentsInCat, ...nonRecentsInCat].slice(0, 6);

        return `
          <div class="category-card p-4 sm:p-5 rounded-2xl bg-gradient-to-b from-noir-900/90 to-noir-950/95 border-2 ${cat.border} shadow-[0_15px_35px_rgba(0,0,0,0.8)] relative overflow-hidden flex flex-col justify-between" data-cat="${cat.id}">
            <div class="absolute -top-10 -right-10 w-24 h-24 ${cat.glow} rounded-full blur-xl pointer-events-none"></div>
            <div>
              <div class="flex items-center justify-between border-b border-noir-700/60 pb-2.5 mb-2.5">
                <div class="flex items-center gap-2">
                  <span class="${cat.color} font-cinzel text-lg">${cat.icon}</span>
                  <div>
                    <h3 class="font-cinzel text-xs sm:text-sm font-bold text-noir-creme">${cat.name}</h3>
                    <p class="font-mono text-[9px] text-noir-aged">${cat.sub}</p>
                  </div>
                </div>
                <span class="font-mono text-[9px] bg-noir-850 px-2 py-0.5 rounded border border-noir-700 ${cat.color}">${cat.id.toUpperCase()} LEDGER</span>
              </div>

              <div class="space-y-2">
                ${displayItems.map((item, idx) => renderSongItem(item, idx, cat.color, item.isRecent)).join('')}
              </div>
            </div>
            <div class="pt-2.5 mt-3 border-t border-noir-800 text-[9px] font-mono text-noir-aged/70 flex justify-between items-center">
              <span>Click entry to test in biosensor</span>
              <span class="${cat.color}">✦ 35MM LEDGER</span>
            </div>
          </div>
        `;
      }).join('');

      leaderboardCardsContainer.innerHTML = cardsHtml;
      attachSongItemClickHandlers();
    }

    function renderSongItem(item, idx, colorClass, isRecent = false) {
      const recentHighlight = isRecent ? 'border-noir-gold shadow-[0_0_12px_rgba(212,175,55,0.35)] bg-noir-900/90 highlight-recent-item' : 'border-noir-700/70 bg-noir-950/80';
      return `
        <div class="song-item group flex items-center justify-between p-2 rounded-lg border ${recentHighlight} hover:border-noir-gold transition-all cursor-pointer" data-song="${item.title}" data-mode="${item.mode || 'courtship'}" data-score="${item.score}">
          <div class="flex items-center gap-2.5 min-w-0 pr-2">
            <span class="font-cinzel font-bold ${colorClass} text-xs">#${idx + 1}</span>
            <div class="truncate">
              <div class="flex items-center gap-1.5 truncate">
                <span class="font-playfair text-xs sm:text-sm text-noir-creme group-hover:text-noir-gold font-semibold truncate transition-colors">${item.title}</span>
                ${isRecent ? '<span class="px-1.5 py-0.2 rounded bg-amber-400 text-noir-950 font-mono text-[8px] font-bold uppercase tracking-wider shrink-0 animate-pulse">JUST AUDITED</span>' : ''}
              </div>
              <div class="font-mono text-[9px] text-noir-aged truncate">${item.details || (item.artist + ' • ' + (item.mode || 'audit'))}</div>
            </div>
          </div>
          <div class="text-right shrink-0">
            <div class="font-cinzel text-xs sm:text-sm font-black ${colorClass}">${Number(item.score).toFixed(1)} / 100</div>
            <span class="font-mono text-[8px] px-1.5 py-0.5 rounded ${item.score >= 65 ? 'bg-emerald-950/80 border border-emerald-500/50 text-emerald-300' : 'bg-rose-950/80 border border-rose-600/50 text-rose-300'} font-bold uppercase tracking-wider">
              ${item.verdict || (item.score >= 65 ? 'HIGH AFFINITY' : 'SWATTER HAZARD')}
            </span>
          </div>
        </div>
      `;
    }

    function attachSongItemClickHandlers() {
      document.querySelectorAll('.song-item').forEach(el => {
        el.addEventListener('click', () => {
          const songTitle = el.getAttribute('data-song') || 'Archived Specimen';
          document.getElementById('stage-top').scrollIntoView({ behavior: 'smooth' });
          resetToPristine(false);
          showToast(`AUDITING ARCHIVED TRACK: "${songTitle}"`);
          setTimeout(() => {
            setSourceMode('online');
            onlineSearchInput.value = songTitle;
            searchOnlineSongs(songTitle);
          }, 300);
        });
      });
    }

    // Category Tabs Filter click handler
    tabButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const cat = btn.getAttribute('data-category');
        tabButtons.forEach(b => {
          b.classList.remove('bg-noir-gold', 'text-noir-950', 'font-bold', 'border-noir-gold', 'active-tab-btn');
          b.classList.add('bg-noir-900/80', 'text-noir-aged', 'border-noir-700');
        });
        btn.classList.add('bg-noir-gold', 'text-noir-950', 'font-bold', 'border-noir-gold', 'active-tab-btn');
        btn.classList.remove('bg-noir-900/80', 'text-noir-aged', 'border-noir-700');
        renderLeaderboard(cat);
      });
    });

    // LEADERBOARD TOGGLE CONTROLLER
    const leaderboardSection = document.getElementById('leaderboard-section');
    const toggleButtons = document.querySelectorAll('.leaderboard-toggle-btn');
    const closeButtons = document.querySelectorAll('.close-leaderboard-btn');
    let isLeaderboardOpen = false;

    function updateToggleButtons(open) {
      toggleButtons.forEach(btn => {
        const textEl = btn.querySelector('.btn-toggle-text');
        const iconEl = btn.querySelector('.btn-toggle-icon');
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        if (open) {
          if (textEl) {
            textEl.textContent = btn.classList.contains('group')
              ? 'HIDE HALL OF ACCLAIM [COLLAPSE LEDGER]'
              : '▲ HIDE HALL OF ACCLAIM';
          }
          if (iconEl) iconEl.textContent = 'keyboard_arrow_up';
          btn.classList.add('border-noir-gold', 'bg-noir-900');
        } else {
          if (textEl) {
            textEl.textContent = btn.classList.contains('group')
              ? 'VIEW HALL OF ACCLAIM [SHOW LEADERBOARD]'
              : '✦ VIEW HALL OF ACCLAIM';
          }
          if (iconEl) iconEl.textContent = 'keyboard_arrow_down';
        }
      });
    }

    function showLeaderboard() {
      isLeaderboardOpen = true;
      leaderboardSection.classList.remove('hidden');
      leaderboardSection.setAttribute('aria-hidden', 'false');
      updateToggleButtons(true);
      requestAnimationFrame(() => {
        leaderboardSection.classList.remove('opacity-0');
        leaderboardSection.classList.add('opacity-100');
        setTimeout(() => {
          leaderboardSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 80);
      });
    }

    function hideLeaderboard(scrollToTop = false) {
      isLeaderboardOpen = false;
      leaderboardSection.classList.remove('opacity-100');
      leaderboardSection.classList.add('opacity-0');
      leaderboardSection.setAttribute('aria-hidden', 'true');
      updateToggleButtons(false);

      // Always ensure upload & search console is pristine and ready
      resetToPristine(false);

      if (scrollToTop) {
        document.getElementById('stage-top').scrollIntoView({ behavior: 'smooth' });
      }
      setTimeout(() => {
        if (!isLeaderboardOpen) leaderboardSection.classList.add('hidden');
      }, 400);
    }

    toggleButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        if (isLeaderboardOpen) hideLeaderboard(false);
        else showLeaderboard();
      });
    });

    closeButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        hideLeaderboard(true);
      });
    });

    // Rate Another Song buttons
    document.querySelectorAll('.btn-return-and-rate').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        hideLeaderboard(true);
        resetToPristine(false);
        showToast("READY FOR NEXT AUDIT • DROP AUDIO FILE OR SEARCH");
      });
    });

    // Initial Leaderboard Fetch
    fetchLeaderboard();
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

@app.route('/api/search_songs', methods=['GET'])
def search_songs():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"results": []})
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://itunes.apple.com/search?term={encoded}&entity=song&limit=10"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        results = []
        for r in data.get('results', []):
            p_url = r.get('previewUrl')
            if not p_url:
                continue
            results.append({
                'id': str(r.get('trackId', '')),
                'title': r.get('trackName', 'Unknown Title'),
                'artist': r.get('artistName', 'Unknown Artist'),
                'album': r.get('collectionName', ''),
                'year': (r.get('releaseDate') or '')[:4],
                'artwork': r.get('artworkUrl100', ''),
                'preview_url': p_url,
                'genre': r.get('primaryGenreName', 'Song')
            })
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e), "results": []}), 500

@app.route('/api/prepare_online_track', methods=['POST'])
def prepare_online_track():
    data = request.get_json() or {}
    preview_url = data.get('preview_url')
    title = data.get('title', 'Online Audio Specimen')
    artist = data.get('artist', 'Unknown Artist')
    
    if not preview_url:
        return jsonify({"error": "No preview URL provided"}), 400
    
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip()
    safe_title = safe_title[:25].replace(' ', '_')
    raw_filename = f"raw_{safe_title}_{abs(hash(preview_url)) % 10000}.m4a"
    wav_filename = f"online_{safe_title}_{abs(hash(preview_url)) % 10000}.wav"
    raw_path = os.path.join(UPLOAD_FOLDER, raw_filename)
    wav_path = os.path.join(UPLOAD_FOLDER, wav_filename)
    
    try:
        req = urllib.request.Request(preview_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response, open(raw_path, 'wb') as out_f:
            shutil.copyfileobj(response, out_f)
        
        # Convert using ffmpeg to 16kHz WAV
        cmd = ['ffmpeg', '-y', '-i', raw_path, '-t', '30', '-ar', '16000', '-ac', '1', wav_path]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return jsonify({
            "filename": wav_filename,
            "title": f"{title} ({artist})" if artist else title,
            "artist": artist
        })
    except Exception as e:
        return jsonify({"error": f"Failed to download and convert online track: {e}"}), 500
    finally:
        if os.path.exists(raw_path):
            try: os.remove(raw_path)
            except Exception: pass

@app.route('/api/prepare_demo_track', methods=['POST'])
def prepare_demo_track():
    data = request.get_json() or {}
    demo_id = data.get('demo_id', 'daft')
    if demo_id in ('discord', 'screech'):
        src = os.path.join('static', 'screech_demo.wav')
        dst_name = f"demo_screech_{abs(hash(os.getpid())) % 1000}.wav"
        title = "Discordant Screech / Fly Swatter Screaming Noise"
    else:
        src = os.path.join('static', 'daft_demo.wav')
        dst_name = f"demo_daft_{abs(hash(os.getpid())) % 1000}.wav"
        title = "Daft Punk — Around The World [Connectome Master]"
    
    dst_path = os.path.join(UPLOAD_FOLDER, dst_name)
    if os.path.exists(src):
        shutil.copyfile(src, dst_path)
    else:
        import soundfile as sf, numpy as np
        sr = 16000
        t = np.linspace(0, 3, sr * 3, endpoint=False)
        w = np.sin(2 * np.pi * 180 * t) * 0.5
        sf.write(dst_path, w, sr, subtype='PCM_16')
        
    return jsonify({"filename": dst_name, "title": title})

@app.route('/api/leaderboard', methods=['GET', 'POST'])
def handle_leaderboard():
    if request.method == 'GET':
        entries = load_leaderboard()
        return jsonify({"leaderboard": entries})
    
    # POST
    body = request.get_json() or {}
    title = body.get('title', 'Unknown Audio Specimen')
    artist = body.get('artist', 'Unknown Artist')
    score = float(body.get('score', 0))
    mode = body.get('mode', 'courtship')
    rank_badge = body.get('rank_badge', '')
    verdict = body.get('verdict', '')
    details = body.get('details', '')
    is_good = score >= 65.0

    cat = 'swatter' if score < 50 else ('sleep' if mode == 'sleep' else ('organ' if mode == 'territorial' else ('affinity' if score >= 85 else 'courtship')))
    
    entry = {
        "id": f"entry-{abs(hash(title + str(score))) % 100000}",
        "title": title,
        "artist": artist,
        "category": cat,
        "mode": mode,
        "score": round(score, 1),
        "verdict": verdict or rank_badge,
        "details": details or f"Audited under {mode.upper()} mode",
        "date": "Recent Audit",
        "type": "good" if is_good else "bad"
      }
    
    entries = load_leaderboard()
    # Check if duplicate title exists, replace or prepend
    filtered = [e for e in entries if e.get('title') != title]
    updated = [entry] + filtered[:49]
    save_leaderboard(updated)
    return jsonify({"status": "ok", "leaderboard": updated})

@app.route('/stream_judge/<filename>')
def stream_judge(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    mode = request.args.get('mode', DEFAULT_MODE)
    if mode not in VALID_MODES:
        mode = DEFAULT_MODE

    def generate():
        msg_queue = queue.Queue()

        def callback(data_dict):
            msg_queue.put(data_dict)

        result_holder = {}

        def run_eval():
            try:
                res = evaluate_song_with_fly(file_path, progress_callback=callback, mode=mode)
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)