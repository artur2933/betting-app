import os
import sys
from pyngrok import ngrok, conf
import time

# -------------------------------------------------------------
# TU VLOŽ SVOJ TOKEN:
NGROK_TOKEN = "cr_38isvRbTFnH1DqA3ZPtC53qD3AL" 
# (Dal som tam ten tvoj z obrazka, ak sa nezmenil, nechaj tak)
# -------------------------------------------------------------

# 1. Povieme Pythonu, kde presne je ngrok.exe
# (Hľadá ho v hlavnom priečinku betting-app)
cesta_k_exe = os.path.join(os.getcwd(), "ngrok.exe")

print(f"--- Hľadám ngrok tu: {cesta_k_exe} ---")

if not os.path.exists(cesta_k_exe):
    print("❌ CHYBA: Nevidím súbor ngrok.exe!")
    print("Uisti sa, že súbor 'ngrok.exe' je v priečinku betting-app (vedľa main.py).")
    sys.exit()

# 2. Nastavíme konfiguráciu
conf.get_default().ngrok_path = cesta_k_exe
ngrok.set_auth_token(NGROK_TOKEN)

# 3. Spustíme tunel
print("--- Štartujem tunel... ---")
try:
    public_url = ngrok.connect(8000).public_url
    print("\n🎉 HOTOVO! Tvoja verejná adresa je:")
    print(f"👉 {public_url} 👈")
    print("\n(Nechaj toto okno bežať, nevypínaj ho)")

    # Udržíme to pri živote
    while True:
        time.sleep(1)
except Exception as e:
    print(f"\n❌ CHYBA PRI SPUSTENÍ: {e}")
    print("Skús reštartovať počítač, ak chyba pretrváva.")
    python backend/tunel.py