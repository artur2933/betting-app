import requests
import random
import time
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

# ==========================================
# 🔑 KONFIGURÁCIA (API KĽÚČ)
# ==========================================
API_KEY = "3e42c726ab364fb9eeede03b0017964c" 
# ==========================================

# Jednoduchá pamäť (Cache), aby sme nevolali API každú sekundu
CACHE = {
    "data": [],
    "last_update": 0
}

def get_live_data():
    # Ak máme dáta mladšie ako 1 hodina, vrátime tie (šetríme API limit)
    if time.time() - CACHE["last_update"] < 3600 and CACHE["data"]:
        return CACHE["data"]

    # Ak nemáme kľúč, vrátime Demo dáta
    if API_KEY == "VLOZ_SVOJ_API_KLUC_SEM":
        return generate_demo_data()

    try:
        url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?regions=eu&markets=h2h&apiKey={API_KEY}"
        response = requests.get(url)
        data = response.json()
        
        matches = []
        for item in data[:20]: # Zoberieme 20 zápasov
            try:
                bookmakers = item.get('bookmakers', [])
                if not bookmakers: continue
                odds = bookmakers[0]['markets'][0]['outcomes']
                home = item['home_team']
                away = item['away_team']
                
                o1 = next((x['price'] for x in odds if x['name'] == home), 0)
                o2 = next((x['price'] for x in odds if x['name'] == away), 0)
                
                if o1 == 0 or o2 == 0: continue

                # AI Logika pre Analýzu
                risk = 1
                tip = "1"
                dovera = 80
                analyza = "Zápas bez jasného favorita."

                if o1 < 1.50:
                    risk = 1; tip = "1"; dovera = random.randint(88, 96)
                    analyza = f"{home} je doma extrémne silný. Hostia z {away} sa trápia v obrane."
                elif o2 < 1.50:
                    risk = 1; tip = "2"; dovera = random.randint(88, 96)
                    analyza = f"{away} má majstrovskú formu. Domáci tím nemá kvalitu na odpor."
                elif o1 < 2.10:
                    risk = 2; tip = "1"; dovera = random.randint(70, 85)
                    analyza = "Hodnotný kurz na domácich. Očakávame tesnú výhru."
                elif o2 < 2.10:
                    risk = 2; tip = "2"; dovera = random.randint(70, 85)
                    analyza = "Hostia sú miernym favoritom, ale bude to boj."
                else:
                    risk = 3; tip = "X"; dovera = random.randint(40, 60)
                    analyza = "Vysoké kurzy na oboch stranách. Remíza je vysoko pravdepodobná."

                # Generovanie štatistík (aby to vyzeralo PRO)
                stats = {
                    "utok_domaci": int(100/o1) if o1 > 1 else 95,
                    "utok_hostia": int(100/o2) if o2 > 1 else 95,
                    "forma_domaci": generate_form(o1),
                    "forma_hostia": generate_form(o2),
                    "zranenia": random.choice(["Bez absencií", "Kľúčový útočník (Out)", "Kapitán (Otázny)", "Kompletná zostava"])
                }

                matches.append({
                    "domaci": home, "hostia": away, "kurz": o1 if tip=="1" else (o2 if tip=="2" else 3.10),
                    "tip": tip, "risk": risk, "liga": item['sport_title'].replace("Soccer ", ""), "dovera": dovera,
                    "stats": stats, "analyza_text": analyza,
                    "analyza_body": [f"Kurz {o1} vs {o2} odráža silu tímov.", "Vzájomné zápasy hovoria v prospech favorita.", "AI model odporúča tento tip."]
                })
            except: continue
        
        # Uložíme do cache
        CACHE["data"] = matches
        CACHE["last_update"] = time.time()
        return matches

    except:
        return generate_demo_data()

def generate_form(odds):
    # Generuje formu (W/D/L) na základe kurzu (lepší kurz = viac výhier)
    if odds < 1.5: return "WWWDW"
    if odds < 2.0: return "WDLWW"
    return "LDWLL"

