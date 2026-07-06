from dataclasses import dataclass, replace

from translation.settings import TranslationSettings
from view_settings import ViewSettings


@dataclass(frozen=True)
class DotExpressSettingsSnapshot:
    translation: TranslationSettings
    translation_tables: dict[str, str]
    view: ViewSettings

    @classmethod
    def create(
        cls,
        translation: TranslationSettings,
        translation_tables: dict[str, str],
        view: ViewSettings,
    ) -> "DotExpressSettingsSnapshot":
        return cls(translation, dict(translation_tables), view)

    def with_translation(self, value: TranslationSettings) -> "DotExpressSettingsSnapshot":
        return replace(self, translation=value)

    def with_translation_tables(
        self,
        value: dict[str, str],
    ) -> "DotExpressSettingsSnapshot":
        return replace(self, translation_tables=dict(value))

    def with_view(self, value: ViewSettings) -> "DotExpressSettingsSnapshot":
        return replace(self, view=value)

    def copied(self) -> "DotExpressSettingsSnapshot":
        return replace(self, translation_tables=dict(self.translation_tables))