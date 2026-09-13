"""Rendering document pages, and locating values on them.

Two jobs, both served by pypdfium2 so that a mark can be drawn over the document
an officer actually uploaded rather than over a transcription of it:

- render a page to a PNG the browser can show;
- find where a value sits on that page, as fractions of the page rather than
  pixels, so the same coordinates work at any zoom or screen size.

Fractions matter. A box in points is only meaningful beside the render scale
that produced it; a box in fractions is meaningful beside nothing at all, which
is what the review screen needs when it lays marks over an image whose displayed
size it does not control.

Scanned documents carry no text layer and so no coordinates. Nothing here
invents them — the caller falls back to showing the text, with the screen saying
why.
"""

import logging
from dataclasses import dataclass

import pypdfium2 as pdfium

logger = logging.getLogger(__name__)

#: Enough to read a certificate on a 1366x768 screen without the render being
#: larger than the connection deserves.
RENDER_SCALE = 2.0


@dataclass(frozen=True)
class Box:
    """Where a value sits, as fractions of the page from its top-left."""

    page_number: int
    left: float
    top: float
    width: float
    height: float


def page_count(data: bytes) -> int:
    try:
        return len(pdfium.PdfDocument(data))
    except Exception:
        logger.info("could not open the document to count its pages")
        return 0


def render_page(data: bytes, page_number: int, scale: float = RENDER_SCALE) -> bytes | None:
    """One page as PNG bytes, or None if it cannot be rendered."""
    import io

    try:
        document = pdfium.PdfDocument(data)
        if page_number < 1 or page_number > len(document):
            return None
        image = document[page_number - 1].render(scale=scale).to_pil()
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()
    except Exception:
        logger.info("could not render page %s", page_number, exc_info=True)
        return None


def locate_values(data: bytes, values: list[str]) -> dict[str, Box]:
    """Find each value's box on whichever page it first appears.

    Only the first occurrence is taken. A name that appears twice is marked once
    — marking every occurrence would clutter the page, and the officer needs to
    be shown the value, not every place it is written.

    A value that cannot be found is simply absent from the result. The finding
    still reaches the screen; it just carries no mark.
    """
    found: dict[str, Box] = {}
    wanted = [v for v in values if v and 2 <= len(v.strip()) <= 120]
    if not wanted:
        return found

    try:
        document = pdfium.PdfDocument(data)
    except Exception:
        logger.info("could not open the document to locate values")
        return found

    for index in range(len(document)):
        page = document[index]
        width, height = page.get_size()
        if not width or not height:
            continue
        textpage = page.get_textpage()

        for value in wanted:
            if value in found:
                continue
            try:
                hit = textpage.search(value.strip()).get_next()
            except Exception:
                continue
            if not hit:
                continue

            start, count = hit
            boxes = []
            for char in range(start, start + count):
                try:
                    box = textpage.get_charbox(char)
                except Exception:
                    box = None
                if box:
                    boxes.append(box)
            if not boxes:
                continue

            xs = [c for b in boxes for c in (b[0], b[2])]
            ys = [c for b in boxes for c in (b[1], b[3])]
            left, right = min(xs), max(xs)
            bottom, top = min(ys), max(ys)

            found[value] = Box(
                page_number=index + 1,
                left=max(0.0, left / width),
                # PDF y runs from the bottom; the screen's runs from the top.
                top=max(0.0, 1 - (top / height)),
                width=min(1.0, (right - left) / width),
                height=min(1.0, (top - bottom) / height),
            )

        if len(found) == len(wanted):
            break

    return found
