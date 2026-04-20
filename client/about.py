import gettext
from pathlib import Path


LOCALE_DOMAIN = "dotexpress"
LOCALE_LANGUAGES = ["zh_TW"]
_translation = gettext.translation(
	LOCALE_DOMAIN,
	localedir=str(Path(__file__).resolve().parent / "locales"),
	languages=LOCALE_LANGUAGES,
	fallback=True,
)
_ = _translation.gettext


copyrightYears = "2025-2026"
name = "DotExpress"
url = "https://coseeing.org"
version = "1.2"
version_detailed = "1.2"

longName = _("DotExpress")
description = _("A text-to-braille translation tool that converts plain text into fixed-width braille, producing output that can be used directly for printed braille.")

copyright = _("Copyright (C) {years} DotExpress Contributors").format(
	years=copyrightYears,
)
aboutMessage = _(
	# Translators: "About DotExpress" dialog box message
	"""{longName} ({name})
Version: {version} ({version_detailed})
URL: {url}
{copyright}

{name} is covered by the GNU General Public License (Version 2 or later).
You are free to share or change this software in any way you like as long as it is accompanied by the license and you make all source code available to anyone who wants it.
This applies to both original and modified copies of this software, plus any derivative works.
For further details, you can view the license online at: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html and https://www.gnu.org/licenses/gpl-3.0.en.html.

{name} is developed by Coseeing, is a community dedicated to advancing digital accessibility.
Through the development of assistive tools, we empower people who are blind or visually impaired to access more information and explore new possibilities.
We also organize outreach and advocacy initiatives to help the broader public better understand the real challenges and needs faced by people with disabilities.
Through diverse approaches and sustained action, we aim to create a world that everyone can see together—appreciating both its richness and each other’s uniqueness.

If you find DotExpress useful and want it to continue to improve, please consider supporting Coseeing by visiting {url}.""",
).format(
	longName=longName,
	name=name,
	version=version,
	version_detailed=version_detailed,
	url=url,
	copyright=copyright,
)
