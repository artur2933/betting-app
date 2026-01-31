from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend import models, crud, database, ai 
from pydantic import BaseModel
import random

# 1. Inicializácia databázy
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

# --- MOCK DATABÁZA ---
# Rozšíril som dáta, aby analýza mala odrážky (body) ako na obrázku
MATCH_DATABASE = [
    # DATA PRE ANALÝZU (Detailné)
    {
        "domaci": "Manchester United", "hostia": "PAOK", "kurz": 1.45, "tip": "Výhra United & Over 1.5", "risk": 1, "liga": "Europa League", "dovera": 88,
        "stats": {"utok_domaci": 82, "utok_hostia": 40, "forma_domaci": "WWDLW", "forma_hostia": "LLDWL", "zranenia": "Man Utd: Maguire (Otázny), Shaw (Out)"},
        "analyza_text": "United pod novým trénerom Amorimom doma dominuje. Old Trafford je pevnosť, zatiaľ čo PAOK vonku v Európe trpí.",
        "analyza_body": [
            "United má priemer 2.1 xG na domáci zápas.",
            "PAOK inkasoval v 4 z 5 posledných zápasov.",
            "Motivácia domácich potvrdiť postup."
        ]
    },
    {
        "domaci": "Lazio Rím", "hostia": "FC Porto", "kurz": 2.10, "tip": "Obaja dajú gól (BTTS)", "risk": 2, "liga": "Europa League", "dovera": 75,
        "stats": {"utok_domaci": 78, "utok_hostia": 85, "forma_domaci": "WWWWL", "forma_hostia": "WWWWW", "zranenia": "Lazio: Immobile (lavička)"},
        "analyza_text": "Súboj dvoch ofenzívne ladených tímov. Porto má smrtiacu formu, ale v Taliansku sa hrá ťažko.",
        "analyza_body": [
            "Lazio skórovalo v 90% domácich zápasov.",
            "Porto má sériu 7 výhier v rade.",
            "Obrany oboch tímov robia chyby pod tlakom."
        ]
    },
    # ĎALŠIE DATA PRE GENERÁTOR TIKETOV (Jednoduchšie)
    {"domaci": "Man City", "hostia": "Sheffield", "kurz": 1.18, "tip": "1", "risk": 1, "liga": "Premier League", "stats": {"utok_domaci": 88, "utok_hostia": 20, "forma_domaci": "WWWWW", "forma_hostia": "LLLLL", "zranenia": ""}, "analyza_text": "", "analyza_body": []},
    {"domaci": "Bayern", "hostia": "Mainz", "kurz": 1.30, "tip": "1 + Over 2.5", "risk": 1, "liga": "Bundesliga", "stats": {"utok_domaci": 90, "utok_hostia": 40, "forma_domaci": "WLWWW", "forma_hostia": "LLLLL", "zranenia": ""}, "analyza_text": "", "analyza_body": []},
    {"domaci": "Arsenal", "hostia": "Chelsea", "kurz": 1.95, "tip": "1", "risk": 2, "liga": "Premier League", "stats": {"utok_domaci": 75, "utok_hostia": 65, "forma_domaci": "WWDLW", "forma_hostia": "LLLLL", "zranenia": ""}, "analyza_text": "", "analyza_body": []},
    {"domaci": "Luton", "hostia": "Liverpool", "kurz": 6.50, "tip": "1X", "risk": 3, "liga": "Premier League", "stats": {"utok_domaci": 40, "utok_hostia": 85, "forma_domaci": "LLWDL", "forma_hostia": "LLLLL", "zranenia": ""}, "analyza_text": "", "analyza_body": []},
]

