from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend import models, crud, database, ai 
from pydantic import BaseModel
import random

# 1. Inicializácia databázy
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

# --- MOCK DATABÁZA (Aby ti fungovalo generovanie tiketov) ---
MATCH_DATABASE = [
    # TUTOVKY (Riziko 1)
    {"domaci": "Man City", "hostia": "Sheffield", "kurz": 1.18, "tip": "1", "risk": 1, "liga": "Premier League", "stats": {"utok_domaci": 88, "utok_hostia": 20, "zranenia": "Žiadne"}},
    {"domaci": "Real Madrid", "hostia": "Almeria", "kurz": 1.25, "tip": "1", "risk": 1, "liga": "La Liga", "stats": {"utok_domaci": 85, "utok_hostia": 30, "zranenia": "Alaba (Out)"}},
    {"domaci": "Bayern", "hostia": "Mainz", "kurz": 1.30, "tip": "1 + Over 1.5", "risk": 1, "liga": "Bundesliga", "stats": {"utok_domaci": 90, "utok_hostia": 40, "zranenia": "Coman (Quest)"}},
    {"domaci": "Inter", "hostia": "Salernitana", "kurz": 1.28, "tip": "1", "risk": 1, "liga": "Serie A", "stats": {"utok_domaci": 82, "utok_hostia": 25, "zranenia": "Martinez (Fit)"}},

    # STREDNÉ RIZIKO (Riziko 2)
    {"domaci": "Arsenal", "hostia": "Chelsea", "kurz": 1.95, "tip": "1", "risk": 2, "liga": "Premier League", "stats": {"utok_domaci": 75, "utok_hostia": 65, "zranenia": "Saka (Fit)"}},
    {"domaci": "Sevilla", "hostia": "Betis", "kurz": 2.10, "tip": "X (Remíza)", "risk": 2, "liga": "La Liga", "stats": {"utok_domaci": 55, "utok_hostia": 55, "zranenia": "Navas (Out)"}},
    {"domaci": "Dortmund", "hostia": "Leipzig", "kurz": 2.05, "tip": "BTTS", "risk": 2, "liga": "Bundesliga", "stats": {"utok_domaci": 80, "utok_hostia": 82, "zranenia": "Reus (Bench)"}},
    {"domaci": "Man Utd", "hostia": "PAOK", "kurz": 1.45, "tip": "1", "risk": 2, "liga": "Europa League", "stats": {"utok_domaci": 82, "utok_hostia": 40, "zranenia": "Maguire (Out)"}},

    # VYSOKÉ RIZIKO (Riziko 3)
    {"domaci": "Luton", "hostia": "Liverpool", "kurz": 6.50, "tip": "1X", "risk": 3, "liga": "Premier League", "stats": {"utok_domaci": 40, "utok_hostia": 85, "zranenia": "Salah (Out)"}},
    {"domaci": "Monza", "hostia": "Juventus", "kurz": 3.40, "tip": "1", "risk": 3, "liga": "Serie A", "stats": {"utok_domaci": 45, "utok_hostia": 70, "zranenia": "Chiesa (Out)"}},
]

