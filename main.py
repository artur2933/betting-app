import requests
import random
import time
import os
import google.generativeai as genai
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

# ==========================================
# 🔑 AKTUALIZOVANÉ API KĽÚČE
# ==========================================
ODDS_API_KEY = "3e42c726ab364fb9eeede03b0017964c"    
GEMINI_API_KEY = "AIzaSyCreRpXTUwxzJegxQKUJ2RiX5BwSagdljg"
FOOTBALL_DATA_KEY = "dad8c8fcd0a146c394fb2d53faab818a" 
# ==========================================

STORAGE = {
    "daily_ticket": [],
    "last_ticket_date": None,
    "analysis_cache": [],
    "standings_cache": {},
    "last_update": 0
}

# Inicializácia Gemini AI
try:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    print(f"Gemini Init Error: {e}")

def get_standings(league_code="PL"):
    """ Získa tabuľku z Football-Data.org s ochranou limitov """
    now = time.time()
    if league_code in STORAGE["standings_cache"] and (now - STORAGE["last_update"]) < 10800:
        return STORAGE["standings_cache"][league_code]

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
                    "points": team['points']
                }
            STORAGE["standings_cache"][league_code] = table
            STORAGE["last_update"] = now
        return table
    except:
        return STORAGE["standings_cache"].get(league_code, {})

def match_team_stats(team_name, standings):
    """ Párovanie mien tímov medzi rôznymi API zdrojmi """
    team_name_clean = team_name.lower().replace("fc", "").strip()
    for key in standings:
        key_clean = key.lower().replace("fc", "").strip()
        if key_clean in team_name_clean or team_name_clean in key_clean:
            return standings[key]
    return {"pos": "?", "form": "N/A", "points": "0"}

def fetch_combined_data():
    """ Agregátor: Spája Odds API kurzy s Football-Data štatistikami a AI analýzou """
    now = time.time()
    if (now - STORAGE["last_update"]) < 3600 and STORAGE["analysis_cache"]:
        return STORAGE["analysis_cache"]

    try:
        standings = get_standings("PL") # Zameranie na Premier League (najvyšší ROI)
        
        odds_url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?regions=eu&markets=h2h&apiKey={ODDS_API_KEY}"
        odds_resp = requests.get(odds_url, timeout=10).json()
        
        if not isinstance(odds_resp, list):
            return STORAGE["analysis_cache"]

        matches = []
        for item in odds_resp[:12]:
            home = item['home_team']
            away = item['away_team']
            
            st_h = match_team_stats(home, standings)
            st_a = match_team_stats(away, standings)
            
            bookies = item.get('bookmakers', [])
            if not bookies: continue
            
            outcomes = bookies[0]['markets'][0]['outcomes']
            o1 = next((x['price'] for x in outcomes if x['name'] == home), 2.0)
            o2 = next((x['price'] for x in outcomes if x['name'] == away), 2.0)

            tip = "1" if o1 < o2 else "2"
            prob = (1 / min(o1, o2)) * 100
            
            # AI Insight context
            context = f"{home} (Pos: {st_h['pos']}, Form: {st_h['form']}) vs {away} (Pos: {st_a['pos']}, Form: {st_a['form']}). Kurzy: {o1} vs {o2}."
            analysis_text, analysis_points = generate_ai_insight(context, tip)

            matches.append({
                "domaci": home, "hostia": away, 
                "kurz": o1 if tip == "1" else o2,
                "tip": tip, "risk": 1 if min(o1, o2) < 1.7 else 2,
                "liga": "Premier League", 
                "dovera": int(prob),
                "stats": {"pos_h": st_h['pos'], "pos_a": st_a['pos'], "form_h": st_h['form']},
                "analyza_text": analysis_text,
                "analyza_body": analysis_points
            })

        STORAGE["analysis_cache"] = matches
        return matches
    except Exception as e:
        print(f"Aggregation Error: {e}")
        return STORAGE["analysis_cache"]

