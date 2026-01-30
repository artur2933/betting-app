from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import random

app = FastAPI()

# --- DATABÁZA ZÁPASOV (MOCK DATA - Simulácia trhu) ---
# Tieto dáta budeme filtrovať podľa toho, čo zákazník chce.
MATCH_DATABASE = [
    {"liga": "Premier League", "domaci": "Man City", "hostia": "Sheffield", "kurz": 1.18, "tip": "1", "risk": 1},
    {"liga": "La Liga", "domaci": "Real Madrid", "hostia": "Almeria", "kurz": 1.25, "tip": "1", "risk": 1},
    {"liga": "Bundesliga", "domaci": "Bayern", "hostia": "Mainz", "kurz": 1.30, "tip": "1 + Over 2.5", "risk": 1},
    {"liga": "Serie A", "domaci": "Inter", "hostia": "Salernitana", "kurz": 1.28, "tip": "1", "risk": 1},
    
    {"liga": "Premier League", "domaci": "Arsenal", "hostia": "Chelsea", "kurz": 1.95, "tip": "1", "risk": 2},
    {"liga": "La Liga", "domaci": "Sevilla", "hostia": "Betis", "kurz": 2.10, "tip": "X (Remíza)", "risk": 2},
    {"liga": "Bundesliga", "domaci": "Dortmund", "hostia": "Leipzig", "kurz": 2.05, "tip": "BTTS (Obaja gól)", "risk": 2},
    
    {"liga": "Premier League", "domaci": "Luton", "hostia": "Liverpool", "kurz": 6.50, "tip": "1X", "risk": 3},
    {"liga": "Serie A", "domaci": "Monza", "hostia": "Juventus", "kurz": 3.40, "tip": "1", "risk": 3},
    {"liga": "Ligue 1", "domaci": "Nantes", "hostia": "PSG", "kurz": 4.10, "tip": "1", "risk": 3},
]

