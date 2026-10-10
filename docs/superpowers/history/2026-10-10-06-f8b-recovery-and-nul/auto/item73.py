"""Items 73-75 (F-8 D12, D13): U+0000 in a package or in an imported file.

Usage: python item73.py <exe> <work folder> <73|74|75>
73: alpha.dep with the text "first line\nsecond\x00 after\nthird" and the braille
    "⠁\x00⠃", beta.dep without U+0000. Start: what startup shows; the source editor's text
    (WM_GETTEXT); Ctrl+Tab to beta and back (the boxes); alpha.dep; close; alpha.dep; start
    again: what startup shows.
74: File > Import data\\zero.txt (the bytes "A\x00B tail\r\nline 2"): the box; the editor;
    the package.
75: File > Import data\\zero.txt and data\\code0.pdf (an untagged PDF whose text string
    holds code 0): the box (none); then File > Open code0, zero and code0 again: the boxes.
Before F-8b (N-f8a2): no box; the editor ends at the first U+0000, and in 73 the first
switch writes that cut text to alpha.dep. Since the review fix (F-8b2) each 已取代字元 box
is also compared with f8bgui.REPLACED_CONTENT (M-5: 轉換前).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f8bgui as B  # noqa: E402
from f8bgui import A, D  # noqa: E402

EXE, d, item = sys.argv[1], os.path.normpath(sys.argv[2]), sys.argv[3]
NUL_TEXT = b"A\x00B tail\r\nline 2"
d = A.prepare(EXE, d)
data = os.path.join(d, "data")


def pdf_with_code_0(path):
	"""A one-page untagged PDF that shows the string (A\\000B) in Helvetica (F-8 spec probe)."""
	content = b"BT /F1 12 Tf 72 700 Td (A\\000B) Tj ET"
	objects = [
		b"<< /Type /Catalog /Pages 2 0 R >>",
		b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
		b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
		b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
		b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
	]
	out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
	offsets = []
	for index, body in enumerate(objects, start=1):
		offsets.append(len(out))
		out += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"
	xref = len(out)
	out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
	for offset in offsets:
		out += f"{offset:010d} 00000 n \n".encode()
	out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
	return A.write(path, bytes(out))


if item == "73":
	A.package(d, "alpha", "first line\nsecond\x00 after\nthird", "⠁\x00⠃")
	A.package(d, "beta", "beta body", "⠃")
	app, w, shown = B.start(d)
	print(f"73 start: shown {B.show(shown)}")
	print(f"73 start: replaced box content as expected {B.replaced_boxes_ok(shown)}")
	print(f"73 docs {D.docs(w)} title {w.window_text()!r} input {B.show(D.get_input(w))}")
	print(f"73 alpha.dep {B.show(B.members(d, 'alpha'))}")
	print(f"73 Ctrl+Tab: {B.show(B.switch(app, w))}")
	print(f"73 Ctrl+Shift+Tab: {B.show(B.switch(app, w, back=True))}")
	print(f"73 input {B.show(D.get_input(w))}")
	print(f"73 alpha.dep {B.show(B.members(d, 'alpha'))}")
	print("close:", D.close(app, w))
	print(f"73 alpha.dep {B.show(B.members(d, 'alpha'))}")
	app, w, shown = B.start(d)
	print(f"73 restart: shown {B.show(shown)} input {B.show(D.get_input(w))}")
else:
	A.write(os.path.join(data, "zero.txt"), NUL_TEXT)
	names = ["zero.txt"]
	if item == "75":
		pdf_with_code_0(os.path.join(data, "code0.pdf"))
		names.append("code0.pdf")
	app, w, shown = B.start(d)
	print(f"{item} start: shown {B.show(shown)} docs {D.docs(w)}")
	B.import_files(app, w, data, names)
	imported = B.box(app)
	print(f"{item} import: box {B.show(imported)}")
	print(f"{item} import: replaced box content as expected {B.replaced_boxes_ok([imported])}")
	print(f"{item} docs {D.docs(w)} title {w.window_text()!r} input {B.show(D.get_input(w))}")
	if item == "75":
		for name in ("code0", "zero", "code0"):
			opened = B.open_document(app, w, name)
			print(f"75 open {name}: box {B.show(opened)}")
			print(f"75 open {name}: replaced box content as expected {B.replaced_boxes_ok([opened])}")
			print(f"75 title {w.window_text()!r} input {B.show(D.get_input(w))}")
	print("close:", D.close(app, w))
	for name in ("zero", "code0")[: len(names)]:
		print(f"{item} {name}.dep {B.show(B.members(d, name))}")
	app, w, shown = B.start(d)
	print(f"{item} restart: shown {B.show(shown)} docs {D.docs(w)}")
B.finish(app, w, d)
