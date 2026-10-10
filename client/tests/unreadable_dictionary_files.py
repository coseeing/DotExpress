"""Dictionary files that cannot be read, for the F-6 tests.

Built in memory as bytes; the tests write them into temporary folders. ``BIG5`` is what
Excel's "CSV (Comma delimited)" writes on Traditional Chinese Windows (cp950);
``UTF8_FIXED`` is the same row saved again as CSV UTF-8, one entry the editor shows.
"""

HEADER = "text,braille,type\r\n"
# Taipei with its Bopomofo: every character exists in cp950, and the sequence parses.
TAIPEI_ROW = "\u81fa\u5317,\u310a\u311e\u02ca\u3105\u311f\u02c7,Bopomofo\r\n"
ASCII_ROWS = "".join(f"w{index:04d},x,General\r\n" for index in range(1000))

BIG5 = (HEADER + TAIPEI_ROW).encode("cp950")
UTF8_FIXED = (HEADER + TAIPEI_ROW).encode("utf-8")
# About 17 KB of ASCII rows first: the header and the first chunks decode as UTF-8.
LATE_BIG5 = (HEADER + ASCII_ROWS).encode("ascii") + TAIPEI_ROW.encode("cp950")
UTF16 = (HEADER + "w,x,General\r\n").encode("utf-16")
# One field longer than the csv module's limit of 131,072 characters.
FIELD_LIMIT = (HEADER + "long," + "x" * 140000 + ",General\r\n").encode("ascii")
READABLE = (HEADER + "Alpha,\u2801,General\r\n").encode("utf-8")


def big5_decode_error() -> UnicodeDecodeError:
    """The error that reading ``BIG5`` as a dictionary raises."""
    try:
        BIG5.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        return error
    raise AssertionError("BIG5 decodes as UTF-8")
