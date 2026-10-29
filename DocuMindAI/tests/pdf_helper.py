"""Build tiny valid PDFs with no third-party library (used by tests and for the sample PDF)."""
from typing import List


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(pages: List[List[str]]) -> bytes:
    """pages = [[line, line, ...], ...]; a page with [] lines is blank."""
    objs = {}
    n = len(pages)
    page_ids = [3 + 2 * i for i in range(n)]
    objs[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objs[2] = f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode()
    font_id = 3 + 2 * n
    for i, lines in enumerate(pages):
        pid, cid = page_ids[i], page_ids[i] + 1
        objs[pid] = (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                     f"/Contents {cid} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>").encode()
        stream = "BT /F1 11 Tf 50 740 Td 15 TL\n" + "".join(f"({_esc(l)}) Tj T*\n" for l in lines) + "ET"
        sb = stream.encode("latin-1")
        objs[cid] = b"<< /Length %d >>\nstream\n" % len(sb) + sb + b"\nendstream"
    objs[font_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + objs[oid] + b"\nendobj\n"
    xref = len(out)
    total = max(objs) + 1
    out += f"xref\n0 {total}\n0000000000 65535 f \n".encode()
    for oid in range(1, total):
        out += f"{offsets[oid]:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {total} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


SAMPLE_PAGES = [
    ["Northwind Analytics - Security and Travel Policy", "",
     "Section 1: Travel",
     "Employees must book flights at least 14 days before departure.",
     "The daily meal allowance for business travel is $60.",
     "Hotel stays are capped at $180 per night."],
    ["Section 2: Equipment",
     "Company laptops are replaced every 36 months.",
     "Employees must return all equipment within 7 days of leaving the company."],
]

if __name__ == "__main__":  # regenerate sample_documents/sample_policy.pdf
    with open("sample_documents/sample_policy.pdf", "wb") as f:
        f.write(make_pdf(SAMPLE_PAGES))
    print("written sample_documents/sample_policy.pdf")
