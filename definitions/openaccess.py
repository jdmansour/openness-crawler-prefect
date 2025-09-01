from read_universities import read_universities


input_file = '../einrichtungen/data/hochschulen.csv'
output_file = "results_openaccess.jsonlines"
combo_keys = ("einrichtung", )
query_template = "{einrichtung} Open Access Richtlinie"
prompt_template = (
    "Finde heraus ob aus dem Text hervorgeht, dass es an der Einrichtung '{einrichtung}' eine "
    "Open-Access-Policy, Leitlinie o.ä. gibt, welche die Publikation in Open Access Journalen "
    "empfiehlt oder unterstützt. Antworte mit Ja oder Nein, der URL und einer kurzen Begründung. "
    "Antworte im JSON-Format. Gebe eine kurze Begründung im Feld `reasoning` an, sowie das"
    "Ergebnis `true` oder `false` im Feld `result`.")

load_institutions = read_universities
def make_combos(einrichtungen: list[str]) -> set[tuple]:
    combos = {(e,) for e in einrichtungen}
    return combos