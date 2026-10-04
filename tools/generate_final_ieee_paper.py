from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    Image as RLImage,
    KeepTogether,
    NextPageTemplate,
    PageTemplate,
    PageBreak,
    Paragraph,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output" / "pdf" / "paper_polished"
FIGURE_DIR = OUTPUT_DIR / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

PDF_PATH = OUTPUT_DIR / "HalluGuard_Med_IEEE_Polished.pdf"

PAGE_W, PAGE_H = A4
LEFT = 50
RIGHT = 50
GAP = 26
COL_W = (PAGE_W - LEFT - RIGHT - GAP) / 2
BOTTOM = 40
FIRST_TOP = 520
NORMAL_TOP = 754


def register_fonts() -> None:
    for name, path in {
        "PaperSerif": r"C:\Windows\Fonts\times.ttf",
        "PaperSerif-Bold": r"C:\Windows\Fonts\timesbd.ttf",
        "PaperSerif-Italic": r"C:\Windows\Fonts\timesi.ttf",
        "PaperSerif-BoldItalic": r"C:\Windows\Fonts\timesbi.ttf",
    }.items():
        if Path(path).exists():
            pdfmetrics.registerFont(TTFont(name, path))


def make_styles() -> dict[str, ParagraphStyle]:
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    sample = getSampleStyleSheet()
    return {
        "body": ParagraphStyle(
            "body",
            parent=sample["BodyText"],
            fontName="PaperSerif",
            fontSize=10.5,
            leading=11.25,
            alignment=TA_JUSTIFY,
            firstLineIndent=12,
            spaceAfter=3,
        ),
        "body_noindent": ParagraphStyle(
            "body_noindent",
            parent=sample["BodyText"],
            fontName="PaperSerif",
            fontSize=10.5,
            leading=11.25,
            alignment=TA_JUSTIFY,
            firstLineIndent=0,
            spaceAfter=3,
        ),
        "abstract": ParagraphStyle(
            "abstract",
            parent=sample["BodyText"],
            fontName="PaperSerif-BoldItalic",
            fontSize=10.5,
            leading=11.25,
            alignment=TA_JUSTIFY,
            firstLineIndent=0,
            spaceAfter=5,
        ),
        "keywords": ParagraphStyle(
            "keywords",
            parent=sample["BodyText"],
            fontName="PaperSerif-Italic",
            fontSize=10.5,
            leading=11.25,
            alignment=TA_JUSTIFY,
            firstLineIndent=0,
            spaceAfter=6,
        ),
        "section": ParagraphStyle(
            "section",
            parent=sample["Heading1"],
            fontName="PaperSerif-Bold",
            fontSize=10.5,
            leading=11.6,
            alignment=TA_CENTER,
            spaceBefore=5,
            spaceAfter=3,
        ),
        "subsection": ParagraphStyle(
            "subsection",
            parent=sample["Heading2"],
            fontName="PaperSerif-Bold",
            fontSize=10.5,
            leading=11.6,
            alignment=TA_LEFT,
            spaceBefore=3,
            spaceAfter=1,
        ),
        "caption": ParagraphStyle(
            "caption",
            parent=sample["BodyText"],
            fontName="PaperSerif",
            fontSize=9.5,
            leading=10.0,
            alignment=TA_CENTER,
            spaceBefore=2,
            spaceAfter=3,
        ),
        "ref": ParagraphStyle(
            "ref",
            parent=sample["BodyText"],
            fontName="PaperSerif",
            fontSize=9.5,
            leading=9.9,
            alignment=TA_LEFT,
            firstLineIndent=-12,
            leftIndent=12,
            spaceAfter=1.5,
        ),
        "table_header": ParagraphStyle(
            "table_header",
            parent=sample["BodyText"],
            fontName="PaperSerif-Bold",
            fontSize=9.5,
            leading=10.3,
            alignment=TA_LEFT,
            firstLineIndent=0,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            parent=sample["BodyText"],
            fontName="PaperSerif",
            fontSize=9.5,
            leading=10.3,
            alignment=TA_LEFT,
            firstLineIndent=0,
        ),
        "table_center": ParagraphStyle(
            "table_center",
            parent=sample["BodyText"],
            fontName="PaperSerif",
            fontSize=9.5,
            leading=10.3,
            alignment=TA_CENTER,
            firstLineIndent=0,
        ),
    }


def draw_header(canvas, _doc) -> None:
    canvas.saveState()
    canvas.setFont("PaperSerif-Bold", 10)
    canvas.drawCentredString(
        PAGE_W / 2,
        PAGE_H - 46,
        "F.Y.B. Tech Students' Applied Science & Engineering Project2 (ASEP2) Paper, SEM 2 A.Y. 2025-26",
    )
    canvas.drawCentredString(PAGE_W / 2, PAGE_H - 60, "Vishwakarma Institute of Technology, Pune, INDIA.")
    canvas.restoreState()


def draw_first_page(canvas, doc) -> None:
    draw_header(canvas, doc)
    canvas.saveState()
    canvas.setFont("PaperSerif-Bold", 17)
    y = PAGE_H - 132
    for line in [
        "HalluGuard-Med: An Explainable Retrieval-Augmented Medical AI",
        "Framework for DeBERTa-v3 MNLI Claim Verification and",
        "Clinical Evidence Grounding",
    ]:
        canvas.drawCentredString(PAGE_W / 2, y, line)
        y -= 21
    canvas.setFont("PaperSerif", 12.5)
    y -= 21
    for line in [
        "Dr. Ramkrishna S. Bharsakade, Harshvardhan M. Patil, Rajvardhan P. Patil,",
        "Bhavesh M. Patil, Kartik N. Patil",
    ]:
        canvas.drawCentredString(PAGE_W / 2, y, line)
        y -= 16
    canvas.setFont("PaperSerif-Bold", 10.5)
    y -= 12
    canvas.drawCentredString(PAGE_W / 2, y, "Department of Engineering, Sciences and Humanities (DESH)")
    y -= 13
    canvas.drawCentredString(PAGE_W / 2, y, "Vishwakarma Institute of Technology, Pune, Maharashtra, India")
    canvas.restoreState()


def p(text: str, style: str = "body"):
    return Paragraph(text, STYLES[style])


def section(title: str):
    return Paragraph(title, STYLES["section"])


def subsection(title: str):
    return Paragraph(title, STYLES["subsection"])


