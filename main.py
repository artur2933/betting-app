import requests, random, time, os, json
from datetime import datetime
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from google import genai

app = FastAPI()

# --- KONFIGURÁCIA ---
ODDS_API_KEY = "3e42c726ab364fb9eeede03b0017964c"    
GEMINI_API_KEY = "AIzaSyCreRpXTUwxzJegxQKUJ2RiX5BwSagdljg"
FOOTBALL_DATA_KEY = "dad8c8fcd0a146c394fb2d53faab818a" 

LEAGUE_MAP = {
    "PL": {"odds": "soccer_epl", "name": "Premier League"},
    "PD": {"odds": "soccer_spain_la_liga", "name": "La Liga"},
    "BL1": {"odds": "soccer_germany_bundesliga", "name": "Bundesliga"},
    "SA": {"odds": "soccer_italy_serie_a", "name": "Serie A"}
}

STORAGE = {"standings": {}, "matches": {}, "last_update": 0}

client = None
if GEMINI_API_KEY:
    try: client = genai.Client(api_key=GEMINI_API_KEY)
    except: pass

# --- LOGIKA DÁT ---
def get_standings(league):
    now = time.time()
    if league in STORAGE["standings"] and (now - STORAGE["last_update"]) < 21600:
        return STORAGE["standings"][league]
    try:
        url = f"https://api.football-data.org/v4/competitions/{league}/standings"
        headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
        resp = requests.get(url, headers=headers, timeout=10).json()
        table = {}
        if 'standings' in resp:
            total = resp['standings'][0]['table']
            home_t = {x['team']['id']: x for x in resp['standings'][1]['table']}
            away_t = {x['team']['id']: x for x in resp['standings'][2]['table']}
            for team in total:
                t_id = team['team']['id']
                name = team['team']['shortName'] or team['team']['name']
                table[name] = {
                    "pos": team['position'], "form": team.get('form', 'N/A'), "pts": team['points'],
                    "h_rank": home_t.get(t_id, {}).get('position', '?'),
                    "a_rank": away_t.get(t_id, {}).get('position', '?'),
                    "goals": round(team['goalsFor'] / (team['playedGames'] or 1), 2)
                }
            STORAGE["standings"][league] = table
            STORAGE["last_update"] = now
        return table
    except: return STORAGE["standings"].get(league, {})

def match_team(name, standings):
    if not standings: return {"pos": "?", "form": "N/A", "pts": 0, "h_rank": "?", "a_rank": "?", "goals": 0}
    clean = name.lower().replace("fc", "").replace("united", "").strip()
    for s_name, data in standings.items():
        if s_name.lower().replace("fc", "").replace("united", "").strip() in clean or clean in s_name.lower():
            return data
    return {"pos": "?", "form": "N/A", "pts": 0, "h_rank": "?", "a_rank": "?", "goals": 0}

@app.get("/api/analysis")
def get_analysis(league: str = "PL"):
    standings = get_standings(league)
    url = f"https://api.the-odds-api.com/v4/sports/{LEAGUE_MAP[league]['odds']}/odds/?regions=eu&markets=h2h,totals&apiKey={ODDS_API_KEY}"
    resp = requests.get(url).json()
    results = []
    if isinstance(resp, list):
        for item in resp[:12]:
            h, a = item['home_team'], item['away_team']
            h_s, a_s = match_team(h, standings), match_team(a, standings)
            bookies = item.get('bookmakers', [])
            if not bookies: continue
            o1, ox, o2, o25 = 2.0, 3.2, 2.0, 1.85
            for m in bookies[0].get('markets', []):
                if m['key'] == 'h2h':
                    o1 = next((x['price'] for x in m['outcomes'] if x['name'] == h), 2.0)
                    ox = next((x['price'] for x in m['outcomes'] if x['name'] == 'Draw'), 3.2)
                    o2 = next((x['price'] for x in m['outcomes'] if x['name'] == a), 2.0)
                if m['key'] == 'totals':
                    o25 = next((x['price'] for x in m['outcomes'] if x['name'] == 'Over' and x['point'] == 2.5), 1.85)
            
            total_p = (1/o1) + (1/ox) + (1/o2)
            p1, px, p2 = round(((1/o1)/total_p)*100), round(((1/ox)/total_p)*100), round(((1/o2)/total_p)*100)
            
            ai_text = "Analýza nedostupná."
            if client:
                try:
                    p = f"Analyzuj: {h} (Doma Rank: {h_s['h_rank']}) vs {a} (Vonku Rank: {a_s['a_rank']}). Kurzy {o1}-{ox}-{o2}. Napíš 1 vetu analýzy v SK."
                    res = client.models.generate_content(model="gemini-2.0-flash", contents=p)
                    ai_text = res.text
                except: pass
            
            results.append({"h": h, "a": a, "o1": o1, "ox": ox, "o2": o2, "o25": o25, "p1": p1, "px": px, "p2": p2, "h_s": h_s, "a_s": a_s, "ai": ai_text})
    return results