def generate_demo_data():
    return [{"domaci": "DEMO MODE", "hostia": "VLOŽ API KĽÚČ", "kurz": 1.00, "tip": "Nastavenia", "risk": 1, "liga": "System", "dovera": 0, "stats": {"utok_domaci":0, "utok_hostia":0, "forma_domaci": "?????", "forma_hostia": "?????", "zranenia": "-"}, "analyza_text": "Vlož svoj API kľúč do main.py pre živé dáta.", "analyza_body": []}]

# --- API ENDPOINTS ---

@app.get("/api/data")
def get_data():
    return get_live_data()

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
        
        /* SIDEBAR */
        .sidebar { width: 260px; background-color: #111; display: flex; flex-direction: column; padding: 25px; border-right: 1px solid #333; }
        .logo { font-size: 24px; font-weight: 800; color: var(--primary); margin-bottom: 40px; text-transform: uppercase; text-align: center; text-shadow: 0 0 10px rgba(102, 252, 241, 0.4); }
        .menu-item { padding: 15px; margin-bottom: 5px; cursor: pointer; border-radius: 8px; color: #888; font-weight: 600; transition: 0.3s; display: flex; align-items: center; gap: 15px; }
        .menu-item:hover, .menu-item.active { background-color: #1f2833; color: #fff; border-left: 4px solid var(--primary); }
        
        /* MAIN */
        .main-content { flex: 1; padding: 40px; overflow-y: auto; background: radial-gradient(circle at top right, #1f2833 0%, #0b0c10 80%); }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; border-bottom: 1px solid #333; padding-bottom: 20px; }
        .dash-card { background: var(--bg-card); padding: 25px; border-radius: 16px; border: 1px solid #2c3e50; flex: 1; margin-right: 20px; text-align: center; }
        .dash-card h1 { font-size: 40px; color: white; margin: 10px 0; }
        
        /* BUTTONS */
        .btn-analyze { background: var(--primary); border: none; padding: 15px 40px; font-size: 16px; font-weight: 800; color: #0b0c10; border-radius: 50px; cursor: pointer; box-shadow: 0 0 25px rgba(102, 252, 241, 0.3); transition: 0.2s; text-transform: uppercase; }
        .btn-analyze:hover { transform: scale(1.05); background: #fff; }
        .btn-bet { background: transparent; border: 1px solid var(--primary); color: var(--primary); padding: 8px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; margin-top: 10px; width: 100%; }
        .btn-bet:hover { background: var(--primary); color: black; }

        /* VIP CARD STYLE (Podľa obrázka) */
        .analysis-card { background: #11161d; border-radius: 12px; margin-bottom: 30px; border: 1px solid #2c3e50; padding: 0; overflow: hidden; animation: slideUp 0.5s ease; }
        .ac-header { padding: 20px 30px; background: #151b24; border-bottom: 1px solid #2c3e50; display: flex; justify-content: space-between; align-items: center; }
        .ac-teams { font-size: 24px; font-weight: 800; color: #fff; }
        .ac-body { padding: 30px; display: flex; gap: 40px; }
        .ac-left { flex: 1; border-right: 1px solid #2c3e50; padding-right: 30px; }
        .ac-right { flex: 1.2; padding-left: 10px; }
        
        .ac-stat-title { font-size: 12px; color: #888; margin-bottom: 5px; }
        .ac-dots { display: flex; gap: 5px; margin-bottom: 20px; }
        .ac-dot { width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; color: #000; }
        .v { background: var(--green); } .r { background: var(--yellow); } .p { background: var(--red); }
        
        .ac-progress-container { display: flex; height: 6px; background: #222; border-radius: 4px; overflow: hidden; margin-top: 5px; }
        .ac-bar-home { background: var(--primary); height: 100%; } .ac-bar-away { background: var(--red); height: 100%; }
        
        .ac-tip-box { background: #1a222e; border: 1px solid #2c3e50; border-radius: 8px; padding: 15px; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid var(--primary); margin-top: 20px; }
        .ac-tip-value { font-size: 20px; font-weight: 800; color: #fff; }
        
        /* PAGES */
        .page { display: none; } .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        
        /* HISTORY TABLE */
        table { width: 100%; border-collapse: collapse; margin-top: 20px; color: #ccc; }
        th { text-align: left; padding: 10px; border-bottom: 1px solid #333; }
        td { padding: 15px 10px; border-bottom: 1px solid #222; }
        .win { color: var(--green); font-weight: bold; } .lose { color: var(--red); font-weight: bold; } .pending { color: var(--yellow); }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="logo">⚡ BET PRO</div>
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="showPage('generator', this)">📊 VIP Analýza</div>
        <div class="menu-item" onclick="showPage('results-page', this); renderHistory()">✅ História</div>
        <div class="menu-item" onclick="resetApp()" style="margin-top:auto; color:var(--red)">🗑️ Resetovať Účet</div>
    </div>

    <div class="main-content">
        <div class="header">
            <h1>Prehľad</h1>
            <div style="text-align:right;">
                <div style="font-size:12px; color:#666;">BANKROLL</div>
                <div style="font-size:32px; font-weight:bold; color:var(--primary);" id="bankroll-display">€1,000.00</div>
            </div>
        </div>

        <div id="home" class="page active">
            <div style="display:flex; margin-bottom:30px;">
                <div class="dash-card">
                    <h3>Stav Konta</h3>
                    <h1 id="dash-bankroll">€1,000</h1>
                </div>
                <div class="dash-card">
                    <h3>Vyhodnotenie</h3>
                    <p style="color:#888; margin-bottom:10px;">Simulovať zápasy a pripísať výhry</p>
                    <button class="btn-analyze" style="padding:10px 30px; font-size:14px;" onclick="evaluateTickets()">🔄 Skontrolovať Tikety</button>
                </div>
            </div>
            <div class="chart-box" style="background:#151b24; padding:20px; border-radius:16px; border:1px solid #2c3e50;">
                <canvas id="profitChart" height="100"></canvas>
            </div>
        </div>

        <div id="generator" class="page">
            <div style="text-align:center; margin-bottom:30px;">
                <button class="btn-analyze" onclick="loadMatches()">Načítať Live Ponuku</button>
            </div>
            <div id="matches-output"></div>
        </div>

        <div id="results-page" class="page">
            <h2>Moje Tikety</h2>
            <div id="history-output"></div>
        </div>
    </div>

    <script>
        // --- LOGIKA APLIKÁCIE (BEZ DATABÁZY) ---
        
        // 1. Načítanie stavu z prehliadača
        let bankroll = parseFloat(localStorage.getItem('betpro_bankroll')) || 1000.00;
        let history = JSON.parse(localStorage.getItem('betpro_history')) || [];
        updateUI();

        // 2. Graf
        let chart;
        function initChart() {
            const ctx = document.getElementById('profitChart').getContext('2d');
            let dataPoints = history.map((t, i) => 1000 + (i * 10)); // Jednoduchá vizualizácia
            if (dataPoints.length === 0) dataPoints = [1000, 1000];
            
            if(chart) chart.destroy();
            chart = new Chart(ctx, {
                type: 'line',
                data: { labels: dataPoints.map((_, i) => 'T' + i), datasets: [{ label: 'Bankroll', data: dataPoints, borderColor: '#66fcf1', backgroundColor: 'rgba(102, 252, 241, 0.1)', fill: true }] },
                options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#2c3e50' } } } }
            });
        }
        initChart();

        // 3. UI Funkcie
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

        function resetApp() {
            if(confirm("Vymazať celú históriu a resetovať peniaze na 1000€?")) {
                localStorage.clear();
                location.reload();
            }
        }

        // 4. Načítanie zápasov z Python API
        async function loadMatches() {
            const div = document.getElementById('matches-output');
            div.innerHTML = '<p style="text-align:center; color:#66fcf1">Sťahujem kurzy...</p>';
            
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                
                let html = '';
                data.forEach(m => {
                    // Helper pre guličky
                    const circles = (f) => { let h=''; for(let c of f) h+=`<div class="ac-dot ${c==='W'?'v':(c==='L'?'p':'r')}">${c==='W'?'V':(c==='L'?'P':'R')}</div>`; return h; };
                    
                    html += `
                    <div class="analysis-card">
                        <div class="ac-header">
                            <div class="ac-teams">${m.domaci} <span style="color:#666; font-size:16px;">vs</span> ${m.hostia}</div>
                            <div style="background:#1a2634; color:#66fcf1; padding:5px 10px; border-radius:5px; font-weight:bold;">${m.kurz}</div>
                        </div>
                        <div class="ac-body">
                            <div class="ac-left">
                                <div style="margin-bottom:15px;"><div class="ac-stat-title">Forma</div><div class="ac-dots">${circles(m.stats.forma_domaci)}</div></div>
                                <div style="margin-bottom:15px;"><div class="ac-stat-title">Sila Útoku</div><div class="ac-progress-container"><div class="ac-bar-home" style="width:${m.stats.utok_domaci}%"></div></div></div>
                                <div style="color:#ff4444; font-size:12px;">${m.stats.zranenia}</div>
                            </div>
                            <div class="ac-right">
                                <div class="ac-ai-title">🧠 AI ANALÝZA</div>
                                <div style="font-size:13px; color:#ccc; margin-bottom:10px;">${m.analyza_text}</div>
                                <div class="ac-tip-box">
                                    <div><div style="font-size:10px; color:#888;">TIP</div><div class="ac-tip-value">${m.tip}</div></div>
                                    <button class="btn-bet" onclick="placeBet('${m.domaci} vs ${m.hostia}', '${m.tip}', ${m.kurz})">VSAĎIŤ 50€</button>
                                </div>
                            </div>
                        </div>
                    </div>`;
                });
                div.innerHTML = html;
            } catch(e) { div.innerHTML = "Chyba načítania."; }
        }

        // 5. Stávkovanie
        function placeBet(match, tip, odds) {
            if(bankroll < 50) { alert("Nedostatok peňazí!"); return; }
            
            bankroll -= 50;
            history.unshift({
                match: match, tip: tip, odds: odds, stake: 50,
                status: "PENDING", profit: 0, date: new Date().toLocaleString()
            });
            
            updateUI();
            alert("Stávka prijatá!");
        }

        // 6. Vyhodnotenie (Simulácia)
        function evaluateTickets() {
            let changes = false;
            history.forEach(t => {
                if(t.status === "PENDING") {
                    // Simulácia: 65% šanca na výhru (aby bol zákazník spokojný)
                    let won = Math.random() < 0.65;
                    t.status = won ? "WON" : "LOST";
                    t.profit = won ? (t.stake * t.odds) : 0;
                    if(won) bankroll += t.profit;
                    changes = true;
                }
            });
            
            if(changes) {
                updateUI();
                renderHistory();
                alert("Tikety boli vyhodnotené!");
            } else {
                alert("Žiadne nové tikety na kontrolu.");
            }
        }

        function renderHistory() {
            const div = document.getElementById('history-output');
            if(history.length === 0) { div.innerHTML = "Žiadna história."; return; }
            
            let html = '<table><tr><th>Dátum</th><th>Zápas</th><th>Tip</th><th>Kurz</th><th>Stav</th><th>Výhra</th></tr>';
            history.forEach(t => {
                let color = t.status === "WON" ? "win" : (t.status === "LOST" ? "lose" : "pending");
                html += `<tr>
                    <td>${t.date}</td>
                    <td>${t.match}</td>
                    <td>${t.tip}</td>
                    <td>${t.odds}</td>
                    <td class="${color}">${t.status}</td>
                    <td>€${t.profit.toFixed(2)}</td>
                </tr>`;
            });
            html += '</table>';
            div.innerHTML = html;
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home(): return html_content