def generate_ai_insight(context, tip):
    """ Použitie Gemini AI na vytvorenie profesionálneho textu """
    try:
        prompt = f"Analyzuj futbal: {context}. Odporúčaný tip: {tip}. Napíš jednu odbornú vetu a 3 technické body prečo (slovensky). Žiadny markdown."
        response = ai_model.generate_content(prompt)
        lines = response.text.split('\n')
        main = lines[0]
        points = [l.strip('-•* ') for l in lines[1:] if l.strip()][:3]
        return main, points
    except:
        return "Štatistická analýza naznačuje výhodu favorita na základe stability kádra.", ["Výrazná prevaha v držaní lopty.", "Efektívna konverzia šancí.", "Defenzíva bez kľúčových absencií."]

# --- API ROUTES ---

@app.get("/")
def home():
    return HTMLResponse(content=html_content)

@app.get("/api/analyza")
def get_analysis():
    return fetch_combined_data()

@app.get("/api/tiket-dna")
def get_daily_ticket():
    today = datetime.now().strftime("%Y-%m-%d")
    if STORAGE["last_ticket_date"] != today or not STORAGE["daily_ticket"]:
        data = fetch_combined_data()
        STORAGE["daily_ticket"] = sorted(data, key=lambda x: x['kurz'])[:3]
        STORAGE["last_ticket_date"] = today
    return STORAGE["daily_ticket"]

