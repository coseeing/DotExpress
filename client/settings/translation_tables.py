import config


def load_translation_tables(store: config.ConfigStore) -> dict[str, str]:
    return dict(store.get_translation_tables())


def save_translation_tables(store: config.ConfigStore, tables: dict[str, str]) -> config.ConfigSaveProblem | None:
    return store.set_translation_tables(dict(tables))
