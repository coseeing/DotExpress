import config


def load_translation_tables() -> dict[str, str]:
    return dict(config.get_translation_tables())


def save_translation_tables(tables: dict[str, str]) -> None:
    config.set_translation_tables(dict(tables))