# --- UI (BLUE CYBERPUNK) ---
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8"><title>Betting PRO AI</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #050a10; --card: #11161d; --primary: #66fcf1; --text: #c5c6c7; }
        body { background: var(--bg); color: var(--text); font-family: 'Rajdhani', sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        .sidebar { width: 260px; background: #0b0c10; border-right: 1px solid #1f2833; padding: 25px; }
        .main { flex: 1; padding: 40px; overflow-y: auto; background: radial-gradient(circle at top right, #1f2833 0%, #0b0c10 80%); }
        .menu-item { padding: 15px; cursor: pointer; color: #888; border-radius: 8px; margin-bottom: 10px; transition: 0.2s; }
        .menu-item:hover, .menu-item.active { background: #1f2833; color: #fff; border-left: 4px solid var(--primary); }
        .analysis-card { background: var(--card); border: 1px solid #2c3e50; border-radius: 12px; padding: 25px; margin-bottom: 25px; position: relative; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 1px solid #333; padding-bottom: 15px; }
        .badge { background: #1a2634; padding: 4px 10px; border-radius: 4px; font-size: 12px; color: var(--primary); font-weight: bold; }
        .tip-box { background: #1a2634; padding: 15px; border-radius: 8px; margin-top: 15px; border-left: 4px solid var(--primary); display: flex; justify-content: space-between; }
        .page { display: none; } .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        .btn-bet { background: var(--primary); color: #000; border: none; padding: 12px 25px; border-radius: 5px; cursor: pointer; font-weight: bold; width: 100%; text-transform: uppercase; margin-top: 15px; }
    </style>
</head>
<body>
<div class="sidebar">
    <h1 style="color:var(--primary); text-align:center; font-size:28px; letter-spacing:2px;">⚡ BET PRO</h1>
    <div style="margin-top:40px;">
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="showPage('analysis', this); loadAnalysis()">📊 VIP Analýzy</div>
        <div class="menu-item" onclick="showPage('ticket', this); loadDailyTicket()">🎯 Tiket Dňa</div>
    </div>
</div>
<div class="main">
    <div class="header">
        <h1 id="title-display">Dashboard</h1>
        <div style="text-align:right">BANKROLL: <b id="ui-bank" style="color:var(--primary)">€1000.00</b></div>
    </div>
    <div id="home" class="page active">
        <div style="background:var(--card); padding:20px; border-radius:12px; border:1px solid #1f2833">
            <canvas id="profitChart" height="100"></canvas>
        </div>
    </div>
    <div id="analysis" class="page">
        <div id="analysis-list">Synchronizujem dáta z globálnych trhov...</div>
    </div>
    <div id="ticket" class="page">
        <div id="daily-ticket-container" style="max-width:500px; margin:0 auto;"></div>
    </div>
</div>
<script>
    let bankroll = parseFloat(localStorage.getItem('bp_bank')) || 1000;
    document.getElementById('ui-bank').innerText = '€' + bankroll.toFixed(2);

    function showPage(id, el) {
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
        document.getElementById(id).classList.add('active');
        el.classList.add('active');
        document.getElementById('title-display').innerText = el.innerText.split(' ')[1];
    }

    async function loadAnalysis() {
        const div = document.getElementById('analysis-list');
        div.innerHTML = '<p style="color:var(--primary)">Prebieha multi-API agregácia štatistík...</p>';
        const res = await fetch('/api/analyza');
        const data = await res.json();
        let html = '';
        data.forEach(m => {
            html += `
                <div class="analysis-card">
                    <div style="display:flex; justify-content:space-between">
                        <h2 style="margin:0">${m.domaci} vs ${m.hostia}</h2>
                        <span style="color:var(--primary); font-size:22px; font-weight:bold">${m.kurz}</span>
                    </div>
                    <div style="display:flex; gap:10px; margin:10px 0">
                        <span class="badge">Pozícia: ${m.stats.pos_h} vs ${m.stats.pos_a}</span>
                        <span class="badge">Forma: ${m.stats.form_h}</span>
                    </div>
                    <p style="font-style:italic; color:#fff; margin:15px 0;">"${m.analyza_text}"</p>
                    <ul style="color:#aaa; font-size:14px; padding-left:20px">
                        ${m.analyza_body.map(p => `<li>${p}</li>`).join('')}
                    </ul>
                    <div class="tip-box">
                        <b>ODPORÚČANÝ TIP: ${m.tip}</b>
                        <span style="color:var(--primary)">Dôvera ${m.dovera}%</span>
                    </div>
                </div>`;
        });
        div.innerHTML = html || 'Dnes nie sú dostupné žiadne zápasy v Premier League.';
    }

    async function loadDailyTicket() {
        const div = document.getElementById('daily-ticket-container');
        div.innerHTML = 'Vyberám zápasy s najlepším pomerom rizika a zisku...';
        const res = await fetch('/api/tiket-dna');
        const data = await res.json();
        let rows = ''; let total = 1;
        data.forEach(m => {
            total *= m.kurz;
            rows += `<div style="display:flex; justify-content:space-between; padding:12px 0; border-bottom:1px dashed #333">
                        <span>${m.domaci} (${m.tip})</span>
                        <b style="color:var(--primary)">${m.kurz}</b>
                     </div>`;
        });
        div.innerHTML = `<div class="analysis-card" style="border:2px solid var(--primary)">
            <h2 style="text-align:center; color:var(--primary); margin-top:0">VIP TIKET DŇA</h2>
            ${rows}
            <div style="display:flex; justify-content:space-between; margin-top:20px; font-size:24px; font-weight:bold">
                <span>CELKOVÝ KURZ</span><span style="color:var(--primary)">${total.toFixed(2)}</span>
            </div>
            <button class="btn-bet" onclick="placeBet(${total.toFixed(2)})">VSAĎIŤ €50</button>
        </div>`;
    }

    function placeBet(odds) {
        if (bankroll < 50) return alert("Prázdne konto!");
        bankroll -= 50;
        localStorage.setItem('bp_bank', bankroll);
        document.getElementById('ui-bank').innerText = '€' + bankroll.toFixed(2);
        alert("Tiket úspešne podaný.");
    }

    const ctx = document.getElementById('profitChart').getContext('2d');
    new Chart(ctx, { type: 'line', data: { labels: ['Po','Ut','St','Št','Pi','So','Ne'], datasets: [{ label: 'Profit %', data: [0, 8, 3, 12, 18, 15, 22], borderColor: '#66fcf1', tension: 0.4 }] }, options: { plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#1f2833' } }, x: { display: false } } } });
</script>
</body>
</html>
"""
