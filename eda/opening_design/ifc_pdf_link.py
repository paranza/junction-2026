"""Does the Facilities_Building IFC match the PDF set exported to the same transfer folder?
Compares IfcDoor tags/names and storeys with door-like words on each PDF page.
Usage: python -I ifc_pdf_link.py <dataset_dir>"""
import sys, os, re, collections
import ifcopenshell
import pymupdf

base = os.path.join(sys.argv[1], "data", "opening_design", "Facilities_Building", "Transfer",
                    "20181108 - to structure & MBM - for pricing")
m = ifcopenshell.open(os.path.join(base, "1810 S Park.ifc"))
doors = m.by_type("IfcDoor")
print("IfcDoor", len(doors), "| tags:", sorted(str(d.Tag) for d in doors)[:20])
print("door names:", collections.Counter((d.Name or "")[:40] for d in doors).most_common(6))
print("IfcSpace", len(m.by_type("IfcSpace")), "| IfcWindow", len(m.by_type("IfcWindow")))
doc = pymupdf.open(os.path.join(base, "20181108 - 1810 S Park St - drawings for pricing exercise.pdf"))
for i, p in enumerate(doc):
    t = p.get_text()
    title = [w for w in re.findall(r"\b[AS]\d{3}\b", t)][:3]
    print(f"p{i+1} sheet? {title} words={len(t.split())} 'DOOR' x{len(re.findall('DOOR', t, re.I))} "
          f"'SCHEDULE' x{len(re.findall('SCHEDULE', t, re.I))}")
