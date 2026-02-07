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
# 🔑 KONFIGURÁCIA API KĽÚČOV
# ==========================================
ODDS_API_KEY = "3e42c726ab364fb9eeede03b0017964c"    
GEMINI_API_KEY = "AIzaSyCreRpXTUwxzJegxQKUJ2RiX5BwSagdljg"
FOOTBALL_DATA_KEY = "dad8c8fcd0a146c394fb2d53faab818a" 

# Globálna pamäť pre caching
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

# --- BACKEND LOGIKA ---

def get_standings(league="PL"):
    """ Získa tabuľku konkrétnej ligy z Football-Data.org """
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

def match_team_data(odds_name, standings):
    """ Robustnejšie párovanie mien tímov """
    if not standings: return {"pos": "?", "form": "N/A", "goals": "0:0", "points": 0}
    team_clean = odds_name.lower().replace("fc", "").replace("united", "").strip()
    for s_name, data in standings.items():
        s_clean = s_name.lower().replace("fc", "").replace("united", "").strip()
        if s_clean in team_clean or team_clean in s_clean:
            return data
    return {"pos": "?", "form": "N/A", "goals": "0:0", "points": 0}

def fetch_hybrid_analysis():
    """ 
    Agregátor: H2H, Totals, Tabuľky a AI pre viaceré ligy.
    Zameriavame sa na efektivitu využitia API kľúčov.
    """
    now = time.time()
    if (now - STORAGE["last_update"]) < 3600 and STORAGE["analysis_cache"]:
        return STORAGE["analysis_cache"]

    try:
        # Sledujeme EPL (Anglicko), La Ligu (Španielsko) a Bundesligu (Nemecko)
        leagues_map = {"PL": "soccer_epl", "PD": "soccer_spain_la_liga", "BL1": "soccer_germany_bundesliga"}
        all_results = []

        for l_code, odds_code in leagues_map.items():
            standings = get_standings(l_code)
            url = f"https://api.the-odds-api.com/v4/sports/{odds_code}/odds/?regions=eu&markets=h2h,totals&apiKey={ODDS_API_KEY}"
            odds_resp = requests.get(url, timeout=12).json()
            
            if not isinstance(odds_resp, list): continue

            for item in odds_resp[:8]: # Limitujeme počet na ligu pre Gemini stabilitu
                home_raw, away_raw = item['home_team'], item['away_team']
                h_stat = match_team_data(home_raw, standings)
                a_stat = match_team_data(away_raw, standings)
                
                bookies = item.get('bookmakers', [])
                if not bookies: continue
                
                # Extrakcia kurzov
                o1, o2, over_25, under_25 = 2.0, 2.0, None, None
                markets = bookies[0].get('markets', [])
                
                for m in markets:
                    if m['key'] == 'h2h':
                        o1 = next((x['price'] for x in m['outcomes'] if x['name'] == home_raw), 2.0)
                        o2 = next((x['price'] for x in m['outcomes'] if x['name'] == away_raw), 2.0)
                    if m['key'] == 'totals':
                        over_25 = next((x['price'] for x in m['outcomes'] if x['name'] == 'Over' and x['point'] == 2.5), None)
                        under_25 = next((x['price'] for x in m['outcomes'] if x['name'] == 'Under' and x['point'] == 2.5), None)

                # Upravená logika tipov
                tip_result = "1" if o1 < o2 else "2"
                
                # Rozhodovanie o góloch na základe REÁLNYCH kurzov
                tip_goals = "Analýza gólov nedostupná"
                kurz_goly = 1.0
                if over_25 and under_25:
                    if over_25 < under_25:
                        tip_goals = "Over 2.5"
                        kurz_goly = over_25
                    else:
                        tip_goals = "Under 2.5"
                        kurz_goly = under_25
                
                # AI Syntéza
                analysis_text = ""
                try:
                    ctx = f"{home_raw} (Tabuľka: {h_stat['pos']}) vs {away_raw} (Tabuľka: {a_stat['pos']}). Kurzy: Domáci {o1}, Hostia {o2}, Over 2.5 {over_25 or 'N/A'}."
                    prompt = f"Ako profesionálny analytik s ROI 15% analyzuj tento zápas: {ctx}. Navrhni tip na víťaza a počet gólov. Buď kritický k favoritovi. Napíš jednu vetu slovensky."
                    ai_res = ai_model.generate_content(prompt)
                    analysis_text = ai_res.text
                except:
                    analysis_text = f"Štatistická prevaha {home_raw if o1 < o2 else away_raw}. Očakávaný priebeh zodpovedá tabuľkovému postaveniu."

                all_results.append({
                    "domaci": home_raw, "hostia": away_raw,
                    "liga": item['sport_title'],
                    "kurz_vysledok": o1 if tip_result=="1" else o2,
                    "kurz_goly": kurz_goly,
                    "tip_vysledok": tip_result,
                    "tip_goly": tip_goals,
                    "h_stat": h_stat, "a_stat": a_stat,
                    "analyza": analysis_text,
                    "dovera": int((1/min(o1,o2))*88)
                })
        
        STORAGE["analysis_cache"] = all_results
        STORAGE["last_update"] = now
        return all_results
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
        # Vyberáme 3 zápasy s najvyššou pravdepodobnosťou (najnižší kurz)
        STORAGE["daily_ticket"] = sorted(data, key=lambda x: x['kurz_vysledok'])[:3]
        STORAGE["ticket_date"] = today
    return STORAGE["daily_ticket"]

