def vypocitaj_value(pravdepodobnost_percenta: float, kurz: float):
    """
    Vypočíta, či je kurz výhodný (Value Bet).
    Vzorec: (Pravdepodobnosť v % / 100) * Kurz
    Ak je výsledok viac ako 1.0, je to výhodné.
    """
    reala_sanca = pravdepodobnost_percenta / 100
    hodnota = reala_sanca * kurz
    
    # Zistíme, či sa to oplatí (musí to byť viac ako 1.0)
    oplati_sa = hodnota > 1.0
    
    # Výpočet, o koľko percent je to výhodné
    percento_vyhodnosti = (hodnota - 1) * 100

    return {
        "je_to_value": oplati_sa,
        "hodnota_index": round(hodnota, 2), # Zaokrúhlené na 2 desatinné miesta
        "ziskovost": f"{round(percento_vyhodnosti, 1)}%"
    }