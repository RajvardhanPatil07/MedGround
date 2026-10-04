from __future__ import annotations

import shutil
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    FrameBreak,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Flowable,
    Image as RLImage,
)


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT.parent / "Reports"
OUTPUT_DIR = REPORTS_DIR / "paper_revision"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR = OUTPUT_DIR / "figures"
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

PDF_PATH = OUTPUT_DIR / "HalluGuard_Med_DeBERTa_IEEE_Style_Matched_Updated.pdf"
DOWNLOADS_COPY = Path.home() / "Downloads" / PDF_PATH.name

PAGE_W, PAGE_H = A4
LEFT = 50
RIGHT = 50
GAP = 26
COL_W = (PAGE_W - LEFT - RIGHT - GAP) / 2
BOTTOM = 48
FIRST_TOP = 520
NORMAL_TOP = 746


def register_fonts() -> None:
    fonts = {
        "PaperSerif": r"C:\Windows\Fonts\times.ttf",
        "PaperSerif-Bold": r"C:\Windows\Fonts\timesbd.ttf",
        "PaperSerif-Italic": r"C:\Windows\Fonts\timesi.ttf",
        "PaperSerif-BoldItalic": r"C:\Windows\Fonts\timesbi.ttf",
    }
    for name, path in fonts.items():
        if Path(path).exists():
            pdfmetrics.registerFont(TTFont(name, path))


def make_styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "body": ParagraphStyle(
            "body",
            parent=sample["BodyText"],
            fontName="PaperSerif",
            fontSize=10.5,
            leading=11.6,
            alignment=TA_JUSTIFY,
            firstLineIndent=12,
            spaceAfter=4,
        ),
        "body_noindent": ParagraphStyle(
            "body_noindent",
            parent=sample["BodyText"],
            fontName="PaperSerif",
            fontSize=10.5,
            leading=11.6,
            alignment=TA_JUSTIFY,
            firstLineIndent=0,
            spaceAfter=4,
        ),
        "abstract": ParagraphStyle(
            "abstract",
            parent=sample["BodyText"],
            fontName="PaperSerif-BoldItalic",
            fontSize=10.5,
            leading=11.6,
            alignment=TA_JUSTIFY,
            firstLineIndent=0,
            spaceAfter=6,
        ),
        "keywords": ParagraphStyle(
            "keywords",
            parent=sample["BodyText"],
            fontName="PaperSerif-Italic",
            fontSize=10.5,
            leading=11.6,
            alignment=TA_JUSTIFY,
            firstLineIndent=0,
            spaceAfter=8,
        ),
        "section": ParagraphStyle(
            "section",
            parent=sample["Heading1"],
            fontName="PaperSerif-Bold",
            fontSize=10.5,
            leading=12.0,
            alignment=TA_CENTER,
            spaceBefore=6,
            spaceAfter=4,
        ),
        "subsection": ParagraphStyle(
            "subsection",
            parent=sample["Heading2"],
            fontName="PaperSerif-Bold",
            fontSize=10.5,
            leading=12.0,
            alignment=TA_LEFT,
            spaceBefore=4,
            spaceAfter=2,
        ),
        "caption": ParagraphStyle(
            "caption",
            parent=sample["BodyText"],
            fontName="PaperSerif",
            fontSize=9.5,
            leading=10.5,
            alignment=TA_CENTER,
            spaceBefore=2,
            spaceAfter=5,
        ),
        "ref": ParagraphStyle(
            "ref",
            parent=sample["BodyText"],
            fontName="PaperSerif",
            fontSize=9.5,
            leading=10.3,
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
    canvas.drawCentredString(
        PAGE_W / 2,
        PAGE_H - 60,
        "Vishwakarma Institute of Technology, Pune, INDIA.",
    )
    canvas.restoreState()


def draw_first_page(canvas, doc) -> None:
    draw_header(canvas, doc)
    canvas.saveState()
    canvas.setFont("PaperSerif-Bold", 17)
    title_lines = [
        "HalluGuard-Med: An Explainable Retrieval-Augmented Medical AI",
        "System for DeBERTa-v3 MNLI Claim Verification and",
        "Baseline MedGemma Comparison",
    ]
    y = PAGE_H - 132
    for line in title_lines:
        canvas.drawCentredString(PAGE_W / 2, y, line)
        y -= 21
    canvas.setFont("PaperSerif", 12.5)
    author_lines = [
        "Dr. Ramkrishna S. Bharsakade, Harshvardhan M. Patil, Rajvardhan P. Patil,",
        "Bhavesh M. Patil, Kartik N. Patil",
    ]
    y -= 21
    for line in author_lines:
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
    for row_index, row in enumerate(data):
        out_row = []
        for col_index, cell in enumerate(row):
            text = escape(str(cell))
            if row_index == 0:
                style = STYLES["table_header"]
            elif col_index > 0 and len(text) <= 14:
                style = STYLES["table_center"]
            else:
                style = STYLES["table_cell"]
            out_row.append(Paragraph(text, style))
        wrapped.append(out_row)
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


class FlowDiagram(Flowable):
    def __init__(self, width: float, height: float = 115):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self) -> None:
        c = self.canv
        c.saveState()
        scale = min(1.0, self.width / 274)
        c.translate((self.width - 274 * scale) / 2, 0)
        c.scale(scale, scale)
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.5)
        boxes = [
            ("Retrieve\nBM25/Qdrant", 6, 72, 58, 24, colors.HexColor("#e8f2ff")),
            ("Generate\nMedGemma", 78, 72, 58, 24, colors.HexColor("#efe8ff")),
            ("Verify\nDeBERTa-v3", 150, 72, 58, 24, colors.HexColor("#ffecec")),
            ("Citations", 78, 32, 58, 24, colors.HexColor("#fff4d6")),
            ("Risk Tier", 150, 32, 58, 24, colors.HexColor("#e8fff7")),
            ("PDF\nReport", 222, 52, 46, 44, colors.HexColor("#e8ffe8")),
        ]
        for label, x, y, w, h, fill in boxes:
            c.setFillColor(fill)
            c.roundRect(x, y, w, h, 3, stroke=1, fill=1)
            c.setFillColor(colors.black)
            c.setFont("PaperSerif-Bold", 6.4)
            lines = label.split("\n")
            for index, line in enumerate(lines):
                c.drawCentredString(x + w / 2, y + h / 2 + 4 - (index * 7), line)
        self._arrow(c, 64, 84, 78, 84)
        self._arrow(c, 136, 84, 150, 84)
        self._arrow(c, 208, 84, 222, 76)
        self._arrow(c, 179, 72, 107, 56)
        self._arrow(c, 136, 44, 150, 44)
        self._arrow(c, 208, 44, 222, 62)
        c.setFont("PaperSerif", 6.2)
        c.drawCentredString(self.width / 2, 8, "Updated workflow: retrieve, generate, verify, enforce citations, assign risk, and report.")
        c.restoreState()

    def _arrow(self, c, x1, y1, x2, y2) -> None:
        c.line(x1, y1, x2, y2)
        dx = x2 - x1
        dy = y2 - y1
        if abs(dx) >= abs(dy):
            direction = 1 if dx >= 0 else -1
            c.line(x2, y2, x2 - 4 * direction, y2 + 3)
            c.line(x2, y2, x2 - 4 * direction, y2 - 3)
        else:
            direction = 1 if dy >= 0 else -1
            c.line(x2, y2, x2 + 3, y2 - 4 * direction)
            c.line(x2, y2, x2 - 3, y2 - 4 * direction)


