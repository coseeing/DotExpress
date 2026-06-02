from __future__ import annotations

from dataclasses import dataclass
from importlib import util as importlib_util
import os
from pathlib import Path
import sys

from config import DEFAULT_MATH_BRAILLE_TABLE, MATH_BRAILLE_TABLES, get_lang


class MathCATError(Exception):
	pass


def get_default_mathcat_resource_root() -> Path:
	return Path(__file__).resolve().parent.parent / "mathcat" / "assets"


@dataclass
class MathCATAdapter:
	resource_root: Path
	_libmathcat: object | None = None
	_dll_directory_handle: object | None = None

	def _rules_dir(self) -> Path:
		return self.resource_root / "Rules"

	def _language_dir(self, language: str) -> Path:
		return self._rules_dir() / "Languages" / Path(*language.split("-"))

	def _has_language_style_file(self, language: str, style: str) -> bool:
		return (self._language_dir(language) / f"{style}_Rules.yaml").exists()

	def _resolve_speech_style(self, language: str) -> str:
		if self._has_language_style_file(language, "ClearSpeak"):
			return "ClearSpeak"
		if self._has_language_style_file(language, "SimpleSpeak"):
			return "SimpleSpeak"
		return "ClearSpeak"

	def _load_libmathcat(self):
		if self._libmathcat is not None:
			return self._libmathcat

		module_path = self.resource_root / "libmathcat_py.pyd"
		if not module_path.exists():
			raise MathCATError(f"MathCAT runtime not found: {module_path}")

		if hasattr(os, "add_dll_directory") and self._dll_directory_handle is None:
			self._dll_directory_handle = os.add_dll_directory(str(self.resource_root))

		spec = importlib_util.spec_from_file_location("libmathcat_py", module_path)
		if spec is None or spec.loader is None:
			raise MathCATError(f"Unable to load MathCAT runtime from {module_path}")

		module = importlib_util.module_from_spec(spec)
		sys.modules.setdefault("libmathcat_py", module)
		spec.loader.exec_module(module)
		self._libmathcat = module
		return module

	def _normalize_braille_code(self, braille_code: str | None) -> str:
		if braille_code in MATH_BRAILLE_TABLES:
			return braille_code
		return DEFAULT_MATH_BRAILLE_TABLE

	def _configure_runtime(self, libmathcat, braille_code: str | None = None) -> None:
		language = get_lang().replace("_", "-").lower()
		speech_style = self._resolve_speech_style(language)
		selected_braille_code = self._normalize_braille_code(braille_code)
		# Re-apply runtime configuration for each conversion. In the stripped-down
		# embedding used by DotExpress, later SetMathML calls can fail if MathCAT
		# keeps stale rule/preference state between requests.
		libmathcat.SetRulesDir(str(self._rules_dir()))
		libmathcat.SetPreference("Language", language)
		libmathcat.SetPreference("SpeechStyle", speech_style)
		libmathcat.SetPreference("Verbosity", "Medium")
		libmathcat.SetPreference("TTS", "None")
		libmathcat.SetPreference("BrailleCode", selected_braille_code)

	def get_braille_for_mathml(self, mathml_text: str, braille_code: str | None = None) -> str:
		try:
			libmathcat = self._load_libmathcat()
			self._configure_runtime(libmathcat, braille_code)
			libmathcat.SetMathML(mathml_text)
			return libmathcat.GetBraille("")
		except MathCATError:
			raise
		except Exception as error:
			raise MathCATError(str(error)) from error


_SHARED_ADAPTER: MathCATAdapter | None = None


def get_shared_mathcat_adapter() -> MathCATAdapter:
	global _SHARED_ADAPTER
	if _SHARED_ADAPTER is None:
		_SHARED_ADAPTER = MathCATAdapter(resource_root=get_default_mathcat_resource_root())
	return _SHARED_ADAPTER
