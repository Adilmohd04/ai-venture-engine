"""Professional VC Investment Memo PDF generator using ReportLab."""

import io
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether,
)

from models import InvestmentMemo

# Regex to strip emoji and other non-BMP Unicode that Helvetica can't render
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"  # dingbats
    "\U000024C2-\U0001F251"
    "\U0001f926-\U0001f937"
    "\U00010000-\U0010ffff"
    "\u2640-\u2642"
    "\u2600-\u2B55"
    "\u200d"
    "\u23cf"
    "\u23e9"
    "\u231a"
    "\ufe0f"
    "\u3030"
    "]+",
    flags=re.UNICODE,
)


def _safe(text: str) -> str:
    """Remove emoji and non-Latin-1 chars that ReportLab Helvetica cannot render."""
    if not text:
        return ""
    text = _EMOJI_RE.sub("", text)
    # Also replace box-drawing and block chars that Helvetica lacks
    text = text.replace("\u2588", "#").replace("\u2591", "-")  # █ → #, ░ → -
    text = text.replace("\u251c", "|").replace("\u2514", "`")  # ├ → |, └ → `
    text = text.replace("\u2500", "-")  # ─ → -
    text = text.replace("\u2605", "*")  # ★ → *
    return text


# -- Color palette --
DARK_BG = colors.HexColor("#18181b")
HEADER_BG = colors.HexColor("#1e3a5f")
ACCENT = colors.HexColor("#4f46e5")
GREEN = colors.HexColor("#22c55e")
RED = colors.HexColor("#ef4444")
AMBER = colors.HexColor("#f59e0b")
LIGHT_GRAY = colors.HexColor("#f4f4f5")
MID_GRAY = colors.HexColor("#a1a1aa")
DARK_TEXT = colors.HexColor("#18181b")
SECTION_BG = colors.HexColor("#f8fafc")
BORDER_COLOR = colors.HexColor("#e4e4e7")


