from pathlib import Path

from adapters.translation.provider import build_default_translation_runtime
from config import DEFAULT_TRANSLATION_TABLES
from conversion.service import translate_and_wrap_both


BASE_DIR = Path(__file__).resolve().parent
SAMPLE_TEXT = """  但只要見到你，任誰都得劍拔弩張。
  ──德國劇作家與詩人布希萊特（Bertolt Bercht, 1898-1956）

p.15

    第一章 正義的殿堂
"""


def run_demo(text: str = SAMPLE_TEXT) -> None:
    runtime = build_default_translation_runtime()
    try:
        braille, source = translate_and_wrap_both(
            table_file="zh-tw.ctb",
            text=text,
            width=40,
            dictionary_path=BASE_DIR / "dictionary" / "default.csv",
            translation_tables=DEFAULT_TRANSLATION_TABLES,
            bopomofo_path=BASE_DIR / "data" / "Bopomofo2Braille.csv",
            runtime=runtime,
        )
        print(braille)
        print(source)
    finally:
        runtime.close()


if __name__ == "__main__":
    run_demo()
