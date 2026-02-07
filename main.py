import requests
import random
import time
import os
import json
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from google import genai

# Inicializácia FastAPI
app = FastAPI()

# ==========================================
# 🔑 KONFIGURÁCIA API KĽÚČOV
# ==========================================
ODDS_API_KEY = "3e42c726ab364fb9eeede03b0017964c"    
GEMINI_API_KEY = "AIzaSyCreRpXTUwxzJegxQKUJ2RiX5BwSagdljg"
FOOTBALL_DATA_KEY = "dad8c8fcd0a146c394fb2d53faab818a" 

# Globálna pamäť (Cache)
STORAGE = {
    "standings": {},      
    "analysis_cache": [], 
    "daily_ticket": [],
    "last_update": 0,
    "ticket_date": None
}

# Inicializácia novej Gemini SDK (google-genai)
client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Gemini Client Init Error: {e}")

# --- BACKEND LOGIKA ---

def get_standings(league="PL"):
    now = time.time()
    if league in STORAGE["standings"] and (now - STORAGE["last_update"]) < 21600:
        return STORAGE["standings"][league]

    try:
        url = f"https://api.football-data.org/v4/competitions/{league}/standings"
        headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
        resp = requests.get(url, headers=headers, timeout=10).json()
        
        table = {}
        if 'standings' in resp:
            for team in resp['standings'][0]['table']:
                name = team['team']['shortName'] or team['team']['name']
                table[name] = {
                    "pos": team['position'],
                    "form": team.get('form', 'N/A'),
                    "goals": f"{team['goalsFor']}:{team['goalsAgainst']}",
                    "points": team['points']
                }
            STORAGE["standings"][league] = table
            STORAGE["last_update"] = now
        return table
    except:
        return STORAGE["standings"].get(league, {})

def match_team(odds_name, standings):
    if not standings: return {"pos": "?", "form": "N/A", "goals": "0:0", "points": 0}
    clean = odds_name.lower().replace("fc", "").replace("united", "").strip()
    for s_name, data in standings.items():
        s_clean = s_name.lower().replace("fc", "").replace("united", "").strip()
        if s_clean in clean or clean in s_clean:
            return data
    return {"pos": "?", "form": "N/A", "goals": "0:0", "points": 0}

def fetch_data():
    now = time.time()
    if (now - STORAGE["last_update"]) < 3600 and STORAGE["analysis_cache"]:
        return STORAGE["analysis_cache"]

    try:
        standings = get_standings("PL")
        url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?regions=eu&markets=h2h,totals&apiKey={ODDS_API_KEY}"
        resp = requests.get(url, timeout=12).json()
        
        if not isinstance(resp, list): return STORAGE["analysis_cache"]

        results = []
        for item in resp[:12]:
            home, away = item['home_team'], item['away_team']
            h_stat = match_team(home, standings)
            a_stat = match_team(away, standings)
            
            bookies = item.get('bookmakers', [])
            if not bookies: continue
            
            o1, ox, o2, over25 = 2.0, 3.2, 2.0, None
            markets = bookies[0].get('markets', [])
            for m in markets:
                if m['key'] == 'h2h':
                    o1 = next((x['price'] for x in m['outcomes'] if x['name'] == home), 2.0)
                    ox = next((x['price'] for x in m['outcomes'] if x['name'] == 'Draw'), 3.2)
                    o2 = next((x['price'] for x in m['outcomes'] if x['name'] == away), 2.0)
                if m['key'] == 'totals':
                    over25 = next((x['price'] for x in m['outcomes'] if x['name'] == 'Over' and x['point'] == 2.5), None)

            # AI Analysis via google-genai
            ai_text = "Analýza sa generuje..."
            if client:
                try:
                    prompt = f"Zápas: {home} (Pos: {h_stat['pos']}) vs {away} (Pos: {a_stat['pos']}). Kurzy: 1({o1}), X({ox}), 2({o2}), Over2.5({over25 or 'N/A'}). Napíš jednu profesionálnu analytickú vetu v slovenčine bez balastu."
                    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                    ai_text = response.text
                except: pass

            results.append({
                "id": item['id'], "domaci": home, "hostia": away,
                "o1": o1, "ox": ox, "o2": o2, "over25": over25 or 1.85,
                "h_stat": h_stat, "a_stat": a_stat, "analyza": ai_text
            })
        
        STORAGE["analysis_cache"] = results
        return results
    except:
        return STORAGE["analysis_cache"]

# --- ENDPOINTS ---

@app.get("/api/matches")
def api_matches(): return fetch_data()

