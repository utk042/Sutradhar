"""Generate a text-layer PDF.

Used by the seed script to produce the sample certificates an officer uploads
during a demonstration. Emitting a real text layer (rather than an image of
text) means extraction reads embedded text exactly as it would from a genuine
digitally-issued certificate, with no model and no network involved.

A minimal PDF by hand, rather than a rendering dependency: the file is small
enough to be worth reading, and the byte offsets in the xref table are why it
has to be built in one pass.
"""

from __future__ import annotations


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def make_pdf(lines: list[str], *, title: str) -> bytes:
    leading = 18
    top = 780
    content_parts = ["BT", "/F1 16 Tf", f"1 0 0 1 60 {top} Tm", f"({_escape(title)}) Tj"]
    content_parts += ["/F1 11 Tf", f"0 -{leading * 2} Td"]
    for i, line in enumerate(lines):
        if i:
            content_parts.append(f"0 -{leading} Td")
        content_parts.append(f"({_escape(line)}) Tj")
    content_parts.append("ET")
    stream = "\n".join(content_parts).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n".encode()
    )
    out += b"%%EOF\n"
    return bytes(out)
