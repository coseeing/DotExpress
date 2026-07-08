from conversion.text.dictionary_rules import apply_dictionary as dictionary_apply_dictionary
from utils import apply_dictionary as utils_apply_dictionary


def test_utils_reexports_dictionary_rules() -> None:
    assert utils_apply_dictionary is dictionary_apply_dictionary
