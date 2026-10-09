"""Equivalence of the production TranslationResult with the pre-split translate.py (P2-5).

Each operation runs on identical seeded random starting states through the frozen
oracle (tests/legacy_translation_result.py) and through the production class. The
four lists, which of them are still the original list objects, the return value and
the type and message of any exception must match. Most cases have a well-formed
alignment, as every producer builds; a fixed share is malformed (shuffled, too long,
too short or out-of-range maps, arbitrary braille_to_raw_pos values) so that the
fallback paths run too.
"""
import hashlib
import random
import unittest
from pathlib import Path

from tests import legacy_translation_result as legacy
from translate import TranslationResult


ORACLE_PATH = Path(__file__).resolve().parent / "legacy_translation_result.py"
ORACLE_MARKER = "# ---- verbatim copy of client/translate.py at d4a7aa1 follows ----\n"
ORACLE_BLOB = "10bd641485327b00cb71a14d4946f01a1788f794"
FIELDS = ("raw", "braille", "braille_to_raw_pos", "raw_to_braille_pos")
BLANK = chr(0x2800)
CELLS = (BLANK, BLANK, "⠁", "⠃")
PUNCTUATION = sorted(
    set().union(*(getattr(legacy.TranslationResult, name) for name in (
        "LEFT_PUNCT", "RIGHT_PUNCT", "MIDDLE_SENTENCE_PUNCT", "END_SENTENCE_PUNCT",
    )))
    | {"—"}
)
UNIT_KINDS = (
    (6, lambda rng: rng.choice("abcXYZ019")),
    (2, lambda rng: "".join(rng.choice("abc12") for _ in range(rng.randint(2, 4)))),
    (2, lambda rng: rng.choice(("the", "1+2", "台灣", "ing"))),
    (5, lambda rng: rng.choice("中文我嶼視台")),
    (2, lambda rng: rng.choice("かなカナ")),
    (1, lambda rng: rng.choice("한글")),
    (1, lambda rng: rng.choice("ㄅㄆㄇ")),
    (7, lambda rng: rng.choice(PUNCTUATION)),
    (3, lambda rng: " "),
    (1, lambda rng: "　"),
    (2, lambda rng: "\n"),
    (1, lambda rng: rng.choice("#+=")),
)
RIGHT = sorted(legacy.TranslationResult.RIGHT_PUNCT)
LEFT = sorted(legacy.TranslationResult.LEFT_PUNCT)
# Dense right/left punctuation, so that reclean_token inserts several separators.
SEPARATOR_UNIT_KINDS = (
    (4, lambda rng: rng.choice(RIGHT)),
    (4, lambda rng: rng.choice(LEFT)),
    (2, lambda rng: rng.choice("視我a1") + rng.choice(RIGHT)),
    (2, lambda rng: rng.choice(LEFT) + rng.choice("共嶼b2")),
    (3, lambda rng: rng.choice("中文ab")),
    (1, lambda rng: " "),
    (1, lambda rng: "\n"),
)


def random_units(rng: random.Random, max_units: int, kinds=UNIT_KINDS) -> list[str]:
    weights = [weight for weight, _make in kinds]
    makers = [make for _weight, make in kinds]
    units = [rng.choices(makers, weights)[0](rng) for _ in range(rng.randint(0, max_units))]
    if units and rng.random() < 0.03:
        units[rng.randrange(len(units))] = ""
    return units


def random_state(rng: random.Random, max_units: int = 14, kinds=UNIT_KINDS) -> tuple[list, list, list, list]:
    """Return (raw, braille, braille_to_raw_pos, raw_to_braille_pos)."""
    raw = random_units(rng, max_units, kinds)
    braille, b2r, r2b = [], [], []
    for index, _unit in enumerate(raw):
        r2b.append(len(braille))
        for _cell in range(rng.choice((0, 1, 1, 2, 2, 3, 4))):
            braille.append(rng.choice(CELLS))
            b2r.append(index)
    if rng.random() < 0.25:
        malform(rng, raw, braille, b2r, r2b)
    return raw, braille, b2r, r2b


def malform(rng: random.Random, raw: list, braille: list, b2r: list, r2b: list) -> None:
    kind = rng.randrange(6)
    if kind == 0:
        rng.shuffle(r2b)
    elif kind == 1:
        r2b.append(rng.randint(0, len(braille)))
    elif kind == 2 and r2b:
        r2b.pop()
    elif kind == 3 and r2b:
        r2b[rng.randrange(len(r2b))] = rng.randint(-3, len(braille) + 3)
    elif kind == 4:
        b2r[:] = [rng.randint(-2, len(raw) + 2) for _ in b2r]
    elif b2r:
        del b2r[rng.randrange(len(b2r))]


