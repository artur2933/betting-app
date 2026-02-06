import requests
import random
import time
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

# ==========================================
# 🔑 API KĽÚČ
# ==========================================
API_KEY = "3e42c726ab364fb9eeede03b0017964c"
# ==========================================

# --- DATABÁZA TÍMOV PRE ZÁCHRANU (Smart Fallback) ---
# Ak API nevráti zápasy (napr. ráno sa nehrá Premier League), 
# systém použije tieto tímy na vygenerovanie realistickej predikcie.
TEAMS_DB = {
    "Premier League": ["Man City", "Arsenal", "Liverpool", "Aston Villa", "Tottenham", "Man Utd", "Newcastle", "West Ham", "Chelsea", "Brighton"],
    "La Liga": ["Real Madrid", "Girona", "Barcelona", "Atl. Madrid", "Ath. Bilbao", "Real Sociedad", "Betis", "Valencia", "Las Palmas", "Getafe"],
    "Bundesliga": ["Leverkusen", "Bayern", "Stuttgart", "Dortmund", "Leipzig", "Frankfurt", "Hoffenheim", "Freiburg", "Heidenheim", "Augsburg"],
    "Serie A": ["Inter", "Juventus", "AC Milan", "Bologna", "AS Roma", "Atalanta", "Napoli", "Fiorentina", "Lazio", "Torino"],
    "Europa League": ["Liverpool", "Leverkusen", "AC Milan", "West Ham", "Roma", "Villarreal", "Marseille", "Sporting", "Benfica", "Rangers"]
}

CACHE = {"data": [], "last_update": 0}

def get_live_data_or_fallback(league_filter="all", risk_filter=1):
    matches = []
    
    # 1. SKÚSIME LIVE API
    if API_KEY != "VLOZ_SVOJ_API_KLUC_SEM":
        # Cache check (60 min)
        if time.time() - CACHE["last_update"] < 3600 and CACHE["data"]:
             matches = CACHE["data"]
        else:
            try:
                url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?regions=eu&markets=h2h&apiKey={API_KEY}"
                response = requests.get(url)
                if response.status_code == 200:
                    raw_data = response.json()
                    # Spracovanie API dát
                    for item in raw_data:
                        try:
                            odds = item['bookmakers'][0]['markets'][0]['outcomes']
                            h, a = item['home_team'], item['away_team']
                            o1 = next((x['price'] for x in odds if x['name'] == h), 0)
                            o2 = next((x['price'] for x in odds if x['name'] == a), 0)
                            if o1 == 0 or o2 == 0: continue
                            
                            # Logika rizika
                            r = 1 if o1 < 1.55 or o2 < 1.55 else (2 if o1 < 2.2 else 3)
                            t = "1" if o1 < o2 else "2"
                            if r == 3: t = "X"
                            
                            l = item['sport_title'].replace("Soccer ", "") # Zjednodušenie názvu ligy

                            matches.append({
                                "domaci": h, "hostia": a, "kurz": o1 if t=="1" else (o2 if t=="2" else 3.10),
                                "tip": t, "risk": r, "liga": l, "source": "LIVE"
                            })
                        except: continue
                    CACHE["data"] = matches
                    CACHE["last_update"] = time.time()
            except: pass

    # 2. FILTROVANIE
    filtered = []
    
    # Filter Ligy
    if league_filter != "all":
        # Hľadáme zhodu v názve ligy (napr. "Premier League" v "EPL")
        filtered = [m for m in matches if league_filter.lower() in m['liga'].lower()]
    else:
        filtered = matches

    # Filter Rizika
    filtered = [m for m in filtered if m['risk'] == risk_filter]

    # 3. SMART FALLBACK (Ak API nenašlo nič, vygenerujeme realistické dáta)
    # Toto zabezpečí, že generátor bude fungovať VŽDY.
    if len(filtered) < 3:
        target_league = league_filter if league_filter != "all" else random.choice(list(TEAMS_DB.keys()))
        teams_list = TEAMS_DB.get(target_league, TEAMS_DB["Premier League"])
        
        needed = 5 - len(filtered)
        for _ in range(needed):
            t1, t2 = random.sample(teams_list, 2)
            
            # Generovanie kurzu podľa rizika
            if risk_filter == 1: # Nízke
                k = round(random.uniform(1.15, 1.45), 2)
                tip = "1"
            elif risk_filter == 2: # Stredné
                k = round(random.uniform(1.75, 2.15), 2)
                tip = "1"
            else: # Vysoké
                k = round(random.uniform(2.80, 3.80), 2)
                tip = "X"

            filtered.append({
                "domaci": t1, "hostia": t2, "kurz": k, "tip": tip, 
                "risk": risk_filter, "liga": target_league, "source": "AI_GEN"
            })

    return filtered