def table(data: list[list[str]], widths: list[float]):
    wrapped = []
    for r, row in enumerate(data):
        wrapped_row = []
        for c, cell in enumerate(row):
            text = escape(str(cell))
            if r == 0:
                style = STYLES["table_header"]
            elif c > 0 and len(text) <= 15:
                style = STYLES["table_center"]
            else:
                style = STYLES["table_cell"]
            wrapped_row.append(Paragraph(text, style))
        wrapped.append(wrapped_row)
    t = Table(wrapped, colWidths=widths, hAlign="CENTER", repeatRows=1)
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "PaperSerif-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "PaperSerif"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("LEADING", (0, 0), (-1, -1), 10.3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def make_figure_assets() -> dict[str, Path]:
    regular = ImageFont.truetype(r"C:\Windows\Fonts\times.ttf", 32)
    bold = ImageFont.truetype(r"C:\Windows\Fonts\timesbd.ttf", 34)
    small = ImageFont.truetype(r"C:\Windows\Fonts\times.ttf", 28)
    tiny = ImageFont.truetype(r"C:\Windows\Fonts\times.ttf", 24)
    chart_title = ImageFont.truetype(r"C:\Windows\Fonts\timesbd.ttf", 42)
    chart_label = ImageFont.truetype(r"C:\Windows\Fonts\times.ttf", 28)
    chart_small = ImageFont.truetype(r"C:\Windows\Fonts\times.ttf", 24)
    arch_title = ImageFont.truetype(r"C:\Windows\Fonts\timesbd.ttf", 58)
    arch_bold = ImageFont.truetype(r"C:\Windows\Fonts\timesbd.ttf", 36)
    arch_small = ImageFont.truetype(r"C:\Windows\Fonts\times.ttf", 27)

    def centered(draw, box, text, font):
        lines = text.split("\n")
        dims = [draw.textbbox((0, 0), line, font=font) for line in lines]
        heights = [d[3] - d[1] for d in dims]
        widths = [d[2] - d[0] for d in dims]
        x1, y1, x2, y2 = box
        y = y1 + ((y2 - y1) - sum(heights) - 4 * (len(lines) - 1)) / 2
        for line, w, h in zip(lines, widths, heights):
            draw.text((x1 + ((x2 - x1) - w) / 2, y), line, font=font, fill=(0, 0, 0))
            y += h + 4

    def arrow(draw, start, end):
        draw.line([start, end], fill=(18, 30, 46), width=4)
        x1, y1 = start
        x2, y2 = end
        if abs(x2 - x1) >= abs(y2 - y1):
            direction = 1 if x2 >= x1 else -1
            pts = [(x2, y2), (x2 - 18 * direction, y2 - 10), (x2 - 18 * direction, y2 + 10)]
        else:
            direction = 1 if y2 >= y1 else -1
            pts = [(x2, y2), (x2 - 10, y2 - 18 * direction), (x2 + 10, y2 - 18 * direction)]
        draw.polygon(pts, fill=(18, 30, 46))

    assets: dict[str, Path] = {}

    def fit_centered(draw, box, text, font, fill=(18, 30, 46), gap=5):
        lines = text.split("\n")
        x1, y1, x2, y2 = box
        metrics = [draw.textbbox((0, 0), line, font=font) for line in lines]
        heights = [m[3] - m[1] for m in metrics]
        widths = [m[2] - m[0] for m in metrics]
        total_h = sum(heights) + gap * (len(lines) - 1)
        y = y1 + ((y2 - y1) - total_h) / 2
        for line, w, h in zip(lines, widths, heights):
            draw.text((x1 + ((x2 - x1) - w) / 2, y), line, font=font, fill=fill)
            y += h + gap

    def draw_icon(draw, center, radius, fill, label):
        cx, cy = center
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill="white", outline=fill, width=4)
        draw.text((cx, cy - 2), label, font=ImageFont.truetype(r"C:\Windows\Fonts\timesbd.ttf", int(radius * 1.25)), fill=fill, anchor="mm")

    img = Image.new("RGB", (2400, 1320), "white")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((55, 48, 2345, 1268), radius=18, fill=(250, 252, 255), outline=(209, 216, 226), width=3)
    d.text((130, 82), "PROFESSIONAL FULL SYSTEM ARCHITECTURE", font=arch_title, fill=(16, 24, 40))
    d.text((130, 150), "HalluGuard-Med: evidence-grounded generation, claim verification, risk classification, and reporting", font=arch_small, fill=(76, 86, 106))

    def arch_box(box, title, subtitle="", fill=(242, 247, 255), accent=(42, 102, 176), icon=""):
        fill = (255, 255, 255)
        accent = (35, 35, 35)
        x1, y1, x2, y2 = box
        d.rounded_rectangle((x1 + 8, y1 + 8, x2 + 8, y2 + 8), radius=12, fill=(222, 226, 232))
        d.rounded_rectangle(box, radius=12, fill=fill, outline=(39, 48, 67), width=3)
        d.rectangle((x1, y1, x1 + 12, y2), fill=accent)
        if icon:
            draw_icon(d, (x1 + 42, (y1 + y2) / 2), 24, accent, icon)
            text_left = x1 + 80
        else:
            text_left = x1 + 16
        if subtitle:
            fit_centered(d, (text_left, y1 + 10, x2 - 12, y1 + 58), title, arch_bold, fill=(18, 30, 46), gap=1)
            fit_centered(d, (text_left, y1 + 60, x2 - 12, y2 - 8), subtitle, arch_small, fill=(76, 86, 106), gap=1)
        else:
            fit_centered(d, (text_left, y1 + 10, x2 - 14, y2 - 10), title, arch_bold, gap=3)

    main_nodes = [
        ((110, 245, 390, 342), "User", "Question / X-ray", (232, 244, 255), (43, 103, 179), "U"),
        ((455, 245, 735, 342), "Frontend", "HTML / CSS / JS", (233, 247, 240), (38, 134, 87), "F"),
        ((800, 245, 1080, 342), "FastAPI\nBackend", "API routing", (255, 246, 226), (204, 119, 34), "A"),
        ((1145, 245, 1425, 342), "Input\nProcessing", "Validation + intent", (246, 239, 255), (111, 78, 180), "I"),
        ((1490, 245, 1770, 342), "Clinical\nOrchestrator", "Service control", (242, 245, 248), (79, 93, 117), "O"),
    ]
    for item in main_nodes:
        arch_box(*item)
    for x1 in [390, 735, 1080, 1425]:
        arrow(d, (x1, 294), (x1 + 65, 294))

    arch_box((1180, 465, 1510, 568), "Medical RAG", "BM25 + embeddings + Qdrant", (229, 242, 255), (43, 103, 179), "R")
    arch_box((1615, 465, 1945, 568), "TorchXRayVision", "Image analysis branch", (255, 239, 229), (218, 105, 59), "X")
    arrow(d, (1630, 342), (1345, 465))
    arrow(d, (1630, 342), (1780, 465))

    arch_box((1180, 690, 1510, 793), "Grounded\nPrompt", "Citation-aware context", (232, 244, 255), (43, 103, 179), "P")
    arch_box((1615, 690, 1945, 793), "MedGemma via\nOllama", "Grounded generation", (233, 247, 240), (38, 134, 87), "M")
    arch_box((2005, 690, 2325, 793), "Claim\nExtraction", "Clinical claims", (255, 246, 226), (204, 119, 34), "C")
    arrow(d, (1345, 568), (1345, 690))
    arrow(d, (1510, 742), (1615, 742))
    arrow(d, (1945, 742), (2005, 742))
    arrow(d, (1780, 568), (1510, 690))

    arch_box((2005, 900, 2325, 1003), "Evidence\nWindows", "Best evidence ranking", (246, 239, 255), (111, 78, 180), "E")
    arch_box((1615, 900, 1945, 1003), "DeBERTa-v3\nMNLI", "Entail / neutral / contradict", (241, 246, 255), (68, 111, 177), "N")
    arch_box((1180, 900, 1510, 1003), "Local\nCalibration", "Lexical + entity + semantic", (236, 247, 236), (47, 143, 92), "L")
    arrow(d, (2165, 793), (2165, 900))
    arrow(d, (2005, 952), (1945, 952))
    arrow(d, (1615, 952), (1510, 952))

    arch_box((735, 900, 1065, 1003), "Confidence\nFusion", "Support + citations", (231, 247, 240), (38, 134, 87), "S")
    arch_box((735, 1095, 1065, 1198), "Risk\nClassification", "Tier + warnings", (255, 241, 236), (190, 72, 72), "T")
    arch_box((1180, 1095, 1510, 1198), "Verified\nResponse", "Answer + citations", (232, 244, 255), (43, 103, 179), "V")
    arch_box((1615, 1095, 1945, 1198), "PDF Report", "Claim audit", (246, 239, 255), (111, 78, 180), "D")
    arch_box((2005, 1095, 2325, 1198), "Audit &\nLogging", "Timing + evaluation logs", (242, 245, 248), (79, 93, 117), "G")
    arrow(d, (1180, 952), (1065, 952))
    arrow(d, (900, 1003), (900, 1095))
    arrow(d, (1065, 1146), (1180, 1146))
    arrow(d, (1510, 1146), (1615, 1146))
    arrow(d, (1945, 1146), (2005, 1146))

    side_nodes = [
        ((780, 480, 1045, 545), "Citations", (43, 103, 179), "C"),
        ((420, 870, 650, 935), "Confidence", (38, 134, 87), "Q"),
        ((420, 970, 650, 1035), "Risk Tier", (190, 72, 72), "R"),
        ((420, 1070, 650, 1135), "Warnings", (204, 119, 34), "W"),
    ]
    for box, title, accent, icon in side_nodes:
        arch_box(box, title, "", (255, 255, 255), accent, icon)
    arrow(d, (1180, 515), (1045, 515))
    arrow(d, (735, 952), (650, 902))
    arrow(d, (735, 1146), (650, 1002))
    arrow(d, (1180, 1146), (650, 1102))

    d.line((120, 1230, 2280, 1230), fill=(35, 35, 35), width=5)
    path = FIGURE_DIR / "fig1_architecture.png"
    img = img.convert("L").convert("RGB")
    img.save(path)
    assets["architecture"] = path

    def vertical_pipeline(path: Path, title: str, labels: list[str], accent=(43, 103, 179)):
        accent = (35, 35, 35)
        img_h = 2300 if len(labels) <= 15 else 2500
        img = Image.new("RGB", (1100, img_h), "white")
        d = ImageDraw.Draw(img)
        d.text((120, 70), title, font=chart_title, fill=(16, 24, 40))
        top = 170
        box_w, box_h, gap = 800, 86, 42
        x = 150
        for index, label in enumerate(labels):
            y = top + index * (box_h + gap)
            box = (x, y, x + box_w, y + box_h)
            fill = (255, 255, 255) if index % 2 == 0 else (246, 246, 246)
            d.rounded_rectangle((x + 7, y + 7, x + box_w + 7, y + box_h + 7), radius=12, fill=(224, 229, 236))
            d.rounded_rectangle(box, radius=12, fill=fill, outline=(38, 48, 67), width=3)
            d.rectangle((x, y, x + 12, y + box_h), fill=accent)
            draw_icon(d, (x + 48, y + box_h / 2), 24, accent, str(index + 1))
            d.text((x + 90, y + 25), label, font=small, fill=(18, 30, 46))
            if index < len(labels) - 1:
                arrow(d, (x + box_w / 2, y + box_h), (x + box_w / 2, y + box_h + gap - 8))
        img = img.convert("L").convert("RGB")
        img.save(path)

    vertical_pipeline(
        FIGURE_DIR / "fig2_workflow.png",
        "End-to-End Workflow",
        [
            "User Query / Chest X-ray",
            "Input Validation",
            "Medical Intent Detection",
            "Hybrid Retrieval",
            "Evidence Ranking",
            "Grounded Prompt",
            "MedGemma Generation",
            "Claim Extraction",
            "Evidence Window Selection",
            "DeBERTa-v3 Verification",
            "Local Calibration",
            "Confidence Fusion",
            "Risk Classification",
            "Verified Response",
            "PDF Report",
        ],
        (43, 103, 179),
    )
    assets["workflow"] = FIGURE_DIR / "fig2_workflow.png"

    vertical_pipeline(
        FIGURE_DIR / "fig3_verification.png",
        "Claim Verification Pipeline",
        [
            "Generated Response",
            "Sentence Segmentation",
            "Clinical Claim Extraction",
            "Medical Entity Detection",
            "Evidence Window Selection",
            "Best Evidence Ranking",
            "DeBERTa-v3 MNLI",
            "Local Calibration",
            "Severity Weighting",
            "Confidence Fusion",
            "Risk Classification",
            "Claim Status",
            "Final Verification Report",
        ],
        (111, 78, 180),
    )
    assets["verification_pipeline"] = FIGURE_DIR / "fig3_verification.png"

    vertical_pipeline(
        FIGURE_DIR / "fig4_evaluation.png",
        "Automatic Proxy Evaluation Pipeline",
        [
            "50 Medical Questions",
            "Raw MedGemma",
            "HalluGuard-Med",
            "Same Proxy Verifier",
            "Compared Dataset",
            "Accuracy Proxy",
            "Hallucination Proxy",
            "Citation Coverage",
            "Support Signals",
        ],
        (38, 134, 87),
    )
    assets["evaluation_pipeline"] = FIGURE_DIR / "fig4_evaluation.png"

    def horizontal_bar(path: Path, title: str, labels: list[str], values: list[float], max_value: float):
        img = Image.new("RGB", (1000, 540), "white")
        d = ImageDraw.Draw(img)
        d.text((330, 24), title, font=bold, fill=(0, 0, 0))
        left, top, bar_h, gap = 315, 80, 26, 22
        chart_w = 560
        for i, (label, value) in enumerate(zip(labels, values)):
            y = top + i * (bar_h + gap)
            d.text((20, y - 2), label, font=small, fill=(0, 0, 0))
            w = int(chart_w * value / max_value)
            d.rectangle((left, y, left + w, y + bar_h), fill="#2f74c0")
            d.text((left + w + 12, y - 1), f"{value:g}", font=tiny, fill=(0, 0, 0))
        d.line((left, 488, left + chart_w, 488), fill=(0, 0, 0), width=2)
        img.save(path)

    horizontal_bar(
        FIGURE_DIR / "fig2_modules.png",
        "Largest Backend Modules",
        ["clinical_claims", "verification", "retrieval", "main", "radiology", "corpus_ingest", "evidence", "pdf_templates"],
        [990, 984, 828, 646, 429, 386, 371, 345],
        1000,
    )
    assets["modules"] = FIGURE_DIR / "fig2_modules.png"

    def grouped_chart(path: Path, title: str, categories: list[str], baseline: list[float], hallu: list[float], max_value: float, ylabel: str = ""):
        img = Image.new("RGB", (1800, 1100), "white")
        d = ImageDraw.Draw(img)
        baseline_color = "#4c78a8"
        hallu_color = "#2ca25f"
        d.text((90, 62), title, font=chart_title, fill=(16, 24, 40))
        left, bottom = 180, 890
        chart_h, chart_w = 620, 1460
        for tick in range(0, 6):
            value = max_value * tick / 5
            y = bottom - int(chart_h * tick / 5)
            d.line((left, y, left + chart_w, y), fill=(224, 230, 238), width=2)
            d.text((95, y - 16), f"{value:g}", font=chart_small, fill=(86, 96, 112))
        d.line((left, bottom, left, bottom - chart_h), fill=(58, 66, 82), width=3)
        d.line((left, bottom, left + chart_w, bottom), fill=(58, 66, 82), width=3)
        d.rounded_rectangle((1070, 70, 1630, 140), radius=10, fill=(248, 250, 252), outline=(209, 216, 226), width=2)
        d.rectangle((1110, 92, 1140, 122), fill=baseline_color)
        d.text((1160, 88), "Raw MedGemma", font=chart_small, fill=(16, 24, 40))
        d.rectangle((1380, 92, 1410, 122), fill=hallu_color)
        d.text((1430, 88), "HalluGuard-Med", font=chart_small, fill=(16, 24, 40))
        group_w = chart_w / len(categories)
        bar_w = 74 if len(categories) <= 3 else 58
        for i, cat in enumerate(categories):
            x = int(left + i * group_w + group_w / 2 - bar_w - 16)
            b_h = int(chart_h * baseline[i] / max_value)
            h_h = int(chart_h * hallu[i] / max_value)
            d.rounded_rectangle((x, bottom - b_h, x + bar_w, bottom), radius=8, fill=baseline_color)
            d.rounded_rectangle((x + bar_w + 32, bottom - h_h, x + 2 * bar_w + 32, bottom), radius=8, fill=hallu_color)
            tw = d.textlength(cat, font=chart_small)
            d.text((left + i * group_w + group_w / 2 - tw / 2, bottom + 30), cat, font=chart_small, fill=(16, 24, 40))
            d.text((x - 4, bottom - b_h - 38), f"{baseline[i]:g}", font=chart_small, fill=(16, 24, 40))
            d.text((x + bar_w + 28, bottom - h_h - 38), f"{hallu[i]:g}", font=chart_small, fill=(16, 24, 40))
        img.save(path)

    def radar_chart(path: Path):
        import math

        labels = [
            "Proxy\nAccuracy",
            "Hallucination\nReduction",
            "Citation\nCoverage",
            "Weighted\nSupport",
            "Confidence",
            "Contradiction\nSafety",
        ]
        raw = [67.54, 67.78, 28.07, 49.82, 59.25, 94.99]
        hallu = [87.08, 88.35, 67.60, 77.77, 64.32, 97.67]
        img = Image.new("RGB", (1700, 1250), "white")
        d = ImageDraw.Draw(img)
        d.text((100, 60), "Radar Comparison: Raw MedGemma vs HalluGuard-Med", font=chart_title, fill=(16, 24, 40))
        cx, cy, radius = 850, 660, 390
        n = len(labels)

        for level in range(1, 6):
            r = radius * level / 5
            pts = []
            for i in range(n):
                angle = -math.pi / 2 + 2 * math.pi * i / n
                pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
            d.line(pts + [pts[0]], fill=(222, 229, 238), width=3)
            d.text((cx + 8, cy - r - 8), f"{level * 20}", font=chart_small, fill=(116, 126, 142))
        for i, label in enumerate(labels):
            angle = -math.pi / 2 + 2 * math.pi * i / n
            end = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
            d.line((cx, cy, end[0], end[1]), fill=(222, 229, 238), width=3)
            lx = cx + (radius + 105) * math.cos(angle)
            ly = cy + (radius + 85) * math.sin(angle)
            fit_centered(d, (lx - 140, ly - 45, lx + 140, ly + 45), label, chart_small, fill=(16, 24, 40), gap=2)

        def points(values):
            out = []
            for i, value in enumerate(values):
                angle = -math.pi / 2 + 2 * math.pi * i / n
                r = radius * value / 100
                out.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
            return out

        raw_pts = points(raw)
        hallu_pts = points(hallu)
        d.polygon(raw_pts, fill=(218, 232, 246))
        d.line(raw_pts + [raw_pts[0]], fill="#4c78a8", width=5)
        d.polygon(hallu_pts, fill=(216, 242, 225))
        d.line(hallu_pts + [hallu_pts[0]], fill="#2ca25f", width=5)
        for pt in raw_pts:
            d.ellipse((pt[0] - 7, pt[1] - 7, pt[0] + 7, pt[1] + 7), fill="#4c78a8")
        for pt in hallu_pts:
            d.ellipse((pt[0] - 7, pt[1] - 7, pt[0] + 7, pt[1] + 7), fill="#2ca25f")
        d.rounded_rectangle((1090, 1040, 1540, 1130), radius=12, fill=(248, 250, 252), outline=(209, 216, 226), width=2)
        d.rectangle((1130, 1065, 1165, 1100), fill="#4c78a8")
        d.text((1185, 1060), "Raw MedGemma", font=chart_small, fill=(16, 24, 40))
        d.rectangle((1380, 1065, 1415, 1100), fill="#2ca25f")
        d.text((1435, 1060), "HalluGuard-Med", font=chart_small, fill=(16, 24, 40))
        img.save(path)

    grouped_chart(
        FIGURE_DIR / "fig3_metrics.png",
        "Automatic Proxy Metrics",
        ["Accuracy", "Halluc.", "Citation"],
        [67.54, 32.22, 28.07],
        [87.08, 11.65, 67.60],
        100,
    )
    assets["metrics"] = FIGURE_DIR / "fig3_metrics.png"
    radar_chart(FIGURE_DIR / "fig6_radar.png")
    assets["radar"] = FIGURE_DIR / "fig6_radar.png"

    grouped_chart(
        FIGURE_DIR / "fig4_claims.png",
        "Claim Outcome Counts",
        ["Supp.", "Weak", "Unsup.", "Contr."],
        [120, 163, 114, 21],
        [324, 87, 44, 11],
        340,
    )
    assets["claims"] = FIGURE_DIR / "fig4_claims.png"

    grouped_chart(
        FIGURE_DIR / "fig5_confidence.png",
        "Support and Confidence Signals",
        ["Weighted", "Citation", "Confidence"],
        [49.82, 28.07, 59.25],
        [77.77, 67.60, 64.32],
        100,
    )
    assets["confidence"] = FIGURE_DIR / "fig5_confidence.png"
    return assets


