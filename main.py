import requests
import random
import time
import os
import google.generativeai as genai
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Inicializácia FastAPI
app = FastAPI()

# ==========================================
# 🔑 KONFIGURÁCIA API KĽÚČOV (VŠETKY 3 INTEGROVANÉ)
# ==========================================
ODDS_API_KEY = "3e42c726ab364fb9eeede03b0017964c"    
GEMINI_API_KEY = "AIzaSyCreRpXTUwxzJegxQKUJ2RiX5BwSagdljg"
FOOTBALL_DATA_KEY = "dad8c8fcd0a146c394fb2d53faab818a" 

# Globálna pamäť pre caching a zdieľané tikety
STORAGE = {
    "standings": {},      
    "analysis_cache": [], 
    "daily_ticket": [],
    "last_update": 0,
    "ticket_date": None
}

# Inicializácia Gemini AI
try:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    print(f"Gemini Init Error: {e}")

# --- BACKEND LOGIKA: AGREGÁCIA DÁT ---

def get_standings():
    """ Získa reálnu tabuľku Premier League z Football-Data.org """
    now = time.time()
    if "PL" in STORAGE["standings"] and (now - STORAGE["last_update"]) < 21600:
        return STORAGE["standings"]["PL"]

    try:
        url = "https://api.football-data.org/v4/competitions/PL/standings"
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
            STORAGE["standings"]["PL"] = table
            STORAGE["last_update"] = now
        return table
    except Exception as e:
        print(f"Football-Data Error: {e}")
        return STORAGE["standings"].get("PL", {})

def match_team_names(odds_name, standings):
    """ Fuzzy matching pre spojenie dvoch rôznych API zdrojov """
    for s_name, data in standings.items():
        if s_name.lower() in odds_name.lower() or odds_name.lower() in s_name.lower():
            return s_name, data
    return odds_name, {"pos": "?", "form": "N/A", "goals": "0:0", "points": 0}

def fetch_hybrid_analysis():
    """ Agregátor: Spája Odds API kurzy s Football-Data štatistikami a AI analýzou """
    now = time.time()
    if (now - STORAGE["last_update"]) < 3600 and STORAGE["analysis_cache"]:
        return STORAGE["analysis_cache"]

    try:
        standings = get_standings()
        url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?regions=eu&markets=h2h&apiKey={ODDS_API_KEY}"
        odds_resp = requests.get(url, timeout=10).json()
        
        if not isinstance(odds_resp, list): return STORAGE["analysis_cache"]

        results = []
        for item in odds_resp[:12]:
            home_raw, away_raw = item['home_team'], item['away_team']
            h_name, h_stat = match_team_names(home_raw, standings)
            a_name, a_stat = match_team_names(away_raw, standings)
            
            bookies = item.get('bookmakers', [])
            if not bookies: continue
            outcomes = bookies[0]['markets'][0]['outcomes']
            
            try:
                o1 = next(x['price'] for x in outcomes if x['name'] == home_raw)
                o2 = next(x['price'] for x in outcomes if x['name'] == away_raw)
            except: continue

            tip = "1" if o1 < o2 else "2"
            risk_level = 1 if min(o1, o2) < 1.65 else 2
            
            analysis_text = "Analýza sa pripravuje..."
            try:
                prompt = (f"Futbal: {h_name} (Pozícia {h_stat['pos']}, Forma {h_stat['form']}) vs "
                          f"{a_name} (Pozícia {a_stat['pos']}, Forma {a_stat['form']}). Kurzy: {o1} vs {o2}. "
                          f"Navrhni tip {tip} jednou vetou v slovenčine.")
                ai_res = ai_model.generate_content(prompt)
                analysis_text = ai_res.text
            except:
                analysis_text = f"Štatistická výhoda na strane {h_name if tip=='1' else a_name}."

            results.append({
                "domaci": h_name, "hostia": a_name, "kurz": o1 if tip=="1" else o2,
                "tip": tip, "risk": risk_level, "liga": "Premier League",
                "h_stat": h_stat, "a_stat": a_stat, "analyza": analysis_text,
                "dovera": int((1/min(o1,o2))*92)
            })
        
        STORAGE["analysis_cache"] = results
        return results
    except Exception as e:
        print(f"Aggregation Error: {e}")
        return STORAGE["analysis_cache"]

