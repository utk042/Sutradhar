"""Reading the fields off an uploaded document.

Two routes, picked by what was actually uploaded:

1. **A PDF with a text layer** is read directly with pypdf. This is not a
   fallback or a stand-in — it is how most documents issued digitally arrive
   (DigiLocker certificates among them), and reading embedded text is more
   accurate than running OCR over a rendering of it. No model is involved and
   no data leaves the host.

2. **An image, or a PDF that is only a scan**, goes to the configured provider
   for vision OCR.

If route 2 is needed and no provider is reachable, `ProviderUnavailable`
propagates. The caller turns that into an `unverifiable` finding, because the
honest answer is "the system could not read this", not a guess.

Everything here returns plain data. Nothing in this module writes to the
database.
"""

import io
import logging
import re

from pypdf import PdfReader

from app.agents.guard import wrap_document_text
from app.providers.base import LLMProvider, ProviderUnavailable

logger = logging.getLogger(__name__)

#: The fields the checks know how to compare, mapped from the labels that appear
#: on the sample certificates. Lives here rather than in the agent so that
#: adding a document type does not mean touching the checks.
FIELD_LABELS: dict[str, str] = {
    "name": "full_name",
    "full name": "full_name",
    "applicant name": "full_name",
    "date of birth": "date_of_birth",
    "dob": "date_of_birth",
    "father's name": "father_name",
    "fathers name": "father_name",
    "father name": "father_name",
    "address": "address",
    "annual income": "annual_income",
    "income": "annual_income",
    "issued on": "issued_on",
    "date of issue": "issued_on",
    "issuing authority": "issuing_authority",
    "certificate number": "record_ref",
    "certificate no": "record_ref",
    "registration number": "record_ref",
    "reference": "record_ref",
}

_LINE = re.compile(r"^\s*([A-Za-z][A-Za-z'\s]{2,30}?)\s*[:\-]\s*(.+?)\s*$")

#: Typographic characters that stand in for plain ASCII in real documents. PDF
#: text layers and word processors both substitute these freely, so "Father's
#: Name" arrives as "Father’s Name" and would otherwise miss the label table.
_NORMALISE = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u2032": "'",
    "\u201c": '"', "\u201d": '"',
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-", "\u2014": "-",
    "\u00a0": " ",
})


def normalise_text(text: str) -> str:
    """Fold typographic punctuation to ASCII so label matching is reliable."""
    return text.translate(_NORMALISE)

EXTRACTION_PROMPT = """\
Transcribe every line of text visible in this document image, exactly as it \
appears, preserving the order and any "Label: value" structure. Do not \
interpret, summarise, correct or translate anything. Output only the \
transcription."""


def read_pdf_text(data: bytes) -> str:
    """Return the embedded text of a PDF, or "" when it carries none."""
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except Exception:
        # A malformed or encrypted PDF is not an error worth surfacing here; the
        # caller falls through to OCR and then to `unverifiable`.
        logger.info("pdf text layer unreadable, falling back to image reading")
        return ""


def parse_fields(text: str) -> dict[str, str]:
    """Pull `Label: value` pairs out of transcribed text.

    Deliberately conservative. A line it does not recognise is left alone rather
    than guessed at — an unrecognised field becomes an `unverifiable` finding,
    which is a better outcome than a confident wrong match.
    """
    fields: dict[str, str] = {}
    for line in normalise_text(text).splitlines():
        match = _LINE.match(line)
        if not match:
            continue
        label = " ".join(match.group(1).split()).lower()
        canonical = FIELD_LABELS.get(label)
        if canonical and canonical not in fields:
            fields[canonical] = match.group(2).strip()
    return fields


async def structure_with_model(provider: LLMProvider, text: str) -> dict[str, str]:
    """Ask the model to label fields when the text is not in `Label: value` form.

    The document text goes inside a delimited block and the system prompt states
    that its contents are data. Whatever comes back is parsed as `Label: value`
    lines and filtered against the known fields — the model cannot introduce a
    field the checks do not already understand.
    """
    from app.agents.guard import SYSTEM_PREAMBLE

    instruction = (
        "From the document text below, list the fields you can identify, one per "
        "line, in the form 'Label: value'. Use only these labels where they apply: "
        + ", ".join(sorted(set(FIELD_LABELS.values())))
        + ". Omit any field that is not clearly present. Output nothing else."
    )
    answer = await provider.generate(
        SYSTEM_PREAMBLE, f"{instruction}\n\n{wrap_document_text(text)}"
    )
    out: dict[str, str] = {}
    for line in answer.splitlines():
        match = _LINE.match(line)
        if not match:
            continue
        label = " ".join(match.group(1).split()).lower().replace(" ", "_")
        if label in set(FIELD_LABELS.values()):
            out.setdefault(label, match.group(2).strip())
    return out


async def extract_document(
    *, data: bytes, mime_type: str, provider: LLMProvider
) -> tuple[str, dict[str, str], str]:
    """Return (raw text, fields, how it was read).

    Raises ProviderUnavailable when the document needs a model and none is
    reachable.
    """
    text = ""
    method = ""

    if mime_type == "application/pdf":
        text = read_pdf_text(data)
        if text:
            method = "pdf_text_layer"

    if not text:
        text = await provider.extract_from_image(data, EXTRACTION_PROMPT)
        method = f"vision:{provider.name}"

    fields = parse_fields(text)
    if not fields and method.startswith("pdf_text_layer"):
        # Text was present but not in a shape we recognise; ask the model to
        # label it, if one is available.
        try:
            fields = await structure_with_model(provider, text)
            method = f"{method}+model_labelled"
        except ProviderUnavailable:
            logger.info("no provider available to structure unlabelled text")

    return text, fields, method
