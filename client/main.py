from pathlib import Path

from adapters.translation.provider import build_default_translation_runtime
from app_paths import build_application_paths
from config import DEFAULT_TRANSLATION_TABLES, ConfigStore
from conversion.preprocessing.user_script import NO_PROCESSING_SCRIPT_NAME
from conversion.service import ConversionRequest, convert_text_with_alignment
from text_scripts.manager import script_path_for_name


BASE_DIR = Path(__file__).resolve().parent
SAMPLE_TEXT = """
請計算$\frac{1}{2} + \frac{2}{5}$的值是？ the test
"""


def run_demo(text: str = SAMPLE_TEXT) -> None:
    paths = build_application_paths()
    config_store = ConfigStore(paths.config)
    runtime = build_default_translation_runtime()
    try:
        output = convert_text_with_alignment(
            ConversionRequest(
                raw_text=text,
                output_mode="unicode",
                width=40,
                dictionary_path=paths.dictionary / "default.csv",
                data_dir=BASE_DIR / "data",
                translation_tables={
                    **DEFAULT_TRANSLATION_TABLES,
                    "default": "en-ueb-g2.ctb",
                    "en": "en-ueb-g2.ctb",
                },
                lang=config_store.get_lang(),
                charset_maps=config_store.get_charset_maps(),
                script_path=script_path_for_name(NO_PROCESSING_SCRIPT_NAME, paths.script),
            ),
            runtime=runtime,
        )
        print(output.display_text)
    finally:
        runtime.close()


if __name__ == "__main__":
    run_demo()