# 2. HTML GRAFIKA - MODRÁ CYBERPUNK (Rozšírená o tikety)
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betting PRO Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <style>
        body { margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0c10; color: #c5c6c7; display: flex; height: 100vh; overflow: hidden; }
        
        /* Sidebar */
        .sidebar { width: 260px; background-color: #111; display: flex; flex-direction: column; padding: 25px; border-right: 1px solid #333; }
        .logo { font-size: 22px; font-weight: 800; color: #66fcf1; margin-bottom: 30px; text-transform: uppercase; letter-spacing: 3px; text-align: center; border-bottom: 2px solid #66fcf1; padding-bottom: 20px;}
        
        .menu-label { font-size: 11px; text-transform: uppercase; color: #666; margin-top: 20px; margin-bottom: 10px; letter-spacing: 1px; font-weight: bold; }
        .menu-item { padding: 15px; margin-bottom: 5px; cursor: pointer; border-radius: 8px; color: #888; font-weight: 600; transition: 0.3s; display: flex; align-items: center; gap: 15px; }
        .menu-item:hover, .menu-item.active { background-color: #1a1a1a; color: #fff; border-left: 4px solid #66fcf1; }
        
        /* Main Content */
        .main-content { flex: 1; padding: 40px; overflow-y: auto; background: #0b0c10; }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }
        .header h1 { margin: 0; color: #fff; font-size: 28px; font-weight: 700; }
        
        /* Tlačidlo */
        .btn-analyze { 
            background: #66fcf1; border: none; padding: 18px 50px; 
            font-size: 18px; font-weight: 800; color: #0b0c10; border-radius: 50px; cursor: pointer; 
            box-shadow: 0 0 25px rgba(102, 252, 241, 0.4); transition: transform 0.2s;
            display: block; margin: 0 auto 40px auto; letter-spacing: 1px;
        }
        .btn-analyze:hover { transform: scale(1.05); background: #fff; }

        /* KARTA ZÁPASU (Pôvodná Analysis) */
        .match-card { 
            background: #151b24; border-radius: 16px; margin-bottom: 30px; overflow: hidden; 
            border: 1px solid #2c3e50; box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            animation: slideUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1);
        }
        
        .match-header { 
            background: linear-gradient(90deg, #0f141a 0%, #1a222e 100%); 
            padding: 25px 30px; display: flex; justify-content: space-between; align-items: center; 
            border-bottom: 1px solid #2c3e50;
        }
        .teams-title { font-size: 32px; font-weight: 800; color: white; letter-spacing: 1px; text-shadow: 0 0 20px rgba(0,0,0,0.5); }
        .match-meta { font-size: 16px; color: #66fcf1; font-weight: bold; background: rgba(102, 252, 241, 0.1); padding: 8px 18px; border-radius: 20px;}
        .match-body { padding: 30px; display: flex; gap: 40px; flex-wrap: wrap; }
        .col-left { flex: 1; min-width: 300px; border-right: 1px solid #2c3e50; padding-right: 30px; }
        .col-right { flex: 1; min-width: 300px; }
        .form-box { display: flex; gap: 5px; margin-top: 5px; }
        .form-badge { width: 25px; height: 25px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; color: black; }
        .win { background: #2ecc71; } .draw { background: #f1c40f; } .loss { background: #e74c3c; }
        .stat-group { margin-bottom: 20px; }
        .stat-label { display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 5px; color: #888; }
        .progress-bg { height: 8px; background: #222; border-radius: 4px; overflow: hidden; }
        .progress-fill { height: 100%; background: #66fcf1; border-radius: 4px; }
        .analysis-section h4 { color: #66fcf1; margin: 0 0 15px 0; text-transform: uppercase; font-size: 14px; letter-spacing: 1px; }
        .analysis-text { font-size: 15px; line-height: 1.6; color: #dcdcdc; }
        .ai-box { background: rgba(102, 252, 241, 0.05); padding: 20px; border-radius: 12px; border: 1px solid rgba(102, 252, 241, 0.2); display: flex; align-items: center; justify-content: space-between; margin-top: 20px; }
        .ai-tip { font-size: 24px; font-weight: 800; color: #fff; }
        .ai-confidence { background: #66fcf1; color: #000; padding: 5px 15px; border-radius: 5px; font-weight: bold; }

        /* --- NOVÉ PRVKY PRE TIKETY (Style match with Cyberpunk Blue) --- */
        
        /* Ticket Slip Design */
        .ticket-wrapper {
            max-width: 600px; margin: 0 auto;
            background: #151b24; border: 2px solid #66fcf1; border-radius: 12px;
            box-shadow: 0 0 40px rgba(102, 252, 241, 0.15); overflow: hidden;
            animation: slideUp 0.5s ease;
        }
        .ticket-header { background: rgba(102, 252, 241, 0.1); padding: 20px; text-align: center; border-bottom: 1px solid #66fcf1; }
        .ticket-title { font-size: 24px; font-weight: 800; color: #66fcf1; letter-spacing: 2px; margin: 0; }
        .ticket-body { padding: 20px; }
        .ticket-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #333; padding: 15px 0; }
        .ticket-row:last-child { border-bottom: none; }
        .t-match { font-size: 16px; font-weight: bold; color: #fff; }
        .t-tip { font-size: 13px; color: #888; margin-top: 4px; }
        .t-odds { background: #0b0c10; color: #66fcf1; padding: 5px 10px; border-radius: 4px; border: 1px solid #333; font-weight: bold; }
        .ticket-footer { background: #0b0c10; padding: 20px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #333; }
        .t-total { font-size: 22px; font-weight: bold; color: #fff; }
        .t-val { color: #66fcf1; font-weight: 900; font-size: 28px; }

        /* Custom Generator Inputs */
        .gen-controls { max-width: 700px; margin: 0 auto; background: #151b24; padding: 30px; border-radius: 12px; border: 1px solid #333; }
        .control-row { margin-bottom: 20px; }
        .c-label { display: block; color: #66fcf1; font-size: 12px; font-weight: bold; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }
        select { width: 100%; padding: 15px; background: #0b0c10; border: 1px solid #333; color: #fff; border-radius: 8px; font-size: 16px; outline: none; transition: 0.3s; }
        select:focus { border-color: #66fcf1; box-shadow: 0 0 10px rgba(102, 252, 241, 0.2); }

        .page { display: none; }
        .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

        .chart-box { background: #151b24; padding: 25px; border-radius: 16px; border: 1px solid #2c3e50; height: 350px; }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="logo">⚡ BET PRO</div>
        
        <div class="menu-label">Hlavné</div>
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="showPage('generator', this)">📊 VIP Analýza</div>
        
        <div class="menu-label">Tikety</div>
        <div class="menu-item" onclick="loadTiketDna(this)">🎯 Tiket Dňa</div>
        <div class="menu-item" onclick="showPage('custom-ticket', this)">🛠️ Vlastný Generátor</div>
        
        <div class="menu-label">Dáta</div>
        <div class="menu-item" onclick="showPage('results-page', this)">✅ Výsledky</div>
    </div>

    <div class="main-content">
        
        <div id="home" class="page active">
            <div class="header"><h1>Vitaj späť, Trader.</h1></div>
            
            <div style="display:flex; gap:20px; margin-bottom: 30px;">
                <div style="background:#151b24; padding:25px; flex:1; border-radius:16px; border:1px solid #2c3e50;">
                    <h3 style="color:#888; font-size:14px; margin-top:0;">DNEŠNÝ POTENCIÁL</h3>
                    <h1 style="color:#fff; font-size:36px; margin:10px 0;">3 Zápasy</h1>
                    <small style="color:#66fcf1">AI našla vysokú hodnotu (Value)</small>
                </div>
                <div style="background:#151b24; padding:25px; flex:1; border-radius:16px; border:1px solid #2c3e50;">
                    <h3 style="color:#888; font-size:14px; margin-top:0;">BANKROLL (Simulácia)</h3>
                    <h1 style="color:#fff; font-size:36px; margin:10px 0;">€2,450.00</h1>
                    <small style="color:#2ecc71">▲ +12.5% tento týždeň</small>
                </div>
            </div>
            
            <div class="chart-box">
                <h3 style="color:#fff; margin-top:0;">Vývoj Zisku</h3>
                <canvas id="profitChart"></canvas>
            </div>
        </div>

        <div id="generator" class="page">
            <div class="header"><h1>Deep AI Analysis</h1></div>
            <div style="text-align:center; margin-bottom:40px;">
                <p style="color:#888; margin-bottom:20px;">Spusti hĺbkový sken zápasov. AI analyzuje formu, xG a zranenia.</p>
                <button class="btn-analyze" onclick="generujAnalyzu()">SPUSTIŤ SKENOVANIE</button>
            </div>
            <div id="analysis-output"></div>
        </div>

        <div id="ticket-day" class="page">
            <div class="header"><h1>🔥 Tiket Dňa (Tutovka)</h1></div>
            <div id="ticket-day-result" style="margin-top: 50px;"></div>
        </div>

        <div id="custom-ticket" class="page">
            <div class="header"><h1>🛠️ Vlastný Tiket</h1></div>
            
            <div class="gen-controls">
                <div class="control-row">
                    <label class="c-label">Riziko</label>
                    <select id="riskLevel">
                        <option value="1">🟢 Nízke (Kurzy 1.2 - 1.5)</option>
                        <option value="2">🟡 Stredné (Kurzy 1.8 - 2.2)</option>
                        <option value="3">🔴 Vysoké (Kurzy 3.0+)</option>
                    </select>
                </div>
                <div class="control-row">
                    <label class="c-label">Počet zápasov</label>
                    <select id="matchCount">
                        <option value="2">2 Zápasy</option>
                        <option value="3">3 Zápasy</option>
                        <option value="5">5 Zápasov</option>
                    </select>
                </div>
                <div class="control-row">
                    <label class="c-label">Liga</label>
                    <select id="leagueSelect">
                        <option value="all">Všetky Ligy</option>
                        <option value="Premier League">Premier League</option>
                        <option value="La Liga">La Liga</option>
                        <option value="Bundesliga">Bundesliga</option>
                        <option value="Serie A">Serie A</option>
                    </select>
                </div>
                <button class="btn-analyze" style="margin-bottom:0;" onclick="generujVlastny()">Vygenerovať</button>
            </div>

            <div id="custom-ticket-result" style="margin-top: 50px;"></div>
        </div>

        <div id="results-page" class="page">
            <div class="header"><h1>Výkonnosť Modelu</h1></div>
            <p>História posledných AI predikcií.</p>
            <div class="match-card">
                <div class="match-header"><div class="teams-title">Včerajší Výkon</div></div>
                <div class="match-body"><p style="color:#aaa;">Načítavam dáta...</p></div>
            </div>
        </div>

    </div>

    <script>
        // Graf (Nezmenený)
        document.addEventListener("DOMContentLoaded", function() {
            const ctx = document.getElementById('profitChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Po', 'Ut', 'St', 'Št', 'Pi', 'So', 'Ne'],
                    datasets: [{
                        label: 'Zisk', data: [2100, 2150, 2120, 2250, 2300, 2380, 2450],
                        borderColor: '#66fcf1', backgroundColor: 'rgba(102, 252, 241, 0.1)', borderWidth: 3, tension: 0.4, fill: true
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#2c3e50' }, ticks: { color: '#888' } }, x: { grid: { display: false }, ticks: { color: '#888' } } } }
            });
        });

        function showPage(id, el) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            if(el) { document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active')); el.classList.add('active'); }
            document.getElementById(id).classList.add('active');
        }

        // --- 1. VIP ANALÝZA (Pôvodná funkcia) ---
        async function generujAnalyzu() {
            const out = document.getElementById('analysis-output');
            out.innerHTML = '<p style="text-align:center; color:#66fcf1">Analyzujem...</p>';
            const res = await fetch('/api/generuj-tiket'); // Pôvodný endpoint pre analýzu
            const data = await res.json();
            
            let html = '';
            // (Tu používam skrátenú verziu tvojej karty z predchádzajúceho kódu, aby to nebolo extrémne dlhé)
            data.slice(0, 2).forEach(m => {
                html += `
                <div class="match-card">
                    <div class="match-header"><div class="teams-title">${m.domaci} vs ${m.hostia}</div></div>
                    <div class="match-body">
                        <div class="col-left">
                            <div class="stat-group"><div class="stat-label"><span>Útok</span><span>${m.stats.utok_domaci}%</span></div><div class="progress-bg"><div class="progress-fill" style="width:${m.stats.utok_domaci}%"></div></div></div>
                        </div>
                        <div class="col-right">
                            <div class="ai-box"><div>Tip: <span style="color:#fff">${m.tip}</span></div><div class="ai-confidence">${m.risk === 1 ? '90%' : '75%'}</div></div>
                        </div>
                    </div>
                </div>`;
            });
            out.innerHTML = html;
        }

        // --- 2. TIKET DŇA (Nová funkcia) ---
        async function loadTiketDna(el) {
            showPage('ticket-day', el);
            const div = document.getElementById('ticket-day-result');
            div.innerHTML = '<p style="text-align:center; color:#66fcf1">Generujem Tiket Dňa...</p>';
            
            const res = await fetch('/api/tiket-dna');
            const data = await res.json();
            renderTicket(data, div, "VIP TIKET DŇA");
        }

        // --- 3. VLASTNÝ GENERÁTOR (Nová funkcia) ---
        async function generujVlastny() {
            const risk = document.getElementById('riskLevel').value;
            const count = document.getElementById('matchCount').value;
            const league = document.getElementById('leagueSelect').value;
            
            const div = document.getElementById('custom-ticket-result');
            div.innerHTML = '<p style="text-align:center; color:#66fcf1">Skladám tiket...</p>';
            
            const res = await fetch(`/api/vlastny-tiket?risk=${risk}&count=${count}&league=${league}`);
            const data = await res.json();
            renderTicket(data, div, "TVOJ VLASTNÝ TIKET");
        }

        // Pomocná funkcia na vykreslenie tiketu
        function renderTicket(data, element, title) {
            if (data.length === 0) { element.innerHTML = "Žiadne zápasy."; return; }
            
            let rows = '';
            let total = 1;
            data.forEach(m => {
                total *= m.kurz;
                rows += `
                <div class="ticket-row">
                    <div>
                        <div class="t-match">${m.domaci} - ${m.hostia}</div>
                        <div class="t-tip">Tip: ${m.tip}</div>
                    </div>
                    <div class="t-odds">${m.kurz}</div>
                </div>`;
            });

            element.innerHTML = `
            <div class="ticket-wrapper">
                <div class="ticket-header"><h2 class="ticket-title">${title}</h2></div>
                <div class="ticket-body">${rows}</div>
                <div class="ticket-footer">
                    <div class="t-total">CELKOVÝ KURZ</div>
                    <div class="t-val">${total.toFixed(2)}</div>
                </div>
            </div>`;
        }
    </script>
</body>
</html>
"""

# 3. BACKEND (Nová logika pre triedenie tiketov)
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def home(): 
    return html_content

# Pôvodný endpoint (pre sekciu Analýza) - vráti všetko
@app.get("/api/generuj-tiket")
def get_all_matches():
    return MATCH_DATABASE

# Nový endpoint: TIKET DŇA (Len risk 1)
@app.get("/api/tiket-dna")
def get_tiket_dna():
    safe_matches = [m for m in MATCH_DATABASE if m['risk'] == 1]
    return safe_matches[:3] # Vráti max 3 tutovky

# Nový endpoint: VLASTNÝ TIKET
@app.get("/api/vlastny-tiket")
def get_custom_ticket(risk: int = 1, count: int = 2, league: str = "all"):
    # 1. Filter podľa rizika
    filtered = [m for m in MATCH_DATABASE if m['risk'] == risk]
    
    # 2. Filter podľa ligy
    if league != "all":
        filtered = [m for m in filtered if m['liga'] == league]
    
    # 3. Ak nemáme dosť zápasov pre konkrétnu ligu, doplň z iných líg (fallback)
    if len(filtered) < count:
        filtered = [m for m in MATCH_DATABASE if m['risk'] == risk]
        
    # 4. Náhodný výber
    if len(filtered) >= count:
        return random.sample(filtered, count)
    return filtered

class WhopInput(BaseModel):
    message: str

@app.post("/whop")
def whop(data: WhopInput): 
    return {"status": "ok"}