class HorizontalBarChart(Flowable):
    def __init__(
        self,
        title: str,
        labels: list[str],
        values: list[float],
        width: float,
        height: float = 150,
        max_value: float | None = None,
        value_suffix: str = "",
        bar_color=colors.HexColor("#1f77b4"),
    ):
        super().__init__()
        self.title = title
        self.labels = labels
        self.values = values
        self.width = width
        self.height = height
        self.max_value = max_value or max(values)
        self.value_suffix = value_suffix
        self.bar_color = bar_color

    def draw(self) -> None:
        c = self.canv
        c.saveState()
        c.setFont("PaperSerif-Bold", 8.5)
        c.drawCentredString(self.width / 2, self.height - 10, self.title)
        left = 76
        right = 24
        top = self.height - 28
        row_h = min(15, (self.height - 42) / max(1, len(self.labels)))
        chart_w = self.width - left - right
        c.setFont("PaperSerif", 7.2)
        for i, (label, value) in enumerate(zip(self.labels, self.values)):
            y = top - i * row_h
            c.drawRightString(left - 5, y, label)
            bar_w = chart_w * (value / self.max_value if self.max_value else 0)
            c.setFillColor(self.bar_color)
            c.rect(left, y - 8, bar_w, 8, stroke=0, fill=1)
            c.setFillColor(colors.black)
            c.drawString(left + bar_w + 3, y - 7, f"{value:g}{self.value_suffix}")
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.4)
        c.line(left, 16, left + chart_w, 16)
        c.restoreState()


class GroupedMetricChart(Flowable):
    def __init__(self, width: float, height: float = 145):
        super().__init__()
        self.width = width
        self.height = height
        self.categories = ["Accuracy", "Halluc.", "Citation"]
        self.baseline = [67.54, 32.22, 28.07]
        self.hallu = [87.08, 11.65, 67.60]

    def draw(self) -> None:
        c = self.canv
        c.saveState()
        c.setFont("PaperSerif-Bold", 8.5)
        c.drawCentredString(self.width / 2, self.height - 9, "Baseline vs HalluGuard-Med proxy metrics")
        left = 34
        bottom = 28
        chart_h = self.height - 48
        chart_w = self.width - 48
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.4)
        c.line(left, bottom, left, bottom + chart_h)
        c.line(left, bottom, left + chart_w, bottom)
        group_w = chart_w / len(self.categories)
        bar_w = 13
        for i, cat in enumerate(self.categories):
            x0 = left + i * group_w + 16
            b_h = chart_h * self.baseline[i] / 100
            h_h = chart_h * self.hallu[i] / 100
            c.setFillColor(colors.HexColor("#6aaed6"))
            c.rect(x0, bottom, bar_w, b_h, stroke=0, fill=1)
            c.setFillColor(colors.HexColor("#2ca25f"))
            c.rect(x0 + bar_w + 4, bottom, bar_w, h_h, stroke=0, fill=1)
            c.setFillColor(colors.black)
            c.setFont("PaperSerif", 6.5)
            c.drawCentredString(x0 + bar_w, bottom - 10, cat)
            c.drawCentredString(x0 + bar_w / 2, bottom + b_h + 3, f"{self.baseline[i]:.0f}")
            c.drawCentredString(x0 + bar_w + 4 + bar_w / 2, bottom + h_h + 3, f"{self.hallu[i]:.0f}")
        c.setFont("PaperSerif", 6.5)
        c.setFillColor(colors.HexColor("#6aaed6"))
        c.rect(left + 6, self.height - 24, 7, 7, stroke=0, fill=1)
        c.setFillColor(colors.black)
        c.drawString(left + 16, self.height - 24, "Baseline")
        c.setFillColor(colors.HexColor("#2ca25f"))
        c.rect(left + 70, self.height - 24, 7, 7, stroke=0, fill=1)
        c.setFillColor(colors.black)
        c.drawString(left + 80, self.height - 24, "HalluGuard")
        c.restoreState()


class GroupedClaimOutcomeChart(Flowable):
    def __init__(self, width: float, height: float = 150):
        super().__init__()
        self.width = width
        self.height = height
        self.categories = ["Supp.", "Weak", "Unsup.", "Contr."]
        self.baseline = [120, 163, 114, 21]
        self.hallu = [324, 87, 44, 11]
        self.max_value = 340

    def draw(self) -> None:
        c = self.canv
        c.saveState()
        c.setFont("PaperSerif-Bold", 8.5)
        c.drawCentredString(self.width / 2, self.height - 9, "Claim outcome counts")
        left = 32
        bottom = 28
        chart_h = self.height - 50
        chart_w = self.width - 42
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.4)
        c.line(left, bottom, left, bottom + chart_h)
        c.line(left, bottom, left + chart_w, bottom)
        group_w = chart_w / len(self.categories)
        bar_w = 10
        for i, cat in enumerate(self.categories):
            x0 = left + i * group_w + 9
            b_h = chart_h * self.baseline[i] / self.max_value
            h_h = chart_h * self.hallu[i] / self.max_value
            c.setFillColor(colors.HexColor("#6aaed6"))
            c.rect(x0, bottom, bar_w, b_h, stroke=0, fill=1)
            c.setFillColor(colors.HexColor("#2ca25f"))
            c.rect(x0 + bar_w + 4, bottom, bar_w, h_h, stroke=0, fill=1)
            c.setFillColor(colors.black)
            c.setFont("PaperSerif", 6.2)
            c.drawCentredString(x0 + bar_w, bottom - 10, cat)
            c.drawCentredString(x0 + bar_w / 2, bottom + b_h + 3, str(self.baseline[i]))
            c.drawCentredString(x0 + bar_w + 4 + bar_w / 2, bottom + h_h + 3, str(self.hallu[i]))
        c.setFont("PaperSerif", 6.5)
        c.setFillColor(colors.HexColor("#6aaed6"))
        c.rect(left + 4, self.height - 24, 7, 7, stroke=0, fill=1)
        c.setFillColor(colors.black)
        c.drawString(left + 14, self.height - 24, "Baseline")
        c.setFillColor(colors.HexColor("#2ca25f"))
        c.rect(left + 68, self.height - 24, 7, 7, stroke=0, fill=1)
        c.setFillColor(colors.black)
        c.drawString(left + 78, self.height - 24, "HalluGuard")
        c.restoreState()


