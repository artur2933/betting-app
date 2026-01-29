from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend import models, crud, database, ai 
from pydantic import BaseModel

models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Betting AI</title>
    <style>
        body { background-color: #000; color: #fff; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        h1 { color: #0f0; margin-bottom: 20px; }
        input { padding: 15px; border-radius: 5px; border: none; width: 250px; text-align: center; font-size: 18px; margin-bottom: 10px;}
        button { padding: 15px 40px; background-color: #0f0; color: #000; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; font-size: 18px; }
        button:hover { background-color: #0c0; }
        #vysledok { margin-top: 20px; font-size: 20px; border: 1px solid #333; padding: 20px; border-radius: 10px; background: #111; display: none; }
    </style>
</head>
<body>
    <h1>🎰 AI Analytik</h1>
    <input type="number" id="zapasId" placeholder="Zadaj ID zápasu">
    <button onclick="analyzuj()">Analyzovať</button>
    <div id="vysledok"></div>

    <script>
        async function analyzuj() {
            const id = document.getElementById('zapasId').value;
            const div = document.getElementById('vysledok');
            if(!id) return;
            div.style.display = 'block';
            div.innerHTML = '⏳ Premýšľam...';
            try {
                const res = await fetch(`/analyzuj/${id}`);
                const data = await res.json();
                div.innerHTML = data.chyba ? data.chyba : `<b>${data.zapas}</b><br><br>💡 ${data.AI_Analytik_Hovori}`;
            } catch (e) { div.innerHTML = 'Chyba spojenia.'; }
        }
    </script>
</body>
</html>
"""

def get_db():
    db = database.SessionLocal(); try: yield db; finally: db.close()

@app.get("/", response_class=HTMLResponse)
def home(): return html_content

@app.get("/analyzuj/{zapas_id}")
def api_analyzuj(zapas_id: int, db: Session = Depends(get_db)):
    z = db.query(models.Zapas).filter(models.Zapas.id == zapas_id).first()
    if not z: return {"chyba": "Zápas nenájdený"}
    return {"zapas": f"{z.domaci} vs {z.hostia}", "AI_Analytik_Hovori": ai.analyzuj_zapas_cez_ai(z.domaci, z.hostia, z.kurz, z.sanca)}

class WhopInput(BaseModel): message: str
@app.post("/whop")
def whop(data: WhopInput): return {"status": "ok"}