def _build_styles():
    """Create all paragraph styles for the memo."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "MemoTitle", parent=styles["Title"],
        fontSize=22, textColor=HEADER_BG, spaceAfter=4,
        alignment=TA_CENTER, fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        "MemoSubtitle", parent=styles["Normal"],
        fontSize=10, textColor=MID_GRAY, alignment=TA_CENTER, spaceAfter=16,
    ))
    styles.add(ParagraphStyle(
        "SectionHead", parent=styles["Heading2"],
        fontSize=13, textColor=HEADER_BG, spaceBefore=18, spaceAfter=8,
        fontName="Helvetica-Bold", borderPadding=(0, 0, 2, 0),
    ))
    styles.add(ParagraphStyle(
        "SubHead", parent=styles["Heading3"],
        fontSize=11, textColor=ACCENT, spaceBefore=10, spaceAfter=4,
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        "BodyText2", parent=styles["Normal"],
        fontSize=9.5, textColor=DARK_TEXT, leading=15,
        alignment=TA_JUSTIFY, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        "SmallGray", parent=styles["Normal"],
        fontSize=8, textColor=MID_GRAY, leading=11,
    ))
    styles.add(ParagraphStyle(
        "VerdictStyle", parent=styles["Normal"],
        fontSize=16, textColor=HEADER_BG, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceBefore=8, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "ScoreStyle", parent=styles["Normal"],
        fontSize=28, textColor=ACCENT, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceBefore=4, spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        "CellText", parent=styles["Normal"],
        fontSize=9, textColor=DARK_TEXT, leading=12,
    ))
    styles.add(ParagraphStyle(
        "CellBold", parent=styles["Normal"],
        fontSize=9, textColor=DARK_TEXT, fontName="Helvetica-Bold", leading=12,
    ))
    styles.add(ParagraphStyle(
        "TreeText", parent=styles["Normal"],
        fontSize=9, textColor=DARK_TEXT, leading=13,
    ))
    return styles


def _section_divider():
    return HRFlowable(width="100%", thickness=0.5, color=BORDER_COLOR, spaceAfter=6, spaceBefore=2)


def _wrap_text(text: str, max_len: int = 2000) -> str:
    """Truncate, clean, and convert markdown to ReportLab XML for PDF rendering."""
    if not text:
        return "N/A"
    cleaned = _safe(text)
    # Replace XML-unsafe chars FIRST (before we add our own XML tags)
    cleaned = cleaned.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Strip markdown heading prefixes (## Heading → Heading)
    cleaned = re.sub(r"^#{1,4}\s+", "", cleaned, flags=re.MULTILINE)
    # Convert **bold** → <b>bold</b>  (must come before single *)
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", cleaned)
    # Convert *italic* → <i>italic</i>
    cleaned = re.sub(r"\*(.+?)\*", r"<i>\1</i>", cleaned)
    # Clean bullet prefixes (- item → • item)
    cleaned = re.sub(r"^[\-\*]\s+", "• ", cleaned, flags=re.MULTILINE)
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len] + "..."
    return cleaned


def _score_color(score: float) -> colors.HexColor:
    if score >= 7:
        return GREEN
    if score >= 5:
        return AMBER
    return RED


def _format_market_num(val: str) -> str:
    """Format raw numbers like 5800000000 into $58B."""
    if not val or val == "N/A":
        return "N/A"
    # If already formatted with $ or B/M/K, return as-is
    if any(c in val for c in "$BMKbmk"):
        return val
    # Try to parse as number
    try:
        num = float(val.replace(",", ""))
    except (ValueError, TypeError):
        return val
    if num >= 1e9:
        formatted = num / 1e9
        return f"${formatted:.0f}B" if formatted == int(formatted) else f"${formatted:.1f}B"
    if num >= 1e6:
        formatted = num / 1e6
        return f"${formatted:.0f}M" if formatted == int(formatted) else f"${formatted:.1f}M"
    if num >= 1e3:
        return f"${num / 1e3:.0f}K"
    return f"${num:,.0f}"


def generate_memo_pdf(memo: InvestmentMemo) -> bytes:
    """Generate a professional VC investment memo PDF and return bytes."""
    try:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=20 * mm, rightMargin=20 * mm,
            topMargin=18 * mm, bottomMargin=18 * mm,
        )
        styles = _build_styles()
        story = []

        page_w = A4[0] - 40 * mm  # usable width
    except Exception as e:
        print(f"❌ PDF setup error: {e}")
        raise

    # ── Title Block ──
    story.append(Paragraph("Investment Memo", styles["MemoTitle"]))
    date_str = ""
    try:
        dt = datetime.fromisoformat(memo.created_at)
        date_str = dt.strftime("%B %d, %Y")
    except Exception:
        date_str = memo.created_at[:10] if memo.created_at else ""
    story.append(Paragraph(f"Generated {date_str} · AI Venture Intelligence Engine", styles["MemoSubtitle"]))
    story.append(_section_divider())

    # ── Investor Readiness Score ──
    if memo.investor_readiness:
        ir = memo.investor_readiness
        story.append(Paragraph("Investor Readiness Score", styles["SectionHead"]))
        story.append(Paragraph(f"{ir.overall:.1f} / 10", styles["ScoreStyle"]))
        ir_data = [["Dimension", "Score"]]
        ir_items = [
            ("Deck Quality", ir.deck_quality),
            ("Market Opportunity", ir.market_opportunity),
            ("Team Credibility", ir.team_credibility),
            ("Business Model Clarity", ir.business_model_clarity),
            ("Defensibility", ir.defensibility),
        ]
        for dim, val in ir_items:
            ir_data.append([dim, f"{val:.1f} / 10"])
        ir_table = Table(ir_data, colWidths=[page_w * 0.55, page_w * 0.45])
        ir_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SECTION_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(ir_table)

    # ── Top 3 Investor Concerns ──
    if memo.top_investor_concerns:
        story.append(Paragraph("Top Investor Concerns", styles["SectionHead"]))
        for i, concern in enumerate(memo.top_investor_concerns[:3], 1):
            story.append(Paragraph(
                f"<b>{i}.</b> {_wrap_text(concern, 300)}",
                styles["BodyText2"],
            ))

    # ── Startup Overview ──
    story.append(Paragraph("Startup Overview", styles["SectionHead"]))
    story.append(Paragraph(_wrap_text(memo.startup_overview), styles["BodyText2"]))

    # ── Market Size ──
    story.append(Paragraph("Market Size (TAM / SAM / SOM)", styles["SectionHead"]))
    try:
        tam_val = "N/A"
        sam_val = "N/A"
        som_val = "N/A"
        sources_text = ""
        
        if memo.market_size:
            tam_val = _format_market_num(memo.market_size.tam or "N/A")
            sam_val = _format_market_num(memo.market_size.sam or "N/A")
            som_val = _format_market_num(memo.market_size.som or "N/A")
            if memo.market_size.sources:
                sources_text = " · ".join(memo.market_size.sources[:3])
        
        market_data = [
            ["TAM", "SAM", "SOM"],
            [tam_val, sam_val, som_val],
        ]
        market_table = Table(market_data, colWidths=[page_w / 3] * 3)
        market_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, 1), (-1, 1), SECTION_BG),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 1), (-1, 1), 12),
            ("TEXTCOLOR", (0, 1), (-1, 1), ACCENT),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(market_table)
        if sources_text:
            story.append(Spacer(1, 3))
            story.append(Paragraph(f"Sources: {_wrap_text(sources_text, 300)}", styles["SmallGray"]))
    except Exception as e:
        print(f"⚠️  Market size section error: {e}")
        story.append(Paragraph("Market size data unavailable", styles["BodyText2"]))

    # ── Competitor Landscape ──
    if memo.competitor_landscape:
        story.append(Paragraph("Competitor Landscape", styles["SectionHead"]))
        comp_data = [["Company", "Description", "Differentiator"]]
        for c in memo.competitor_landscape[:6]:
            comp_data.append([
                Paragraph(c.name, styles["CellBold"]),
                Paragraph(_wrap_text(c.description, 200), styles["CellText"]),
                Paragraph(_wrap_text(c.differentiator or "—", 150), styles["CellText"]),
            ])
        comp_table = Table(comp_data, colWidths=[page_w * 0.22, page_w * 0.45, page_w * 0.33])
        comp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SECTION_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(comp_table)

    # ── Ecosystem Map ──
    if memo.ecosystem_map and memo.ecosystem_map.categories:
        story.append(Paragraph(
            f"{_safe(memo.ecosystem_map.startup_name)} Ecosystem Map",
            styles["SectionHead"],
        ))
        for cat in memo.ecosystem_map.categories:
            story.append(Paragraph(f"<b>{_safe(cat.name)}</b>", styles["SubHead"]))
            for i, company in enumerate(cat.companies):
                prefix = "`--" if i == len(cat.companies) - 1 else "|--"
                is_main = company.lower() == memo.ecosystem_map.startup_name.lower()
                if is_main:
                    story.append(Paragraph(
                        f"&nbsp;&nbsp;{prefix} <b>{_wrap_text(company, 100)}</b> *",
                        styles["TreeText"],
                    ))
                else:
                    story.append(Paragraph(
                        f"&nbsp;&nbsp;{prefix} {_wrap_text(company, 100)}",
                        styles["TreeText"],
                    ))
        story.append(Spacer(1, 4))

    # ── Market Benchmarking ──
    if memo.market_benchmark and memo.market_benchmark.categories:
        story.append(Paragraph(
            f"Market Benchmarking: {_safe(memo.market_benchmark.startup_name)} vs Competitors",
            styles["SectionHead"],
        ))
        for cat in memo.market_benchmark.categories:
            story.append(Paragraph(f"<b>{_safe(cat.metric_name)}</b>", styles["SubHead"]))
            bm_data = [["Entity", "Value", "Source"]]
            for entry in cat.entries:
                entity_name = _safe(entry.entity)
                if entry.is_startup:
                    entity_name = f"<b>{entity_name}</b> *"
                elif entry.is_median:
                    entity_name = f"<i>{entity_name}</i>"
                bm_data.append([
                    Paragraph(entity_name, styles["CellText"]),
                    Paragraph(_wrap_text(entry.value, 100), styles["CellBold"]),
                    Paragraph(_wrap_text(entry.source, 100), styles["CellText"]),
                ])
            bm_table = Table(bm_data, colWidths=[page_w * 0.35, page_w * 0.35, page_w * 0.30])
            bm_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SECTION_BG]),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(bm_table)
            if cat.startup_verdict:
                story.append(Paragraph(
                    f"Verdict: <b>{_safe(cat.startup_verdict)}</b>"
                    + (f" ({_safe(cat.startup_percentile)})" if cat.startup_percentile else ""),
                    styles["SmallGray"],
                ))
            story.append(Spacer(1, 4))
        if memo.market_benchmark.overall_position:
            story.append(Paragraph(
                f"Overall: {_wrap_text(memo.market_benchmark.overall_position, 300)}",
                styles["BodyText2"],
            ))

    story.append(_section_divider())

    # ── Key Metrics with Citations ──
    if memo.structured_extraction and memo.structured_extraction.key_metrics:
        story.append(Paragraph("Key Metrics (with Citations)", styles["SectionHead"]))
        metrics_data = [["Metric / Claim", "Source", "Page"]]
        for c in memo.structured_extraction.key_metrics[:12]:
            metrics_data.append([
                Paragraph(_wrap_text(c.text, 250), styles["CellText"]),
                Paragraph(_wrap_text(c.source, 100), styles["CellText"]),
                str(c.page) if c.page else "—",
            ])
        metrics_table = Table(metrics_data, colWidths=[page_w * 0.55, page_w * 0.30, page_w * 0.15])
        metrics_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SECTION_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ]))
        story.append(metrics_table)

    # ── Claim Verifications ──
    if memo.claim_verifications:
        story.append(Paragraph("Claim Verification", styles["SectionHead"]))
        cv_data = [["Claim", "Confidence", "Reasoning"]]
        for cv in memo.claim_verifications[:10]:
            conf_display = cv.confidence.upper()
            cv_data.append([
                Paragraph(_wrap_text(cv.claim, 200), styles["CellText"]),
                Paragraph(conf_display, styles["CellBold"]),
                Paragraph(_wrap_text(cv.reasoning, 200), styles["CellText"]),
            ])
        cv_table = Table(cv_data, colWidths=[page_w * 0.35, page_w * 0.15, page_w * 0.50])
        cv_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SECTION_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ]))
        story.append(cv_table)

    # ── Missing Information ──
    if memo.missing_info:
        story.append(Paragraph("Missing Information", styles["SectionHead"]))
        for item in memo.missing_info:
            story.append(Paragraph(f"• {_wrap_text(item, 300)}", styles["BodyText2"]))

    # ── Confidence Scores ──
    if memo.confidence_scores:
        story.append(Paragraph("Analysis Confidence", styles["SectionHead"]))
        conf_data = [["Dimension", "Confidence"]]
        for dim, level in memo.confidence_scores.items():
            conf_data.append([
                dim.replace("_", " ").title(),
                level.upper(),
            ])
        conf_table = Table(conf_data, colWidths=[page_w * 0.50, page_w * 0.50])
        conf_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SECTION_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ]))
        story.append(conf_table)

    story.append(_section_divider())

    # ── Bull / Bear Debate ──
    story.append(Paragraph("Investment Debate", styles["SectionHead"]))

    # Bull Case
    story.append(Paragraph("Bull Case", styles["SubHead"]))
    story.append(Paragraph(_wrap_text(memo.bull_case, 500), styles["BodyText2"]))

    # Bear Case
    story.append(Paragraph("Bear Case", styles["SubHead"]))
    story.append(Paragraph(_wrap_text(memo.bear_case, 500), styles["BodyText2"]))

    # Bull Rebuttal
    story.append(Paragraph("Bull Rebuttal", styles["SubHead"]))
    story.append(Paragraph(_wrap_text(memo.bull_rebuttal, 500), styles["BodyText2"]))

    # Bear Rebuttal
    story.append(Paragraph("Bear Rebuttal", styles["SubHead"]))
    story.append(Paragraph(_wrap_text(memo.bear_rebuttal, 500), styles["BodyText2"]))

    story.append(_section_divider())

    # ── Risk Signals ──
    if memo.risk_signals and memo.risk_signals.signals:
        story.append(Paragraph("Risk Signals", styles["SectionHead"]))
        risk_data = [["Category", "Severity", "Description"]]
        for sig in memo.risk_signals.signals:
            sev_display = sig.severity.upper()
            risk_data.append([
                Paragraph(sig.category.replace("_", " ").title(), styles["CellBold"]),
                Paragraph(sev_display, styles["CellText"]),
                Paragraph(_wrap_text(sig.description, 250), styles["CellText"]),
            ])
        risk_table = Table(risk_data, colWidths=[page_w * 0.25, page_w * 0.15, page_w * 0.60])
        risk_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SECTION_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(risk_table)
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"Overall Risk Level: <b>{memo.risk_signals.overall_risk_level.upper()}</b> — {_wrap_text(memo.risk_signals.summary, 300)}",
            styles["SmallGray"],
        ))

    story.append(_section_divider())

    # ── Investment Score ──
    story.append(Paragraph("Investment Score", styles["SectionHead"]))

    score_color = _score_color(memo.final_score)
    story.append(Paragraph(f"{memo.final_score:.1f} / 10", styles["ScoreStyle"]))
    story.append(Paragraph(memo.verdict, styles["VerdictStyle"]))
    story.append(Spacer(1, 8))

    # Score breakdown table
    try:
        sb = memo.score_breakdown
        score_items = [
            ("Market Potential", sb.market_potential if sb else 0),
            ("Team Strength", sb.team_strength if sb else 0),
            ("Product Differentiation", sb.product_differentiation if sb else 0),
            ("Moat", sb.moat if sb else 0),
            ("Traction", sb.traction if sb else 0),
        ]
        score_data = [["Dimension", "Score"]]
        for dim, val in score_items:
            score_data.append([dim, f"{val:.1f} / 10"])
        score_table = Table(score_data, colWidths=[page_w * 0.55, page_w * 0.45])
        score_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SECTION_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ]))
        story.append(score_table)
    except Exception as e:
        print(f"⚠️  Score breakdown error: {e}")
        story.append(Paragraph("Score breakdown unavailable", styles["BodyText2"]))

    # ── Judge Reasoning ──
    story.append(Spacer(1, 10))
    story.append(Paragraph("Judge Reasoning", styles["SectionHead"]))
    story.append(Paragraph(_wrap_text(memo.judge_reasoning, 3000), styles["BodyText2"]))

    # ── Footer ──
    story.append(Spacer(1, 20))
    story.append(_section_divider())
    story.append(Paragraph(
        "This memo was generated by the AI Venture Intelligence Engine. "
        "It is intended for informational purposes only and does not constitute investment advice.",
        styles["SmallGray"],
    ))

    try:
        doc.build(story)
        return buf.getvalue()
    except Exception as e:
        print(f"❌ PDF build error: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise Exception(f"PDF generation failed: {str(e)}")
