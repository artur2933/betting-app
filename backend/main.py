from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from backend import database, models
from sqlalchemy.orm import Session
from pydantic import BaseModel
import random
import time

# 1. Inicializácia
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

# --- KONFIGURÁCIA AI BOTA (Tímy a Ligy) ---
# Tieto dáta slúžia pre generátor, aby skladal reálne vyzerajúce dvojice.
TEAMS_DB = {
    "Premier League": ["Man City", "Liverpool", "Arsenal", "Aston Villa", "Tottenham", "Man Utd", "Newcastle", "Chelsea", "West Ham", "Brighton"],
    "La Liga": ["Real Madrid", "Girona", "Barcelona", "Atl. Madrid", "Ath. Bilbao", "Real Sociedad", "Betis", "Valencia", "Sevilla", "Villarreal"],
    "Bundesliga": ["Leverkusen", "Bayern", "Stuttgart", "Dortmund", "Leipzig", "Frankfurt", "Hoffenheim", "Freiburg", "Augsburg", "Wolfsburg"],
    "Serie A": ["Inter", "Juventus", "AC Milan", "Bologna", "AS Roma", "Atalanta", "Napoli", "Fiorentina", "Lazio", "Torino"]
}

ZRANENIA_DB = ["Otázny štart", "Zranený sval", "Karta (Out)", "Chrípka", "Šetrí sa na pohár", "Bez zranení"]

# --- FUNKCIA BOTA: Generovanie zápasov ---
def bot_scan_market(risk_filter=None, league_filter="all", limit=10):
    matches = []
    
    # Aká liga sa má skenovať?
    leagues_to_scan = [league_filter] if league_filter != "all" else list(TEAMS_DB.keys())
    
    for _ in range(limit):
        liga = random.choice(leagues_to_scan)
        t1, t2 = random.sample(TEAMS_DB[liga], 2)
        
        # Simulácia sily tímov a kurzov
        sila_t1 = random.randint(40, 95)
        sila_t2 = random.randint(40, 95)
        
        # Výpočet kurzu podľa sily
        diff = sila_t1 - sila_t2
        if diff > 20: # Favorit doma
            kurz = round(random.uniform(1.15, 1.55), 2)
            tip = "1"
            risk = 1
            analyza = f"{t1} doma dominuje. Sila útoku je drvivá."
        elif diff < -20: # Favorit hostia
            kurz = round(random.uniform(1.60, 2.20), 2)
            tip = "2"
            risk = 2
            analyza = f"{t2} má lepšiu formu a {t1} sa trápi v obrane."
        else: # Vyrovnané
            kurz = round(random.uniform(2.80, 3.60), 2)
            tip = "X" if random.random() > 0.5 else "BTTS"
            risk = 3
            analyza = "Veľmi vyrovnaný zápas. Očakávame taktický boj."

        # Filter podľa rizika (ak je zapnutý)
        if risk_filter and risk != risk_filter:
            continue

        # Generovanie štatistík
        match = {
            "domaci": t1, "hostia": t2, "kurz": kurz, "tip": tip, "risk": risk, "liga": liga,
            "dovera": random.randint(60, 98) if risk == 1 else random.randint(40, 75),
            "stats": {
                "utok_domaci": sila_t1, "utok_hostia": sila_t2,
                "forma_domaci": "".join(random.choices(["W", "D", "L"], weights=[50, 30, 20], k=5)),
                "forma_hostia": "".join(random.choices(["W", "D", "L"], weights=[40, 30, 30], k=5)),
                "zranenia": random.choice(ZRANENIA_DB)
            },
            "analyza_text": analyza,
            "analyza_body": [
                f"{t1} má priemer {round(random.uniform(1.1, 2.8), 1)} gólu na zápas.",
                f"{t2} inkasoval v {random.randint(3,5)} z posledných 5 zápasov.",
                "Zápas ovplyvní aktuálna forma kľúčových hráčov."
            ]
        }
        matches.append(match)
    
    # Vrátime unikátne zápasy
    return matches[:limit]