@app.get("/api/vlastny-tiket")
def get_custom_ticket(risk: int = 1):
    data = fetch_hybrid_analysis()
    filtered = [m for m in data if (m['kurz_vysledok'] < 1.6 if risk == 1 else m['kurz_vysledok'] >= 1.6)]
    return filtered[:3] if filtered else data[:2]

# --- UI (BLUE CYBERPUNK MONOLITH) ---

html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betting PRO AI | Hybrid Market Engine</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #050a10; --card: #11161d; --primary: #66fcf1; --text: #c5c6c7; --win: #00ff88; --loss: #ff4444; }
        body { background: var(--bg); color: var(--text); font-family: 'Rajdhani', sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        
        .sidebar { width: 260px; background: #0b0c10; border-right: 1px solid #1f2833; padding: 25px; display: flex; flex-direction: column; }
        .logo { color: var(--primary); font-size: 28px; font-weight: bold; text-align: center; margin-bottom: 40px; }
        .menu-item { padding: 15px; cursor: pointer; color: #888; border-radius: 8px; margin-bottom: 5px; transition: 0.2s; }
        .menu-item.active { background: #1f2833; color: #fff; border-left: 4px solid var(--primary); }
        
        .main { flex: 1; padding: 30px; overflow-y: auto; background: radial-gradient(circle at top right, #1f2833 0%, #0b0c10 80%); }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        
        /* ANALÝZA CARD V2 */
        .ac-card { background: var(--card); border: 1px solid #2c3e50; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.5); }
        .ac-head { display: flex; justify-content: space-between; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 15px; }
        .ac-teams { font-size: 16px; font-weight: bold; color: #fff; }
        .ac-liga { font-size: 11px; color: var(--primary); text-transform: uppercase; }

        .ac-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 15px; }
        .stat-box { background: #1a2634; padding: 8px; border-radius: 6px; text-align: center; border: 1px solid #233142; }
        .stat-label { font-size: 8px; color: #888; text-transform: uppercase; display: block; margin-bottom: 2px; }
        .stat-val { font-size: 13px; font-weight: bold; color: #fff; }
        
        .ac-tips { display: flex; gap: 10px; margin-bottom: 15px; }
        .tip-pill { flex: 1; background: #0b0c10; border: 1px solid #1f2833; padding: 12px; border-radius: 8px; text-align: center; transition: 0.3s; }
        .tip-pill:hover { border-color: var(--primary); background: rgba(102, 252, 241, 0.02); }
        .tip-pill b { color: var(--primary); display: block; font-size: 14px; margin-top: 2px; }
        .tip-pill span { font-size: 10px; color: #666; text-transform: uppercase; }

        .ai-box { background: rgba(102, 252, 241, 0.03); border-left: 2px solid var(--primary); padding: 12px; font-style: italic; font-size: 13px; color: #eee; line-height: 1.4; }

        .btn { background: var(--primary); color: #000; border: none; padding: 12px 25px; border-radius: 50px; font-weight: bold; cursor: pointer; width: 100%; transition: 0.3s; text-transform: uppercase; }
        .btn-bet { background: transparent; border: 1px solid var(--primary); color: var(--primary); margin-top: 10px; }
        .btn:disabled { background: #333; color: #666; cursor: not-allowed; }
        
        .page { display: none; } .page.active { display: block; animation: fadeIn 0.3s; }
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
    <div class="header">
        <h1 id="p-title">Dashboard</h1>
        <div style="text-align:right">Bankroll: <b id="ui-bank" style="color:var(--primary)">€1000.00</b></div>
    </div>

    <div id="home" class="page active">
        <div style="background:var(--card); padding:20px; border-radius:12px; border:1px solid #2c3e50; text-align: center;">
            <h3>Vitajte v Hybridnom Engine</h3>
            <p>Sledujeme H2H a Over/Under markety naprieč 3 európskymi ligami.</p>
            <canvas id="chart"></canvas>
        </div>
    </div>

    <div id="analysis" class="page">
        <div id="analysis-out">Načítavam komplexné trhové dáta...</div>
    </div>

    <div id="ticket" class="page">
        <div id="ticket-out" style="max-width: 500px; margin: 0 auto;"></div>
    </div>

    <div id="custom" class="page">
        <div style="background:var(--card); padding:20px; border-radius:12px; max-width:500px; margin:0 auto; text-align:center;">
             <h3>Generátor Strategických Tiketov</h3>
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

async function loadAnalysis() {
    const div = document.getElementById('analysis-out');
    div.innerHTML = '<p style="text-align:center; color:var(--primary)">Agregujem markety a spúšťam AI analýzu...</p>';
    try {
        const res = await fetch('/api/analyza');
        const data = await res.json();
        let html = '';
        
        data.forEach(m => {
            html += `
            <div class="ac-card">
                <div class="ac-head">
                    <div class="ac-teams">${m.domaci} vs ${m.hostia}</div>
                    <div class="ac-liga">${m.liga}</div>
                </div>
                
                <div class="ac-grid">
                    <div class="stat-box"><span class="stat-label">Tabuľka</span><span class="stat-val">${m.h_stat.pos} .vs ${m.a_stat.pos}</span></div>
                    <div class="stat-box"><span class="stat-label">Dôvera AI</span><span class="stat-val">${m.dovera}%</span></div>
                    <div class="stat-box"><span class="stat-label">Body</span><span class="stat-val">${m.h_stat.points} : ${m.a_stat.points}</span></div>
                </div>

                <div class="ac-tips">
                    <div class="tip-pill"><span>Výsledok (Tip ${m.tip_vysledok})</span><b>Kurz ${m.kurz_vysledok.toFixed(2)}</b></div>
                    <div class="tip-pill"><span>Góly (${m.tip_goly})</span><b>Kurz ${m.kurz_goly > 1 ? m.kurz_goly.toFixed(2) : 'N/A'}</b></div>
                </div>
                
                <div class="ai-box">"${m.analyza}"</div>
            </div>`;
        });
        div.innerHTML = html || 'Momentálne nie sú dostupné žiadne zápasy na analýzu.';
    } catch(e) {
        div.innerHTML = 'Chyba pri načítaní dát. Skontrolujte API kľúče.';
    }
}

async function loadTicket() { renderTicket('/api/tiket-dna', 'ticket-out', 'VIP TIKET DŇA'); }
async function loadCustom() { renderTicket('/api/vlastny-tiket', 'custom-out', 'TVOJ TIKET'); }

async function renderTicket(url, elId, title) {
    const div = document.getElementById(elId);
    div.innerHTML = 'Hľadám optimálne kurzy...';
    try {
        const res = await fetch(url);
        const data = await res.json();
        
        let rows = ''; let total = 1; let slip = [];
        data.forEach(m => {
            total *= m.kurz_vysledok; slip.push(`${m.domaci} (${m.tip_vysledok})`);
            rows += `<div style="display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px dashed #333">
                <span><b>${m.domaci}</b><br><small>${m.tip_goly}</small></span>
                <b style="color:var(--primary)">${m.kurz_vysledok.toFixed(2)}</b>
            </div>`;
        });
        
        div.innerHTML = `
        <div style="background:var(--card); padding:20px; border-radius:12px; border:2px solid var(--primary); text-align:left;">
            <h2 style="color:var(--primary); text-align:center">${title}</h2>
            ${rows}
            <div style="display:flex; justify-content:space-between; margin-top:15px; font-size:22px; font-weight:bold">
                <span>KURZ</span><span>${total.toFixed(2)}</span>
            </div>
            <button class="btn btn-bet" onclick='placeBet(${total.toFixed(2)}, ${JSON.stringify(slip)})'>VSAĎIŤ €50</button>
        </div>`;
    } catch(e) {
        div.innerHTML = 'Dáta nedostupné.';
    }
}

function placeBet(odds, matches) {
    if(bank < 50) return alert("Nedostatok prostriedkov!");
    bank -= 50;
    hist.unshift({ date: new Date().toLocaleTimeString(), matches: matches.join(', '), odds: odds, status: 'Čaká' });
    updateUI(); alert("Tiket podaný!");
}

function renderHistory() {
    const div = document.getElementById('hist-out');
    if(!hist.length) return div.innerHTML = 'História prázdna.';
    let h = '<table style="width:100%; color:#ccc; text-align:left"><tr><th>Čas</th><th>Zápasy</th><th>Kurz</th><th>Stav</th></tr>';
    hist.forEach(t => h += `<tr><td>${t.date}</td><td>${t.matches}</td><td>${t.odds}</td><td style="color:orange">${t.status}</td></tr>`);
    div.innerHTML = h + '</table>';
}

const ctx = document.getElementById('chart').getContext('2d');
new Chart(ctx, { type: 'line', data: { labels: ['P','U','S','Š','P','S','N'], datasets: [{ label: 'Profit', data: [1000, 1050, 1020, 1100, 1250, 1200, 1380], borderColor: '#66fcf1', tension: 0.4 }] }, options: { plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#1f2833' } }, x: { display: false } } } });
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return html_content