# --- HTML GRAFIKA (Gold & Navy) ---
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betting PRO Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    
    <style>
        :root {
            --bg-body: #0f172a; --bg-card: #1e293b; --accent: #fbbf24; 
            --text-main: #f8fafc; --text-muted: #94a3b8; --success: #22c55e; --danger: #ef4444;
        }
        body { margin: 0; padding: 0; font-family: 'Inter', sans-serif; background-color: var(--bg-body); color: var(--text-main); display: flex; height: 100vh; overflow: hidden; }
        
        /* Sidebar */
        .sidebar { width: 250px; background-color: #020617; border-right: 1px solid #334155; display: flex; flex-direction: column; padding: 30px 20px; }
        .logo { font-size: 24px; font-weight: 800; color: #fff; margin-bottom: 40px; display:flex; align-items:center; gap:10px; }
        .logo span { color: var(--accent); }
        .menu-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; margin-bottom: 10px; letter-spacing: 1px; margin-top: 20px; }
        .menu-item { padding: 14px; margin-bottom: 8px; cursor: pointer; border-radius: 8px; color: var(--text-muted); font-weight: 600; transition: 0.2s; font-size: 15px; display: flex; align-items: center; gap: 10px; }
        .menu-item:hover, .menu-item.active { background: var(--accent); color: #000; }
        
        /* Content */
        .main-content { flex: 1; padding: 40px; overflow-y: auto; background: var(--bg-body); }
        .header { margin-bottom: 30px; }
        .header h1 { font-size: 28px; font-weight: 800; color: #fff; }

        /* TIKET KARTA (Design tiketu) */
        .ticket-slip {
            background: #fff; color: #000; padding: 0; border-radius: 12px;
            max-width: 500px; margin: 0 auto; box-shadow: 0 0 30px rgba(251, 191, 36, 0.2);
            overflow: hidden; animation: slideUp 0.5s ease;
        }
        .slip-header { background: var(--accent); padding: 20px; text-align: center; font-weight: 800; font-size: 20px; text-transform: uppercase; letter-spacing: 2px; }
        .slip-body { padding: 20px; }
        .slip-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #ccc; padding: 15px 0; }
        .slip-row:last-child { border-bottom: none; }
        .slip-match { font-weight: 700; font-size: 16px; }
        .slip-meta { font-size: 12px; color: #666; }
        .slip-odds { background: #000; color: #fff; padding: 5px 10px; border-radius: 5px; font-weight: bold; }
        .slip-footer { background: #f1f5f9; padding: 20px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #e2e8f0; }
        .total-odds { font-size: 24px; font-weight: 900; color: #000; }

        /* Generator Controls */
        .custom-gen-box { background: var(--bg-card); border-radius: 16px; padding: 30px; border: 1px solid #334155; max-width: 800px; margin: 0 auto; }
        .control-group { margin-bottom: 25px; }
        .control-label { display: block; color: var(--text-muted); margin-bottom: 10px; font-weight: 600; text-transform: uppercase; font-size: 12px; }
        
        select, input[type=range] { width: 100%; padding: 15px; background: #0f172a; border: 1px solid #334155; color: #fff; border-radius: 8px; font-size: 16px; outline: none; }
        input[type=range] { height: 5px; padding: 0; }
        input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; height: 20px; width: 20px; background: var(--accent); border-radius: 50%; cursor: pointer; }

        .btn-generate { background: var(--accent); color: #000; width: 100%; padding: 18px; border: none; border-radius: 8px; font-weight: 800; font-size: 18px; cursor: pointer; margin-top: 20px; text-transform: uppercase; }
        .btn-generate:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(251, 191, 36, 0.3); }

        .page { display: none; }
        .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="logo">BET<span>PRO</span></div>
        <div class="menu-label">Menu</div>
        <div class="menu-item active" onclick="showPage('home')">🏠 Dashboard</div>
        <div class="menu-item" onclick="loadTiketDna()">🎯 Tiket Dňa (Tutovka)</div>
        <div class="menu-item" onclick="showPage('custom')">🛠️ Vlastný Tiket</div>
    </div>

    <div class="main-content">
        
        <div id="home" class="page active">
            <div class="header"><h1>Prehľad</h1></div>
            <div style="background:var(--bg-card); padding:40px; border-radius:12px; text-align:center; border:1px solid #334155;">
                <h2 style="color:white; margin-bottom:10px;">Vitaj v Centre Analýz</h2>
                <p style="color:var(--text-muted)">Vyber si z menu vľavo: <b>Tiket Dňa</b> pre istotu, alebo <b>Vlastný Tiket</b> pre nastavenie stratégie.</p>
            </div>
        </div>

        <div id="ticket-day" class="page">
            <div class="header"><h1>🔥 Tiket Dňa (Safe)</h1></div>
            <div id="tiket-dna-loading" style="text-align:center; color:var(--accent);">Načítavam najlepšie zápasy...</div>
            <div id="tiket-dna-result"></div>
        </div>

        <div id="custom" class="page">
            <div class="header"><h1>⚙️ Generátor Tiketov</h1></div>
            
            <div class="custom-gen-box">
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                    <div class="control-group">
                        <label class="control-label">Riziko (Risk Management)</label>
                        <select id="riskLevel">
                            <option value="1">🟢 Nízke (Kurzy 1.20 - 1.50)</option>
                            <option value="2">🟡 Stredné (Kurzy 1.80 - 2.20)</option>
                            <option value="3">🔴 Vysoké (Kurzy 3.00+)</option>
                        </select>
                    </div>
                    <div class="control-group">
                        <label class="control-label">Počet Zápasov (AKO)</label>
                        <select id="matchCount">
                            <option value="2">2 Zápasy</option>
                            <option value="3">3 Zápasy</option>
                            <option value="5">5 Zápasov (Plachta)</option>
                        </select>
                    </div>
                </div>

                <div class="control-group">
                    <label class="control-label">Preferovaná Liga</label>
                    <select id="leagueSelect">
                        <option value="all">🌍 Všetky Ligy (Mix)</option>
                        <option value="Premier League">🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League</option>
                        <option value="La Liga">🇪🇸 La Liga</option>
                        <option value="Bundesliga">🇩🇪 Bundesliga</option>
                        <option value="Serie A">🇮🇹 Serie A</option>
                    </select>
                </div>

                <button class="btn-generate" onclick="generujVlastny()">🚀 Vygenerovať Tiket</button>
            </div>

            <div id="custom-result" style="margin-top: 40px;"></div>
        </div>

    </div>

    <script>
        function showPage(id) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.getElementById(id).classList.add('active');
        }

        // 1. NAČÍTANIE TIKETU DŇA (TUTOVKA)
        async function loadTiketDna() {
            showPage('ticket-day');
            const div = document.getElementById('tiket-dna-result');
            const load = document.getElementById('tiket-dna-loading');
            div.innerHTML = '';
            load.style.display = 'block';

            try {
                const res = await fetch('/api/tiket-dna');
                const data = await res.json();
                load.style.display = 'none';
                renderTicket(data, div, "VIP TIKET DŇA");
            } catch(e) { load.innerHTML = "Chyba."; }
        }

        // 2. GENERÁTOR VLASTNÉHO TIKETU
        async function generujVlastny() {
            const risk = document.getElementById('riskLevel').value;
            const count = document.getElementById('matchCount').value;
            const league = document.getElementById('leagueSelect').value;
            
            const div = document.getElementById('custom-result');
            div.innerHTML = '<div style="text-align:center; color:var(--accent);">⏳ AI skladá tiket podľa požiadaviek...</div>';

            try {
                // Posielame parametre do backendu
                const res = await fetch(`/api/vlastny-tiket?risk=${risk}&count=${count}&league=${league}`);
                const data = await res.json();
                renderTicket(data, div, "TVOJ VLASTNÝ TIKET");
            } catch(e) { div.innerHTML = "Nepodarilo sa nájsť vhodné zápasy."; }
        }

        // FUNKCIA NA VYKRESLENIE TIKETU (VZHĽAD PAPIERA)
        function renderTicket(data, element, title) {
            let matchesHtml = '';
            let totalOdds = 1;

            if(data.length === 0) {
                element.innerHTML = '<p style="text-align:center; color:#ccc">Nenašli sa žiadne zápasy pre tento výber.</p>';
                return;
            }

            data.forEach(m => {
                totalOdds *= m.kurz;
                matchesHtml += `
                <div class="slip-row">
                    <div>
                        <div class="slip-meta">${m.liga}</div>
                        <div class="slip-match">${m.domaci} - ${m.hostia}</div>
                        <div style="font-size:13px; color:#555;">Tip: <b>${m.tip}</b></div>
                    </div>
                    <div class="slip-odds">${m.kurz.toFixed(2)}</div>
                </div>`;
            });

            element.innerHTML = `
            <div class="ticket-slip">
                <div class="slip-header">${title}</div>
                <div class="slip-body">
                    ${matchesHtml}
                </div>
                <div class="slip-footer">
                    <span style="font-size:14px; color:#555;">Celkový kurz</span>
                    <span class="total-odds">${totalOdds.toFixed(2)}</span>
                </div>
                <div style="background:#000; color:#fff; text-align:center; padding:10px; font-size:12px;">
                    DÔVERA AI: ${data[0].risk === 1 ? '95% (Vysoká)' : (data[0].risk === 2 ? '75% (Stredná)' : '40% (Risk)')}
                </div>
            </div>`;
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home():
    return html_content

# API 1: TIKET DŇA (Automaticky vyberie 2-3 najbezpečnejšie zápasy)
@app.get("/api/tiket-dna")
def get_tiket_dna():
    # Vyfiltrujeme len RISK 1 (Tutovky)
    safe_matches = [m for m in MATCH_DATABASE if m['risk'] == 1]
    # Vyberieme náhodne 3 z nich
    if len(safe_matches) >= 3:
        return random.sample(safe_matches, 3)
    return safe_matches

# API 2: VLASTNÝ TIKET (Podľa parametrov)
@app.get("/api/vlastny-tiket")
def get_vlastny_tiket(risk: int = 1, count: int = 2, league: str = "all"):
    # 1. Filter podľa rizika
    filtered = [m for m in MATCH_DATABASE if m['risk'] == risk]
    
    # 2. Filter podľa ligy (ak nie je 'all')
    if league != "all":
        filtered = [m for m in filtered if m['liga'] == league]
    
    # 3. Ak nemáme dosť zápasov, vrátime prázdny list
    if len(filtered) < count:
        # Fallback: ak nenájde v lige, vráti aspoň podľa rizika z iných líg (aby nebol prázdny)
        filtered = [m for m in MATCH_DATABASE if m['risk'] == risk]
    
    # 4. Výber náhodného počtu
    if len(filtered) >= count:
        return random.sample(filtered, count)
    
    return filtered

class WhopInput(BaseModel):
    message: str

@app.post("/whop")
def whop(data: WhopInput):
    return {"status": "ok"}