def build_pair(state) -> tuple[legacy.TranslationResult, TranslationResult]:
    return (
        legacy.TranslationResult(*[list(values) for values in state]),
        TranslationResult(*[list(values) for values in state]),
    )


def outcome(result, operation) -> tuple:
    before = {name: getattr(result, name) for name in FIELDS}
    try:
        value = ("returned", operation(result))
    except Exception as error:
        value = ("raised", type(error).__name__, str(error))
    lists = tuple(list(getattr(result, name)) for name in FIELDS)
    kept = tuple(getattr(result, name) is before[name] for name in FIELDS)
    return value, lists, kept


class OracleTest(unittest.TestCase):
    def test_oracle_is_the_pre_split_translate_py(self) -> None:
        text = ORACLE_PATH.read_text(encoding="utf-8")
        _header, marker, body = text.partition(ORACLE_MARKER)
        data = body.encode("utf-8")

        self.assertEqual(marker, ORACLE_MARKER)
        self.assertEqual(hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest(), ORACLE_BLOB)
        self.assertIsNot(legacy.TranslationResult, TranslationResult)


class SplitEquivalenceTest(unittest.TestCase):
    def assert_equivalent(self, seed: int, cases: int, operation, kinds=UNIT_KINDS) -> None:
        rng = random.Random(seed)
        paths = {"returned": 0, "raised": 0}
        for case in range(cases):
            state = random_state(rng, 14, kinds)
            arguments = operation.arguments(rng, state) if hasattr(operation, "arguments") else ()
            oracle, production = build_pair(state)
            expected = outcome(oracle, lambda result: operation(result, *arguments))
            actual = outcome(production, lambda result: operation(result, *arguments))
            paths[expected[0][0]] += 1
            if actual != expected:
                self.fail(f"seed {seed} case {case}: {state!r} {arguments!r}\nexpected {expected!r}\nactual   {actual!r}")
        self.assertGreater(paths["returned"], cases // 2)

    def test_bind_contracted_tokens_matches_the_oracle(self) -> None:
        self.assert_equivalent(101, 4000, lambda result: result.bind_contracted_tokens())

    def test_bind_word_tokens_matches_the_oracle(self) -> None:
        self.assert_equivalent(102, 4000, lambda result: result.bind_word_tokens())

    def test_insert_token_matches_the_oracle(self) -> None:
        def insert(result, index, text, braille):
            return result.insert_token(index, text, braille)

        def arguments(rng, state):
            raw = state[0]
            index = rng.randint(-1, len(raw) + 1)
            braille = "".join(rng.choice(CELLS) for _ in range(rng.randint(0, 3)))
            return index, rng.choice((" ", "x", "「")), braille if rng.random() < 0.5 else list(braille)

        insert.arguments = arguments
        self.assert_equivalent(103, 4000, insert)

    def test_reclean_token_matches_the_oracle(self) -> None:
        self.assert_equivalent(104, 2000, lambda result: result.reclean_token())
        self.assert_equivalent(108, 2000, lambda result: result.reclean_token(), SEPARATOR_UNIT_KINDS)

    def test_reclean_braille_endspace_matches_the_oracle(self) -> None:
        self.assert_equivalent(105, 4000, lambda result: result.reclean_braille_endspace())

    def test_wrap_matches_the_oracle(self) -> None:
        def wrap(result, width):
            return result.wrap(width)

        wrap.arguments = lambda rng, state: (rng.choice((rng.randint(1, 45), rng.randint(1, 6), 0, None)),)
        self.assert_equivalent(106, 4000, wrap)

    def test_whole_post_processing_matches_the_oracle(self) -> None:
        rng = random.Random(107)
        for case in range(2000):
            kinds = SEPARATOR_UNIT_KINDS if case % 2 else UNIT_KINDS
            states = [random_state(rng, 8, kinds) for _ in range(rng.randint(1, 3))]
            width = rng.randint(1, 45)
            pairs = [build_pair(state) for state in states]
            expected = self.post_process(legacy.TranslationResult, [oracle for oracle, _production in pairs], width)
            actual = self.post_process(TranslationResult, [production for _oracle, production in pairs], width)
            if actual != expected:
                self.fail(f"case {case}: {states!r} width {width}\nexpected {expected!r}\nactual   {actual!r}")

    @staticmethod
    def post_process(cls, results, width) -> tuple:
        merged = cls.concat(results)
        steps = []
        for name in ("reclean_braille_endspace", "bind_word_tokens", "reclean_token"):
            steps.append(outcome(merged, lambda result: getattr(result, name)()))
        steps.append(outcome(merged, lambda result: result.wrap(width)))
        return tuple(steps)


if __name__ == "__main__":
    unittest.main()
