
from typing import Callable

class BaseDefinition:
    # input_file: str
    output_file: str
    combo_keys: tuple
    query_template: str
    prompt_template: str

    @classmethod
    def load_institutions(cls):
        """ Läd die liste der Institutionen. """
        raise NotImplementedError("Diese Methode muss überschrieben werden.")

    @staticmethod
    def make_combos(einrichtungen: list[str]) -> set[tuple]:
        """
        Diese Methode soll überschrieben werden. Die Methode
        nimmt die Liste der Einrichtungen, und macht daraus
        zu untersuchende Tuple, z.B.:
        [
            ('Uni Göttingen', 'Moodle'),
            ('Uni Göttingen', 'Ilias'),
            ('Uni Göttingen', 'OpenOLAT')
        ]

        Die Basisversion fügt keine Kombinationen dazu,
        sondern gibt nur die Einrichtungen selbst zurück.
        """
        combos = {(e,) for e in einrichtungen}
        return combos