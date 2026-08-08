from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PyPdfError


class InvalidPdfError(Exception):
    def __init__(self):
        super().__init__("file could not be parsed as a PDF")


class PdfTooLongError(Exception):
    def __init__(self, pages: int, max_pages: int):
        self.pages = pages
        self.max_pages = max_pages
        super().__init__(f"PDF has {pages} pages, maximum is {max_pages}")


def validate_pdf(content: bytes, max_pages: int) -> None:
    """Ensure the content is a readable PDF within the page limit.

    Raises InvalidPdfError for corrupt or encrypted files and
    PdfTooLongError when the page count exceeds max_pages.
    """
    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted:
            raise InvalidPdfError()
        pages = len(reader.pages)
    except PyPdfError as exc:
        raise InvalidPdfError() from exc

    if pages > max_pages:
        raise PdfTooLongError(pages, max_pages)
