from pathlib import Path

from adapters.translation.provider import build_default_translation_runtime
from config import DEFAULT_TRANSLATION_TABLES
from conversion.service import ConversionRequest, convert_text_with_alignment


BASE_DIR = Path(__file__).resolve().parent
SAMPLE_TEXT = """
請計算$\frac{1}{2} + \frac{2}{5}$的值是？ the test
"""


def run_demo(text: str = SAMPLE_TEXT) -> None:
    runtime = build_default_translation_runtime()
    try:
        output = convert_text_with_alignment(
            ConversionRequest(
                raw_text=text,
                output_mode="unicode",
                width=40,
                dictionary_path=BASE_DIR / "dictionary" / "default.csv",
                data_dir=BASE_DIR / "data",
                translation_tables={
                    **DEFAULT_TRANSLATION_TABLES,
                    "default": "en-ueb-g2.ctb",
                    "en": "en-ueb-g2.ctb",
                },
            ),
            runtime=runtime,
        )
        print(output.display_text)
    finally:
        runtime.close()


if __name__ == "__main__":
    run_demo()
