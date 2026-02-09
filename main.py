import requests
import random
import time
import os
import json
from datetime import datetime
from fastapi import FastAPI, Query
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

LEAGUE_MAP = {
    "PL": {"odds": "soccer_epl", "name": "Premier League"},
    "PD": {"odds": "soccer_spain_la_liga", "name": "La Liga"},
    "BL1": {"odds": "soccer_germany_bundesliga", "name": "Bundesliga"},
    "SA": {"odds": "soccer_italy_serie_a", "name": "Serie A"}
}

STORAGE = {
    "standings": {},      
    "matches_cache": {}, 
    "daily_ticket": None,
    "last_update": 0,
    "ticket_date": None
}

client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Gemini Client Init Error: {e}")

# --- BACKEND LOGIKA ---

def get_standings(league_code):
    now = time.time()
    if league_code in STORAGE["standings"] and (now - STORAGE["last_update"]) < 21600:
        return STORAGE["standings"][league_code]

    try:
        url = f"https://api.football-data.org/v4/competitions/{league_code}/standings"
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
            STORAGE["standings"][league_code] = table
            STORAGE["last_update"] = now
        return table
    except:
        return STORAGE["standings"].get(league_code, {})

def match_team(odds_name, standings):
    if not standings: return {"pos": "?", "form": "N/A", "goals": "0:0", "points": 0}
    clean = odds_name.lower().replace("fc", "").replace("united", "").strip()
    for s_name, data in standings.items():
        s_clean = s_name.lower().replace("fc", "").replace("united", "").strip()
        if s_clean in clean or clean in s_clean:
            return data
    return {"pos": "?", "form": "N/A", "goals": "0:0", "points": 0}

def fetch_all_leagues_data():
    now = time.time()
    if (now - STORAGE["last_update"]) < 3600 and STORAGE["matches_cache"]:
        return STORAGE["matches_cache"]

    all_matches = {}
    for code, info in LEAGUE_MAP.items():
        try:
            standings = get_standings(code)
            url = f"https://api.the-odds-api.com/v4/sports/{info['odds']}/odds/?regions=eu&markets=h2h,totals&apiKey={ODDS_API_KEY}"
            resp = requests.get(url, timeout=12).json()
            
            league_results = []
            if isinstance(resp, list):
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

                    total_p = (1/o1) + (1/ox) + (1/o2)
                    prob_1 = round(((1/o1) / total_p) * 100)
                    prob_x = round(((1/ox) / total_p) * 100)
                    prob_2 = round(((1/o2) / total_p) * 100)

                    league_results.append({
                        "id": item['id'], "domaci": home, "hostia": away,
                        "o1": o1, "ox": ox, "o2": o2, "over25": over25 or 1.85,
                        "probs": {"1": prob_1, "X": prob_x, "2": prob_2},
                        "h_stat": h_stat, "a_stat": a_stat, "league_name": info['name']
                    })
            all_matches[code] = league_results
        except: continue
    
    STORAGE["matches_cache"] = all_matches
    STORAGE["last_update"] = now
    return all_matches

# --- API ENDPOINTS ---

@app.get("/api/analysis")
def get_analysis(league: str = "PL"):
    data = fetch_all_leagues_data()
    matches = data.get(league, [])
    for m in matches:
        if "analyza" not in m:
            ai_text = "Dáta sú pripravené na spracovanie."
            if client:
                try:
                    prompt = f"Zápas: {m['domaci']} vs {m['hostia']}. Kurzy: 1({m['o1']}), X({m['ox']}), 2({m['o2']}). Napíš jednu vetu analýzy o šanciach tímu v slovenčine."
                    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                    ai_text = response.text
                except: pass
            m["analyza"] = ai_text
    return matches

@app.get("/api/tiket-dna")
def get_daily_ticket():
    today = datetime.now().strftime("%Y-%m-%d")
    data = fetch_all_leagues_data()
    flat = [item for sub in data.values() for item in sub]
    return sorted(flat, key=lambda x: min(x['o1'], x['o2']))[:3]

@app.get("/api/generate-ticket")
def generate_ticket(league: str = "PL", risk: str = "low"):
    data = fetch_all_leagues_data()
    matches = data.get(league, [])
    if risk == "low": filtered = [m for m in matches if min(m['o1'], m['o2']) < 1.6]
    elif risk == "medium": filtered = [m for m in matches if 1.6 <= min(m['o1'], m['o2']) <= 2.2]
    else: filtered = [m for m in matches if min(m['o1'], m['o2']) > 2.2]
    return random.sample(filtered, min(len(filtered), 3)) if filtered else matches[:2]

