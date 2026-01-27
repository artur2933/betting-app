import sys
import os
sys.path.append(os.getcwd())

from playwright.sync_api import sync_playwright
from backend.database import SessionLocal
from backend import crud

def spusti_robota():
    print("--- ⚽ ROBOT: Idem na Flashscore (Verzia 3.1 - S okuliarmi) ---")
    
    db = SessionLocal()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) 
        page = browser.new_page()
        
        try:
            print("Načítavam stránku...")
            page.goto("https://www.flashscore.sk/", timeout=60000)
            
            # 1. COOKIES
            try:
                page.locator("#onetrust-accept-btn-handler").click(timeout=3000)
            except:
                try:
                    page.get_by_role("button", name="Súhlasím", exact=False).click(timeout=3000)
                except:
                    pass

            print("Hľadám tímy...")
            page.wait_for_selector("div[class*='participant']", timeout=15000)
            
            # Stiahneme texty
            vsetky_timy = page.locator("div[class*='participant']").all_inner_texts()
            
            # 2. INTELIGENTNÉ ČISTENIE (Odstránime duplikáty)
            # Flashscore dáva [Arsenal, Arsenal, Liverpool, Liverpool...]
            # My zoberieme len každé druhé slovo, ak sú rovnaké
            unikatne_timy = []
            for tim in vsetky_timy:
                tim = tim.replace("\n", " ").strip()
                if len(tim) > 2:
                    # Ak je to nový tím, pridáme ho. Ak je to ten istý ako posledný, ignorujeme.
                    if not unikatne_timy or unikatne_timy[-1] != tim:
                        unikatne_timy.append(tim)

            print(f"✅ Našiel som {len(unikatne_timy)} unikátnych tímov.")
            
            # 3. PÁROVANIE (Domáci vs Hostia)
            for i in range(0, len(unikatne_timy) - 1, 2):
                if i+1 < len(unikatne_timy):
                    domaci = unikatne_timy[i]
                    hostia = unikatne_timy[i+1]
                    
                    # Ochrana proti nezmyslom
                    if "Séria" in domaci or "Postup" in domaci:
                        continue

                    print(f"Ukladám: {domaci} vs {hostia}")
                    
                    crud.vytvor_zapas(
                        db=db,
                        domaci=domaci,
                        hostia=hostia,
                        kurz=2.10, # Kurz stále simulujeme (zajtra dáme realitu)
                        sanca=50
                    )

            print("--- ✅ Misia úspešná! Dáta sú opravené. ---")

        except Exception as e:
            print(f"❌ CHYBA: {e}")
            page.screenshot(path="chyba_oprava.png")

        browser.close()
    
    db.close()

if __name__ == "__main__":
    spusti_robota()