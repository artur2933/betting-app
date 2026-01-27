from sqlalchemy.orm import Session
from backend import models

# Funkcia 1: Prečítaj všetky zápasy
def get_vsetky_zapasy(db: Session):
    return db.query(models.Zapas).all()

# Funkcia 2: Vytvor nový zápas
def vytvor_zapas(db: Session, domaci: str, hostia: str, kurz: float, sanca: float):
    # Vypočítame, či je to value (použijeme jednoduchú logiku priamo tu)
    je_value = (sanca / 100 * kurz) > 1.0

    novy_zapas = models.Zapas(
        domaci=domaci,
        hostia=hostia,
        kurz=kurz,
        sanca=sanca,
        je_to_value=je_value
    )

    db.add(novy_zapas)  # Pridaj do "pamäte"
    db.commit()         # Ulož to natrvalo (ako Ctrl+S)
    db.refresh(novy_zapas) # Obnov dáta
    return novy_zapas