# --- API ENDPOINTS ---

@app.get("/api/analyza")
def api_analyza():
    # Pre analýzu vrátime mix všetkého
    return get_live_data_or_fallback(league_filter="all", risk_filter=1) + get_live_data_or_fallback(league_filter="all", risk_filter=2)

@app.get("/api/tiket-dna")
def api_ticket_day():
    # Tiket dňa je vždy Risk 1 (Bezpečný) a mix líg
    data = get_live_data_or_fallback(league_filter="all", risk_filter=1)
    return data[:3]

@app.get("/api/vlastny-tiket")
def api_custom(risk: int = 1, count: int = 2, league: str = "all"):
    # Tu sa deje mágia filtrovania
    data = get_live_data_or_fallback(league_filter=league, risk_filter=risk)
    # Vrátime náhodný výber z dostupných/vygenerovaných
    if len(data) >= count:
        return random.sample(data, count)
    return data[:count]

# --- FRONTEND ---
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
        :root { --bg-dark: #050a10; --bg-card: #151b24; --primary: #66fcf1; --text-main: #c5c6c7; --green: #00ff88; --red: #ff4444; --yellow: #ffcc00; }
        body { margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; background-color: #0b0c10; color: var(--text-main); height: 100vh; overflow: hidden; display: flex; }
        
        .sidebar { width: 260px; background-color: #111; display: flex; flex-direction: column; padding: 25px; border-right: 1px solid #333; }
        .logo { font-size: 24px; font-weight: 800; color: var(--primary); margin-bottom: 40px; text-transform: uppercase; text-align: center; text-shadow: 0 0 10px rgba(102, 252, 241, 0.4); }
        .menu-item { padding: 15px; margin-bottom: 5px; cursor: pointer; border-radius: 8px; color: #888; font-weight: 600; transition: 0.3s; }
        .menu-item:hover, .menu-item.active { background-color: #1f2833; color: #fff; border-left: 4px solid var(--primary); }
        
        .main-content { flex: 1; padding: 40px; overflow-y: auto; background: radial-gradient(circle at top right, #1f2833 0%, #0b0c10 80%); }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; border-bottom: 1px solid #333; padding-bottom: 20px; }
        
        .dash-card { background: var(--bg-card); padding: 25px; border-radius: 16px; border: 1px solid #2c3e50; flex: 1; margin-right: 20px; text-align: center; }
        .dash-card h1 { font-size: 40px; color: white; margin: 10px 0; }
        
        .btn-analyze { background: var(--primary); border: none; padding: 15px 40px; font-size: 16px; font-weight: 800; color: #0b0c10; border-radius: 50px; cursor: pointer; box-shadow: 0 0 25px rgba(102, 252, 241, 0.3); transition: 0.2s; text-transform: uppercase; }
        .btn-analyze:hover { transform: scale(1.05); background: #fff; }
        .btn-bet { background: transparent; border: 1px solid var(--primary); color: var(--primary); padding: 8px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; margin-top: 10px; width: 100%; }
        .btn-bet:hover { background: var(--primary); color: black; }

        .analysis-card { background: #11161d; border-radius: 12px; margin-bottom: 20px; border: 1px solid #2c3e50; padding: 20px; animation: slideUp 0.5s ease; }
        .ac-header { padding: 15px; background: #151b24; border-bottom: 1px solid #2c3e50; display: flex; justify-content: space-between; align-items: center; }
        
        .ticket-wrapper { max-width: 600px; margin: 0 auto 30px auto; background: #151b24; border: 2px solid var(--primary); border-radius: 12px; overflow: hidden; animation: slideUp 0.5s ease; }
        .ticket-header { background: rgba(102, 252, 241, 0.1); padding: 20px; text-align: center; border-bottom: 1px solid var(--primary); }
        .ticket-row { display: flex; justify-content: space-between; padding: 15px; border-bottom: 1px dashed #444; }
        .ticket-footer { background: #0b0c10; padding: 20px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #333; }
        .btn-ticket { width: 100%; padding: 15px; background: var(--primary); border: none; font-weight: bold; cursor: pointer; color: black; font-size: 16px; text-transform: uppercase; }

        .gen-controls { max-width: 600px; margin: 0 auto; background: #151b24; padding: 30px; border-radius: 12px; }
        select { width: 100%; padding: 15px; background: #0b0c10; border: 1px solid #333; color: #fff; border-radius: 8px; font-size: 16px; margin-bottom: 20px; }

        .page { display: none; } .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        
        table { width: 100%; border-collapse: collapse; margin-top: 20px; color: #ccc; }
        th { text-align: left; padding: 10px; border-bottom: 1px solid #333; color:#666; font-size:12px; text-transform:uppercase; }
        td { padding: 15px 10px; border-bottom: 1px solid #222; }
        .win { color: var(--green); font-weight: bold; } .lose { color: var(--red); font-weight: bold; } .pending { color: var(--yellow); }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="logo">⚡ BET PRO</div>
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="showPage('generator', this)">📊 VIP Analýza</div>
        <div class="menu-item" onclick="showPage('ticket-day', this)">🎯 Tiket Dňa</div>
        <div class="menu-item" onclick="showPage('custom-ticket', this)">🛠️ Vlastný Tiket</div>
        <div class="menu-item" onclick="showPage('results-page', this); renderHistory()">✅ História</div>
        <div class="menu-item" onclick="resetApp()" style="margin-top:auto; color:var(--red)">🗑️ Resetovať</div>
    </div>

    <div class="main-content">
        <div class="header">
            <h1>Prehľad</h1>
            <div style="text-align:right;">
                <div style="font-size:12px; color:#666;">BANKROLL</div>
                <div style="font-size:32px; font-weight:bold; color:var(--primary);" id="bankroll-display">€1,000.00</div>
            </div>
        </div>

        <!-- 1. DASHBOARD -->
        <div id="home" class="page active">
            <div style="display:flex; margin-bottom:30px;">
                <div class="dash-card"><h3>Stav Konta</h3><h1 id="dash-bankroll">€1,000</h1></div>
                <div class="dash-card"><h3>Vyhodnotenie</h3><p style="color:#888; margin-bottom:10px;">Simulovať zápasy a pripísať výhry</p><button class="btn-analyze" style="padding:10px 30px; font-size:14px;" onclick="evaluateTickets()">🔄 Skontrolovať Tikety</button></div>
            </div>
            <div style="background:#151b24; padding:20px; border-radius:16px; border:1px solid #2c3e50;">
                <h3 style="color:#fff; margin:0 0 20px 0;">Vývoj Zisku</h3>
                <canvas id="profitChart" height="100"></canvas>
            </div>
        </div>

        <!-- 2. VIP ANALÝZA (Bez Vsaďiť) -->
        <div id="generator" class="page">
            <div style="text-align:center; margin-bottom:30px;">
                <button class="btn-analyze" onclick="loadAnalysis()">Načítať Live Analýzy</button>
            </div>
            <div id="analysis-output"></div>
        </div>

        <!-- 3. TIKET DŇA -->
        <div id="ticket-day" class="page">
            <div style="text-align:center; margin-bottom:30px;">
                <h2 style="color:var(--primary)">🔥 DENNÁ TUTOVKA</h2>
                <button class="btn-analyze" onclick="loadTiketDna()">VYGENEROVAŤ TIKET</button>
            </div>
            <div id="ticket-dna-result"></div>
        </div>

        <!-- 4. VLASTNÝ GENERÁTOR -->
        <div id="custom-ticket" class="page">
            <div class="gen-controls">
                <label style="color:var(--primary); font-weight:bold;">RIZIKO</label>
                <select id="riskLevel">
                    <option value="1">🟢 Nízke (1.2 - 1.5)</option>
                    <option value="2">🟡 Stredné (1.8 - 2.2)</option>
                    <option value="3">🔴 Vysoké (3.0+)</option>
                </select>
                <label style="color:var(--primary); font-weight:bold;">POČET ZÁPASOV</label>
                <select id="matchCount">
                    <option value="2">2 Zápasy</option>
                    <option value="3">3 Zápasy</option>
                    <option value="5">5 Zápasov</option>
                </select>
                <label style="color:var(--primary); font-weight:bold;">LIGA</label>
                <select id="leagueSelect">
                    <option value="all">Všetky</option>
                    <option value="Premier League">Premier League</option>
                    <option value="La Liga">La Liga</option>
                    <option value="Bundesliga">Bundesliga</option>
                    <option value="Serie A">Serie A</option>
                    <option value="Europa League">Europa League</option>
                </select>
                <button class="btn-analyze" style="width:100%" onclick="loadCustom()">GENEROVAŤ TIKET</button>
            </div>
            <div id="custom-ticket-output" style="margin-top:30px;"></div>
        </div>

        <!-- 5. HISTÓRIA -->
        <div id="results-page" class="page">
            <h2>Moje Tikety</h2>
            <div id="history-output"></div>
        </div>
    </div>

    <script>
        let bankroll = parseFloat(localStorage.getItem('betpro_bankroll')) || 1000.00;
        let history = JSON.parse(localStorage.getItem('betpro_history')) || [];
        updateUI();

        let chart;
        function initChart() {
            const ctx = document.getElementById('profitChart').getContext('2d');
            let dataPoints = history.length ? history.map(t => t.balance_after || 1000).reverse() : [1000, 1000];
            if(history.length === 0) dataPoints = [1000, 1000, 1000, 1000, 1000];
            if(chart) chart.destroy();
            chart = new Chart(ctx, {
                type: 'line',
                data: { labels: dataPoints.map((_, i) => ''), datasets: [{ label: 'Bankroll', data: dataPoints, borderColor: '#66fcf1', backgroundColor: 'rgba(102, 252, 241, 0.1)', fill: true, tension: 0.4 }] },
                options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#2c3e50' } }, x: { display: false } } }
            });
        }
        setTimeout(initChart, 500);

        function showPage(id, el) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            if(el) el.classList.add('active');
        }

        function updateUI() {
            document.getElementById('bankroll-display').innerText = '€' + bankroll.toFixed(2);
            document.getElementById('dash-bankroll').innerText = '€' + bankroll.toFixed(2);
            localStorage.setItem('betpro_bankroll', bankroll);
            localStorage.setItem('betpro_history', JSON.stringify(history));
        }

        function resetApp() { if(confirm("Naozaj?")) { localStorage.clear(); location.reload(); } }

        async function loadAnalysis() {
            const div = document.getElementById('analysis-output');
            div.innerHTML = '<p style="text-align:center;color:#66fcf1">Načítavam...</p>';
            const res = await fetch('/api/analyza'); const data = await res.json();
            let html = '';
            data.forEach(m => {
                html += `<div class="analysis-card"><div class="ac-header"><div style="font-size:24px; color:white; font-weight:bold;">${m.domaci} <span style="color:#666">vs</span> ${m.hostia}</div><div style="color:#66fcf1; font-weight:bold;">${m.kurz}</div></div><div class="ac-body" style="padding:20px; color:#ccc;"><p>Liga: ${m.liga}</p><p style="color:#888;">${m.analyza_text}</p><div class="ac-tip-box" style="margin-top:15px; border-left:4px solid #66fcf1; padding:10px; background:#1a2634;"><span style="color:white; font-weight:bold;">TIP: ${m.tip}</span></div></div></div>`;
            });
            div.innerHTML = html;
        }

        async function loadTiketDna() { renderTicketSection('/api/tiket-dna', 'ticket-dna-result', 'VIP TIKET DŇA'); }
        
        async function loadCustom() { 
            const r = document.getElementById('riskLevel').value; 
            const c = document.getElementById('matchCount').value;
            const l = document.getElementById('leagueSelect').value;
            renderTicketSection(`/api/vlastny-tiket?risk=${r}&count=${c}&league=${l}`, 'custom-ticket-output', 'TVOJ TIKET'); 
        }

        async function renderTicketSection(url, elId, title) {
            const div = document.getElementById(elId);
            div.innerHTML = '<p style="text-align:center;color:#66fcf1">Generujem...</p>';
            const res = await fetch(url); const data = await res.json();
            if(data.length === 0) { div.innerHTML = "Žiadne zápasy."; return; }
            
            let rows = ''; let total = 1; let ticketInfo = [];
            data.forEach(m => {
                total *= m.kurz; ticketInfo.push(`${m.domaci} (${m.tip})`);
                rows += `<div class="ticket-row"><div><div style="font-weight:bold; color:white;">${m.domaci} - ${m.hostia}</div><div style="color:#888; font-size:12px;">${m.liga}</div></div><div style="color:var(--primary); font-weight:bold;">${m.kurz}</div></div>`;
            });
            div.innerHTML = `<div class="ticket-wrapper"><div class="ticket-header"><h2 style="margin:0; color:var(--primary);">${title}</h2></div><div class="ticket-body">${rows}</div><div class="ticket-footer"><div style="color:#888;">CELKOVÝ KURZ</div><div style="font-size:24px; font-weight:bold; color:var(--primary);">${total.toFixed(2)}</div></div><button class="btn-ticket" onclick='saveTicket(${total.toFixed(2)}, ${JSON.stringify(ticketInfo)})'>VSAĎIŤ 50€</button></div>`;
        }

        function saveTicket(odds, matches) {
            if(bankroll < 50) { alert("Nemáš dosť peňazí!"); return; }
            bankroll -= 50;
            history.unshift({ matches: matches.join(", "), odds: odds, stake: 50, status: "PENDING", profit: 0, date: new Date().toLocaleString(), balance_after: bankroll });
            updateUI(); alert("Tiket uložený!"); initChart();
        }

        function evaluateTickets() {
            let changes = false;
            history.forEach(t => {
                if(t.status === "PENDING") {
                    let won = Math.random() < 0.60; 
                    t.status = won ? "WON" : "LOST";
                    t.profit = won ? (t.stake * t.odds) : 0;
                    if(won) bankroll += t.profit;
                    t.balance_after = bankroll;
                    changes = true;
                }
            });
            if(changes) { updateUI(); renderHistory(); initChart(); alert("Tikety vyhodnotené!"); } else { alert("Žiadne nové tikety."); }
        }

        function renderHistory() {
            const div = document.getElementById('history-output');
            if(history.length === 0) { div.innerHTML = "<p style='color:#666'>Žiadna história.</p>"; return; }
            let html = '<table style="width:100%; text-align:left; color:#ccc;"><tr><th>Dátum</th><th>Zápasy</th><th>Kurz</th><th>Stav</th><th>Zisk</th></tr>';
            history.forEach(t => {
                let color = t.status === "WON" ? "#00ff88" : (t.status === "LOST" ? "#ff4444" : "#ffcc00");
                html += `<tr><td>${t.date}</td><td>${t.matches}</td><td>${t.odds}</td><td style="color:${color}; font-weight:bold;">${t.status}</td><td>€${t.profit.toFixed(2)}</td></tr>`;
            });
            div.innerHTML = html + '</table>';
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home(): return html_content

class WhopInput(BaseModel): message: str
@app.post("/whop")
def whop(data: WhopInput): return {"status": "ok"}
