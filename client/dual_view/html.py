import html
import json

from dual_view.model import AlignmentItem, AlignmentSegment, DualViewModel


def _render_item(item: AlignmentItem) -> str:
	if item.is_newline:
		return '<span class="line-break" role="separator"></span>'

	classes = "cell space" if item.is_space else "cell"
	if item.source_kind == "math" and item.source_html is not None:
		source = item.source_html
	else:
		source = "&nbsp;" if item.is_space else html.escape(item.raw_text, quote=True)
	braille = html.escape(item.braille_text, quote=True) or '<span class="empty">∅</span>'
	metadata = html.escape(
		json.dumps(
			{
				"raw_index": item.raw_index,
				"braille_start": item.braille_start,
				"braille_end": item.braille_end,
			},
			ensure_ascii=False,
		),
		quote=True,
	)
	return (
		f'<span class="{classes}" data-alignment="{metadata}">'
		f'<span class="source">{source}</span>'
		f'<span class="braille">{braille}</span>'
		"</span>"
	)


def render_dual_view_html(
	model: DualViewModel,
	*,
	empty_message: str = "No conversion data is available for this document.",
) -> str:
	if model.segments:
		body = "".join(
			_render_item(item)
			for segment in model.segments
			for item in segment.items
		)
	else:
		body = f'<p class="empty-state">{html.escape(empty_message, quote=True)}</p>'

	return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{ color-scheme: light dark; font-family: "Noto Sans", sans-serif; }}
body {{ margin: 0; padding: 1rem; background: #f5f1e8; color: #17201d; }}
.document {{ display: flex; flex-wrap: wrap; align-items: flex-start; gap: .35rem; }}
.cell {{ display: inline-grid; grid-template-rows: auto auto; min-width: 2rem; text-align: center;
  border: 1px solid #d7cdbb; border-radius: .25rem; overflow: hidden; }}
.source, .braille {{ padding: .25rem .4rem; }}
.source {{ font-size: 1rem; background: #eee6d7; white-space: pre-wrap; }}
.braille {{ font-family: "SimBraille", "Noto Sans Symbols 2", sans-serif; font-size: 1.35rem; }}
.line-break {{ flex-basis: 100%; height: 0; }}
.empty {{ color: #777; font-size: .85rem; }}
.empty-state {{ max-width: 34rem; padding: 1rem; border: 1px dashed #8b8172; }}
@media (prefers-color-scheme: dark) {{
  body {{ background: #1c211f; color: #f4efe5; }}
  .cell {{ border-color: #59625e; }}
  .source {{ background: #343c38; }}
}}
</style>
</head>
<body><main class="document">{body}</main></body>
</html>"""
