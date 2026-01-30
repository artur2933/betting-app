from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend import models, crud, database, ai 
from pydantic import BaseModel
import random

# 1. Inicializácia databázy
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

# 2. HTML GRAFIKA - PRO VERZIA (Tmavý dizajn, Grafy, Analýzy)
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betting PRO Analytics</title>
    <style>
        body { margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; background-color: #0b0c10; color: #c5c6c7; display: flex; height: 100vh; overflow: hidden; }
        
        /* Sidebar */
        .sidebar { width: 260px; background-color: #1f2833; display: flex; flex-direction: column; padding: 20px; border-right: 1px solid #45a29e; }
        .logo { font-size: 24px; font-weight: bold; color: #66fcf1; margin-bottom: 40px; text-transform: uppercase; letter-spacing: 2px; text-align: center; }
        .menu-item { padding: 15px; margin-bottom: 5px; cursor: pointer; border-radius: 5px; color: #fff; font-weight: 500; transition: 0.3s; display: flex; align-items: center; gap: 10px; }
        .menu-item:hover, .menu-item.active { background-color: #45a29e; color: #0b0c10; box-shadow: 0 0 10px rgba(102, 252, 241, 0.4); }
        
        /* Main Content */
        .main-content { flex: 1; padding: 30px; overflow-y: auto; background: radial-gradient(circle at top, #1f2833 0%, #0b0c10 80%); }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 2px solid #45a29e; padding-bottom: 15px; }
        .header h1 { margin: 0; color: #fff; }
        
        /* Tlačidlo */
        .btn-analyze { 
            background: linear-gradient(45deg, #45a29e, #66fcf1); border: none; padding: 15px 40px; 
            font-size: 18px; font-weight: bold; color: #0b0c10; border-radius: 30px; cursor: pointer; 
            box-shadow: 0 0 20px rgba(102, 252, 241, 0.3); transition: transform 0.2s;
            display: block; margin: 0 auto 30px auto;
        }
        .btn-analyze:hover { transform: scale(1.05); }

        /* KARTA ZÁPASU */
        .match-card { 
            background: #1f2833; border-radius: 10px; margin-bottom: 25px; overflow: hidden; 
            border: 1px solid #333; box-shadow: 0 5px 15px rgba(0,0,0,0.5);
            animation: slideUp 0.5s ease;
        }
        
        .match-header { 
            background: #0b0c10; padding: 15px; display: flex; justify-content: space-between; align-items: center; 
            border-bottom: 1px solid #45a29e;
        }
        .teams { font-size: 20px; font-weight: bold; color: white; }
        .league { font-size: 14px; color: #66fcf1; font-weight: bold; }
        
        .match-body { padding: 20px; display: flex; gap: 20px; flex-wrap: wrap; }
        
        /* Ľavá časť - Štatistiky */
        .stats-col { flex: 1; min-width: 250px; border-right: 1px solid #333; padding-right: 20px; }
        .stat-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }
        .stat-bar { height: 6px; background: #333; border-radius: 3px; overflow: hidden; margin-top: 2px; }
        .stat-fill { height: 100%; background: #66fcf1; }

        /* Pravá časť - AI Analýza */
        .analysis-col { flex: 1.5; min-width: 250px; padding-left: 10px; }
        .prediction-box { 
            background: rgba(69, 162, 158, 0.2); padding: 15px; border-radius: 5px; 
            border-left: 4px solid #66fcf1; margin-bottom: 15px;
        }
        .prediction-title { color: #66fcf1; font-weight: bold; font-size: 12px; text-transform: uppercase; }
        .prediction-value { font-size: 20px; font-weight: bold; color: white; margin-top: 5px; }
        .reason-text { font-size: 14px; color: #ccc; line-height: 1.6; font-style: italic; }

        .page { display: none; }
        .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="logo">⚡ BET PRO</div>
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="showPage('generator', this)">📊 Analýza Zápasov</div>
        <div class="menu-item" onclick="showPage('history', this)">📜 História</div>
    </div>

    <div class="main-content">
        
        <div id="home" class="page active">
            <div class="header"><h1>Prehľad Trhu</h1></div>
            <div style="display:flex; gap:20px;">
                <div style="background:#1f2833; padding:20px; flex:1; border-radius:10px;">
                    <h3>💰 Tvoj Bankroll</h3>
                    <h1 style="color:#66fcf1">€2,450.00</h1>
                    <small style="color:#888">Simulovaný stav</small>
                </div>
                <div style="background:#1f2833; padding:20px; flex:1; border-radius:10px;">
                    <h3>📈 Úspešnosť Modelu</h3>
                    <h1 style="color:#66fcf1">78.4%</h1>
                    <small style="color:#888">Posledných 30 dní</small>
                </div>
            </div>
            
            <div style="margin-top: 30px; padding: 20px; background: #151b24; border-radius: 10px; border: 1px solid #333;">
                <h3 style="color: #66fcf1;">📢 Novinky v systéme</h3>
                <p>Pridaná podpora pre detailné štatistiky xG (Očakávané góly). Prejdi do sekcie <b>Analýza Zápasov</b> a vyskúšaj nový generátor.</p>
            </div>
        </div>

        <div id="generator" class="page">
            <div class="header"><h1>AI Analýza & Tipy</h1></div>
            
            <div style="text-align:center; margin-bottom:30px;">
                <p>Klikni a nechaj AI spracovať štatistiky dnešných zápasov.</p>
                <button class="btn-analyze" onclick="generujTiket()">🚀 Skenovať Ponuku</button>
            </div>

            <div id="loading" style="display:none; text-align:center; color:#66fcf1; margin-top: 50px;">
                <h2>⏳ Sťahujem dáta o strelách, držaní lopty a forme...</h2>
                <p>Prosím čakaj, prebieha hĺbková analýza.</p>
            </div>

            <div id="results"></div>
        </div>

        <div id="history" class="page">
            <div class="header"><h1>História</h1></div>
            <p>Zatiaľ žiadne uzavreté tikety.</p>
        </div>

    </div>

    <script>
        function showPage(id, el) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            if(el) el.classList.add('active');
        }

        async function generujTiket() {
            const out = document.getElementById('results');
            const load = document.getElementById('loading');
            out.innerHTML = '';
            load.style.display = 'block';

            try {
                const res = await fetch('/api/generuj-tiket');
                const data = await res.json();
                load.style.display = 'none';

                let html = '';
                data.forEach(m => {
                    let homePower = m.stats.utok_domaci; 
                    let awayPower = m.stats.utok_hostia;

                    html += `
                    <div class="match-card">
                        <div class="match-header">
                            <div class="teams">${m.domaci} vs ${m.hostia}</div>
                            <div class="league">Kurz: ${m.kurz}</div>
                        </div>
                        <div class="match-body">
                            <div class="stats-col">
                                <div style="color:#888; margin-bottom:10px; font-size:12px; font-weight:bold;">KĽÚČOVÉ ŠTATISTIKY</div>
                                
                                <div class="stat-row">
                                    <span>Gólový priemer</span>
                                    <span>${m.stats.goly_priemer}</span>
                                </div>
                                <div class="stat-row">
                                    <span>xG (Očakávané góly)</span>
                                    <span>${m.stats.xg_data}</span>
                                </div>
                                
                                <div style="margin-top:15px;">
                                    <div class="stat-row"><span>Sila Útoku (Domáci)</span><span>${homePower}%</span></div>
                                    <div class="stat-bar"><div class="stat-fill" style="width:${homePower}%"></div></div>
                                </div>
                                <div style="margin-top:10px;">
                                    <div class="stat-row"><span>Sila Útoku (Hostia)</span><span>${awayPower}%</span></div>
                                    <div class="stat-bar"><div class="stat-fill" style="width:${awayPower}%"></div></div>
                                </div>
                            </div>

                            <div class="analysis-col">
                                <div class="prediction-box">
                                    <div class="prediction-title">ODPORÚČANÝ TIP</div>
                                    <div class="prediction-value">${m.tip}</div>
                                </div>
                                <div class="reason-text">
                                    "<b>${m.analyza_titulek}</b>"<br>
                                    ${m.analyza_text}
                                </div>
                            </div>
                        </div>
                    </div>
                    `;
                });
                out.innerHTML = html;
            } catch(e) { 
                load.style.display = 'none';
                alert("Chyba spojenia so serverom."); 
            }
        }
    </script>
</body>
</html>
"""

# 3. BACKEND - OPRAVENÁ SYNTAX A DÁTA
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def home(): 
    return html_content

@app.get("/api/generuj-tiket")
def generuj_denny_tiket(db: Session = Depends(get_db)):
    # Simulácia PROFESIONÁLNYCH DÁT (kým napojíme live API)
    profesionalne_data = [
        {
            "domaci": "Manchester United",
            "hostia": "PAOK Solún",
            "kurz": 1.25,
            "tip": "Manchester zvíťazí a Over 2.5",
            "stats": {
                "goly_priemer": "2.4 - 0.8",
                "xg_data": "1.85 vs 0.42",
                "utok_domaci": 85,
                "utok_hostia": 30
            },
            "analyza_titulek": "Jasná dominancia na Old Trafford",
            "analyza_text": "United má doma priemer 18 striel na bránu proti slabším tímom. PAOK má problémy v obrane (inkasovali 5 gólov v posledných 3 zápasoch). Očakávame rýchly gól."
        },
        {
            "domaci": "Lazio Rím",
            "hostia": "FC Porto",
            "kurz": 1.75,
            "tip": "Obaja dajú gól (BTTS)",
            "stats": {
                "goly_priemer": "1.8 - 1.9",
                "xg_data": "1.20 vs 1.35",
                "utok_domaci": 65,
                "utok_hostia": 70
            },
            "analyza_titulek": "Otvorený ofenzívny futbal",
            "analyza_text": "Lazio doma skórovalo v 9 z 10 zápasov. Porto má smrtiace protiútoky. Štatistika xG naznačuje, že čisté konto tu neudrží nikto."
        },
        {
            "domaci": "Galatasaray",
            "hostia": "Tottenham",
            "kurz": 2.10,
            "tip": "Viac ako 3.5 gólov",
            "stats": {
                "goly_priemer": "3.1 - 2.8",
                "xg_data": "2.40 vs 2.10",
                "utok_domaci": 90,
                "utok_hostia": 88
            },
            "analyza_titulek": "Gólová prestrelka v Istanbule",
            "analyza_text": "Osimhen proti útoku Spurs. Oba tímy ignorujú obranu a hrajú na góly. Posledné zápasy oboch tímov skončili divoko (4:3, 3:2). Value bet na góly."
        }
    ]
    return profesionalne_data

class WhopInput(BaseModel):
    message: str

@app.post("/whop")
def whop(data: WhopInput): 
    return {"status": "ok"}