@app.get("/api/tiket-dna")
def daily():
    standings = get_standings("PL")
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?regions=eu&markets=h2h&apiKey={ODDS_API_KEY}"
    resp = requests.get(url).json()
    return sorted(resp[:10], key=lambda x: x['bookmakers'][0]['markets'][0]['outcomes'][0]['price'])[:3] if isinstance(resp, list) else []

@app.get("/api/generate")
def gen(risk: str = "low"):
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?regions=eu&markets=h2h&apiKey={ODDS_API_KEY}"
    resp = requests.get(url).json()
    if not isinstance(resp, list): return []
    if risk == "low": f = [m for m in resp if m['bookmakers'][0]['markets'][0]['outcomes'][0]['price'] < 1.6]
    else: f = [m for m in resp if m['bookmakers'][0]['markets'][0]['outcomes'][0]['price'] >= 1.6]
    return random.sample(f, min(len(f), 3)) if f else resp[:2]

# --- UI (BLUE CYBERPUNK) ---
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Bet PRO AI</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg: #050a10; --card: #0d121b; --primary: #66fcf1; --text: #c5c6c7; --win: #00ff88; --loss: #ff4444; --border: #1f2833; }
        body { background: var(--bg); color: var(--text); font-family: 'Rajdhani', sans-serif; margin: 0; display: flex; height: 100vh; overflow: hidden; }
        .sidebar { width: 240px; background: #0b0c10; border-right: 1px solid var(--border); padding: 20px; display: flex; flex-direction: column; }
        .main { flex: 1; padding: 20px; overflow-y: auto; padding-bottom: 90px; background: radial-gradient(circle at top right, #141b24 0%, #050a10 100%); }
        .menu-item { padding: 12px; cursor: pointer; color: #666; border-radius: 8px; margin-bottom: 5px; display: flex; align-items: center; gap: 10px; }
        .menu-item.active { background: #1a222d; color: #fff; border-left: 3px solid var(--primary); }
        .mobile-nav { display: none; position: fixed; bottom: 0; width: 100%; background: #0b0c10; border-top: 1px solid var(--border); justify-content: space-around; padding: 10px 0; z-index: 100; }
        .nav-icon { display: flex; flex-direction: column; align-items: center; font-size: 10px; color: #555; }
        .nav-icon.active { color: var(--primary); }
        .tab-s { overflow-x: auto; display: flex; gap: 8px; margin-bottom: 15px; }
        .tab { white-space: nowrap; background: #141b24; border: 1px solid var(--border); padding: 8px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; }
        .tab.active { background: var(--primary); color: #000; font-weight: bold; }
        .m-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 15px; margin-bottom: 10px; cursor: pointer; }
        .m-card.open { border-color: var(--primary); }
        .summary { display: flex; justify-content: space-between; font-size: 13px; }
        .details { display: none; margin-top: 15px; border-top: 1px solid #1f2833; padding-top: 10px; }
        .m-card.open .details { display: block; }
        .stats-v { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .team-b { background: #050a10; padding: 8px; border-radius: 6px; font-size: 12px; }
        .p-bar { display: flex; height: 5px; border-radius: 5px; overflow: hidden; background: #333; margin: 8px 0; }
        .p1 { background: var(--win); } .px { background: #555; } .p2 { background: var(--loss); }
        .ai-v { background: rgba(102,252,241,0.05); border-left: 2px solid var(--primary); padding: 10px; margin-top: 10px; font-size: 12px; font-style: italic; }
        .btn-m { background: var(--primary); color: #000; border: none; padding: 12px; border-radius: 30px; font-weight: bold; width: 100%; margin-top: 10px; cursor: pointer; }
        .page { display: none; } .page.active { display: block; }
        @media (max-width: 768px) { .sidebar { display: none; } .mobile-nav { display: flex; } }
    </style>
</head>
<body>
<div class="sidebar">
    <div style="color:var(--primary); font-size:22px; font-weight:bold; margin-bottom:30px; text-align:center;">⚡ BET PRO</div>
    <div class="menu-item active" onclick="show('home', this)">🏠 Domov</div>
    <div class="menu-item" onclick="show('vip', this); loadVip('PL')">📊 VIP Analýza</div>
    <div class="menu-item" onclick="show('ticket', this); loadDaily()">🎯 Tiket Dňa</div>
    <div class="menu-item" onclick="show('gen', this)">🛠️ Generátor</div>
</div>
<div class="main">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;"><h2 id="title">Dashboard</h2><b>€<span id="bank">1000.00</span></b></div>
    <div id="home" class="page active"><canvas id="chart" height="150"></canvas></div>
    <div id="vip" class="page">
        <div class="tab-s">
            <div class="tab active" onclick="setL('PL', this)">Premier League</div>
            <div class="tab" onclick="setL('PD', this)">La Liga</div>
            <div class="tab" onclick="setL('BL1', this)">Bundesliga</div>
        </div>
        <div id="vip-out">Vyberte ligu...</div>
    </div>
    <div id="ticket" class="page"><div id="ticket-out"></div></div>
    <div id="gen" class="page">
        <select id="g-risk" style="width:100%; padding:10px; background:#141b24; color:#fff; border-radius:8px; border:1px solid var(--border);"><option value="low">Nízke riziko</option><option value="high">Vysoké riziko</option></select>
        <button class="btn-m" onclick="loadGen()">Vygenerovať stratégiu</button>
        <div id="gen-out" style="margin-top:15px;"></div>
    </div>
    <div id="history" class="page"><div id="hist-out">Žiadna história.</div></div>
</div>
<div class="mobile-nav">
    <div class="nav-icon active" onclick="show('home', this)">🏠<span>Domov</span></div>
    <div class="nav-icon" onclick="show('vip', this); loadVip('PL')">📊<span>Analýzy</span></div>
    <div class="nav-icon" onclick="show('ticket', this); loadDaily()">🎯<span>Tiket</span></div>
    <div class="nav-icon" onclick="show('history', this)">✅<span>História</span></div>
</div>
<script>
let bank = 1000.00;
function show(id, el) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.menu-item, .nav-icon').forEach(m => m.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    if(el) el.classList.add('active');
    document.getElementById('title').innerText = id.toUpperCase();
}
function setL(c, el) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    el.classList.add('active'); loadVip(c);
}
async function loadVip(l) {
    const div = document.getElementById('vip-out'); div.innerHTML = 'Načítavam...';
    const res = await fetch(`/api/analysis?league=${l}`); const data = await res.json();
    let html = '';
    data.forEach(m => {
        html += `<div class="m-card" onclick="this.classList.toggle('open')">
            <div class="summary"><b>${m.h} - ${m.a}</b><span>${m.o1.toFixed(2)} | ${m.ox.toFixed(2)} | ${m.o2.toFixed(2)}</span></div>
            <div class="details">
                <div class="stats-v">
                    <div class="team-b"><b>${m.h}</b><br>Rank: #${m.h_s.pos}<br>Doma: #${m.h_s.h_rank}<br>Góly: ${m.h_s.goals}</div>
                    <div class="team-b"><b>${m.a}</b><br>Rank: #${m.a_s.pos}<br>Vonku: #${m.a_s.a_rank}<br>Góly: ${m.a_s.goals}</div>
                </div>
                <div class="p-bar"><div class="p1" style="width:${m.p1}%"></div><div class="px" style="width:${m.px}%"></div><div class="p2" style="width:${m.p2}%"></div></div>
                <div class="ai-v"><p>"${m.ai}"</p></div>
            </div>
        </div>`;
    });
    div.innerHTML = html || 'Žiadne zápasy.';
}
async function loadDaily() {
    const div = document.getElementById('ticket-out'); div.innerHTML = 'Generujem...';
    const res = await fetch('/api/tiket-dna'); const data = await res.json();
    let rows = ''; let total = 1;
    data.forEach(m => {
        let o = m.bookmakers[0].markets[0].outcomes[0].price; total *= o;
        rows += `<div style="display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px dashed #333"><span>${m.home_team}</span><b>${o.toFixed(2)}</b></div>`;
    });
    div.innerHTML = `<div style="background:var(--card); padding:15px; border-radius:10px; border:1px solid var(--primary);"><h4>TIKET DŇA</h4>${rows}<h3 style="text-align:right">KURZ: ${total.toFixed(2)}</h3><button class="btn-m" onclick="bet(${total})">VSAĎIŤ €50</button></div>`;
}
async function loadGen() {
    const div = document.getElementById('gen-out'); div.innerHTML = 'Počítam...';
    const res = await fetch(`/api/generate?risk=${document.getElementById('g-risk').value}`); const data = await res.json();
    let rows = ''; let total = 1;
    data.forEach(m => {
        let o = m.bookmakers[0].markets[0].outcomes[0].price; total *= o;
        rows += `<div style="display:flex; justify-content:space-between; padding:5px 0;"><span>${m.home_team}</span><b>${o.toFixed(2)}</b></div>`;
    });
    div.innerHTML = `<div style="background:var(--card); padding:15px; border-radius:10px; border:1px solid var(--border);"><h4>VÁŠ TIKET</h4>${rows}<h3 style="text-align:right">${total.toFixed(2)}</h3><button class="btn-m" onclick="bet(${total})">VSAĎIŤ €50</button></div>`;
}
function bet(o) { if(bank < 50) return alert("Málo peňazí!"); bank -= 50; document.getElementById('bank').innerText = bank.toFixed(2); alert("Vsadili ste na tiket!"); }
const ctx = document.getElementById('chart').getContext('2d');
new Chart(ctx, { type: 'line', data: { labels: ['P','U','S','Š','P','S','N'], datasets: [{ label: 'Profit', data: [1000, 1080, 1040, 1150, 1290, 1250, 1452], borderColor: '#66fcf1', tension: 0.4 }] }, options: { plugins: { legend: { display: false } }, scales: { y: { display: false }, x: { grid: { display: false } } } } });
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home(): return html_content