def fig(name: str, height: float):
    return RLImage(str(FIGURES[name]), width=COL_W, height=height)


def fig_full(name: str, height: float):
    return RLImage(str(FIGURES[name]), width=PAGE_W - LEFT - RIGHT, height=height)


def build_story() -> list:
    story: list = []
    story.append(NextPageTemplate("normal"))

    story.append(p(
        "<b><i>Abstract</i></b> -- Medical large language models can produce fluent clinical explanations, "
        "but unsupported medical claims remain a major safety concern when answers are not tied to verifiable "
        "evidence. HalluGuard-Med is an explainable retrieval-augmented medical AI framework that combines "
        "hybrid evidence retrieval, MedGemma response generation, clinical claim extraction, DeBERTa-v3 MNLI "
        "verification, severity-weighted confidence fusion, risk tier assignment, and PDF report generation. "
        "The system retrieves medical evidence from a preprocessed MedlinePlus-based corpus using BM25, Google "
        "embeddings, and a Qdrant vector database, generates answers through MedGemma via Ollama, and verifies "
        "generated claims against condition-aligned evidence windows. Chest X-ray support is provided through "
        "TorchXRayVision as an auxiliary caution signal. In automatic proxy evaluation on 50 medical questions, "
        "HalluGuard-Med is compared with Raw MedGemma using the same claim-verification pipeline. HalluGuard-Med "
        "achieves 87.08% proxy claim accuracy compared with 67.54% for Raw MedGemma, while reducing proxy "
        "hallucination rate from 32.22% to 11.65%. Citation coverage increases from 0.2807 to 0.6760, and "
        "weighted claim support increases from 0.4982 to 0.7777. These results show that claim-level evidence "
        "grounding can substantially improve the auditability and reliability profile of medical LLM responses. "
        "The reported metrics are automatic proxy verification results and are not a substitute for clinician "
        "validation.",
        "abstract",
    ))
    story.append(p(
        "<b><i>Keywords</i></b> -- HalluGuard-Med, Medical Hallucination Detection, Retrieval-Augmented Generation, "
        "DeBERTa-v3, MNLI, MedGemma, Clinical Claim Verification, Explainable AI, Qdrant, BM25, Confidence Fusion.",
        "keywords",
    ))

    story.append(section("I. INTRODUCTION"))
    story.append(p(
        "Large language models are increasingly used to answer patient-facing medical questions, summarize common "
        "conditions, and explain symptoms. Their fluency makes them attractive for educational support, but fluency "
        "does not guarantee clinical reliability. A medical answer can be grammatically correct, confident in tone, "
        "and still contain unsupported claims about diagnosis, treatment, warning signs, contraindications, or urgent "
        "care. In medical settings, this gap between language quality and evidence support is a serious concern."
    ))
    story.append(p(
        "Retrieval-augmented generation addresses part of this problem by providing external context to the model. "
        "However, retrieval alone does not verify whether the generated answer actually follows the retrieved evidence. "
        "The generator may omit important qualifications, combine unrelated facts, overstate a recommendation, or "
        "produce a claim that is only partially supported. For this reason, medical AI systems require a post-generation "
        "verification layer that evaluates each clinically meaningful statement against evidence."
    ))
    story.append(p(
        "HalluGuard-Med is designed around this requirement. The framework retrieves medical evidence, generates a "
        "grounded response, extracts clinical claims from the response, verifies those claims using DeBERTa-v3 MNLI "
        "and local evidence signals, estimates confidence, assigns a risk tier, and exports a readable verification "
        "report. The objective is not to replace a clinician, but to make the generated answer more transparent, "
        "auditable, and cautious."
    ))
    story.append(subsection("1.1 Contributions"))
    story.append(p(
        "The main contributions of this work are fourfold. First, HalluGuard-Med integrates hybrid medical retrieval, "
        "MedGemma generation, DeBERTa-v3 MNLI verification, confidence fusion, risk tiering, and report generation "
        "into one end-to-end workflow. Second, the claim verification process combines natural language inference "
        "with evidence-window selection, concept coverage, entity overlap, condition alignment, local calibration, "
        "and severity weighting. Third, the system provides explainability through claim-level status labels, citation "
        "links, support breakdowns, warnings, and PDF reports. Fourth, the system is evaluated against Raw MedGemma "
        "on the same 50-question medical benchmark using automatic proxy claim-level metrics."
    ))

    story.append(section("II. LITERATURE REVIEW"))
    story.append(subsection("2.1 Hallucination Detection in Generative Models"))
    story.append(p(
        "Hallucination detection has become an important research area for generative language models. Manakul et al. "
        "proposed SelfCheckGPT, a black-box approach that identifies unsupported content by measuring consistency "
        "across multiple sampled responses [1]. The method is useful because hallucinated statements often vary "
        "between generations. However, consistency among model outputs does not prove medical correctness. Several "
        "generated responses may agree with each other and still be unsupported by clinical evidence. HalluGuard-Med "
        "therefore uses external retrieved evidence and claim-level verification rather than relying only on response "
        "self-consistency."
    ))
    story.append(subsection("2.2 Medical LLM Hallucination and Med-HALT"))
    story.append(p(
        "Medical hallucination is more critical than general factual error because medical responses can influence "
        "health behavior. Pal et al. introduced Med-HALT to study hallucination tendencies in medical language models "
        "[2]. Benchmarks such as Med-HALT show that medical memory, reasoning, and safety remain difficult for LLMs. "
        "They also show why a practical medical assistant should not only generate answers but also report evidence, "
        "uncertainty, and verification status. HalluGuard-Med follows this operational direction by treating every "
        "answer as a set of claims that must be checked."
    ))
    story.append(subsection("2.3 Retrieval-Augmented Generation"))
    story.append(p(
        "Lewis et al. introduced retrieval-augmented generation for knowledge-intensive NLP tasks [3]. RAG improves "
        "factual grounding by retrieving external documents and conditioning generation on them. In the medical domain, "
        "RAG can reduce unsupported responses by exposing the model to trusted content. Nevertheless, retrieved context "
        "is not equivalent to verified output. A generated sentence may be absent from the retrieved passage or may "
        "misrepresent the evidence. HalluGuard-Med uses RAG as the evidence supply layer and then applies claim-level "
        "post-generation verification."
    ))
    story.append(subsection("2.4 BERT, RoBERTa, DeBERTa, and Medical NLI"))
    story.append(p(
        "Transformer encoders such as BERT and RoBERTa established strong baselines for sentence-pair understanding "
        "and natural language inference [6], [7]. DeBERTa introduced disentangled attention and improved contextual "
        "representations [8], while DeBERTa-v3 further refined pretraining with ELECTRA-style objectives [9]. NLI is "
        "well suited for evidence verification because the retrieved passage can be treated as the premise and the "
        "generated medical claim as the hypothesis. HalluGuard-Med uses this formulation to estimate whether evidence "
        "supports, contradicts, or fails to support each extracted claim."
    ))
    story.append(subsection("2.5 MedGemma and Medical Language Generation"))
    story.append(p(
        "Gemma and MedGemma provide compact open model families for language and medical vision-language tasks [12], "
        "[13]. MedGemma can produce useful medical explanations, but raw generation alone does not provide a complete "
        "safety mechanism. A system that uses MedGemma for medical answers must still verify whether the generated "
        "content is grounded, cite evidence, and communicate uncertainty. HalluGuard-Med uses MedGemma as the response "
        "generator inside a larger evidence-verification architecture."
    ))
    story.append(subsection("2.6 Chest X-ray AI and Multimodal Caution"))
    story.append(p(
        "Chest X-ray AI has been studied through systems such as CheXNet and software resources such as TorchXRayVision "
        "[4], [11]. These tools demonstrate that neural models can identify radiological patterns, but image model output "
        "should be interpreted cautiously. HalluGuard-Med uses TorchXRayVision as an auxiliary signal for chest X-ray "
        "screening and risk assessment rather than as a diagnostic authority. Imaging findings are incorporated into "
        "the evidence trail only with uncertainty-aware handling."
    ))
    story.append(subsection("2.7 Explainable AI and Confidence Estimation"))
    story.append(p(
        "Medical AI systems require explanations that are meaningful to users. Confidence estimation is also important "
        "because a generated answer should communicate when support is weak. Work on semantic uncertainty emphasizes "
        "that reliability should be considered at the level of meaning, not only at the level of tokens [5]. HalluGuard-"
        "Med estimates confidence from multiple interpretable signals: retrieval quality, evidence quality, citation "
        "coverage, claim support, contradiction risk, entity alignment, source conflicts, and imaging status."
    ))
    story.append(subsection("2.8 Research Gap"))
    story.append(p(
        "The reviewed work suggests that no single method is sufficient for trustworthy medical AI. Self-consistency "
        "can reveal unstable generations but cannot prove evidence support. Medical hallucination benchmarks reveal "
        "risk but do not provide an operational assistant. RAG improves access to knowledge but does not verify the "
        "final answer. NLI can compare a claim with evidence but needs retrieval, claim extraction, calibration, and "
        "user-facing reporting to become useful in practice. HalluGuard-Med addresses this gap by combining retrieval, "
        "medical generation, claim verification, confidence fusion, risk tiering, optional image caution, and PDF "
        "reporting in one explainable framework."
    ))
    story.append(KeepTogether([
        table([
            ["Research need", "HalluGuard-Med mechanism"],
            ["Evidence-grounded answering", "Hybrid retrieval over a medical corpus"],
            ["Claim-level verification", "Clinical claim extraction and DeBERTa-v3 MNLI"],
            ["Explainable reliability", "Confidence fusion and support breakdowns"],
            ["User-facing audit trail", "Citation links, risk tier, and PDF report"],
            ["Baseline comparison", "Raw MedGemma versus HalluGuard-Med evaluation"],
        ], [COL_W * 0.44, COL_W * 0.56]),
        p("Table 1. Research gaps and corresponding HalluGuard-Med mechanisms.", "caption"),
    ]))

    story.append(section("III. PROPOSED SYSTEM ARCHITECTURE"))
    story.append(p(
        "HalluGuard-Med is organized as a layered medical AI architecture rather than a single chat model. Each layer "
        "has a specific purpose, receives a defined input, and produces an auditable output for the next layer. This "
        "design is important because hallucination control in medicine requires more than generation quality: the "
        "system must preserve evidence provenance, verify generated claims, communicate uncertainty, and export a "
        "reviewable report."
    ))
    story.append(KeepTogether([
        fig("architecture", 155),
        p("Fig. 1. Layered HalluGuard-Med architecture showing input processing, retrieval, imaging, generation, verification, confidence fusion, risk classification, reporting, and logging.", "caption"),
    ]))
    story.append(subsection("3.1 Frontend and Backend Entry Layer"))
    story.append(p(
        "The frontend layer is implemented with HTML, CSS, and JavaScript. Its purpose is to collect the medical "
        "question, optionally accept an image upload, display the final answer, and request a PDF report. Its input is "
        "the user's query and optional file; its output is a form payload sent to the backend. The FastAPI backend is "
        "the entry point for computation. It receives the payload, validates inputs, reads image bytes safely, and "
        "returns a structured response containing the answer, citations, confidence, warnings, risk tier, and report "
        "metadata."
    ))
    story.append(subsection("3.2 Input Processing and Clinical Orchestration"))
    story.append(p(
        "The input processing layer normalizes the query, validates file type and size, verifies that uploaded images "
        "are readable, and detects medical intent. The output is a cleaned query and validated optional image stream. "
        "The clinical orchestrator then coordinates the remaining services. It is important because retrieval, image "
        "analysis, generation, verification, and reporting must operate on the same case state rather than as isolated "
        "components."
    ))
    story.append(subsection("3.3 Medical Corpus, Retrieval, and Grounded Prompting"))
    story.append(p(
        "The corpus layer stores MedlinePlus-derived health-topic content as condition-oriented chunks with section, "
        "citation, title, alias, and source metadata. The retrieval service receives the cleaned query and returns "
        "ranked evidence objects. BM25 captures exact medical terms, Google embeddings capture semantic similarity, "
        "and Qdrant stores the dense vectors. Reciprocal rank fusion and domain-specific reranking produce a compact "
        "evidence set. The grounded prompt builder then converts retrieved evidence into a prompt that MedGemma can "
        "use while preserving citation identifiers for later verification."
    ))
    story.append(subsection("3.4 Generation, Imaging, and Claim Verification"))
    story.append(p(
        "The generation layer sends the grounded prompt to MedGemma through Ollama and returns an educational medical "
        "answer. When a chest X-ray image is provided, TorchXRayVision produces screening findings and imaging "
        "confidence; this output is treated as an auxiliary caution signal, not as a diagnostic conclusion. The claim "
        "extraction layer receives the generated answer and outputs clinically meaningful claims with claim type and "
        "severity weight. Evidence window selection then maps each claim to focused evidence spans before DeBERTa-v3 "
        "MNLI estimates entailment, neutral, and contradiction probabilities."
    ))
    story.append(subsection("3.5 Calibration, Confidence, Risk, and Reporting"))
    story.append(p(
        "Evidence calibration receives NLI scores and local evidence features, including lexical support, concept "
        "coverage, semantic similarity, entity overlap, citation quality, condition alignment, and retrieval strength. "
        "The confidence fusion layer converts these signals into a reliability score and label. Risk classification "
        "uses support status, contradiction risk, severity weighting, citation coverage, and imaging mismatch to assign "
        "a user-facing tier. The final response layer returns the answer, citations, confidence, warnings, and claim "
        "verification details. The PDF report generator and logs preserve the case for audit, debugging, and evaluation."
    ))
    story.append(KeepTogether([
        table([
            ["Layer", "Purpose / input / output"],
            ["Frontend", "Collect query and optional image; output structured form payload"],
            ["FastAPI backend", "Validate input, coordinate modules, and return answer plus analysis payload"],
            ["Input processing", "Normalize query, validate files, and detect medical intent"],
            ["Medical RAG service", "Retrieve BM25 and Qdrant evidence as citation objects"],
            ["Image analysis service", "Convert chest X-ray screening output into caution-aware findings"],
            ["MedGemma generation", "Produce grounded educational response from evidence prompt"],
            ["Claim verification", "Map extracted claims to evidence and assign support status"],
            ["Confidence and risk", "Fuse support, citations, evidence quality, imaging, and severity signals"],
            ["Reporting and logs", "Export PDF report and preserve timing, audit, and evaluation traces"],
        ], [COL_W * 0.36, COL_W * 0.64]),
        p("Table 2. Architectural layers with their purpose, input role, and output role.", "caption"),
    ]))

    story.append(section("IV. METHODOLOGY"))
    story.append(subsection("4.1 End-to-End Workflow"))
    story.append(p(
        "The workflow begins with a user query q. The retrieval module obtains evidence passages E = {e1, e2, ..., en}. "
        "The grounded query combines q with the highest-ranked evidence. MedGemma generates an answer A. The claim "
        "extractor splits A into clinical claims C = {c1, c2, ..., cm}. Each claim is verified against selected evidence "
        "windows, assigned a support status, and passed to the confidence and risk modules. Finally, the response and "
        "verification payload are exported as a report."
    ))
    story.append(p(
        "Query preprocessing removes empty content, normalizes the medical question, and builds an expanded retrieval "
        "query when image findings are available. Hybrid retrieval then supplies evidence before generation. Verification "
        "is performed after generation so that the final answer is judged at claim level rather than accepted as a single "
        "uninspected paragraph."
    ))
    story.append(KeepTogether([
        table([
            ["Step", "Operation"],
            ["1", "Receive user query and optional chest X-ray image"],
            ["2", "Preprocess query and retrieve evidence using BM25 and dense vector search"],
            ["3", "Construct grounded prompt from retrieved citation objects"],
            ["4", "Generate educational medical answer using MedGemma through Ollama"],
            ["5", "Extract clinical claims from the generated answer"],
            ["6", "Select condition-aligned evidence windows for each claim"],
            ["7", "Run DeBERTa-v3 MNLI and local evidence calibration"],
            ["8", "Fuse confidence, assign risk tier, and export PDF report"],
        ], [COL_W * 0.16, COL_W * 0.84]),
        p("Table 3. End-to-end HalluGuard-Med workflow.", "caption"),
    ]))
    story.append(KeepTogether([
        fig("workflow", 150),
        p("Fig. 2. End-to-end workflow from query preprocessing to report generation.", "caption"),
    ]))
    story.append(subsection("4.2 Hybrid Retrieval Scoring"))
    story.append(p(
        "Hybrid retrieval uses reciprocal rank fusion to combine BM25 and dense retrieval. If rB(e) is the BM25 rank "
        "of evidence e and rD(e) is the dense rank, the fused score is computed as:"
    ))
    story.append(p("RRF(e) = 1 / (k + rB(e)) + 1 / (k + rD(e)).        (1)", "body_noindent"))
    story.append(p(
        "This formulation gives high weight to evidence that appears near the top of either retrieval list while still "
        "allowing lexical and semantic retrieval to complement each other. The final evidence list is filtered and "
        "packaged into citation records."
    ))
    story.append(subsection("4.3 Clinical Claim Extraction"))
    story.append(p(
        "The claim extractor removes headings, citation appendices, generic formatting, and safety-policy boilerplate "
        "before selecting clinical sentences. Very short fragments and low-value image statements are skipped. Each "
        "remaining claim is assigned a claim type, entities, and a severity weight. Claim types include emergency triage, "
        "diagnosis, medication or dosage, treatment, contraindication or adverse effect, risk or complication, prognosis, "
        "symptom, and general medical statements."
    ))
    story.append(subsection("4.4 Evidence Window Selection"))
    story.append(p(
        "Retrieved passages are often longer than a single claim and may contain several facts. HalluGuard-Med builds "
        "focused evidence windows from individual sentences, adjacent sentence pairs, and compact grouped windows. "
        "Windows are ranked using lexical support, concept coverage, semantic support, entity overlap, condition "
        "alignment, and retrieval score. The highest-ranked windows are then used as premises for DeBERTa-v3 MNLI."
    ))
    story.append(subsection("4.5 DeBERTa-v3 MNLI Verification"))
    story.append(p(
        "For each claim ci and evidence window ej, the NLI verifier estimates entailment, contradiction, and neutral "
        "probabilities. A claim is supported when the entailment signal is strong, contradicted when the contradiction "
        "signal is high, and unsupported when evidence is neutral or insufficient. The local evidence score is computed "
        "from interpretable support features:"
    ))
    story.append(p(
        "Slocal = 0.22L + 0.30K + 0.18M + 0.15O + 0.10A + 0.05R.        (2)",
        "body_noindent",
    ))
    story.append(p(
        "Here L is lexical support, K is concept coverage, M is semantic support, O is entity overlap, A is condition "
        "alignment, and R is normalized retrieval score. Local calibration prevents strong condition-aligned evidence "
        "from being ignored when the NLI model assigns an overly neutral label."
    ))
    story.append(KeepTogether([
        fig("verification_pipeline", 145),
        p("Fig. 3. Claim verification pipeline combining evidence windows, DeBERTa-v3 MNLI, local calibration, severity weighting, confidence fusion, and risk tiering.", "caption"),
    ]))
    story.append(subsection("4.6 Severity Weighting and Confidence Fusion"))
    story.append(p(
        "Each claim receives a severity weight w based on its clinical type. Emergency, diagnosis, dosage, treatment, "
        "and contraindication claims receive higher weights than general statements. Weighted support is computed as "
        "the weighted average of supported and weakly supported claims. Confidence fusion combines weighted support, "
        "citation coverage, evidence quality, RAG score, contradiction risk, entity alignment, and source consistency. "
        "The output is a confidence score, confidence label, and set of explanatory reasons."
    ))
    story.append(subsection("4.7 Risk Tier Assignment and Reporting"))
    story.append(p(
        "Risk assessment converts verification signals into a user-facing tier. Tier 1 indicates broadly supported "
        "evidence with low contradiction risk. Tier 2 indicates moderate caution, weak evidence, incomplete citation "
        "coverage, or unsupported claims. Tier 3 is reserved for high-severity triggers such as strong contradiction, "
        "severe unsupported emergency-related content, or image-response mismatch. The PDF report records the final "
        "answer, risk tier, confidence score, claim table, citations, warnings, and optional imaging summary."
    ))
    story.append(KeepTogether([
        table([
            ["Claim status", "Meaning"],
            ["Supported", "Evidence entails or strongly supports the generated claim"],
            ["Weak support", "Evidence partially supports the claim or support is below strong threshold"],
            ["Unsupported", "Retrieved evidence does not adequately support the claim"],
            ["Contradicted", "Evidence conflicts with the generated claim"],
            ["Insufficient", "No condition-aligned evidence was available"],
        ], [COL_W * 0.34, COL_W * 0.66]),
        p("Table 4. Claim status labels used by HalluGuard-Med.", "caption"),
    ]))

    story.append(section("V. IMPLEMENTATION DETAILS"))
    story.append(p(
        "The implementation is a full-stack Python and web application. The backend is organized into modules that "
        "separate retrieval, generation, claim verification, evidence scoring, source conflict detection, confidence "
        "fusion, radiology analysis, PDF report generation, runtime checks, and audit logging. This modular design "
        "makes the system easier to test and allows each safety signal to be inspected independently."
    ))
    story.append(p(
        "The repository contains 29 backend Python modules and 5 frontend HTML, CSS, and JavaScript files. The backend "
        "contains approximately 7,869 lines of Python code at the time of this paper. The values in Table 5 are derived "
        "from repository files, manifests, and configuration defaults rather than estimated externally."
    ))
    story.append(KeepTogether([
        table([
            ["Implementation item", "Repository value"],
            ["Programming language", "Python backend; HTML, CSS, JavaScript frontend"],
            ["Backend framework", "FastAPI with Uvicorn-compatible routing"],
            ["Frontend files", "assistant.html, how.html, index.html, style.css, script.js"],
            ["Backend modules", "29 Python modules, approximately 7,869 lines"],
            ["Medical corpus", "8,281 processed MedlinePlus chunks"],
            ["Chunking configuration", "Maximum 1,800 characters; minimum 220 characters"],
            ["BM25 tokenizer", "regex:[a-z0-9]+"],
            ["Vector database", "Qdrant collection halluguard_med_corpus_v1"],
            ["Embedding model", "gemini-embedding-001, 768 dimensions"],
            ["Retrieval configuration", "BM25 top-8, dense top-8, final top-5, RRF k=60"],
            ["LLM", "MedGemma through Ollama"],
            ["Verification model", "cross-encoder/nli-deberta-v3-base"],
            ["Image analysis model", "TorchXRayVision"],
        ], [COL_W * 0.42, COL_W * 0.58]),
        p("Table 5. Repository-derived implementation configuration.", "caption"),
    ]))
    story.append(subsection("5.1 Backend Module Responsibilities"))
    story.append(p(
        "The main backend route is implemented in the chat orchestration module. It reads the query and image data, "
        "calls retrieval, forwards grounded context to MedGemma, appends citation metadata when needed, performs "
        "post-generation verification, invokes the final risk assessment, and returns the response payload. The "
        "retrieval module builds BM25 and dense retrieval results. The clinical claim module extracts claims and "
        "verifies each one. The verification module aggregates RAG, NLI, imaging, and safety signals into final risk "
        "assessment fields."
    ))
    story.append(p(
        "The evidence scoring module measures evidence quality, section usefulness, specificity, semantic relevance, "
        "and source consistency. The confidence fusion module converts evidence and claim signals into a confidence "
        "score. The source conflict module identifies contradictory source pairs. The radiology analyzer uses "
        "TorchXRayVision and formats image findings. The report generator and PDF template modules convert the "
        "analysis payload into a readable report without rerunning model inference."
    ))
    story.append(subsection("5.2 Runtime Behavior and Routing"))
    story.append(p(
        "The system runs locally with FastAPI, Ollama, Qdrant, Google embeddings, DeBERTa-v3, and TorchXRayVision. "
        "The NLI model is loaded lazily, and runtime status endpoints report model availability, retrieval status, "
        "Qdrant state, GPU status, and safety pipeline readiness. Logging records stage timing, verification mode, "
        "risk tier, warnings, and citation count. The design is suitable for academic demonstration because it provides "
        "observable intermediate outputs rather than a black-box answer alone."
    ))
    story.append(p(
        "The backend exposes health, model-status, retrieval-status, chat, and report-download routes. The chat route "
        "receives the form payload, calls image validation and optional image analysis, runs the RAG pipeline, generates "
        "a grounded response, invokes post-generation safety and claim verification, and stores the case payload for "
        "report export. The report route accepts a case identifier, rebuilds a report-friendly data object from the "
        "server-stored case state, and renders the PDF in memory. This communication pattern keeps frontend behavior "
        "simple while preserving backend control over risk, confidence, and report fields."
    ))
    story.append(p(
        "The report pathway is intentionally separated from model inference. After the response has been generated and "
        "verified, the report generator consumes the stored analysis payload and creates a document containing the final "
        "answer, citations, claim verification rows, risk tier, confidence label, and warnings. This separation makes "
        "the report reproducible: changing the visual report layout does not require rerunning MedGemma, DeBERTa, or "
        "retrieval."
    ))

    story.append(section("VI. EXPERIMENTAL SETUP"))
    story.append(subsection("6.1 Dataset and Question Set"))
    story.append(p(
        "The automatic evaluation uses 50 medical questions covering common symptoms, chronic disease management, "
        "urgent warning signs, infectious disease, respiratory disease, cardiovascular disease, endocrine disorders, "
        "pregnancy complications, gastrointestinal disease, urinary symptoms, musculoskeletal pain, mental health, "
        "and thromboembolic conditions. The questions are designed to produce multi-claim educational answers rather "
        "than single-word outputs."
    ))
    story.append(KeepTogether([
        table([
            ["Question group", "Representative topics"],
            ["Chronic disease", "Diabetes, hypertension, cholesterol, COPD, heart failure"],
            ["Emergency warning signs", "Stroke, sepsis, heart attack, meningitis, anaphylaxis"],
            ["Respiratory disease", "Pneumonia, asthma, tuberculosis, COVID-19, pulmonary embolism"],
            ["Endocrine and metabolic", "Thyroid disease, DKA, hypoglycemia, vitamin B12 deficiency"],
            ["Gastrointestinal and urinary", "GERD, gallstones, liver disease, pancreatitis, hematuria"],
            ["Musculoskeletal and vascular", "Back pain, arthritis, leg swelling, deep vein thrombosis"],
        ], [COL_W * 0.38, COL_W * 0.62]),
        p("Table 6. Question groups represented in the 50-question evaluation set.", "caption"),
    ]))
    story.append(subsection("6.2 Experimental Configuration"))
    story.append(p(
        "The evaluation uses the repository's processed MedlinePlus corpus containing 8,281 chunks. Chunks are created "
        "with a maximum size of 1,800 characters and a minimum compacted size of 220 characters. BM25 uses the recorded "
        "regex tokenizer [a-z0-9]+, while dense retrieval uses gemini-embedding-001 with 768-dimensional vectors stored "
        "in the Qdrant collection halluguard_med_corpus_v1. Retrieval uses top-8 BM25 candidates, top-8 dense candidates, "
        "RRF k=60, and top-5 fused evidence passages. The virtual environment records Python 3.11.9. Hardware details "
        "are not recorded in the repository artifacts and are therefore not claimed."
    ))
    story.append(subsection("6.3 Compared Systems"))
    story.append(p(
        "Two systems are compared. Raw MedGemma generates answers directly from the medical question using the same "
        "MedGemma model through Ollama. HalluGuard-Med uses the complete framework: retrieval, grounded generation, "
        "claim extraction, DeBERTa-v3 verification, local evidence calibration, confidence fusion, risk tiering, and "
        "citation reporting. Both systems are evaluated using the same proxy verification pipeline after answer generation."
    ))
    story.append(subsection("6.4 Evaluation Protocol and Metrics"))
    story.append(p(
        "For every question, both answers are processed by the claim-verification pipeline. The evaluator extracts "
        "claims, retrieves evidence for the question, verifies each claim, and stores a compact row for each method. "
        "The completed dataset contains 100 rows, 50 per method, with no empty answers and no zero-claim rows. The "
        "primary metrics are proxy claim accuracy, proxy hallucination rate, citation coverage, weighted claim support, "
        "weighted contradiction risk, contradiction count, and mean confidence score."
    ))
    story.append(KeepTogether([
        fig("evaluation_pipeline", 95),
        p("Fig. 4. Automatic proxy evaluation pipeline used for the Raw MedGemma and HalluGuard-Med comparison.", "caption"),
    ]))
    story.append(p(
        "Proxy claim accuracy is calculated as:"
    ))
    story.append(p("Accuracyproxy = (Supported + WeakSupport) / TotalClaims.        (3)", "body_noindent"))
    story.append(p(
        "Proxy hallucination rate is calculated as:"
    ))
    story.append(p("Hallucinationproxy = (Unsupported + Contradicted) / TotalClaims.        (4)", "body_noindent"))
    story.append(p(
        "These values should be interpreted as automatic proxy evaluation results. They measure whether the verifier "
        "finds support in retrieved evidence, not whether a clinician independently judged the answer correct."
    ))
    story.append(KeepTogether([
        table([
            ["Validation item", "Value"],
            ["Questions", "50"],
            ["Compared methods", "2"],
            ["Dataset rows", "100"],
            ["Empty answers", "0"],
            ["Zero-claim rows", "0"],
            ["Record errors", "0"],
        ], [COL_W * 0.55, COL_W * 0.45]),
        p("Table 7. Final automatic evaluation dataset validation.", "caption"),
    ]))
    story.append(subsection("6.5 Qualitative Case Study"))
    story.append(p(
        "A representative end-to-end trace is the question: 'What are signs of a heart attack?' The retrieval layer "
        "selected MedlinePlus Heart Attack as the top citation, with additional cardiovascular sources returned by "
        "the hybrid search. The grounded prompt therefore contained evidence about blocked blood flow, oxygen loss, "
        "rapid treatment, chest discomfort, shortness of breath, upper-body discomfort, nausea, dizziness, and cold "
        "sweat. MedGemma generated an educational answer summarizing these warning signs and emphasizing urgent care."
    ))
    story.append(p(
        "The claim extractor produced 10 clinical claims. The verification layer marked all 10 as supported in the "
        "stored evaluation trace. Example verified claims include that a heart attack occurs when blood flow to the "
        "heart is suddenly blocked, that the heart can be deprived of oxygen, that delayed treatment can damage heart "
        "muscle, and that chest discomfort is a common symptom. For this case, citation coverage was 1.0, weighted "
        "claim support was 1.0, confidence was 0.8286 with a high label, and the assigned risk level was Tier 1. This "
        "case illustrates how the system connects the final response to retrieved evidence, claim verification, "
        "confidence fusion, and risk reporting without introducing a separate manual judgment."
    ))

    story.append(section("VII. RESULTS AND ANALYSIS"))
    story.append(p(
        "Table 8 summarizes the final automatic proxy results. HalluGuard-Med produces more extracted claims because "
        "its answer flow tends to include more evidence-grounded clinical detail. More importantly, it produces a "
        "larger number of supported claims and fewer unsupported or contradicted claims than Raw MedGemma."
    ))
    story.append(KeepTogether([
        fig("metrics", 130),
        p("Fig. 5. Automatic proxy metric comparison between Raw MedGemma and HalluGuard-Med.", "caption"),
    ]))
    story.append(KeepTogether([
        fig("radar", 150),
        p("Fig. 6. Radar comparison of Raw MedGemma and HalluGuard-Med across proxy accuracy, hallucination reduction, citation coverage, weighted support, confidence, and contradiction safety.", "caption"),
    ]))
    story.append(KeepTogether([
        table([
            ["Metric", "Raw MedGemma", "HalluGuard-Med"],
            ["Questions", "50", "50"],
            ["Total extracted claims", "419", "472"],
            ["Supported claims", "120", "324"],
            ["Weakly supported claims", "163", "87"],
            ["Unsupported claims", "114", "44"],
            ["Contradicted claims", "21", "11"],
            ["Proxy claim accuracy", "67.54%", "87.08%"],
            ["Proxy hallucination rate", "32.22%", "11.65%"],
            ["Mean weighted claim support", "0.4982", "0.7777"],
            ["Mean citation coverage", "0.2807", "0.6760"],
            ["Mean confidence score", "0.5925", "0.6432"],
        ], [COL_W * 0.48, COL_W * 0.26, COL_W * 0.26]),
        p("Table 8. Raw MedGemma and HalluGuard-Med automatic proxy comparison.", "caption"),
    ]))
    story.append(subsection("7.1 Claim Accuracy and Hallucination Rate"))
    story.append(p(
        "In automatic proxy evaluation, HalluGuard-Med reaches 87.08% claim accuracy, while Raw MedGemma reaches "
        "67.54%. This is an absolute gain of 19.54 percentage points and a relative gain of 28.93%. The hallucination "
        "rate decreases from 32.22% to 11.65%, an absolute reduction of 20.57 percentage points and a relative reduction "
        "of 63.84%. These values suggest that retrieval and claim verification substantially reduce unsupported content."
    ))
    story.append(p(
        "The hallucination reduction is particularly important because the evaluation counts both unsupported and "
        "contradicted claims as hallucination-proxy events. Unsupported claims may be unverifiable rather than clinically "
        "false, but they are still undesirable in a medical assistant because a user cannot inspect a clear evidence path. "
        "Contradicted claims are more severe because retrieved evidence conflicts with the generated statement."
    ))
    story.append(KeepTogether([
        fig("claims", 130),
        p("Fig. 7. Claim outcome distribution across the 50-question comparison.", "caption"),
    ]))
    story.append(subsection("7.2 Citation Coverage and Weighted Support"))
    story.append(p(
        "Citation coverage increases from 0.2807 for Raw MedGemma to 0.6760 for HalluGuard-Med. Weighted claim support "
        "increases from 0.4982 to 0.7777. This matters because weighted support gives greater importance to clinically "
        "sensitive claims such as diagnosis, emergency triage, treatment, dosage, and contraindication statements. The "
        "higher score indicates that HalluGuard-Med connects important claims to stronger evidence more consistently."
    ))
    story.append(KeepTogether([
        fig("confidence", 130),
        p("Fig. 8. Weighted support, citation coverage, and confidence signals.", "caption"),
    ]))
    story.append(subsection("7.3 Contradiction and Confidence"))
    story.append(p(
        "Raw MedGemma produces 21 contradicted claims out of 419 extracted claims, corresponding to a contradiction "
        "rate of approximately 5.01%. HalluGuard-Med produces 11 contradicted claims out of 472 extracted claims, "
        "corresponding to approximately 2.33%. Mean confidence also increases from 0.5925 to 0.6432. The confidence "
        "gain is smaller than the support and citation gains because confidence fusion remains conservative when any "
        "unsupported or weakly supported claims are present."
    ))
    story.append(KeepTogether([
        table([
            ["Criterion", "HalluGuard-Med", "Raw MedGemma", "Tie"],
            ["Higher weighted claim support", "43", "7", "0"],
            ["Lower hallucination rate", "37", "5", "8"],
        ], [COL_W * 0.48, COL_W * 0.22, COL_W * 0.20, COL_W * 0.10]),
        p("Table 9. Per-question win counts in the automatic comparison.", "caption"),
    ]))
    story.append(p(
        "On a per-question basis, HalluGuard-Med has higher weighted claim support on 43 out of 50 questions. It has "
        "a lower hallucination rate on 37 questions, Raw MedGemma has a lower hallucination rate on 5 questions, and "
        "8 questions are tied. This pattern indicates that the benefit is not caused by a small number of outlier cases."
    ))

    story.append(section("VIII. DISCUSSION"))
    story.append(subsection("8.1 Why HalluGuard-Med Performs Better"))
    story.append(p(
        "The performance difference arises from the separation between generation and verification. Raw MedGemma is "
        "asked to generate a complete answer directly. It may produce a fluent response, but the response is not forced "
        "to maintain an explicit relationship with retrieved evidence. HalluGuard-Med first supplies evidence through "
        "hybrid retrieval and then checks the generated answer claim by claim. This turns the answer from a single block "
        "of text into an auditable set of clinical statements."
    ))
    story.append(subsection("8.2 Role of Retrieval and Evidence Grounding"))
    story.append(p(
        "Retrieval supplies the factual basis for the answer. BM25 captures exact clinical terms, while dense retrieval "
        "captures semantically related evidence. Qdrant enables vector search over the corpus, and citation metadata "
        "keeps retrieved evidence connected to later verification. Evidence grounding is therefore present not only "
        "before generation but also after generation when each claim is matched to a best evidence window."
    ))
    story.append(p(
        "Evidence grounding also changes how the answer can be inspected. A raw answer gives the user a paragraph of "
        "medical text. HalluGuard-Med produces a structured trail: source condition, evidence section, citation id, "
        "claim text, support score, contradiction score, and reason. This structure is useful for debugging and for "
        "academic evaluation because errors can be traced to retrieval, generation, claim extraction, or verification."
    ))
    story.append(subsection("8.3 Role of Claim Verification"))
    story.append(p(
        "Claim verification is the central safety layer. DeBERTa-v3 MNLI provides a sentence-pair reasoning signal, "
        "while local evidence calibration adds interpretable support features. This combination is useful because "
        "medical evidence may be phrased differently from generated text. The local support features help distinguish "
        "a weak lexical match from a meaningful clinical match."
    ))
    story.append(subsection("8.4 Explainability and User Trust"))
    story.append(p(
        "The system is explainable because it reports why an answer is considered reliable or risky. A user can inspect "
        "claim status labels, best citations, support scores, contradiction scores, confidence reasons, warnings, and "
        "risk tier. This audit trail is more informative than a raw answer. It also makes failure modes visible: if a "
        "claim is unsupported, the report exposes that weakness instead of hiding it behind fluent text."
    ))
    story.append(p(
        "The confidence score is also explainable because it is derived from named signals. Low confidence can result "
        "from weak claim support, poor citation coverage, source conflict, low evidence quality, imaging mismatch, or "
        "elevated contradiction risk. This makes confidence different from a generic probability attached to the model. "
        "It is a summary of observable verification evidence."
    ))
    story.append(subsection("8.5 Proxy Evaluation and Human Evaluation"))
    story.append(p(
        "The evaluation is intentionally described as automatic proxy evaluation. It is valuable for comparing system "
        "behavior under a fixed verifier, but it is not equivalent to clinician-labeled accuracy. A verifier can miss "
        "nuance, over-credit partial evidence, or be limited by the retrieved corpus. Human evaluation remains necessary "
        "for publication-level clinical claims. The present results should therefore be interpreted as evidence that "
        "the architecture improves evidence alignment, not as proof of clinical correctness."
    ))
    story.append(subsection("8.6 Trade-offs and Research Implications"))
    story.append(p(
        "The main trade-off is computational overhead. HalluGuard-Med performs retrieval, evidence scoring, MedGemma "
        "generation, claim extraction, NLI verification, confidence fusion, risk assessment, logging, and optional PDF "
        "generation, whereas Raw MedGemma only generates text. The repository records timing fields for these stages, "
        "but this paper does not report hardware-normalized latency because hardware details are not recorded in the "
        "project artifacts. The added computation is justified when the goal is auditability rather than only short "
        "answer latency."
    ))
    story.append(p(
        "The clinical usefulness of the framework lies in transparency. A user or reviewer can see which claims are "
        "supported, which citations were used, which claims are weak, and why a confidence score was assigned. For "
        "research, the architecture separates sources of error: retrieval failure, generation drift, claim extraction "
        "error, NLI misclassification, and confidence calibration can be studied independently. This makes the system "
        "a practical foundation for future clinician-reviewed evaluation."
    ))

    story.append(section("IX. LIMITATIONS"))
    story.append(p(
        "The first limitation is the use of proxy evaluation. The same automated verifier evaluates both systems, which "
        "makes the comparison consistent but not clinically definitive. The second limitation is corpus coverage. "
        "MedlinePlus provides trusted consumer health information, but it does not cover every specialty guideline, "
        "local protocol, drug interaction, or rare condition. If relevant evidence is absent from the corpus, the system "
        "may mark a correct claim as unsupported or may fail to retrieve the best source."
    ))
    story.append(p(
        "The third limitation is the NLI model. DeBERTa-v3 MNLI is strong for general natural language inference, but "
        "it is not a dedicated biomedical fact-verification model. The fourth limitation is retrieval quality. Hybrid "
        "retrieval improves coverage but can still return off-topic passages for broad or ambiguous queries. The fifth "
        "limitation is imaging. TorchXRayVision provides useful caution signals, but the image pathway is not a substitute "
        "for radiologist interpretation. The current implementation is also English-oriented and depends on local "
        "services such as Ollama and Qdrant. Dataset scale is limited to the 50-question automatic comparison and the "
        "available MedlinePlus-derived corpus. Finally, the system has not yet been validated by clinicians, so its "
        "results should be treated as academic prototype evidence."
    ))

    story.append(section("X. FUTURE WORK"))
    story.append(p(
        "The most important future direction is clinician evaluation. Medical experts should label extracted claims "
        "as supported, partially supported, unsupported, contradicted, or not assessable. System labels can then be "
        "compared with human labels using accuracy, precision, recall, F1-score, and inter-rater agreement. A larger "
        "question set should also be constructed across more specialties, medication scenarios, emergency cases, and "
        "multimodal examples."
    ))
    story.append(p(
        "Future research can also examine biomedical NLI models trained on clinical or biomedical entailment data, "
        "medical knowledge graphs, guideline-based retrieval, FHIR/EHR integration, human-in-the-loop verification, "
        "sentence-level citation grounding inside the final answer, multilingual support, and stronger multimodal "
        "reasoning. The report generator can be extended with reviewer-friendly error analysis, and the corpus can "
        "include guideline sources where licensing permits. These directions would move the system from an explainable "
        "prototype toward a stronger research-grade clinical safety framework."
    ))

    story.append(section("XI. CONCLUSION"))
    story.append(p(
        "HalluGuard-Med presents a complete explainable medical AI framework that combines retrieval, MedGemma generation, "
        "claim extraction, DeBERTa-v3 MNLI verification, local evidence calibration, severity weighting, confidence fusion, "
        "risk tiering, optional chest X-ray caution, and PDF report generation. The system is designed around the principle "
        "that medical answers should be verifiable at the claim level rather than accepted solely because they are fluent."
    ))
    story.append(p(
        "Automatic proxy evaluation on 50 medical questions shows that HalluGuard-Med outperforms Raw MedGemma across "
        "claim accuracy, hallucination rate, weighted support, citation coverage, contradiction rate, and per-question "
        "win counts. The results support the value of retrieval-grounded verification and explainable reporting. At the "
        "same time, the paper treats these metrics honestly as proxy verifier results and identifies clinician evaluation "
        "as the key next step."
    ))

    story.append(section("XII. ACKNOWLEDGMENT"))
    story.append(p(
        "The authors thank the Department of Engineering, Sciences and Humanities at Vishwakarma Institute of Technology, "
        "Pune, for guidance and support during the development of this project. The authors also acknowledge the open-"
        "source communities and public medical data providers whose tools, datasets, and documentation supported the "
        "implementation of HalluGuard-Med."
    ))

    story.append(section("REFERENCES"))
    refs = [
        '[1] P. Manakul, A. Liusie, and M. J. F. Gales, "SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models," arXiv:2303.08896, 2023.',
        '[2] A. Pal et al., "Med-HALT: Medical Domain Hallucination Test for Large Language Models," arXiv:2307.15343, 2023.',
        '[3] P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," Advances in Neural Information Processing Systems, vol. 33, pp. 9459-9474, 2020.',
        '[4] P. Rajpurkar et al., "CheXNet: Radiologist-Level Pneumonia Detection on Chest X-Rays with Deep Learning," arXiv:1711.05225, 2017.',
        '[5] S. Kuhn et al., "Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation," Nature, vol. 625, pp. 517-523, 2024.',
        '[6] J. Devlin, M. W. Chang, K. Lee, and K. Toutanova, "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding," NAACL-HLT, 2019.',
        '[7] Y. Liu et al., "RoBERTa: A Robustly Optimized BERT Pretraining Approach," arXiv:1907.11692, 2019.',
        '[8] P. He, X. Liu, J. Gao, and W. Chen, "DeBERTa: Decoding-enhanced BERT with Disentangled Attention," International Conference on Learning Representations, 2021.',
        '[9] P. He, J. Gao, and W. Chen, "DeBERTaV3: Improving DeBERTa using ELECTRA-Style Pre-Training with Gradient-Disentangled Embedding Sharing," arXiv:2111.09543, 2021.',
        '[10] N. Reimers and I. Gurevych, "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks," EMNLP-IJCNLP, 2019.',
        '[11] J. D. M. Cohen et al., "TorchXRayVision: A Library of Chest X-ray Datasets and Models," Medical Imaging with Deep Learning, 2020.',
        '[12] Google DeepMind, "Gemma: Open Models Based on Gemini Research and Technology," Technical Report, 2024.',
        '[13] Google DeepMind, "MedGemma: Medical Vision-Language Models for Healthcare Applications," Technical Documentation, 2025.',
        '[14] Qdrant Team, "Qdrant: Vector Similarity Search Engine and Vector Database," Technical Documentation, 2024.',
        '[15] Google AI, "Generative AI Embeddings API Documentation," 2024.',
        '[16] MedlinePlus, "Health Topics XML Files," U.S. National Library of Medicine.',
        '[17] S. Robertson and H. Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond," Foundations and Trends in Information Retrieval, 2009.',
        '[18] Hugging Face, "Transformers: State-of-the-art Machine Learning for PyTorch, TensorFlow, and JAX," Software Documentation.',
    ]
    for ref in refs:
        story.append(Paragraph(ref, STYLES["ref"]))
    return story