def make_figure_assets() -> dict[str, Path]:
    from PIL import Image, ImageDraw, ImageFont

    regular = ImageFont.truetype(r"C:\Windows\Fonts\times.ttf", 25)
    bold = ImageFont.truetype(r"C:\Windows\Fonts\timesbd.ttf", 27)
    small = ImageFont.truetype(r"C:\Windows\Fonts\times.ttf", 22)
    tiny = ImageFont.truetype(r"C:\Windows\Fonts\times.ttf", 20)

    def centered(draw, box, text, font, fill=(0, 0, 0)):
        lines = text.split("\n")
        heights = []
        widths = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            widths.append(bbox[2] - bbox[0])
            heights.append(bbox[3] - bbox[1])
        total_h = sum(heights) + (len(lines) - 1) * 4
        x1, y1, x2, y2 = box
        y = y1 + ((y2 - y1) - total_h) / 2
        for line, w, h in zip(lines, widths, heights):
            draw.text((x1 + ((x2 - x1) - w) / 2, y), line, font=font, fill=fill)
            y += h + 4

    def arrow(draw, start, end):
        draw.line([start, end], fill=(0, 0, 0), width=2)
        x1, y1 = start
        x2, y2 = end
        if abs(x2 - x1) >= abs(y2 - y1):
            direction = 1 if x2 >= x1 else -1
            pts = [(x2, y2), (x2 - 12 * direction, y2 - 8), (x2 - 12 * direction, y2 + 8)]
        else:
            direction = 1 if y2 >= y1 else -1
            pts = [(x2, y2), (x2 - 8, y2 - 12 * direction), (x2 + 8, y2 - 12 * direction)]
        draw.polygon(pts, fill=(0, 0, 0))

    assets: dict[str, Path] = {}

    # Fig. 1 flow diagram.
    img = Image.new("RGB", (1000, 420), "white")
    d = ImageDraw.Draw(img)
    boxes = [
        ("Retrieve\nBM25/Qdrant", (40, 95, 210, 170), "#e8f2ff"),
        ("Generate\nMedGemma", (275, 95, 445, 170), "#efe8ff"),
        ("Verify\nDeBERTa-v3", (510, 95, 680, 170), "#ffecec"),
        ("Citations", (275, 245, 445, 320), "#fff4d6"),
        ("Risk Tier", (510, 245, 680, 320), "#e8fff7"),
        ("PDF\nReport", (760, 160, 900, 285), "#e8ffe8"),
    ]
    for text, box, color in boxes:
        d.rounded_rectangle(box, radius=12, fill=color, outline=(0, 0, 0), width=2)
        centered(d, box, text, bold)
    arrow(d, (210, 132), (275, 132))
    arrow(d, (445, 132), (510, 132))
    arrow(d, (680, 132), (760, 195))
    arrow(d, (595, 170), (360, 245))
    arrow(d, (445, 282), (510, 282))
    arrow(d, (680, 282), (760, 230))
    path = FIGURE_DIR / "fig1_flow.png"
    img.save(path)
    assets["flow"] = path

    def horizontal_bar(path: Path, title: str, labels: list[str], values: list[float], max_value: float, suffix: str = ""):
        img = Image.new("RGB", (1000, 540), "white")
        d = ImageDraw.Draw(img)
        d.text((330, 24), title, font=bold, fill=(0, 0, 0))
        left, top, bar_h, gap = 315, 80, 26, 22
        chart_w = 560
        for i, (label, value) in enumerate(zip(labels, values)):
            y = top + i * (bar_h + gap)
            d.text((20, y - 2), label, font=small, fill=(0, 0, 0))
            w = int(chart_w * value / max_value)
            d.rectangle((left, y, left + w, y + bar_h), fill="#1f77b4")
            d.text((left + w + 12, y - 1), f"{value:g}{suffix}", font=tiny, fill=(0, 0, 0))
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

    def grouped_chart(path: Path, title: str, categories: list[str], baseline: list[float], hallu: list[float], max_value: float):
        img = Image.new("RGB", (1000, 540), "white")
        d = ImageDraw.Draw(img)
        d.text((290, 22), title, font=bold, fill=(0, 0, 0))
        left, bottom = 100, 440
        chart_h, chart_w = 300, 760
        d.line((left, bottom, left, bottom - chart_h), fill=(0, 0, 0), width=2)
        d.line((left, bottom, left + chart_w, bottom), fill=(0, 0, 0), width=2)
        d.rectangle((120, 62, 140, 82), fill="#6aaed6")
        d.text((150, 58), "Baseline", font=small, fill=(0, 0, 0))
        d.rectangle((300, 62, 320, 82), fill="#2ca25f")
        d.text((330, 58), "HalluGuard", font=small, fill=(0, 0, 0))
        group_w = chart_w / len(categories)
        bar_w = 45 if len(categories) <= 3 else 34
        for i, cat in enumerate(categories):
            x = int(left + i * group_w + group_w / 2 - bar_w - 8)
            b_h = int(chart_h * baseline[i] / max_value)
            h_h = int(chart_h * hallu[i] / max_value)
            d.rectangle((x, bottom - b_h, x + bar_w, bottom), fill="#6aaed6")
            d.rectangle((x + bar_w + 16, bottom - h_h, x + 2 * bar_w + 16, bottom), fill="#2ca25f")
            d.text((x - 8, bottom + 12), cat, font=tiny, fill=(0, 0, 0))
            d.text((x, bottom - b_h - 28), f"{baseline[i]:g}", font=tiny, fill=(0, 0, 0))
            d.text((x + bar_w + 16, bottom - h_h - 28), f"{hallu[i]:g}", font=tiny, fill=(0, 0, 0))
        img.save(path)

    grouped_chart(
        FIGURE_DIR / "fig3_metrics.png",
        "Proxy Metric Comparison",
        ["Accuracy", "Halluc.", "Citation"],
        [67.54, 32.22, 28.07],
        [87.08, 11.65, 67.60],
        100,
    )
    assets["metrics"] = FIGURE_DIR / "fig3_metrics.png"

    grouped_chart(
        FIGURE_DIR / "fig4_claims.png",
        "Claim Outcome Counts",
        ["Supp.", "Weak", "Unsup.", "Contr."],
        [120, 163, 114, 21],
        [324, 87, 44, 11],
        340,
    )
    assets["claims"] = FIGURE_DIR / "fig4_claims.png"

    return assets


