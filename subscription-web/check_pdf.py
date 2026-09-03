import importlib.util as u
print({"pdfplumber": bool(u.find_spec("pdfplumber")), "reportlab": bool(u.find_spec("reportlab"))})
