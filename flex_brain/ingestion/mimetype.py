import mimetypes

from magika import Magika

DEFAULT_MIMETYPE = "application/octet-stream"

_TEXT_PROBE_SIZE = 8192

# labels magika falls back to when the model has no confident answer;
# these are worth refining with the filename extension instead
_GENERIC_LABELS = {"txt", "unknown", "empty"}

# fresh instance: the module-level guess_type reads the Windows registry,
# which maps e.g. .csv to application/vnd.ms-excel and varies per platform
_extension_db = mimetypes.MimeTypes()

# loads the ONNX model once; reused across requests
_magika = Magika()


def detect_mimetype(
    content: bytes,
    filename: str | None = None,
    declared_type: str | None = None,
) -> str:
    """Detect a file's mimetype, most trustworthy signal first.

    Order: magika model inference on the content, filename extension,
    client-declared type, UTF-8 probe. Falls back to application/octet-stream.
    """
    result = _magika.identify_bytes(content=content)
    label = str(result.output.label)
    if result.ok and label not in _GENERIC_LABELS:
        return result.output.mime_type

    if filename:
        guessed, _ = _extension_db.guess_type(filename)
        if guessed:
            return guessed

    if declared_type and declared_type != DEFAULT_MIMETYPE:
        return declared_type

    if label == "txt" and _decodes_as_utf8(content):
        return "text/plain"
    return DEFAULT_MIMETYPE


def _decodes_as_utf8(content: bytes) -> bool:
    probe = content[:_TEXT_PROBE_SIZE]
    if b"\x00" in probe:
        # NUL bytes decode as valid UTF-8 but never appear in real text
        return False
    if len(content) > _TEXT_PROBE_SIZE:
        # avoid a false negative from a multibyte char cut at the probe edge
        probe = probe[:-3]
    try:
        probe.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True