def fig(name: str, height: float):
    return RLImage(str(FIGURES[name]), width=COL_W, height=height)


def build_story() -> list:
    story: list = []
    story.append(NextPageTemplate("normal"))
    story.append(p(
        "<b><i>Abstract</i></b> -- Medical large language models can produce fluent and useful responses, "
        "but their reliability is limited when generated claims are not grounded in retrieved evidence. "
        "This revised IEEE-style report documents the improved HalluGuard-Med project after strengthening "
        "the claim-verification layer and adding a direct 50-question comparison with baseline MedGemma. "
        "The system integrates a FastAPI backend, hybrid BM25 and Qdrant retrieval, Google embedding based "
        "indexing, MedGemma generation through Ollama, DeBERTa-v3 MNLI claim verification, evidence-window "
        "selection, severity-weighted confidence fusion, risk tiering, citation grounding, and PDF report "
        "generation. Compared with direct MedGemma, HalluGuard-Med improved proxy claim accuracy from 67.54% "
        "to 87.08% and reduced proxy hallucination rate from 32.22% to 11.65% over 50 medical questions. "
        "The retest contained 100 evaluated rows, no empty answers, and no zero-claim rows. These results "
        "show that retrieval-grounded verification improves transparency and reduces unsupported clinical "
        "content, while the metrics remain proxy verifier results rather than human gold-standard clinical validation.",
        "abstract",
    ))
    story.append(p(
        "<b><i>Keywords</i></b> -- DeBERTa-v3, MNLI, Medical Claim Verification, Retrieval-Augmented "
        "Generation, Hallucination Detection, MedGemma, Clinical Evidence Verification, Qdrant, BM25.",
        "keywords",
    ))

    story.append(section("I. INTRODUCTION"))
    story.append(p(
        "Large language models are increasingly used to explain symptoms, summarize conditions, and answer "
        "patient-facing medical questions. In non-critical domains, a fluent answer may be acceptable when a "
        "user later verifies details manually. In medicine, however, a fluent but unsupported answer can create "
        "real risk. Claims about warning signs, diagnosis, medication, urgent care, and imaging findings must "
        "be connected to evidence and must communicate uncertainty."
    ))
    story.append(p(
        "The earlier HalluGuard-Med paper presented a retrieval-augmented medical assistant with claim-level "
        "checking, confidence estimation, risk tiering, and PDF reporting. The updated project preserves that "
        "architecture but improves the scoring layer. The revised verifier separates safety-policy boilerplate "
        "from clinical claims, ranks evidence windows more precisely, uses DeBERTa-v3 MNLI for claim-evidence "
        "classification, and applies local evidence calibration so that strong retrieved support can reduce "
        "false neutral or false contradiction outcomes."
    ))
    story.append(subsection("1.1 Contributions of the Updated Work"))
    story.append(p(
        "The first contribution is an improved clinical claim verifier that combines DeBERTa-v3 MNLI with "
        "concept coverage, entity overlap, condition alignment, retrieval strength, and semantic support. "
        "The second contribution is a preserved end-to-end safety workflow: the same response flow, API "
        "contract, and PDF report format remain intact. The third contribution is a new 50-question comparison "
        "between HalluGuard-Med and direct baseline MedGemma. The fourth contribution is a clearer research "
        "interpretation that reports proxy verifier metrics honestly instead of claiming final clinical accuracy."
    ))
    story.append(subsection("1.2 Problem Statement"))
    story.append(p(
        "The central problem addressed in this work is not simply whether a medical chatbot can generate a "
        "reasonable answer. The harder problem is whether the system can explain why the answer should be trusted. "
        "A response may sound medically correct while still containing unsupported claims, missing citations, "
        "weak evidence, or hidden contradictions. The revised HalluGuard-Med system therefore treats every final "
        "answer as an object that must be audited after generation."
    ))
    story.append(p(
        "This design is especially important for educational medical queries where users often ask broad questions "
        "about symptoms, causes, management, warning signs, and urgent care. These questions produce multi-claim "
        "answers. A single unsupported sentence inside an otherwise useful answer can change the safety profile. "
        "For that reason, the system evaluates claim-level support rather than assigning only a single global score."
    ))

    story.append(section("II. LITERATURE REVIEW"))
    story.append(subsection("2.1 Hallucination Detection and Medical Benchmarks"))
    story.append(p(
        "SelfCheckGPT showed that inconsistent generations can indicate hallucination [1], while Med-HALT "
        "highlighted the difficulty of hallucination evaluation in medical language models [2]. These works "
        "motivate verification, but they do not by themselves provide a user-facing medical workflow with "
        "retrieved citations, claim status labels, confidence scoring, and report generation."
    ))
    story.append(subsection("2.2 Retrieval-Augmented Generation and Evidence Grounding"))
    story.append(p(
        "Retrieval-augmented generation improves factual grounding by placing external evidence into the "
        "generation context [3]. In HalluGuard-Med, retrieval is not treated as sufficient. A generated answer "
        "can still ignore evidence or overstate a point. Therefore, the revised system verifies each extracted "
        "claim against retrieved evidence after generation."
    ))
    story.append(subsection("2.3 Transformer-Based Natural Language Inference"))
    story.append(p(
        "BERT, RoBERTa, DeBERTa, and DeBERTa-v3 demonstrate the value of transformer sentence-pair models "
        "for language understanding [6]-[9]. Natural language inference fits the HalluGuard-Med task because "
        "each evidence snippet can be treated as a premise and each generated clinical statement as a hypothesis. "
        "The verifier labels the relation as supported, contradicted, or unsupported."
    ))
    story.append(subsection("2.4 Medical Imaging and Multi-Modal Caution"))
    story.append(p(
        "Chest X-ray models such as CheXNet and software libraries such as TorchXRayVision show that machine "
        "learning can detect visual patterns in radiology images [4], [11]. However, image classification output "
        "does not automatically become a clinical diagnosis. HalluGuard-Med uses imaging as a cautionary evidence "
        "source and communicates uncertainty through findings, confidence thresholds, and risk tiers."
    ))
    story.append(subsection("2.5 Confidence and Semantic Uncertainty"))
    story.append(p(
        "Semantic uncertainty research argues that generated text should be evaluated at the meaning level rather "
        "than only at the token level [5]. HalluGuard-Med follows a related idea but grounds confidence in retrieved "
        "evidence. The confidence score is not a raw probability that the model is correct. It is a fused reliability "
        "signal based on evidence quality, claim support, citation coverage, conflicts, imaging status, and risk."
    ))
    story.append(KeepTogether([
        table([
            ["Gap in prior work", "Updated HalluGuard-Med response"],
            ["RAG does not verify every generated claim", "Post-generation claim extraction and MNLI verification"],
            ["Lexical overlap can miss semantic support", "Evidence-window ranking with local semantic calibration"],
            ["Raw LLM answers lack auditability", "Citation grounding, claim rows, confidence, and PDF reports"],
            ["No baseline comparison", "50-question HalluGuard-Med vs baseline MedGemma evaluation"],
        ], [COL_W * 0.52, COL_W * 0.48]),
        p("Table 1. Literature and implementation gaps addressed by the revised project.", "caption"),
    ]))

    story.append(section("III. PROPOSED SYSTEM ARCHITECTURE"))
    story.append(p(
        "The architecture remains consistent with the submitted project. The frontend provides a chat-style "
        "medical interface and optional image upload. The FastAPI backend orchestrates retrieval, response "
        "generation, pre-generation safety, post-generation claim verification, confidence fusion, risk "
        "assessment, audit logging, and report export. This preservation is important because the improvements "
        "are scoring improvements, not a redesign of the user workflow."
    ))
    story.append(p(
        "The medical knowledge layer combines a processed corpus, BM25 lexical retrieval, Qdrant vector search, "
        "and Google embedding based indexing. Retrieved evidence is normalized into citation objects with source, "
        "condition, section, score, and rank metadata. MedGemma receives the grounded query and generates an "
        "educational answer. The verifier then extracts claims from the answer and checks each claim against "
        "condition-aligned evidence."
    ))
    story.append(subsection("3.1 User Interface and API Flow"))
    story.append(p(
        "The user begins with a text query and may optionally upload a chest X-ray image. The frontend sends the "
        "input to the FastAPI backend using the existing chat endpoint. The backend first checks image validity "
        "and file size, then constructs the retrieval query. If image analysis is available, likely image findings "
        "are converted into text evidence so that later verification can consider both textual and visual signals."
    ))
    story.append(subsection("3.2 Retrieval and Citation Object Construction"))
    story.append(p(
        "The retrieval layer uses lexical and dense retrieval together because medical questions often contain both "
        "exact clinical terms and broader semantic descriptions. BM25 is useful for exact symptom and disease names, "
        "while dense vectors help retrieve related passages when wording differs. The final citation object stores "
        "the source id, source type, condition, section, text, rank, and score. These fields are later reused in "
        "claim verification and report generation."
    ))
    story.append(subsection("3.3 Response Generation and Safety Gate"))
    story.append(p(
        "The generator receives the grounded context rather than the raw user query alone. This design reduces "
        "ungrounded generation but does not eliminate hallucination. Therefore, HalluGuard-Med does not stop at "
        "RAG. It verifies the generated answer after generation and can warn the user when support is weak, "
        "contradictory, or incomplete."
    ))
    story.append(subsection("3.4 Report Generation"))
    story.append(p(
        "The report layer converts the analysis payload into a readable PDF without re-running model inference. "
        "The report includes risk tier, confidence, claim verification rows, citations, warnings, and image findings "
        "when present. This gives the project an audit trail that is useful for demonstrations, debugging, and "
        "academic evaluation."
    ))
    story.append(KeepTogether([
        table([
            ["Layer", "Function"],
            ["Frontend", "Collects query, optional image, and displays answer/report"],
            ["FastAPI backend", "Coordinates retrieval, generation, verification, and audit flow"],
            ["Retrieval", "BM25, Qdrant, Google embeddings, citation packaging"],
            ["Generation", "MedGemma through Ollama using grounded context"],
            ["Verification", "Claim extraction, DeBERTa-v3 MNLI, local evidence calibration"],
            ["Reporting", "Risk tier, confidence, citations, claim rows, PDF report"],
        ], [COL_W * 0.36, COL_W * 0.64]),
        p("Table 2. Preserved architecture of the revised HalluGuard-Med system.", "caption"),
    ]))
    story.append(KeepTogether([
        fig("flow", 98),
        p("Fig. 1. Updated HalluGuard-Med flow for retrieval, generation, verification, citation grounding, risk assessment, and report export.", "caption"),
    ]))

    story.append(section("IV. UPDATED VERIFICATION METHODOLOGY"))
    story.append(subsection("4.1 Claim Extraction"))
    story.append(p(
        "The revised claim extractor removes low-value safety-policy boilerplate before scoring. Statements such "
        "as general disclaimers, citation instructions, and generic assistant warnings are not treated as clinical "
        "claims. However, dangerous negated advice such as telling a user not to seek emergency care remains "
        "detectable. This prevents the score from being distorted by non-clinical text while preserving safety."
    ))
    story.append(subsection("4.2 Evidence Window Selection"))
    story.append(p(
        "Long retrieved passages can confuse an NLI model because they contain multiple facts. The updated "
        "system builds focused single-sentence and two-sentence evidence windows and then ranks them by local "
        "support features. The ranking considers lexical support, concept coverage, semantic support, entity "
        "overlap, condition alignment, and retrieval score. This gives DeBERTa-v3 a cleaner premise."
    ))
    story.append(subsection("4.3 DeBERTa-v3 MNLI with Local Calibration"))
    story.append(p(
        "The main verifier uses the cross-encoder/nli-deberta-v3-base checkpoint. A claim is checked against "
        "the top evidence windows and assigned entailment, contradiction, and neutral probabilities. The updated "
        "pipeline then combines this NLI signal with local support. If DeBERTa predicts neutral or contradiction "
        "but the evidence has strong condition-aligned support, the system can soften the label to weak support "
        "or supported. This reduces false unsupported labels without ignoring the NLI signal."
    ))
    story.append(subsection("4.4 Confidence Fusion and Risk Tiering"))
    story.append(p(
        "Confidence is calculated from RAG quality, evidence quality, claim support, citation coverage, source "
        "conflicts, entity alignment, and contradiction risk. Claim severity weights give higher importance to "
        "emergency triage, diagnosis, treatment, dosage, and contraindication claims. Risk tiers remain interpretable: "
        "Tier 1 indicates lower risk, Tier 2 indicates moderate caution, and Tier 3 is reserved for high-severity "
        "triggers such as strong contradiction, imaging mismatch, severe unsupported content, or emergency escalation."
    ))
    story.append(subsection("4.5 Claim Type and Severity Weighting"))
    story.append(p(
        "The updated scorer assigns each claim a type such as emergency triage, diagnosis, medication or dosage, "
        "treatment, contraindication or adverse effect, risk or complication, prognosis, symptom, or general. "
        "Higher severity weights are assigned to claims that could directly influence urgent care or medical "
        "decisions. This prevents low-risk general statements from dominating the score when a high-risk claim is "
        "unsupported."
    ))
    story.append(subsection("4.6 Citation Coverage"))
    story.append(p(
        "Citation coverage measures whether supported or weakly supported claims are linked to retrieved evidence. "
        "The revised system improved this signal by selecting cleaner evidence windows and by keeping citation ids "
        "attached to best evidence snippets. Citation coverage is important because an answer without retrievable "
        "evidence is difficult to audit even when it appears fluent."
    ))
    story.append(KeepTogether([
        table([
            ["Claim status", "Meaning in the verifier"],
            ["Supported", "Evidence entails or strongly supports the generated claim"],
            ["Weak support", "Evidence partially supports the claim or support is below strong threshold"],
            ["Unsupported", "Retrieved evidence does not adequately support the claim"],
            ["Contradicted", "Evidence conflicts with the generated claim"],
            ["Insufficient", "No condition-aligned evidence was available"],
        ], [COL_W * 0.34, COL_W * 0.66]),
        p("Table 4. Claim status labels used during post-generation verification.", "caption"),
    ]))

    story.append(section("V. IMPLEMENTATION DETAILS"))
    story.append(p(
        "The code-level changes were intentionally scoped. The public APIs, response flow, frontend behavior, "
        "and PDF report format were preserved. The main implementation changes were placed in the clinical claim "
        "verification module. Safety-policy filtering was added before claim construction. Evidence windows were "
        "expanded to include smaller candidate premises. A shared local support scoring helper now drives both "
        "fallback scoring and NLI calibration."
    ))
    story.append(p(
        "The verifier still returns the same claim-verification fields: claim id, claim text, status, support score, "
        "contradiction score, best citation id, best evidence, reason, support breakdown, matched concepts, missing "
        "concepts, NLI metadata, claim type, and severity weight. This means existing report generation and risk "
        "calculation continue to work without downstream redesign."
    ))
    story.append(KeepTogether([
        table([
            ["Improvement", "Purpose"],
            ["Safety-boilerplate filtering", "Avoids scoring disclaimers as medical facts"],
            ["Smaller evidence windows", "Gives DeBERTa cleaner claim-evidence pairs"],
            ["Local support calibration", "Reduces false neutral or false contradiction outcomes"],
            ["Severity weighting", "Prioritizes high-risk clinical claim types"],
            ["Preserved API/report shape", "Maintains compatibility with existing workflow"],
        ], [COL_W * 0.45, COL_W * 0.55]),
        p("Table 5. Main implementation improvements after the earlier paper.", "caption"),
    ]))
    story.append(subsection("5.1 Runtime Robustness"))
    story.append(p(
        "The DeBERTa-v3 verifier is loaded lazily so that startup remains practical. If model loading fails, the "
        "pipeline falls back to the local lexical, concept, entity, and semantic support scorer instead of crashing. "
        "This fallback behavior is important for classroom demonstration and resource-constrained execution. The "
        "system also logs model status, retrieval status, runtime checks, and verification mode."
    ))
    story.append(subsection("5.2 Preserved Interfaces"))
    story.append(p(
        "No new user-facing feature was required for the scoring improvements. The existing chat endpoint still "
        "returns the final response, analysis payload, warnings, citations, risk tier, and report data. The PDF "
        "report continues to consume the same analysis fields. This makes the improvement easy to evaluate because "
        "the new system can be compared with the old behavior without changing the external workflow."
    ))
    story.append(KeepTogether([
        fig("modules", 126),
        p("Fig. 2. Largest backend modules by approximate current lines of code.", "caption"),
    ]))

    story.append(section("VI. EVALUATION DESIGN"))
    story.append(p(
        "The revised evaluation compares two methods on the same 50 medical questions. The baseline method uses "
        "direct MedGemma generation. The HalluGuard-Med method uses the full retrieval-grounded response flow with "
        "verification, confidence scoring, and citation grounding. Both answers are evaluated by the same claim "
        "verification pipeline, which extracts claims and labels them as supported, weakly supported, unsupported, "
        "or contradicted."
    ))
    story.append(p(
        "The completed retest produced 100 evaluated rows: 50 baseline rows and 50 HalluGuard-Med rows. Final "
        "validation found zero empty answers, zero zero-claim rows, and zero hidden record errors. The dataset files "
        "are proxy_eval_compared_dataset.csv, proxy_eval_metrics.json, and proxy_eval_records.json in the evaluation "
        "retest folder. The metrics are described as proxy claim-level verification metrics because they are produced "
        "by the system verifier rather than by independent clinician labels."
    ))
    story.append(KeepTogether([
        table([
            ["Validation item", "Value"],
            ["Questions evaluated", "50"],
            ["Compared methods", "2"],
            ["Dataset rows", "100"],
            ["Empty answers", "0"],
            ["Zero-claim rows", "0"],
            ["Hidden record errors", "0"],
        ], [COL_W * 0.55, COL_W * 0.45]),
        p("Table 6. Final validation of the comparison dataset.", "caption"),
    ]))
    story.append(subsection("6.1 Question Set"))
    story.append(p(
        "The 50 questions cover common medical information needs such as diabetes, cardiovascular disease, stroke, "
        "pneumonia, hypertension, cholesterol, abdominal pain, appendicitis, asthma, COPD, urinary tract infection, "
        "sepsis, anemia, thyroid disease, chest pain, pulmonary embolism, lung cancer, depression, migraine, "
        "meningitis, dehydration, allergic reaction, GERD, gallstones, liver disease, heart failure, COVID-19, "
        "tuberculosis, back pain, arthritis, vitamin B12 deficiency, pregnancy complications, diabetic ketoacidosis, "
        "hypoglycemia, thyroid storm, hematuria, pancreatitis, inflammatory bowel disease, leg swelling, and deep "
        "vein thrombosis."
    ))
    story.append(subsection("6.2 Output Dataset"))
    story.append(p(
        "For each question, the dataset stores the question id, method name, question text, generated answer, total "
        "claims, supported claims, weak support count, unsupported count, contradicted count, proxy precision, proxy "
        "hallucination rate, mean support, citation coverage, weighted claim support, weighted contradiction risk, "
        "entailed citation coverage, RAG score, confidence score, confidence label, and verification mode. The raw "
        "records file also preserves the detailed claim-verification rows for later inspection."
    ))

    story.append(section("VII. RESULTS AND COMPARISON"))
    story.append(p(
        "The comparison shows a clear improvement for HalluGuard-Med. Baseline MedGemma produced 419 extracted "
        "claims, while HalluGuard-Med produced 472 extracted claims. HalluGuard-Med had more supported claims, "
        "fewer unsupported claims, fewer contradicted claims, higher weighted claim support, higher citation coverage, "
        "and a lower hallucination rate."
    ))
    story.append(KeepTogether([
        fig("metrics", 126),
        p("Fig. 3. Proxy accuracy, hallucination rate, and citation coverage for baseline MedGemma and HalluGuard-Med.", "caption"),
    ]))
    story.append(KeepTogether([
        table([
            ["Metric", "Baseline", "HalluGuard"],
            ["Questions", "50", "50"],
            ["Total extracted claims", "419", "472"],
            ["Supported claims", "120", "324"],
            ["Weakly supported claims", "163", "87"],
            ["Unsupported claims", "114", "44"],
            ["Contradicted claims", "21", "11"],
            ["Proxy claim accuracy / precision", "67.54%", "87.08%"],
            ["Proxy hallucination rate", "32.22%", "11.65%"],
            ["Mean weighted claim support", "0.4982", "0.7777"],
            ["Mean citation coverage", "0.2807", "0.6760"],
            ["Mean confidence score", "0.5925", "0.6432"],
        ], [COL_W * 0.50, COL_W * 0.25, COL_W * 0.25]),
        p("Table 7. Baseline MedGemma and HalluGuard-Med comparison over 50 questions.", "caption"),
    ]))
    story.append(p(
        "The absolute proxy accuracy improvement is 19.54 percentage points, corresponding to a 28.93% relative "
        "gain over baseline. The proxy hallucination rate decreased by 20.57 percentage points, corresponding to "
        "a 63.84% relative reduction. Mean weighted claim support increased by 0.2795, and mean citation coverage "
        "increased by 0.3953. These gains are important because citation coverage and claim support directly affect "
        "whether a medical answer can be audited."
    ))
    story.append(KeepTogether([
        table([
            ["Criterion", "HG-Med", "Base", "Tie"],
            ["Higher weighted claim support", "43", "7", "0"],
            ["Lower hallucination rate", "37", "5", "8"],
        ], [COL_W * 0.48, COL_W * 0.20, COL_W * 0.22, COL_W * 0.10]),
        p("Table 8. Per-question win counts in the completed retest.", "caption"),
    ]))
    story.append(KeepTogether([
        fig("claims", 126),
        p("Fig. 4. Claim outcome distribution across the 50-question comparison.", "caption"),
    ]))
    story.append(subsection("7.1 Claim Outcome Analysis"))
    story.append(p(
        "The largest difference is visible in supported claim count. Baseline MedGemma had 120 supported claims "
        "and 163 weakly supported claims. HalluGuard-Med had 324 supported claims and 87 weakly supported claims. "
        "This indicates that the retrieval-grounded flow not only reduces unsupported content but also moves many "
        "claims from partial support into stronger evidence alignment."
    ))
    story.append(p(
        "Unsupported and contradicted claims also decreased. Baseline MedGemma had 114 unsupported and 21 contradicted "
        "claims. HalluGuard-Med had 44 unsupported and 11 contradicted claims. In medical response evaluation, this "
        "reduction is important because unsupported and contradicted statements are the categories most closely "
        "related to hallucination risk."
    ))
    story.append(subsection("7.2 Weighted Support and Citation Coverage"))
    story.append(p(
        "Mean weighted claim support increased from 0.4982 to 0.7777. This is stronger than a raw count-based gain "
        "because severity-weighted scoring gives greater importance to more clinically sensitive claims. Citation "
        "coverage increased from 0.2807 to 0.6760, showing that the improved workflow connects a much larger share "
        "of answer content to evidence."
    ))

    story.append(section("VIII. DISCUSSION"))
    story.append(subsection("8.1 Meaning of the Improvement"))
    story.append(p(
        "The results indicate that the verification layer improves the reliability profile of the generated answer. "
        "Direct MedGemma can answer many questions fluently, but the output is not automatically connected to "
        "retrieved evidence. HalluGuard-Med improves this by forcing the answer through retrieval, citation packaging, "
        "claim extraction, NLI verification, support scoring, and confidence fusion."
    ))
    story.append(subsection("8.2 Why Citation Coverage Improved"))
    story.append(p(
        "Citation coverage improved because the system stores retrieved evidence as citation objects and links "
        "verified claims to the best supporting evidence. The response may still be generated by MedGemma, but the "
        "post-generation layer evaluates whether the final text is actually supported by retrieved material. This "
        "creates a readable audit path from answer to citation to claim status."
    ))
    story.append(subsection("8.3 Why the Metrics Are Still Proxy Metrics"))
    story.append(p(
        "The evaluation is useful but should be interpreted carefully. A verifier-assigned supported label is not "
        "identical to clinician-confirmed truth. The metrics measure support relative to the retrieved evidence and "
        "the verifier's decision logic. Therefore, the paper should describe these values as proxy claim-level metrics. "
        "For publication-level clinical claims, a human-labeled or expert-reviewed benchmark is still required."
    ))
    story.append(subsection("8.4 Research Value"))
    story.append(p(
        "The project is strongest as a systems paper about explainable verification around a medical LLM. Its novelty "
        "does not depend only on using MedGemma or DeBERTa-v3. The research value comes from combining retrieval, "
        "claim extraction, NLI verification, local evidence calibration, severity weighting, confidence fusion, "
        "risk tiering, citation grounding, imaging caution, and PDF reporting into a single reproducible workflow."
    ))
    story.append(subsection("8.5 Practical Meaning for Users"))
    story.append(p(
        "For a user, the important difference is that HalluGuard-Med does not simply answer. It shows whether the "
        "answer is grounded. The user can inspect citations, warnings, risk tier, and claim-level support. This "
        "does not make the system a clinician, but it makes the generated text more transparent and reduces the "
        "chance that unsupported claims are silently accepted."
    ))

    story.append(section("IX. SAFETY AND LIMITATIONS"))
    story.append(p(
        "HalluGuard-Med is designed as decision support, not as a diagnostic or treatment authority. The system can "
        "retrieve incomplete evidence, miss rare conditions, or assign imperfect NLI labels. DeBERTa-v3 MNLI is a "
        "general NLI model and not a specialized clinical fact-verification model. The imaging component is also a "
        "screening aid and should not replace radiologist interpretation."
    ))
    story.append(p(
        "The project handles uncertainty by using risk tiers, warnings, confidence scores, and citation-linked claim "
        "rows. However, deployment in a real clinical setting would require expert validation, broader datasets, "
        "privacy controls, regulatory review, and monitoring for model drift. The current contribution is therefore "
        "best described as an explainable academic prototype with promising proxy evidence."
    ))
    story.append(subsection("9.1 Privacy and PHI Considerations"))
    story.append(p(
        "The project should avoid storing personally identifiable health information in exported reports or logs. "
        "For demonstration, queries should use synthetic or general medical scenarios. If the system is ever used "
        "with real patient data, it would require explicit consent, secure storage, access control, audit policies, "
        "and deletion procedures."
    ))
    story.append(subsection("9.2 Future Work"))
    story.append(p(
        "Future work should focus on expert-labeled evaluation. The same 50-question dataset can be extended by "
        "asking clinicians or trained annotators to label claims as supported, partially supported, unsupported, "
        "or contradicted. The system labels can then be compared with human labels using accuracy, precision, "
        "recall, F1-score, Cohen's kappa, and error analysis."
    ))
    story.append(KeepTogether([
        table([
            ["Future enhancement", "Reason"],
            ["Human-labeled benchmark", "Converts proxy metrics into externally validated metrics"],
            ["Clinical-domain NLI model", "May improve claim-evidence reasoning"],
            ["Larger question set", "Tests robustness across more conditions"],
            ["Better retrieval coverage", "Reduces insufficient evidence outcomes"],
            ["Report-level error analysis", "Identifies systematic unsupported claim patterns"],
        ], [COL_W * 0.43, COL_W * 0.57]),
        p("Table 9. Recommended next steps for conference-quality validation.", "caption"),
    ]))

    story.append(section("X. CONCLUSION"))
    story.append(p(
        "This revised paper documents the improved HalluGuard-Med system after adding stronger claim filtering, "
        "focused evidence-window selection, DeBERTa-v3 MNLI verification, local support calibration, severity-weighted "
        "confidence scoring, and a direct baseline comparison with MedGemma. The system preserved the existing "
        "architecture, API behavior, report format, and response flow while improving the scoring layer."
    ))
    story.append(p(
        "The 50-question retest showed that HalluGuard-Med outperformed baseline MedGemma on proxy claim accuracy, "
        "hallucination rate, weighted support, citation coverage, and per-question win counts. These results strengthen "
        "the project as a research prototype. The next step for a conference-quality paper is to validate the same "
        "outputs against a human-labeled clinical benchmark and report inter-rater or expert agreement."
    ))
    story.append(section("XI. PROJECT OUTCOME SUMMARY"))
    story.append(p(
        "The final project outcome is an end-to-end explainable medical AI assistant that can answer medical questions, "
        "retrieve supporting evidence, classify generated claims, identify weak or unsupported content, assign a risk "
        "tier, and export a readable verification report. Compared with the earlier paper version, the current version "
        "adds stronger verification logic and a direct baseline comparison. This moves the work from a demonstration "
        "of architecture to a measurable evaluation of verification benefit."
    ))
    story.append(p(
        "From an academic perspective, the most valuable part of the project is the movement from answer generation "
        "to answer verification. Many AI assistant projects stop after connecting a model to an interface. HalluGuard-"
        "Med goes further by asking whether each generated claim is supported, where the evidence came from, how "
        "confident the system should be, and what warning should be shown to the user."
    ))

    story.append(section("XII. ACKNOWLEDGMENT"))
    story.append(p(
        "The authors thank the Department of Engineering, Sciences and Humanities at Vishwakarma Institute of "
        "Technology, Pune, for guidance and support during the development of this project. The authors also "
        "acknowledge the open-source communities and public medical data providers whose tools, datasets, and "
        "documentation supported the implementation of HalluGuard-Med."
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

    doc = BaseDocTemplate(
        str(PDF_PATH),
        pagesize=A4,
        leftMargin=LEFT,
        rightMargin=RIGHT,
        topMargin=PAGE_H - NORMAL_TOP,
        bottomMargin=BOTTOM,
    )
    doc.addPageTemplates([
        PageTemplate(id="first", frames=first_frames, onPage=draw_first_page),
        PageTemplate(id="normal", frames=normal_frames, onPage=draw_header),
    ])
    doc.build(build_story())
    shutil.copy2(PDF_PATH, DOWNLOADS_COPY)


if __name__ == "__main__":
    register_fonts()
    STYLES = make_styles()
    build_pdf()
    reader = PdfReader(str(PDF_PATH))
    print(PDF_PATH)
    print(f"pages={len(reader.pages)}")
    print(DOWNLOADS_COPY)
