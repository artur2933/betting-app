from openai import OpenAI

# ---------------------------------------------------------
# TU VLOŽ SVOJ KĽÚČ (medzi úvodzovky):
MOJ_API_KLUC = "cr_38isvRbTFnH1DqA3ZPtC53qD3AL" 
# ---------------------------------------------------------

client = OpenAI(api_key=MOJ_API_KLUC)

def analyzuj_zapas_cez_ai(domaci, hostia, kurz, sanca):
    """
    Pošle dáta do ChatGPT a vypýta si krátku analýzu.
    """
    prompt = f"""
    Si profesionálny stávkový poradca. Analyzuj tento zápas:
    Zápas: {domaci} vs {hostia}
    Kurz stávkovej kancelárie: {kurz}
    Naša vypočítaná šanca na výhru: {sanca}%
    
    Tvojou úlohou je:
    1. Vypočítať, či je to Value Bet (hodnotná stávka).
    2. Napísať krátke odporúčanie pre klienta (max 2 vety).
    3. Byť prísny. Ak sa to neoplatí, povedz to rovno.
    
    Odpovedz v slovenčine.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o", # Alebo gpt-3.5-turbo (je lacnejší)
            messages=[
                {"role": "system", "content": "Si stručný a prísny analytik."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Chyba AI: {str(e)} (Skontroluj API Kľúč)"