@app.get("/api/tiket-dna")
def api_td():
    data = fetch_data()
    return sorted(data, key=lambda x: x['o1'])[:3]

# --- UI (BLUE CYBERPUNK - CLEAN VERSION) ---

html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betting PRO AI</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #050a10; --card: #0d121b; --primary: #66fcf1; --text: #c5c6c7; --win: #00ff88; --loss: #ff4444; --border: #1f2833; }
        body { background: var(--bg); color: var(--text); font-family: 'Rajdhani', sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        
        /* Layout */
        .sidebar { width: 240px; background: #0b0c10; border-right: 1px solid var(--border); padding: 25px; display: flex; flex-direction: column; }
        .main { flex: 1; padding: 30px; overflow-y: auto; background: radial-gradient(circle at top right, #141b24 0%, #050a10 100%); }
        .logo { color: var(--primary); font-size: 26px; font-weight: bold; text-align: center; margin-bottom: 40px; letter-spacing: 2px; }
        
        /* Nav */
        .menu-item { padding: 14px; cursor: pointer; color: #666; border-radius: 8px; margin-bottom: 6px; transition: 0.2s; font-weight: 500; }
        .menu-item:hover, .menu-item.active { background: #1a222d; color: #fff; border-left: 4px solid var(--primary); }
        
        /* VIP Analysis Card */
        .vip-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 25px; padding: 0; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        .vip-header { padding: 15px 20px; background: rgba(102, 252, 241, 0.03); border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .vip-teams { font-size: 18px; font-weight: bold; color: #fff; }
        
        .vip-body { padding: 20px; display: grid; grid-template-columns: 1.2fr 1fr; gap: 20px; }
        .vip-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .stat-box { background: #141b24; padding: 12px; border-radius: 8px; border: 1px solid #1f2833; text-align: center; }
        .stat-label { font-size: 9px; color: #555; text-transform: uppercase; margin-bottom: 4px; display: block; }
        .stat-val { font-size: 15px; font-weight: bold; color: var(--primary); }
        
        .vip-odds { display: flex; flex-direction: column; gap: 8px; }
        .odds-row { display: flex; justify-content: space-between; background: #050a10; padding: 10px 15px; border-radius: 6px; font-size: 14px; border: 1px solid #141b24; }
        .odds-row b { color: var(--win); }

        .vip-footer { padding: 15px 20px; background: #050a10; border-top: 1px solid var(--border); font-style: italic; color: #eee; font-size: 14px; line-height: 1.5; }
        
        /* Custom Ticket Picker */
        .picker-grid { display: grid; grid-template-columns: 1fr; gap: 15px; }
        .pick-item { background: var(--card); border: 1px solid var(--border); padding: 15px; border-radius: 10px; display: flex; justify-content: space-between; align-items: center; }
        .pick-btns { display: flex; gap: 6px; }
        .btn-odd { background: #141b24; border: 1px solid var(--border); color: #fff; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; min-width: 45px; transition: 0.2s; }
        .btn-odd:hover { border-color: var(--primary); color: var(--primary); }
        .btn-odd.active { background: var(--primary); color: #000; font-weight: bold; }

        /* Slip Sidebar */
        .slip-box { background: var(--card); border: 2px solid var(--primary); padding: 20px; border-radius: 12px; position: sticky; top: 0; }
        .slip-row { display: flex; justify-content: space-between; border-bottom: 1px dashed #333; padding: 8px 0; font-size: 14px; }
        
        .btn-main { background: var(--primary); color: #000; border: none; padding: 12px 25px; border-radius: 50px; font-weight: bold; cursor: pointer; width: 100%; text-transform: uppercase; margin-top: 15px; transition: 0.3s; }
        .btn-main:hover { box-shadow: 0 0 20px var(--primary); }

        .page { display: none; } .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }

        @media (max-width: 768px) { .sidebar { display: none; } .mobile-nav { display: flex; position: fixed; bottom: 0; width: 100%; background: #0b0c10; padding: 12px; justify-content: space-around; border-top: 1px solid var(--border); z-index: 100; } }
        .mobile-nav { display: none; }
    </style>
</head>
<body>

<div class="sidebar">
    <div class="logo">⚡ BET PRO</div>
    <div style="margin-top: 30px;">
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="showPage('analysis', this); loadVIP()">📊 VIP Analýza</div>
        <div class="menu-item" onclick="showPage('custom', this); loadPicker()">🛠️ Vlastný Tiket</div>
        <div class="menu-item" onclick="showPage('history', this); renderHistory()">✅ História</div>
    </div>
</div>

<div class="main">
    <div style="display:flex; justify-content:space-between; margin-bottom:30px;">
        <h1 id="p-title" style="margin:0">Dashboard</h1>
        <div style="text-align:right">Bankroll: <b id="ui-bank" style="color:var(--primary); font-size: 22px;">€1000.00</b></div>
    </div>

    <!-- DASHBOARD -->
    <div id="home" class="page active">
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 25px;">
            <div style="background:var(--card); padding:20px; border-radius:12px; border:1px solid var(--border); text-align:center;">
                <span style="color:#555; font-size:11px; text-transform:uppercase;">Týždenný Profit</span>
                <h2 style="color:var(--win); margin:5px 0;">+€312.40</h2>
            </div>
            <div style="background:var(--card); padding:20px; border-radius:12px; border:1px solid var(--border); text-align:center;">
                <span style="color:#555; font-size:11px; text-transform:uppercase;">AI Win-Rate</span>
                <h2 style="color:var(--primary); margin:5px 0;">76%</h2>
            </div>
        </div>
        <div style="background:var(--card); padding:20px; border-radius:12px; border:1px solid var(--border);">
            <canvas id="chart" height="120"></canvas>
        </div>
    </div>

    <!-- VIP ANALYSIS -->
    <div id="analysis" class="page">
        <div id="vip-out">Načítavam hĺbkovú analýzu...</div>
    </div>

    <!-- CUSTOM TICKET (PICKER) -->
    <div id="custom" class="page">
        <div style="display:grid; grid-template-columns: 1fr 320px; gap: 30px;">
            <div id="picker-list" class="picker-grid">Načítavam zápasy...</div>
            <div class="slip-box">
                <h3 style="margin-top:0; text-align:center; color:var(--primary)">TVOJ TIKET</h3>
                <div id="slip-items">Zvoľte kurzy zo zoznamu...</div>
                <div style="margin-top:20px; display:flex; justify-content:space-between; font-size:18px; font-weight:bold;">
                    <span>KURZ</span><span id="slip-odds" style="color:var(--primary)">1.00</span>
                </div>
                <button class="btn-main" onclick="placeBet()">VSAĎIŤ €50</button>
                <button style="background:transparent; border:none; color:#555; width:100%; margin-top:10px; cursor:pointer;" onclick="clearSlip()">Vymazať všetko</button>
            </div>
        </div>
    </div>

    <div id="history" class="page"><div id="hist-out"></div></div>
</div>

<div class="mobile-nav">
    <span onclick="showPage('home')">🏠</span><span onclick="showPage('analysis'); loadVIP()">📊</span><span onclick="showPage('custom'); loadPicker()">🛠️</span><span onclick="showPage('history'); renderHistory()">✅</span>
</div>

<script>
let bank = parseFloat(localStorage.getItem('bp_bank')) || 1000;
let hist = JSON.parse(localStorage.getItem('bp_hist')) || [];
let slip = [];
let allMatches = [];

function updateUI() {
    document.getElementById('ui-bank').innerText = '€' + bank.toFixed(2);
    localStorage.setItem('bp_bank', bank);
    localStorage.setItem('bp_hist', JSON.stringify(hist));
}

function showPage(id, el) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    if(el) {
        document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
        el.classList.add('active');
        document.getElementById('p-title').innerText = el.innerText.split(' ')[1];
    }
}

// VIP ANALYSIS
async function loadVIP() {
    const div = document.getElementById('vip-out');
    div.innerHTML = '<p style="text-align:center; color:var(--primary)">Agregujem trhy a AI štatistiky...</p>';
    const res = await fetch('/api/matches');
    const data = await res.json();
    let html = '';
    data.forEach(m => {
        html += `
        <div class="vip-card">
            <div class="vip-header"><div class="vip-teams">${m.domaci} vs ${m.hostia}</div><div style="font-size:12px; color:var(--primary)">PREMIER LEAGUE</div></div>
            <div class="vip-body">
                <div class="vip-stats">
                    <div class="stat-box"><span class="stat-label">Tabuľka</span><span class="stat-val">${m.h_stat.pos} .vs ${m.a_stat.pos}</span></div>
                    <div class="stat-box"><span class="stat-label">Body</span><span class="stat-val">${m.h_stat.points} : ${m.a_stat.points}</span></div>
                    <div class="stat-box" style="grid-column: span 2"><span class="stat-label">Forma Domáci</span><span class="stat-val" style="font-size:12px; color:#fff">${m.h_stat.form}</span></div>
                </div>
                <div class="vip-odds">
                    <div class="odds-row"><span>Výsledok (1X2)</span><b>${m.o1.toFixed(2)} | ${m.ox.toFixed(2)} | ${m.o2.toFixed(2)}</b></div>
                    <div class="odds-row"><span>Over 2.5 Gólu</span><b>${m.over25.toFixed(2)}</b></div>
                </div>
            </div>
            <div class="vip-footer">AI INSIGHT: "${m.analyza}"</div>
        </div>`;
    });
    div.innerHTML = html || 'Žiadne dáta.';
}

// CUSTOM TICKETING (THE PICKER)
async function loadPicker() {
    const div = document.getElementById('picker-list');
    div.innerHTML = 'Načítavam zápasy...';
    const res = await fetch('/api/matches');
    allMatches = await res.json();
    let html = '';
    allMatches.forEach((m, idx) => {
        html += `
        <div class="pick-item">
            <div style="font-weight:bold; color:#fff;">${m.domaci} - ${m.hostia}</div>
            <div class="pick-btns">
                <button class="btn-odd" onclick="togglePick(${idx}, '1', ${m.o1})">1 (${m.o1.toFixed(2)})</button>
                <button class="btn-odd" onclick="togglePick(${idx}, 'X', ${m.ox})">X (${m.ox.toFixed(2)})</button>
                <button class="btn-odd" onclick="togglePick(${idx}, '2', ${m.o2})">2 (${m.o2.toFixed(2)})</button>
                <button class="btn-odd" style="border-color:var(--win)" onclick="togglePick(${idx}, 'Over 2.5', ${m.over25})">O2.5 (${m.over25.toFixed(2)})</button>
            </div>
        </div>`;
    });
    div.innerHTML = html;
}

function togglePick(matchIdx, type, odd) {
    const match = allMatches[matchIdx];
    // Zistíme či už tento zápas na tikete je
    const existingIdx = slip.findIndex(p => p.matchId === match.id);
    if(existingIdx > -1) slip.splice(existingIdx, 1);
    
    slip.push({ matchId: match.id, teams: `${match.domaci}-${match.hostia}`, type: type, odd: odd });
    renderSlip();
}

function renderSlip() {
    const div = document.getElementById('slip-items');
    let total = 1;
    if(slip.length === 0) { div.innerHTML = 'Zvoľte kurzy...'; document.getElementById('slip-odds').innerText = '1.00'; return; }
    
    let html = '';
    slip.forEach((p, i) => {
        total *= p.odd;
        html += `<div class="slip-row"><span><b>${p.type}</b> ${p.teams}</span><b>${p.odd.toFixed(2)}</b></div>`;
    });
    div.innerHTML = html;
    document.getElementById('slip-odds').innerText = total.toFixed(2);
}

function clearSlip() { slip = []; renderSlip(); }

function placeBet() {
    if(slip.length === 0) return alert("Prázdny tiket!");
    if(bank < 50) return alert("Nedostatok peňazí!");
    
    let totalOdds = document.getElementById('slip-odds').innerText;
    bank -= 50;
    hist.unshift({ date: new Date().toLocaleString(), matches: slip.map(s => `${s.teams} (${s.type})`).join(', '), odds: totalOdds, status: 'Čaká' });
    clearSlip(); updateUI(); alert("Tiket úspešne podaný!");
}

function renderHistory() {
    const div = document.getElementById('hist-out');
    if(!hist.length) return div.innerHTML = 'Žiadne stávky.';
    let h = '<table style="width:100%; color:#ccc; text-align:left; border-collapse:collapse;">';
    h += '<tr style="border-bottom:1px solid #1f2833;"><th style="padding:10px;">Čas</th><th>Zápasy</th><th>Kurz</th><th>Stav</th></tr>';
    hist.forEach(t => h += `<tr style="border-bottom:1px solid #111;"><td style="padding:10px; font-size:12px;">${t.date}</td><td style="font-size:13px;">${t.matches}</td><td>${t.odds}</td><td style="color:orange">${t.status}</td></tr>`);
    div.innerHTML = h + '</table>';
}

const ctx = document.getElementById('chart').getContext('2d');
new Chart(ctx, { type: 'line', data: { labels: ['Po','Ut','St','Št','Pi','So','Ne'], datasets: [{ label: 'Kapitál', data: [1000, 1050, 1020, 1100, 1250, 1200, 1312], borderColor: '#66fcf1', tension: 0.4 }] }, options: { plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#1f2833' } }, x: { display: false } } } });
updateUI();
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return html_content
