from definitions.base import BaseDefinition
from read_universities import read_universities

class OpenLMS(BaseDefinition):
    input_file = '../einrichtungen/data/hochschulen.csv'
    output_file = "results_new.jsonlines"
    combo_keys = ("einrichtung", "software")
    # query_template = "site:{website} {software}"
    query_template = "{einrichtung} {software}"
    prompt_template = (
        "Finde heraus ob aus dem Text hervorgeht, dass {software} oder eine auf {software} "
        "basierende Software in der Einrichtung {einrichtung} genutzt wird. Antworte im "
        "JSON-Format. Gebe eine kurze Begründung im Feld `reasoning` an, sowie das Ergebnis "
        "`true` oder `false` im Feld `result`.")

    @classmethod
    def load_institutions(cls):
        return read_universities(cls.input_file)

    @staticmethod
    def make_combos(einrichtungen: list[str]) -> set[tuple]:
        options = ["Moodle", "Ilias", "OpenOLAT"]
        combos = {(einrichtung, software)
                for einrichtung in einrichtungen
                for software in options}
        return combos