def build_pdf() -> None:
    global FIGURES
    FIGURES = make_figure_assets()
    first_frames = [
        Frame(LEFT, BOTTOM, COL_W, FIRST_TOP - BOTTOM, id="first_left", leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0),
        Frame(LEFT + COL_W + GAP, BOTTOM, COL_W, FIRST_TOP - BOTTOM, id="first_right", leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0),
    ]
    normal_frames = [
        Frame(LEFT, BOTTOM, COL_W, NORMAL_TOP - BOTTOM, id="normal_left", leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0),
        Frame(LEFT + COL_W + GAP, BOTTOM, COL_W, NORMAL_TOP - BOTTOM, id="normal_right", leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0),
    ]
    arch_frame_h = 308
    arch_columns_top = NORMAL_TOP - arch_frame_h - 14
    arch_frames = [
        Frame(LEFT, NORMAL_TOP - arch_frame_h, PAGE_W - LEFT - RIGHT, arch_frame_h, id="arch_full", leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0),
        Frame(LEFT, BOTTOM, COL_W, arch_columns_top - BOTTOM, id="arch_left", leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0),
        Frame(LEFT + COL_W + GAP, BOTTOM, COL_W, arch_columns_top - BOTTOM, id="arch_right", leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0),
    ]
    doc = BaseDocTemplate(str(PDF_PATH), pagesize=A4, leftMargin=LEFT, rightMargin=RIGHT, topMargin=PAGE_H - NORMAL_TOP, bottomMargin=BOTTOM)
    doc.addPageTemplates([
        PageTemplate(id="first", frames=first_frames, onPage=draw_first_page),
        PageTemplate(id="normal", frames=normal_frames, onPage=draw_header),
        PageTemplate(id="arch", frames=arch_frames, onPage=draw_header),
    ])
    doc.build(build_story())


if __name__ == "__main__":
    register_fonts()
    STYLES = make_styles()
    build_pdf()
    reader = PdfReader(str(PDF_PATH))
    print(PDF_PATH)
    print(f"pages={len(reader.pages)}")