# 2. HTML GRAFIKA
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

        /* --- ŠTÝLY PRE VIP ANALÝZU (PODĽA OBRÁZKA) --- */
        .analysis-card {
            background: #11161d; border-radius: 12px; margin-bottom: 30px; 
            border: 1px solid #2c3e50; padding: 0; overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            animation: slideUp 0.5s ease;
        }
        
        .ac-header {
            padding: 20px 30px; background: #151b24; border-bottom: 1px solid #2c3e50;
            display: flex; justify-content: space-between; align-items: center;
        }
        .ac-teams { font-size: 28px; font-weight: 800; color: #fff; }
        .ac-vs { color: #888; font-size: 20px; font-weight: 400; margin: 0 10px; }
        .ac-odds-badge { background: #1a2634; color: #66fcf1; padding: 8px 15px; border-radius: 8px; font-weight: bold; border: 1px solid #2c3e50; }

        .ac-body { padding: 30px; display: flex; gap: 40px; }
        .ac-left { flex: 1; border-right: 1px solid #2c3e50; padding-right: 30px; }
        .ac-right { flex: 1.2; padding-left: 10px; }

        /* Forma Dots (Obrázok style) */
        .ac-stat-title { font-size: 12px; color: #888; margin-bottom: 10px; }
        .ac-form-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
        .ac-team-label { font-size: 14px; color: #ccc; margin-bottom: 5px; display: block; }
        .ac-dots { display: flex; gap: 5px; }
        .ac-dot { width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; color: #000; }
        .ac-dot.v { background: #00ff88; } /* Výhra - Zelená */
        .ac-dot.r { background: #ffcc00; } /* Remíza - Žltá */
        .ac-dot.p { background: #ff4444; } /* Prehra - Červená */

        /* Progress Bar (Obrázok style) */
        .ac-progress-container { display: flex; height: 8px; background: #222; border-radius: 4px; overflow: hidden; margin-top: 5px; }
        .ac-bar-home { background: #66fcf1; height: 100%; }
        .ac-bar-away { background: #ff4444; height: 100%; }
        .ac-stat-val { font-size: 12px; color: #888; text-align: right; margin-top: 5px; }

        /* Injuries */
        .ac-injuries { color: #ff4444; font-size: 13px; margin-top: 5px; }

        /* Right Side Analysis */
        .ac-ai-title { color: #ff66cc; font-weight: bold; font-size: 12px; text-transform: uppercase; margin-bottom: 10px; display: flex; align-items: center; gap: 5px; }
        .ac-text { font-size: 14px; line-height: 1.6; color: #ccc; margin-bottom: 15px; }
        .ac-list { list-style: none; padding: 0; margin-bottom: 20px; }
        .ac-list li { margin-bottom: 8px; padding-left: 15px; position: relative; color: #aaa; font-size: 13px; }
        .ac-list li::before { content: "•"; color: #66fcf1; position: absolute; left: 0; font-weight: bold; }

        /* Recommendation Box (Obrázok style) */
        .ac-tip-box { 
            background: #1a222e; border: 1px solid #2c3e50; border-radius: 8px; padding: 15px; 
            display: flex; justify-content: space-between; align-items: center;
        }
        .ac-tip-label { font-size: 10px; color: #888; text-transform: uppercase; display: block; margin-bottom: 2px; }
        .ac-tip-value { font-size: 20px; font-weight: 800; color: #fff; }
        .ac-conf-badge { background: #66fcf1; color: #000; padding: 5px 10px; border-radius: 4px; font-weight: bold; font-size: 14px; }

        /* --- ŠTÝLY PRE TIKETY A GENERÁTOR (Zachované) --- */
        .ticket-wrapper { max-width: 600px; margin: 0 auto; background: #151b24; border: 2px solid #66fcf1; border-radius: 12px; box-shadow: 0 0 40px rgba(102, 252, 241, 0.15); }
        .ticket-header { background: rgba(102, 252, 241, 0.1); padding: 20px; text-align: center; border-bottom: 1px solid #66fcf1; }
        .ticket-title { font-size: 24px; font-weight: 800; color: #66fcf1; margin: 0; }
        .ticket-body { padding: 20px; }
        .ticket-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #333; padding: 15px 0; }
        .t-match { font-size: 16px; font-weight: bold; color: #fff; }
        .t-tip { font-size: 13px; color: #888; margin-top: 4px; }
        .t-odds { background: #0b0c10; color: #66fcf1; padding: 5px 10px; border-radius: 4px; border: 1px solid #333; font-weight: bold; }
        .ticket-footer { background: #0b0c10; padding: 20px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #333; }
        .t-val { color: #66fcf1; font-weight: 900; font-size: 28px; }

        .gen-controls { max-width: 700px; margin: 0 auto; background: #151b24; padding: 30px; border-radius: 12px; border: 1px solid #333; }
        .c-label { display: block; color: #66fcf1; font-size: 12px; font-weight: bold; margin-bottom: 8px; text-transform: uppercase; }
        select { width: 100%; padding: 15px; background: #0b0c10; border: 1px solid #333; color: #fff; border-radius: 8px; font-size: 16px; outline: none; }

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
            <div class="chart-box"><canvas id="profitChart"></canvas></div>
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
                <div style="margin-bottom:20px;">
                    <label class="c-label">Riziko</label>
                    <select id="riskLevel">
                        <option value="1">🟢 Nízke (1.2 - 1.5)</option>
                        <option value="2">🟡 Stredné (1.8 - 2.2)</option>
                        <option value="3">🔴 Vysoké (3.0+)</option>
                    </select>
                </div>
                <div style="margin-bottom:20px;">
                    <label class="c-label">Počet zápasov</label>
                    <select id="matchCount">
                        <option value="2">2 Zápasy</option>
                        <option value="3">3 Zápasy</option>
                        <option value="5">5 Zápasov</option>
                    </select>
                </div>
                <div style="margin-bottom:20px;">
                    <label class="c-label">Liga</label>
                    <select id="leagueSelect">
                        <option value="all">Všetky Ligy</option>
                        <option value="Premier League">Premier League</option>
                        <option value="La Liga">La Liga</option>
                        <option value="Bundesliga">Bundesliga</option>
                    </select>
                </div>
                <button class="btn-analyze" style="margin-bottom:0;" onclick="generujVlastny()">Vygenerovať</button>
            </div>
            <div id="custom-ticket-result" style="margin-top: 50px;"></div>
        </div>

        <div id="results-page" class="page">
            <div class="header"><h1>Výkonnosť Modelu</h1></div>
            <p style="color:#aaa;">Načítavam dáta...</p>
        </div>

    </div>

    <script>
        // Graf
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

        // --- 1. VIP ANALÝZA (Dizajn presne podľa obrázka) ---
        async function generujAnalyzu() {
            const out = document.getElementById('analysis-output');
            out.innerHTML = '<p style="text-align:center; color:#66fcf1">Analyzujem...</p>';
            const res = await fetch('/api/generuj-tiket'); 
            const data = await res.json();
            
            let html = '';
            // Berieme len prvé 2 zápasy pre ukážku, ktoré majú vyplnené detaily
            data.slice(0, 2).forEach(m => {
                
                // Helper pre guličky (V/R/P)
                const circles = (formStr) => {
                    let h = '';
                    for (let c of formStr) {
                        let cl = c === 'W' ? 'v' : (c === 'L' ? 'p' : 'r'); // css triedy
                        let txt = c === 'W' ? 'V' : (c === 'L' ? 'P' : 'R'); // text
                        h += `<div class="ac-dot ${cl}">${txt}</div>`;
                    }
                    return h;
                };

                // Helper pre body analýzy
                let listHtml = '';
                if(m.analyza_body) {
                    m.analyza_body.forEach(li => listHtml += `<li>${li}</li>`);
                }

                html += `
                <div class="analysis-card">
                    <div class="ac-header">
                        <div class="ac-teams">${m.domaci} <span class="ac-vs">vs</span> ${m.hostia}</div>
                        <div class="ac-odds-badge">Kurz: ${m.kurz}</div>
                    </div>
                    <div class="ac-body">
                        
                        <div class="ac-left">
                            <div style="margin-bottom: 25px;">
                                <div class="ac-stat-title">Forma (Posledných 5)</div>
                                <div class="ac-form-row">
                                    <div><span class="ac-team-label">${m.domaci}</span><div class="ac-dots">${circles(m.stats.forma_domaci)}</div></div>
                                    <div style="text-align:right;"><span class="ac-team-label">${m.hostia}</span><div class="ac-dots" style="justify-content:flex-end;">${circles(m.stats.forma_hostia)}</div></div>
                                </div>
                            </div>

                            <div style="margin-bottom: 25px;">
                                <div class="ac-stat-title">Sila Útoku (xG Power)</div>
                                <div class="ac-progress-container">
                                    <div class="ac-bar-home" style="width:${m.stats.utok_domaci}%"></div>
                                    <div class="ac-bar-away" style="width:${m.stats.utok_hostia}%"></div>
                                </div>
                                <div class="ac-stat-val">${m.stats.utok_domaci}% vs ${m.stats.utok_hostia}%</div>
                            </div>

                            <div>
                                <div class="ac-stat-title">Absencie (Zranenia)</div>
                                <div class="ac-injuries">${m.stats.zranenia}</div>
                            </div>
                        </div>

                        <div class="ac-right">
                            <div class="ac-ai-title">🧠 AI DEEP DIVE ANALÝZA</div>
                            <div class="ac-text">${m.analyza_text}</div>
                            <ul class="ac-list">
                                ${listHtml}
                            </ul>

                            <div class="ac-tip-box">
                                <div>
                                    <span class="ac-tip-label">ODPORÚČANÝ TIP</span>
                                    <div class="ac-tip-value">${m.tip}</div>
                                </div>
                                <div style="text-align:right;">
                                    <span class="ac-tip-label">Dôvera</span>
                                    <div class="ac-conf-badge">${m.dovera}%</div>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>`;
            });
            out.innerHTML = html;
        }

        // --- 2. TIKET DŇA (Logika) ---
        async function loadTiketDna(el) {
            showPage('ticket-day', el);
            const div = document.getElementById('ticket-day-result');
            div.innerHTML = '<p style="text-align:center; color:#66fcf1">Generujem Tiket Dňa...</p>';
            const res = await fetch('/api/tiket-dna');
            const data = await res.json();
            renderTicket(data, div, "VIP TIKET DŇA");
        }

        // --- 3. VLASTNÝ GENERÁTOR (Logika) ---
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
            if (data.length === 0) { element.innerHTML = "<p style='text-align:center;color:#888'>Žiadne zápasy.</p>"; return; }
            let rows = ''; let total = 1;
            data.forEach(m => { total *= m.kurz; rows += `<div class="ticket-row"><div><div class="t-match">${m.domaci} - ${m.hostia}</div><div class="t-tip">Tip: ${m.tip}</div></div><div class="t-odds">${m.kurz}</div></div>`; });
            element.innerHTML = `<div class="ticket-wrapper"><div class="ticket-header"><h2 class="ticket-title">${title}</h2></div><div class="ticket-body">${rows}</div><div class="ticket-footer"><div class="t-match">CELKOVÝ KURZ</div><div class="t-val">${total.toFixed(2)}</div></div></div>`;
        }
    </script>
</body>
</html>
"""

# 3. BACKEND (Logika)
def get_db():
    db = database.SessionLocal()
    try: yield db
    finally: db.close()

@app.get("/", response_class=HTMLResponse)
def home(): return html_content

@app.get("/api/generuj-tiket")
def get_all_matches():
    return MATCH_DATABASE

@app.get("/api/tiket-dna")
def get_tiket_dna():
    safe_matches = [m for m in MATCH_DATABASE if m['risk'] == 1]
    return safe_matches[:3]

@app.get("/api/vlastny-tiket")
def get_custom_ticket(risk: int = 1, count: int = 2, league: str = "all"):
    filtered = [m for m in MATCH_DATABASE if m['risk'] == risk]
    if league != "all": filtered = [m for m in filtered if m.get('liga') == league]
    if len(filtered) < count: filtered = [m for m in MATCH_DATABASE if m['risk'] == risk] 
    if len(filtered) >= count: return random.sample(filtered, count)
    return filtered

class WhopInput(BaseModel):
    message: str

@app.post("/whop")
def whop(data: WhopInput): return {"status": "ok"}
