from __future__ import annotations

import html

from config import DEFAULT_MATH_BRAILLE_TABLE
from log import get_logger


logger = get_logger("dotexpress.math", "log/math.log")


class MathConversionError(Exception):
	pass


def _convert_latex_to_mathml(latex_text: str) -> str:
	from latex2mathml import converter

	return converter.convert(latex_text)


def latex_to_mathml(latex_text: str) -> str:
	normalized = latex_text.replace(r"\vec{", r"\overset{⇀}{")
	mathml = html.unescape(_convert_latex_to_mathml(normalized))
	return mathml.replace("<mi>⇀</mi>", "<mo>⇀</mo>")


def mathml_to_nemeth_braille(mathml_text: str, braille_code: str = DEFAULT_MATH_BRAILLE_TABLE) -> str:
	from conversion.mathcat_adapter import get_shared_mathcat_adapter

	return get_shared_mathcat_adapter().get_braille_for_mathml(mathml_text, braille_code=braille_code)


def translate_math_segment(latex_text: str, braille_code: str = DEFAULT_MATH_BRAILLE_TABLE) -> str:
	mathml_text = None
	try:
		mathml_text = latex_to_mathml(latex_text)
		return mathml_to_nemeth_braille(mathml_text, braille_code=braille_code)
	except Exception as error:
		logger.exception(
			"Math conversion failed | stage=%s | latex=%r | mathml=%r",
			"mathml_to_nemeth_braille" if mathml_text is not None else "latex_to_mathml",
			latex_text,
			mathml_text,
		)
		raise MathConversionError(str(error)) from error