# --- UI (BLUE CYBERPUNK - MOBILE OPTIMIZED) ---

html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Betting PRO AI</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #050a10; --card: #0d121b; --primary: #66fcf1; --text: #c5c6c7; --win: #00ff88; --loss: #ff4444; --border: #1f2833; }
        body { background: var(--bg); color: var(--text); font-family: 'Rajdhani', sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        
        /* Desktop Sidebar */
        .sidebar { width: 240px; background: #0b0c10; border-right: 1px solid var(--border); padding: 25px; display: flex; flex-direction: column; }
        .main { flex: 1; padding: 20px; overflow-y: auto; padding-bottom: 80px; background: radial-gradient(circle at top right, #141b24 0%, #050a10 100%); }
        .logo { color: var(--primary); font-size: 26px; font-weight: bold; text-align: center; margin-bottom: 40px; }
        
        .menu-item { padding: 14px; cursor: pointer; color: #666; border-radius: 8px; margin-bottom: 6px; transition: 0.2s; display: flex; align-items: center; gap: 10px; }
        .menu-item.active { background: #1a222d; color: #fff; border-left: 4px solid var(--primary); }
        
        /* Mobile Bottom Nav */
        .mobile-nav { display: none; position: fixed; bottom: 0; left: 0; width: 100%; background: #0b0c10; border-top: 1px solid var(--border); justify-content: space-around; padding: 12px 0; z-index: 1000; }
        .nav-icon { display: flex; flex-direction: column; align-items: center; font-size: 10px; color: #666; cursor: pointer; }
        .nav-icon.active { color: var(--primary); }
        .nav-icon i { font-size: 20px; margin-bottom: 3px; }

        /* VIP Styling */
        .tab-scroll { overflow-x: auto; display: flex; gap: 8px; margin-bottom: 20px; padding-bottom: 5px; -webkit-overflow-scrolling: touch; }
        .tab { white-space: nowrap; background: #141b24; border: 1px solid var(--border); color: #888; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px; }
        .tab.active { background: var(--primary); color: #000; font-weight: bold; }

        .match-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 15px; margin-bottom: 12px; cursor: pointer; }
        .match-card.open { border-color: var(--primary); }
        .summary { display: flex; justify-content: space-between; font-size: 14px; }
        .details { display: none; margin-top: 15px; border-top: 1px solid #1f2833; padding-top: 15px; }
        .match-card.open .details { display: block; }

        .prob-bar { display: flex; height: 6px; border-radius: 10px; overflow: hidden; background: #333; margin: 10px 0; }
        .p1 { background: var(--win); } .px { background: #555; } .p2 { background: var(--loss); }
        
        .ticket-box { background: var(--card); border: 1px solid var(--primary); border-radius: 12px; padding: 20px; margin-bottom: 15px; }
        .btn-main { background: var(--primary); color: #000; border: none; padding: 14px; border-radius: 50px; font-weight: bold; width: 100%; text-transform: uppercase; margin-top: 15px; }

        select { background: #141b24; color: #fff; border: 1px solid var(--border); padding: 12px; border-radius: 8px; width: 100%; margin-bottom: 15px; }

        .page { display: none; } .page.active { display: block; animation: fadeIn 0.3s; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

        /* Media Queries for Mobile */
        @media (max-width: 768px) {
            .sidebar { display: none; }
            .mobile-nav { display: flex; }
            .main { padding: 15px; padding-bottom: 90px; }
            .header h1 { font-size: 20px; }
            .dash-grid { grid-template-columns: 1fr !important; }
        }
    </style>
</head>
<body>

<div class="sidebar">
    <div class="logo">⚡ BET PRO</div>
    <div style="margin-top: 30px;">
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="showPage('analysis', this); loadAnalysis('PL')">📊 VIP Analýza</div>
        <div class="menu-item" onclick="showPage('daily', this); loadDaily()">🎯 Tiket Dňa</div>
        <div class="menu-item" onclick="showPage('custom', this)">🛠️ Vlastný Tiket</div>
        <div class="menu-item" onclick="showPage('history', this); renderHistory()">✅ História</div>
    </div>
</div>

<div class="main">
    <div class="header" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
        <h1 id="p-title" style="margin:0; font-size:22px;">Dashboard</h1>
        <div style="text-align:right">
            <span style="font-size:10px; color:#555; display:block">BANKROLL</span>
            <b id="ui-bank" style="color:var(--primary); font-size: 18px;">€1000.00</b>
        </div>
    </div>

    <!-- DASHBOARD -->
    <div id="home" class="page active">
        <div class="dash-grid" style="display:grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
            <div style="background:var(--card); padding:15px; border-radius:10px; border:1px solid var(--border); text-align:center;">
                <span style="color:#555; font-size:10px;">PROFIT</span>
                <h3 style="color:var(--win); margin:5px 0;">+€452.10</h3>
            </div>
            <div style="background:var(--card); padding:15px; border-radius:10px; border:1px solid var(--border); text-align:center;">
                <span style="color:#555; font-size:10px;">WIN RATE</span>
                <h3 style="color:var(--primary); margin:5px 0;">76%</h3>
            </div>
        </div>
        <div style="background:var(--card); padding:15px; border-radius:10px; border:1px solid var(--border);"><canvas id="chart" height="150"></canvas></div>
    </div>

    <!-- VIP -->
    <div id="analysis" class="page">
        <div class="tab-scroll">
            <div class="tab active" onclick="setLeague('PL', this)">Premier League</div>
            <div class="tab" onclick="setLeague('PD', this)">La Liga</div>
            <div class="tab" onclick="setLeague('BL1', this)">Bundesliga</div>
            <div class="tab" onclick="setLeague('SA', this)">Serie A</div>
        </div>
        <div id="match-list">Načítavam...</div>
    </div>

    <!-- TIKET DNA -->
    <div id="daily" class="page"><div id="daily-ticket-out"></div></div>

    <!-- CUSTOM -->
    <div id="custom" class="page">
        <div class="ticket-box">
            <h3 style="margin:0 0 15px 0; text-align:center; color:var(--primary)">GENERÁTOR</h3>
            <select id="gen-league"><option value="PL">Premier League</option><option value="PD">La Liga</option></select>
            <select id="gen-risk"><option value="low">Nízke riziko</option><option value="medium">Stredné riziko</option><option value="high">Vysoké riziko</option></select>
            <button class="btn-main" onclick="generateSmartTicket()">GENEROVAŤ</button>
            <div id="gen-out" style="margin-top:20px"></div>
        </div>
    </div>

    <!-- HISTORY -->
    <div id="history" class="page"><div id="hist-out"></div></div>
</div>

<!-- Bottom Nav for Mobile -->
<div class="mobile-nav">
    <div class="nav-icon active" onclick="showPage('home', this)">🏠<span>Domov</span></div>
    <div class="nav-icon" onclick="showPage('analysis', this); loadAnalysis('PL')">📊<span>Analýzy</span></div>
    <div class="nav-icon" onclick="showPage('daily', this); loadDaily()">🎯<span>Tiket</span></div>
    <div class="nav-icon" onclick="showPage('history', this); renderHistory()">✅<span>História</span></div>
</div>

<script>
let bank = parseFloat(localStorage.getItem('bp_bank')) || 1000;
let hist = JSON.parse(localStorage.getItem('bp_hist')) || [];

function updateUI() {
    document.getElementById('ui-bank').innerText = '€' + bank.toFixed(2);
    localStorage.setItem('bp_bank', bank);
    localStorage.setItem('bp_hist', JSON.stringify(hist));
}

function showPage(id, el) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.menu-item, .nav-icon').forEach(m => m.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    if(el) el.classList.add('active');
    
    const titles = {'home':'Dashboard', 'analysis':'VIP Analýza', 'daily':'Tiket Dňa', 'custom':'Vlastný Tiket', 'history':'História'};
    document.getElementById('p-title').innerText = titles[id];
}

async function loadAnalysis(league) {
    const div = document.getElementById('match-list');
    div.innerHTML = '<p style="text-align:center; color:var(--primary)">Sťahujem trhy...</p>';
    const res = await fetch(`/api/analysis?league=${league}`);
    const matches = await res.json();
    let html = '';
    matches.forEach(m => {
        html += `
        <div class="match-card" onclick="this.classList.toggle('open')">
            <div class="summary">
                <b>${m.domaci} - ${m.hostia}</b>
                <span style="color:var(--primary)">${m.o1.toFixed(2)} | ${m.ox.toFixed(2)} | ${m.o2.toFixed(2)}</span>
            </div>
            <div class="details">
                <div style="display:flex; justify-content:space-between; font-size:11px; color:#555">
                    <span>POZÍCIA: ${m.h_stat.pos} vs ${m.a_stat.pos}</span>
                    <span>BODY: ${m.h_stat.points} : ${m.a_stat.points}</span>
                </div>
                <div class="prob-bar">
                    <div class="p1" style="width:${m.probs['1']}%"></div>
                    <div class="px" style="width:${m.probs['X']}%"></div>
                    <div class="p2" style="width:${m.probs['2']}%"></div>
                </div>
                <p style="font-size:13px; font-style:italic; margin:10px 0; color:#fff">"${m.analyza}"</p>
            </div>
        </div>`;
    });
    div.innerHTML = html || '<p style="text-align:center">Žiadne zápasy.</p>';
}

function setLeague(code, el) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active');
    loadAnalysis(code);
}

async function loadDaily() {
    const div = document.getElementById('daily-ticket-out');
    div.innerHTML = 'Generujem...';
    const res = await fetch('/api/tiket-dna');
    const data = await res.json();
    renderSlip(data, div, 'TIKET DŇA');
}

async function generateSmartTicket() {
    const div = document.getElementById('gen-out');
    div.innerHTML = 'Počítam...';
    const res = await fetch(`/api/generate-ticket?league=${document.getElementById('gen-league').value}&risk=${document.getElementById('gen-risk').value}`);
    const data = await res.json();
    renderSlip(data, div, 'VYGENEROVANÝ TIKET');
}

function renderSlip(data, container, title) {
    if(!data.length) return container.innerHTML = 'Dáta chýbajú.';
    let total = 1;
    let rows = '';
    let matches = [];
    data.forEach(m => {
        const odd = m.o1 < m.o2 ? m.o1 : m.o2;
        total *= odd;
        matches.push(`${m.domaci} (${m.o1 < m.o2 ? '1':'2'})`);
        rows += `<div style="display:flex; justify-content:space-between; font-size:14px; padding:8px 0; border-bottom:1px dashed #222">
            <span><b>${m.domaci}</b></span><b>${odd.toFixed(2)}</b>
        </div>`;
    });
    container.innerHTML = `<div class="ticket-box"><h4 style="margin:0 0 10px 0; text-align:center">${title}</h4>${rows}<div style="display:flex; justify-content:space-between; margin-top:15px; font-weight:bold"><span>CELKOVÝ KURZ</span><span style="color:var(--primary)">${total.toFixed(2)}</span></div><button class="btn-main" onclick="placeBet(${total.toFixed(2)}, '${matches.join(', ')}')">VSAĎIŤ €50</button></div>`;
}

function placeBet(odds, matches) {
    if(bank < 50) return alert("Málo peňazí!");
    bank -= 50;
    hist.unshift({ date: new Date().toLocaleString(), matches: matches, odds: odds.toFixed(2), status: 'V hre' });
    updateUI(); alert("Tiket odoslaný!");
}

function renderHistory() {
    const div = document.getElementById('hist-out');
    if(!hist.length) return div.innerHTML = '<p style="text-align:center">Žiadna história.</p>';
    let h = '<table style="width:100%; text-align:left; border-collapse:collapse; font-size:13px;">';
    h += '<tr style="color:var(--primary); border-bottom:1px solid var(--border)"><th style="padding:10px">Čas</th><th>Zápasy</th><th>Kurz</th></tr>';
    hist.forEach(t => h += `<tr style="border-bottom:1px solid #111"><td style="padding:10px; font-size:10px">${t.date}</td><td>${t.matches}</td><td style="color:var(--primary)">${t.odds}</td></tr>`);
    div.innerHTML = h + '</table>';
}

const ctx = document.getElementById('chart').getContext('2d');
new Chart(ctx, { type: 'line', data: { labels: ['P','U','S','Š','P','S','N'], datasets: [{ label: 'Profit', data: [1000, 1080, 1040, 1150, 1290, 1250, 1452], borderColor: '#66fcf1', tension: 0.4 }] }, options: { plugins: { legend: { display: false } }, scales: { y: { display: false }, x: { grid: { display: false } } } } });
updateUI();
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return html_content

# Inštrukcia pre Render: uvicorn main:app --host 0.0.0.0 --port $PORT

