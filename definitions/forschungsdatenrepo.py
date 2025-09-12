from definitions.base import BaseDefinition
from read_universities import read_universities

class Forschungsdatenrepo(BaseDefinition):
    input_file = '../einrichtungen/data/hochschulen.csv'
    output_file = "results_forschungsdatenrepo.jsonlines"
    combo_keys = ("einrichtung", )
    query_template = "{einrichtung} Forschungsdaten Repositorium"
    prompt_template = (
        "Finde heraus ob aus dem Text hervorgeht, dass an der Einrichtung '{einrichtung}' ein "
        "öffentlich zugängliches Forschungsdatenrepositorium betrieben oder genutzt wird. "
        "Nachweis einer öffentlich zugänglichen Infrastruktur für ein Forschungsdaten-Repositorium u.a. durch:\n"
        ' - Textsuche auf der Webseite: Präsenz von Schlüsselbegriffen wie "Forschungsdaten-Repositorium", "Forschungsdatenmanagement", "Research Data Management", "RDM", "FDM" in Titeln, Überschriften\n'
        ' - Identifikation spezifischer URL-Muster: Auffinden von URLs, die /forschungsdaten/, /researchdata/, /rdm/ oder ähnliche Muster enthalten.\n'
        ' - Verlinkung von relevanten Bereichen: Direkte Links von der Hauptwebseite (z.B. aus dem Hauptmenü, dem Bereich "Forschung" oder "Bibliothek") zu einer URL, die auf ein solches Repositorium hindeutet.\n'
        '\n'
        "Antworte mit Ja oder Nein, der URL und einer kurzen Begründung. "
        "Antworte im JSON-Format. Gebe eine kurze Begründung im Feld `reasoning` an, sowie das "
        "Ergebnis `true` oder `false` im Feld `result`.")

    @classmethod
    def load_institutions(cls):
        return read_universities(cls.input_file)