# 2. HTML GRAFIKA (Nezmenená - Modrá Cyberpunk)
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betting PRO Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">
    
    <style>
        /* --- GLOBAL STYLES (Cyberpunk Blue Theme) --- */
        :root {
            --bg-dark: #050a10; --bg-card: #151b24; --primary: #66fcf1; --text-main: #c5c6c7;
            --green: #00ff88; --red: #ff4444; --yellow: #ffcc00;
        }
        body { margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; background-color: #0b0c10; color: var(--text-main); display: flex; height: 100vh; overflow: hidden; }
        ::-webkit-scrollbar { width: 8px; } ::-webkit-scrollbar-thumb { background: #1f2833; border-radius: 4px; }

        /* SIDEBAR */
        .sidebar { width: 260px; background-color: #111; display: flex; flex-direction: column; padding: 25px; border-right: 1px solid #333; }
        .logo { font-size: 24px; font-weight: 800; color: var(--primary); margin-bottom: 40px; text-transform: uppercase; letter-spacing: 2px; text-align: center; border-bottom: 2px solid var(--primary); padding-bottom: 20px; text-shadow: 0 0 10px rgba(102, 252, 241, 0.4); }
        .menu-label { font-size: 11px; text-transform: uppercase; color: #666; margin-top: 20px; margin-bottom: 10px; font-weight: bold; }
        .menu-item { padding: 15px; margin-bottom: 5px; cursor: pointer; border-radius: 8px; color: #888; font-weight: 600; transition: 0.3s; display: flex; align-items: center; gap: 15px; }
        .menu-item:hover, .menu-item.active { background-color: #1f2833; color: #fff; border-left: 4px solid var(--primary); }
        
        /* MAIN CONTENT */
        .main-content { flex: 1; padding: 40px; overflow-y: auto; background: radial-gradient(circle at top right, #1f2833 0%, #0b0c10 80%); }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; border-bottom: 1px solid #333; padding-bottom: 20px; }
        .header h1 { margin: 0; color: #fff; font-size: 32px; font-weight: 700; letter-spacing: 1px; }
        
        /* DASHBOARD */
        .dash-card { background: var(--bg-card); padding: 25px; flex: 1; border-radius: 16px; border: 1px solid #2c3e50; }
        .dash-card h1 { color: #fff; font-size: 42px; margin: 10px 0; font-weight: 800; }
        .chart-box { background: var(--bg-card); padding: 25px; border-radius: 16px; border: 1px solid #2c3e50; height: 350px; }

        /* BUTTONS */
        .btn-analyze { 
            background: var(--primary); border: none; padding: 18px 50px; font-size: 16px; font-weight: 800; color: #0b0c10; 
            border-radius: 50px; cursor: pointer; box-shadow: 0 0 25px rgba(102, 252, 241, 0.3); transition: 0.2s; display: block; margin: 0 auto 40px auto; text-transform: uppercase;
        }
        .btn-analyze:hover { transform: scale(1.05); background: #fff; }

        /* VIP ANALÝZA STYLE */
        .analysis-card { background: #11161d; border-radius: 12px; margin-bottom: 30px; border: 1px solid #2c3e50; padding: 0; overflow: hidden; animation: slideUp 0.5s ease; }
        .ac-header { padding: 20px 30px; background: #151b24; border-bottom: 1px solid #2c3e50; display: flex; justify-content: space-between; align-items: center; }
        .ac-teams { font-size: 28px; font-weight: 800; color: #fff; }
        .ac-vs { color: #666; font-size: 20px; font-weight: 400; margin: 0 10px; }
        .ac-odds-badge { background: #1a2634; color: var(--primary); padding: 8px 15px; border-radius: 8px; font-weight: bold; border: 1px solid #2c3e50; font-size: 16px; }
        .ac-body { padding: 30px; display: flex; gap: 40px; flex-wrap: wrap; }
        .ac-left { flex: 1; min-width: 300px; border-right: 1px solid #2c3e50; padding-right: 30px; }
        .ac-right { flex: 1.2; min-width: 300px; padding-left: 10px; }
        .ac-stat-title { font-size: 12px; color: #888; margin-bottom: 10px; font-weight: 600; }
        .ac-form-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
        .ac-team-label { font-size: 14px; color: #ccc; margin-bottom: 5px; display: block; font-weight: 600; }
        .ac-dots { display: flex; gap: 5px; }
        .ac-dot { width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; color: #000; }
        .ac-dot.v { background: var(--green); } .ac-dot.r { background: var(--yellow); } .ac-dot.p { background: var(--red); }
        .ac-progress-container { display: flex; height: 8px; background: #222; border-radius: 4px; overflow: hidden; margin-top: 5px; }
        .ac-bar-home { background: var(--primary); height: 100%; } .ac-bar-away { background: var(--red); height: 100%; }
        .ac-stat-val { font-size: 12px; color: #888; text-align: right; margin-top: 5px; font-weight: bold; }
        .ac-ai-title { color: #ff66cc; font-weight: bold; font-size: 12px; text-transform: uppercase; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; }
        .ac-text { font-size: 14px; line-height: 1.7; color: #ccc; margin-bottom: 20px; }
        .ac-list { list-style: none; padding: 0; margin-bottom: 25px; }
        .ac-list li { margin-bottom: 10px; padding-left: 20px; position: relative; color: #aaa; font-size: 14px; }
        .ac-list li::before { content: "•"; color: var(--primary); position: absolute; left: 0; font-weight: bold; }
        .ac-tip-box { background: #1a222e; border: 1px solid #2c3e50; border-radius: 8px; padding: 20px; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid var(--primary); }
        .ac-tip-value { font-size: 22px; font-weight: 800; color: #fff; }
        .ac-conf-badge { background: var(--primary); color: #000; padding: 6px 12px; border-radius: 6px; font-weight: 800; font-size: 16px; }

        /* TIKETY */
        .ticket-wrapper { max-width: 600px; margin: 0 auto; background: #151b24; border: 2px solid var(--primary); border-radius: 12px; box-shadow: 0 0 50px rgba(102, 252, 241, 0.15); animation: slideUp 0.5s ease; }
        .ticket-header { background: rgba(102, 252, 241, 0.1); padding: 25px; text-align: center; border-bottom: 1px solid var(--primary); }
        .ticket-title { font-size: 26px; font-weight: 900; color: var(--primary); margin: 0; letter-spacing: 2px; text-transform: uppercase; }
        .ticket-body { padding: 30px; }
        .ticket-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #444; padding: 15px 0; }
        .t-match { font-size: 17px; font-weight: 700; color: #fff; }
        .t-tip { font-size: 14px; color: #aaa; margin-top: 5px; }
        .t-odds { background: #0b0c10; color: var(--primary); padding: 6px 12px; border-radius: 6px; border: 1px solid #333; font-weight: 800; }
        .ticket-footer { background: #0b0c10; padding: 25px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #333; }
        .t-val { color: var(--primary); font-weight: 900; font-size: 32px; }

        /* GENERÁTOR */
        .gen-controls { max-width: 700px; margin: 0 auto; background: #151b24; padding: 40px; border-radius: 16px; border: 1px solid #333; }
        .c-label { display: block; color: var(--primary); font-size: 12px; font-weight: bold; margin-bottom: 10px; text-transform: uppercase; }
        select { width: 100%; padding: 18px; background: #0b0c10; border: 1px solid #333; color: #fff; border-radius: 8px; font-size: 16px; outline: none; }

        .page { display: none; }
        .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
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
                <div class="dash-card">
                    <h3>Dnešný Potenciál</h3>
                    <h1 id="dash-potential">Načítavam...</h1>
                    <small style="color:var(--primary)">Aktívny Sken Trhu</small>
                </div>
                <div class="dash-card">
                    <h3>Bankroll</h3>
                    <h1 id="dash-bankroll">€2,450.00</h1>
                    <small style="color:#00ff88">▲ +12.5% tento týždeň</small>
                </div>
            </div>
            <div class="chart-box"><h3 style="color:#fff; margin:0 0 20px 0;">Vývoj Zisku</h3><canvas id="profitChart"></canvas></div>
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
                    <select id="riskLevel"><option value="1">🟢 Nízke (1.2 - 1.5)</option><option value="2">🟡 Stredné (1.8 - 2.2)</option><option value="3">🔴 Vysoké (3.0+)</option></select>
                </div>
                <div style="margin-bottom:20px;">
                    <label class="c-label">Počet zápasov</label>
                    <select id="matchCount"><option value="2">2 Zápasy</option><option value="3">3 Zápasy</option><option value="5">5 Zápasov</option></select>
                </div>
                <div style="margin-bottom:20px;">
                    <label class="c-label">Liga</label>
                    <select id="leagueSelect"><option value="all">Všetky Ligy</option><option value="Premier League">Premier League</option><option value="La Liga">La Liga</option><option value="Bundesliga">Bundesliga</option><option value="Serie A">Serie A</option></select>
                </div>
                <button class="btn-analyze" style="margin-bottom:0;" onclick="generujVlastny()">Vygenerovať</button>
            </div>
            <div id="custom-ticket-result" style="margin-top: 50px;"></div>
        </div>

        <div id="results-page" class="page">
            <div class="header"><h1>Výkonnosť Modelu</h1></div>
            <p style="color:#aaa;">Načítavam históriu...</p>
            <div class="analysis-card" style="padding:20px; text-align:center; color:#666;">História je zatiaľ prázdna.</div>
        </div>

    </div>

    <script>
        document.addEventListener("DOMContentLoaded", function() {
            // Dashboard random data
            document.getElementById('dash-potential').innerText = Math.floor(Math.random() * 10 + 5) + " Zápasov";
            const ctx = document.getElementById('profitChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: { labels: ['Po', 'Ut', 'St', 'Št', 'Pi', 'So', 'Ne'], datasets: [{ label: 'Zisk', data: [2100, 2150, 2120, 2250, 2300, 2380, 2450], borderColor: '#66fcf1', backgroundColor: 'rgba(102, 252, 241, 0.1)', borderWidth: 3, tension: 0.4, fill: true }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#2c3e50' }, ticks: { color: '#888' } }, x: { grid: { display: false }, ticks: { color: '#888' } } } }
            });
        });

        function showPage(id, el) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            if(el) { document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active')); el.classList.add('active'); }
            document.getElementById(id).classList.add('active');
        }

        async function generujAnalyzu() {
            const out = document.getElementById('analysis-output');
            out.innerHTML = '<p style="text-align:center; color:#66fcf1; font-size:18px;">⏳ Bot skenuje trh...</p>';
            try {
                const res = await fetch('/api/generuj-tiket?limit=50'); // Skenuj vela
                const data = await res.json();
                let html = '';
                data.forEach(m => {
                    const circles = (f) => { let h=''; for(let c of f) h+=`<div class="ac-dot ${c==='W'?'v':(c==='L'?'p':'r')}">${c==='W'?'V':(c==='L'?'P':'R')}</div>`; return h; };
                    let listHtml = ''; m.analyza_body.forEach(li => listHtml += `<li>${li}</li>`);
                    html += `
                    <div class="analysis-card">
                        <div class="ac-header"><div class="ac-teams">${m.domaci} <span class="ac-vs">vs</span> ${m.hostia}</div><div class="ac-odds-badge">Kurz: ${m.kurz.toFixed(2)}</div></div>
                        <div class="ac-body">
                            <div class="ac-left">
                                <div style="margin-bottom:25px;"><div class="ac-stat-title">Forma</div><div class="ac-form-row"><div><span class="ac-team-label">${m.domaci}</span><div class="ac-dots">${circles(m.stats.forma_domaci)}</div></div><div style="text-align:right;"><span class="ac-team-label">${m.hostia}</span><div class="ac-dots" style="justify-content:flex-end;">${circles(m.stats.forma_hostia)}</div></div></div></div>
                                <div style="margin-bottom:25px;"><div class="ac-stat-title">Sila Útoku</div><div class="ac-progress-container"><div class="ac-bar-home" style="width:${m.stats.utok_domaci}%"></div><div class="ac-bar-away" style="width:${m.stats.utok_hostia}%"></div></div><div class="ac-stat-val">${m.stats.utok_domaci}% vs ${m.stats.utok_hostia}%</div></div>
                                <div><div class="ac-stat-title">Zranenia</div><div class="ac-injuries">${m.stats.zranenia}</div></div>
                            </div>
                            <div class="ac-right">
                                <div class="ac-ai-title">🧠 AI DEEP DIVE</div><div class="ac-text">${m.analyza_text}</div><ul class="ac-list">${listHtml}</ul>
                                <div class="ac-tip-box"><div><span class="ac-tip-label">TIP</span><div class="ac-tip-value">${m.tip}</div></div><div style="text-align:right;"><span class="ac-tip-label">Dôvera</span><div class="ac-conf-badge">${m.dovera}%</div></div></div>
                            </div>
                        </div>
                    </div>`;
                });
                out.innerHTML = html;
            } catch(e) { out.innerHTML = "Chyba."; }
        }

        async function loadTiketDna(el) {
            showPage('ticket-day', el);
            const div = document.getElementById('ticket-day-result');
            div.innerHTML = '<p style="text-align:center; color:#66fcf1; font-size:18px;">⏳ Generujem najlepší tiket dňa...</p>';
            const res = await fetch('/api/tiket-dna');
            const data = await res.json();
            renderTicket(data, div, "VIP TIKET DŇA");
        }

        async function generujVlastny() {
            const risk = document.getElementById('riskLevel').value;
            const count = document.getElementById('matchCount').value;
            const league = document.getElementById('leagueSelect').value;
            const div = document.getElementById('custom-ticket-result');
            div.innerHTML = '<p style="text-align:center; color:#66fcf1; font-size:18px;">⏳ Skladám tiket...</p>';
            const res = await fetch(`/api/vlastny-tiket?risk=${risk}&count=${count}&league=${league}`);
            const data = await res.json();
            renderTicket(data, div, "TVOJ VLASTNÝ TIKET");
        }

        function renderTicket(data, element, title) {
            if (data.length === 0) { element.innerHTML = "<p style='text-align:center;color:#888'>Žiadne zápasy.</p>"; return; }
            let rows = ''; let total = 1;
            data.forEach(m => { total *= m.kurz; rows += `<div class="ticket-row"><div><div class="t-match">${m.domaci} - ${m.hostia}</div><div class="t-tip">Tip: ${m.tip}</div></div><div class="t-odds">${m.kurz.toFixed(2)}</div></div>`; });
            element.innerHTML = `<div class="ticket-wrapper"><div class="ticket-header"><h2 class="ticket-title">${title}</h2></div><div class="ticket-body">${rows}</div><div class="ticket-footer"><div class="t-total">CELKOVÝ KURZ</div><div class="t-val">${total.toFixed(2)}</div></div></div>`;
        }
    </script>
</body>
</html>
"""

# 3. BACKEND (Generátor)
def get_db():
    db = database.SessionLocal()
    try: yield db
    finally: db.close()

@app.get("/", response_class=HTMLResponse)
def home(): return html_content

@app.get("/api/generuj-tiket")
def get_analysis_matches(limit: int = 10):
    return bot_scan_market(limit=limit)

@app.get("/api/tiket-dna")
def get_tiket_dna():
    # Vygeneruje 3 čerstvé safe zápasy
    return bot_scan_market(risk_filter=1, limit=3)

@app.get("/api/vlastny-tiket")
def get_custom_ticket(risk: int = 1, count: int = 2, league: str = "all"):
    # Vygeneruje čerstvé zápasy podľa filtra
    return bot_scan_market(risk_filter=risk, league_filter=league, limit=count)

class WhopInput(BaseModel):
    message: str

@app.post("/whop")
def whop(data: WhopInput): return {"status": "ok"}