# --- API ENDPOINTS ---

@app.get("/api/analyza")
def get_vip_analysis():
    return fetch_hybrid_analysis()

@app.get("/api/tiket-dna")
def get_daily_fixed_ticket():
    today = datetime.now().strftime("%Y-%m-%d")
    if STORAGE["ticket_date"] != today or not STORAGE["daily_ticket"]:
        data = fetch_hybrid_analysis()
        STORAGE["daily_ticket"] = sorted(data, key=lambda x: x['kurz'])[:3]
        STORAGE["ticket_date"] = today
    return STORAGE["daily_ticket"]

@app.get("/api/vlastny-tiket")
def get_custom_ticket(risk: int = 1):
    data = fetch_hybrid_analysis()
    filtered = [m for m in data if m['risk'] == int(risk)]
    return filtered[:3] if filtered else data[:2]

# --- UI (CYBERPUNK MONOLITH) ---

html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betting PRO AI | Triple Engine</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #050a10; --card: #11161d; --primary: #66fcf1; --text: #c5c6c7; --win: #00ff88; --loss: #ff4444; }
        body { background: var(--bg); color: var(--text); font-family: 'Rajdhani', sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        .sidebar { width: 260px; background: #0b0c10; border-right: 1px solid #1f2833; padding: 25px; display: flex; flex-direction: column; }
        .logo { color: var(--primary); font-size: 28px; font-weight: bold; text-align: center; margin-bottom: 40px; }
        .menu-item { padding: 15px; cursor: pointer; color: #888; border-radius: 8px; margin-bottom: 5px; transition: 0.3s; }
        .menu-item:hover, .menu-item.active { background: #1f2833; color: #fff; border-left: 4px solid var(--primary); }
        .main { flex: 1; padding: 30px; overflow-y: auto; background: radial-gradient(circle at top right, #1f2833 0%, #0b0c10 80%); }
        
        /* VIP Analysis Style */
        .ac-card { background: var(--card); border: 1px solid #2c3e50; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.4); }
        .ac-head { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 15px; }
        .ac-stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px; }
        .stat-box { background: #1a2634; padding: 8px; border-radius: 6px; text-align: center; }
        .stat-label { font-size: 10px; color: #888; text-transform: uppercase; display: block; }
        .stat-val { font-size: 15px; font-weight: bold; color: var(--primary); }
        .form-row { display: flex; gap: 4px; justify-content: center; margin-top: 4px; }
        .dot { width: 8px; height: 8px; border-radius: 50%; }
        .W { background: var(--win); } .D { background: #ffcc00; } .L { background: var(--loss); } .N { background: #444; }
        .ai-text { background: rgba(102, 252, 241, 0.05); border-left: 3px solid var(--primary); padding: 12px; font-style: italic; font-size: 14px; color: #fff; }

        .dash-card { background: var(--card); padding: 20px; border-radius: 12px; border: 1px solid #2c3e50; text-align: center; margin-bottom: 20px; }
        .btn { background: var(--primary); color: #000; border: none; padding: 12px 25px; border-radius: 50px; font-weight: bold; cursor: pointer; width: 100%; transition: 0.3s; text-transform: uppercase; }
        .btn-bet { background: transparent; border: 1px solid var(--primary); color: var(--primary); margin-top: 10px; }
        .page { display: none; } .page.active { display: block; animation: fadeIn 0.5s; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @media (max-width: 768px) { .sidebar { display: none; } .mobile-nav { display: flex; position: fixed; bottom: 0; width: 100%; background: #111; padding: 15px; justify-content: space-around; border-top: 1px solid #333; z-index: 100; } }
        .mobile-nav { display: none; }
    </style>
</head>
<body>

<div class="sidebar">
    <div class="logo">⚡ BET PRO</div>
    <div style="margin-top: 40px;">
        <div class="menu-item active" onclick="show('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="show('analysis', this); loadAnalysis()">📊 VIP Analýza</div>
        <div class="menu-item" onclick="show('ticket', this); loadTicket()">🎯 Tiket Dňa</div>
        <div class="menu-item" onclick="show('custom', this)">🛠️ Vlastný Tiket</div>
        <div class="menu-item" onclick="show('history', this); renderHistory()">✅ História</div>
    </div>
</div>

<div class="main">
    <div style="display:flex; justify-content:space-between; margin-bottom:30px;">
        <h1 id="p-title">Dashboard</h1>
        <div style="text-align:right">Bankroll: <b id="ui-bank" style="color:var(--primary)">€1000.00</b></div>
    </div>

    <!-- DASHBOARD -->
    <div id="home" class="page active">
        <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
            <div class="dash-card"><h3>Aktuálny Stav</h3><h1 id="d-bank">€1000</h1></div>
            <div class="dash-card"><h3>ROI AI</h3><h1 style="color:var(--win)">+24.8%</h1></div>
        </div>
        <div class="dash-card"><canvas id="chart"></canvas></div>
    </div>

    <!-- VIP ANALYZA (Nový dizajn s Football-Data) -->
    <div id="analysis" class="page">
        <div id="analysis-out">Načítavam hĺbkovú analýzu...</div>
    </div>

    <!-- TIKETY (S funkciou vsadiť) -->
    <div id="ticket" class="page">
        <div id="ticket-out" style="max-width: 500px; margin: 0 auto;"></div>
    </div>

    <div id="custom" class="page">
        <div class="dash-card" style="max-width: 500px; margin: 0 auto;">
            <label>Úroveň rizika</label>
            <select id="risk" style="width:100%; padding:10px; background:#000; color:#fff; border:1px solid #333; margin:10px 0; border-radius:8px;">
                <option value="1">Nízke (1.20 - 1.60)</option>
                <option value="2">Stredné (1.65 - 2.10)</option>
            </select>
            <button class="btn" onclick="loadCustom()">Generovať</button>
        </div>
        <div id="custom-out" style="max-width: 500px; margin: 20px auto;"></div>
    </div>

    <div id="history" class="page">
        <div id="hist-out"></div>
    </div>
</div>

<div class="mobile-nav">
    <span onclick="show('home')">🏠</span><span onclick="show('analysis'); loadAnalysis()">📊</span><span onclick="show('ticket'); loadTicket()">🎯</span><span onclick="show('history'); renderHistory()">✅</span>
</div>

<script>
let bank = parseFloat(localStorage.getItem('bp_bank')) || 1000;
let hist = JSON.parse(localStorage.getItem('bp_hist')) || [];
updateUI();

function updateUI() {
    document.getElementById('ui-bank').innerText = '€' + bank.toFixed(2);
    if(document.getElementById('d-bank')) document.getElementById('d-bank').innerText = '€' + bank.toFixed(2);
    localStorage.setItem('bp_bank', bank);
    localStorage.setItem('bp_hist', JSON.stringify(hist));
}

function show(id, el) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    if(el) {
        document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
        el.classList.add('active');
        document.getElementById('p-title').innerText = el.innerText.split(' ')[1];
    }
}

// 1. VIP ANALYZA (Data z viacerých API)
async function loadAnalysis() {
    const div = document.getElementById('analysis-out');
    div.innerHTML = 'Synchronizujem dáta o forme a tabuľkách...';
    const res = await fetch('/api/analyza'); const data = await res.json();
    let html = '';
    
    data.forEach(m => {
        const renderForm = (f) => f.split(',').map(c => `<div class="dot ${c.trim()}"></div>`).join('');
        html += `
        <div class="ac-card">
            <div class="ac-head">
                <div style="font-size:18px; font-weight:bold; color:#fff">${m.domaci} vs ${m.hostia}</div>
                <div style="background:var(--primary); color:#000; padding:4px 10px; border-radius:5px; font-weight:bold">${m.kurz}</div>
            </div>
            <div class="ac-stats-grid">
                <div class="stat-box"><span class="stat-label">Tabuľka</span><span class="stat-val">${m.h_stat.pos} .vs ${m.a_stat.pos}</span></div>
                <div class="stat-box"><span class="stat-label">Dôvera</span><span class="stat-val">${m.dovera}%</span></div>
                <div class="stat-box"><span class="stat-label">Forma Domáci</span><div class="form-row">${renderForm(m.h_stat.form)}</div></div>
                <div class="stat-box"><span class="stat-label">Forma Hostia</span><div class="form-row">${renderForm(m.a_stat.form)}</div></div>
            </div>
            <div class="ai-text">"${m.analyza}"</div>
        </div>`;
    });
    div.innerHTML = html;
}

// 2. TIKETY (S funkciou vsadiť)
async function loadTicket() { renderTicket('/api/tiket-dna', 'ticket-out', 'VIP TIKET DŇA'); }
async function loadCustom() { renderTicket('/api/vlastny-tiket?risk='+document.getElementById('risk').value, 'custom-out', 'TVOJ GENERÁT'); }

async function renderTicket(url, elId, title) {
    const div = document.getElementById(elId);
    div.innerHTML = 'Hľadám najlepšie kurzy...';
    const res = await fetch(url); const data = await res.json();
    
    let rows = ''; let total = 1; let slip = [];
    data.forEach(m => {
        total *= m.kurz; slip.push(`${m.domaci} (${m.tip})`);
        rows += `<div style="display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px dashed #333">
            <span><b>${m.domaci}</b><br><small>${m.tip}</small></span>
            <b style="color:var(--primary)">${m.kurz}</b>
        </div>`;
    });
    
    div.innerHTML = `
    <div class="dash-card" style="text-align:left; border: 1px solid var(--primary);">
        <h2 style="color:var(--primary); text-align:center">${title}</h2>
        ${rows}
        <div style="display:flex; justify-content:space-between; margin-top:15px; font-size:22px; font-weight:bold">
            <span>KURZ</span><span>${total.toFixed(2)}</span>
        </div>
        <button class="btn btn-bet" onclick='placeBet(${total.toFixed(2)}, ${JSON.stringify(slip)})'>VSAĎIŤ €50</button>
    </div>`;
}

function placeBet(odds, matches) {
    if(bank < 50) return alert("Málo peňazí!");
    bank -= 50;
    hist.unshift({ date: new Date().toLocaleTimeString(), matches: matches.join(', '), odds: odds, status: 'Čaká' });
    updateUI(); alert("Vsadili ste na tiket!");
}

function renderHistory() {
    const div = document.getElementById('hist-out');
    if(!hist.length) return div.innerHTML = 'História je prázdna.';
    let h = '<table style="width:100%; color:#ccc; text-align:left"><tr><th>Čas</th><th>Tiket</th><th>Kurz</th><th>Stav</th></tr>';
    hist.forEach(t => h += `<tr><td>${t.date}</td><td>${t.matches}</td><td>${t.odds}</td><td style="color:orange">${t.status}</td></tr>`);
    div.innerHTML = h + '</table>';
}

const ctx = document.getElementById('chart').getContext('2d');
new Chart(ctx, { type: 'line', data: { labels: ['P','U','S','Š','P','S','N'], datasets: [{ label: 'Kapitál', data: [1000, 1050, 1020, 1100, 1250, 1200, 1380], borderColor: '#66fcf1', tension: 0.4 }] }, options: { plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#1f2833' } }, x: { display: false } } } });
</script>

</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return html_content

# Startovacia inštrukcia pre Render: uvicorn main:app --host 0.0.0.0 --port $PORT
