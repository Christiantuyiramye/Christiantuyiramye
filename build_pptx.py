"""
Generate a polished PowerPoint deck for the Conversational EDA Chatbot &
E-Commerce Customer Churn Prediction project.

Run:
    python3 build_pptx.py

Produces: presentation.pptx (16:9 widescreen)
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
import os

# ---------------------------------------------------------------------------
# Project palette (KDU blue + accents from the report)
# ---------------------------------------------------------------------------
P_BLUE       = RGBColor(0x1E, 0x3C, 0x72)
P_BLUE_LIGHT = RGBColor(0x2A, 0x52, 0x98)
P_ORANGE     = RGBColor(0xE7, 0x6F, 0x51)
P_TEAL       = RGBColor(0x2A, 0x9D, 0x8F)
P_YELLOW     = RGBColor(0xF4, 0xA2, 0x61)
P_GRAY       = RGBColor(0x4B, 0x55, 0x61)
P_BG         = RGBColor(0xF8, 0xF9, 0xFB)
WHITE        = RGBColor(0xFF, 0xFF, 0xFF)
BLACK        = RGBColor(0x10, 0x10, 0x10)

LOGO_GLOBAL = "logos/kdu_global.png"
LOGO_CREST  = "logos/kdu_crest.png"

# Slide size: 16:9 widescreen (13.333" x 7.5")
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

prs = Presentation()
prs.slide_width  = SLIDE_W
prs.slide_height = SLIDE_H

BLANK = prs.slide_layouts[6]   # fully blank layout, we draw everything


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def add_rect(slide, x, y, w, h, fill, line=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
    shp.shadow.inherit = False
    return shp


def add_text(slide, x, y, w, h, text, *,
             size=18, bold=False, italic=False,
             color=BLACK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP,
             font="Calibri"):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = font
    run.font.color.rgb = color
    return tb


def add_bullets(slide, x, y, w, h, items, *,
                size=18, color=BLACK, bullet_color=None):
    """items: list of strings, or list of (text, bool_bold) tuples."""
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = Inches(0.05)
    for i, item in enumerate(items):
        if isinstance(item, tuple):
            text, bold = item
        else:
            text, bold = item, False
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.level = 0
        p.space_after = Pt(6)
        run = p.add_run()
        run.text = "•  " + text
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.bold = bold
        run.font.name = "Calibri"
    return tb


def add_slide_chrome(slide, page_num, total_pages, title_text):
    """Top blue header bar with title + footer with project name and page."""
    # Header bar
    add_rect(slide, 0, 0, SLIDE_W, Inches(0.85), P_BLUE)
    add_text(slide, Inches(0.5), Inches(0.12), SLIDE_W - Inches(2.5),
             Inches(0.65), title_text,
             size=28, bold=True, color=WHITE,
             anchor=MSO_ANCHOR.MIDDLE)

    # Tiny crest in top-right of the header
    if os.path.exists(LOGO_CREST):
        slide.shapes.add_picture(
            LOGO_CREST,
            SLIDE_W - Inches(1.8), Inches(0.08),
            height=Inches(0.7),
        )

    # Footer thin rule
    add_rect(slide, 0, SLIDE_H - Inches(0.5),
             SLIDE_W, Inches(0.04), P_BLUE_LIGHT)

    # Footer text (left)
    add_text(slide, Inches(0.5), SLIDE_H - Inches(0.45),
             Inches(8.0), Inches(0.35),
             "EDA Chatbot & Customer Churn Prediction  •  Spring 2025",
             size=11, color=P_GRAY, italic=True,
             anchor=MSO_ANCHOR.MIDDLE)

    # Footer text (right)
    add_text(slide, SLIDE_W - Inches(2.5), SLIDE_H - Inches(0.45),
             Inches(2.0), Inches(0.35),
             f"{page_num} / {total_pages}",
             size=11, color=P_BLUE, bold=True,
             align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)


def add_pill(slide, x, y, w, h, text, fill=P_TEAL, color=WHITE, size=14):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    shp.line.fill.background()
    tf = shp.text_frame
    tf.margin_left = tf.margin_right = Inches(0.08)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = True
    run.font.color.rgb = color
    run.font.name = "Calibri"
    return shp


def add_arrow_down(slide, x, y, h=Inches(0.35)):
    shp = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, x, y, Inches(0.35), h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = P_GRAY
    shp.line.fill.background()


def add_arrow_right(slide, x, y, w=Inches(0.4)):
    shp = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x, y, w, Inches(0.35))
    shp.fill.solid()
    shp.fill.fore_color.rgb = P_GRAY
    shp.line.fill.background()


# ===========================================================================
# Slide builders
# ===========================================================================

TOTAL = 16  # we know how many we'll generate


def slide_title():
    s = prs.slides.add_slide(BLANK)
    # Full-bleed gradient backdrop (two stacked blue rectangles)
    add_rect(s, 0, 0, SLIDE_W, SLIDE_H, P_BLUE)
    add_rect(s, 0, Inches(5.6), SLIDE_W, Inches(1.9), P_BLUE_LIGHT)

    # Logos
    if os.path.exists(LOGO_GLOBAL):
        s.shapes.add_picture(LOGO_GLOBAL, Inches(0.6), Inches(0.45),
                             height=Inches(1.2))
    if os.path.exists(LOGO_CREST):
        s.shapes.add_picture(LOGO_CREST,
                             SLIDE_W - Inches(2.6), Inches(0.5),
                             height=Inches(1.1))

    # Title block
    add_text(s, Inches(0.5), Inches(2.2), SLIDE_W - Inches(1.0),
             Inches(1.1),
             "Conversational EDA Chatbot",
             size=54, bold=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, Inches(0.5), Inches(3.2), SLIDE_W - Inches(1.0),
             Inches(0.5),
             "— and —",
             size=22, italic=True, color=P_YELLOW,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, Inches(0.5), Inches(3.7), SLIDE_W - Inches(1.0),
             Inches(1.1),
             "E-Commerce Customer Churn Prediction",
             size=44, bold=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    add_text(s, Inches(0.5), Inches(4.85), SLIDE_W - Inches(1.0),
             Inches(0.4),
             "A Production-Grade Data Science Project",
             size=20, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    # Authors / supervisor strip
    add_text(s, Inches(0.5), Inches(5.85), SLIDE_W - Inches(1.0),
             Inches(0.4),
             "Tuyiramye Christian  (2517025)   •   Dushime Pacifique  (2517004)",
             size=20, bold=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, Inches(0.5), Inches(6.3), SLIDE_W - Inches(1.0),
             Inches(0.4),
             "Supervisor:  Prof. Dr. Jebran Khan",
             size=18, color=P_YELLOW,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, Inches(0.5), Inches(6.75), SLIDE_W - Inches(1.0),
             Inches(0.4),
             "Kyungdong University Global  •  Department of AI  •  Spring 2025",
             size=16, italic=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def slide_outline():
    s = prs.slides.add_slide(BLANK)
    add_slide_chrome(s, 2, TOTAL, "Outline")
    items = [
        "1. Motivation & Problem Statement",
        "2. Objectives",
        "3. System Architecture",
        "4. Phase A — SQL Agent",
        "5. Phase B — Visual Router & Pandas Agent",
        "6. Sandboxed Execution & Guardrails",
        "7. Churn Prediction — Dataset & Pipeline",
        "8. Modeling & Results",
        "9. Feature Importance",
        "10. Discussion, Limitations, Future Work",
        "11. Conclusion & Acknowledgments",
    ]
    add_bullets(s, Inches(1.2), Inches(1.4), Inches(11),
                Inches(5.4), items, size=24, color=P_BLUE)


def slide_motivation():
    s = prs.slides.add_slide(BLANK)
    add_slide_chrome(s, 3, TOTAL, "Motivation — Two Industry Pain Points")
    # Two side-by-side panels
    panel_y = Inches(1.3)
    panel_h = Inches(5.5)
    pw = Inches(5.8)

    # Left panel
    add_rect(s, Inches(0.5), panel_y, pw, panel_h, P_BG, line=P_BLUE)
    add_text(s, Inches(0.7), panel_y + Inches(0.1), pw - Inches(0.4),
             Inches(0.55),
             "1.  Data-access bottleneck",
             size=24, bold=True, color=P_BLUE)
    add_bullets(s, Inches(0.7), panel_y + Inches(0.85),
                pw - Inches(0.4), panel_h - Inches(1.0),
                [
                    "Stakeholders depend on analysts to write SQL for every new question.",
                    "Round-trip slows decisions by hours to days.",
                    "Cognitive cost of SQL gates which questions get asked at all.",
                    "Companies become biased toward questions that fit existing dashboards.",
                ], size=18, color=P_GRAY)

    # Right panel
    add_rect(s, Inches(7.0), panel_y, pw, panel_h, P_BG, line=P_ORANGE)
    add_text(s, Inches(7.2), panel_y + Inches(0.1), pw - Inches(0.4),
             Inches(0.55),
             "2.  Reactive retention",
             size=24, bold=True, color=P_ORANGE)
    add_bullets(s, Inches(7.2), panel_y + Inches(0.85),
                pw - Inches(0.4), panel_h - Inches(1.0),
                [
                    "Churn is discovered AFTER revenue is lost.",
                    "Acquiring a new customer costs 5–25× more than retention.",
                    "Most retention programs only kick in after a bad quarter.",
                    "They target the wrong cohort because they rely on intuition.",
                ], size=18, color=P_GRAY)


def slide_objectives():
    s = prs.slides.add_slide(BLANK)
    add_slide_chrome(s, 4, TOTAL, "Objectives")

    add_text(s, Inches(0.6), Inches(1.1), Inches(6.0), Inches(0.5),
             "Functional", size=22, bold=True, color=P_BLUE)
    add_bullets(s, Inches(0.6), Inches(1.7), Inches(6.0), Inches(5.0),
                [
                    "Translate plain English into syntactically valid MySQL.",
                    "Dynamic output: table / summary / interactive chart.",
                    "Multi-turn conversational memory across follow-ups.",
                    "Predict churn and rank customers by retention risk.",
                ], size=18, color=P_GRAY)

    add_text(s, Inches(6.9), Inches(1.1), Inches(6.0), Inches(0.5),
             "Non-functional", size=22, bold=True, color=P_TEAL)
    add_bullets(s, Inches(6.9), Inches(1.7), Inches(6.0), Inches(5.0),
                [
                    "Strict read-only safety — no INSERT/UPDATE/DELETE/DROP.",
                    "Reliability — no generated code can crash the UI.",
                    "Performance — cache DB pool and LLM client across reruns.",
                    "Reproducibility — fixed-seed dataset, leak-free CV.",
                    "Interpretability — surface drivers, not just scores.",
                ], size=18, color=P_GRAY)


def slide_architecture():
    s = prs.slides.add_slide(BLANK)
    add_slide_chrome(s, 5, TOTAL, "System Architecture — Dual-Agent Pipeline")

    # Center column of stacked boxes
    cx = Inches(5.2)
    cw = Inches(3.0)
    boxes = [
        ("Stakeholder",       "natural language",     P_BLUE_LIGHT),
        ("Streamlit UI",      "app.py",               P_BLUE_LIGHT),
        ("Phase A: SQL Agent","ZSR-D + read-only",    P_ORANGE),
        ("Visual Router",     "keyword classifier",   P_YELLOW),
    ]
    y = Inches(1.2)
    bh = Inches(0.85)
    gap = Inches(0.25)
    for title, sub, color in boxes:
        add_rect(s, cx, y, cw, bh, color)
        add_text(s, cx, y + Inches(0.05), cw, Inches(0.4), title,
                 size=16, bold=True, color=WHITE,
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        add_text(s, cx, y + Inches(0.42), cw, Inches(0.35), sub,
                 size=12, italic=True, color=WHITE,
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        add_arrow_down(s, cx + cw/2 - Inches(0.18), y + bh + Inches(-0.02))
        y += bh + gap

    # Branch: Text/Table  |  Pandas Agent -> Sandbox
    branch_y = y + Inches(0.05)
    left_x = cx - Inches(3.4)
    right_x = cx + Inches(3.4)

    add_rect(s, left_x, branch_y, Inches(3.0), Inches(0.85), P_TEAL)
    add_text(s, left_x, branch_y + Inches(0.18), Inches(3.0), Inches(0.5),
             "Text / Table answer", size=16, bold=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    add_rect(s, right_x, branch_y, Inches(3.0), Inches(0.85), P_ORANGE)
    add_text(s, right_x, branch_y + Inches(0.05), Inches(3.0), Inches(0.4),
             "Phase B: Pandas Agent", size=15, bold=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, right_x, branch_y + Inches(0.42), Inches(3.0), Inches(0.35),
             "Plotly / Matplotlib code", size=12, italic=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    # Arrow down from Pandas Agent to sandbox
    add_arrow_down(s, right_x + Inches(1.35), branch_y + Inches(0.85))

    add_rect(s, right_x, branch_y + Inches(1.25), Inches(3.0),
             Inches(0.85), P_BLUE)
    add_text(s, right_x, branch_y + Inches(1.30), Inches(3.0), Inches(0.4),
             "Sandboxed exec()", size=16, bold=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, right_x, branch_y + Inches(1.65), Inches(3.0), Inches(0.4),
             "Streamlit chart", size=12, italic=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    # External services side notes
    add_text(s, Inches(0.5), Inches(1.4), Inches(3.5), Inches(0.4),
             "OpenAI GPT-4o  (T=0)", size=14, italic=True, color=P_BLUE,
             align=PP_ALIGN.CENTER)
    add_text(s, Inches(9.4), Inches(1.4), Inches(3.5), Inches(0.4),
             "MySQL  (pymysql)", size=14, italic=True, color=P_BLUE,
             align=PP_ALIGN.CENTER)


def slide_phaseA():
    s = prs.slides.add_slide(BLANK)
    add_slide_chrome(s, 6, TOTAL, "Phase A — The SQL Agent")

    # Left: bullets
    add_bullets(s, Inches(0.6), Inches(1.2), Inches(7.0), Inches(5.5),
                [
                    ("Built with create_sql_agent(", True),
                    "Agent type: ZERO_SHOT_REACT_DESCRIPTION.",
                    "Transparent Thought → Action → Observation loop.",
                    "Read-only system prefix forbids INSERT/UPDATE/DELETE/DROP/...",
                    "handle_parsing_errors=True (recoverable parse failures).",
                    "max_iterations=12 (prevents runaway billing).",
                    "sample_rows_in_table_info=3 (column disambiguation).",
                    "@st.cache_resource keeps the SQLAlchemy pool warm across reruns.",
                ], size=17, color=P_GRAY)

    # Right: ReAct loop mini diagram
    rx = Inches(8.0)
    ry = Inches(1.2)
    cells = [
        ("Thought:  list tables",            P_BLUE),
        ("Action:   list_tables",            P_ORANGE),
        ("Obs:      customers, orders, ...", P_TEAL),
        ("Thought:  inspect schema",         P_BLUE),
        ("Action:   schema(customers)",      P_ORANGE),
        ("Obs:      columns + sample rows",  P_TEAL),
        ("Thought:  draft SELECT",           P_BLUE),
        ("Action:   query(SELECT ...)",      P_ORANGE),
        ("Obs:      result rows",            P_TEAL),
        ("Final:    summary + table",        P_BLUE_LIGHT),
    ]
    cw = Inches(4.9)
    ch = Inches(0.36)
    gap = Inches(0.08)
    for text, color in cells:
        add_rect(s, rx, ry, cw, ch, color)
        add_text(s, rx + Inches(0.1), ry, cw - Inches(0.1), ch, text,
                 size=12, bold=True, color=WHITE,
                 align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE,
                 font="Consolas")
        ry += ch + gap


def slide_phaseB():
    s = prs.slides.add_slide(BLANK)
    add_slide_chrome(s, 7, TOTAL, "Phase B — Visual Router & Pandas Agent")

    add_text(s, Inches(0.6), Inches(1.1), Inches(12.0), Inches(0.5),
             "Two-step visualization pipeline:",
             size=20, bold=True, color=P_BLUE)

    # Step pipeline
    steps = [
        ("Keyword router",
         "chart, plot, graph,\nbar, line, pie, ...",
         P_YELLOW),
        ("Parse SQL output",
         "Markdown table\n→ DataFrame df",
         P_TEAL),
        ("Pandas agent",
         "writes Plotly /\nMatplotlib code",
         P_ORANGE),
        ("Sandbox exec",
         "render in\nStreamlit",
         P_BLUE),
    ]
    sx = Inches(0.6)
    sy = Inches(1.7)
    sw = Inches(2.9)
    sh = Inches(1.6)
    gap = Inches(0.25)
    for i, (title, sub, color) in enumerate(steps):
        add_rect(s, sx, sy, sw, sh, color)
        add_text(s, sx, sy + Inches(0.1), sw, Inches(0.5), title,
                 size=18, bold=True, color=WHITE,
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        add_text(s, sx, sy + Inches(0.65), sw, Inches(0.85), sub,
                 size=13, italic=True, color=WHITE,
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        if i < len(steps) - 1:
            add_arrow_right(s, sx + sw + Inches(-0.05),
                            sy + sh/2 - Inches(0.18))
        sx += sw + gap

    # Note
    add_text(s, Inches(0.6), Inches(4.0), Inches(12.0), Inches(0.5),
             "Why a deterministic keyword router?",
             size=20, bold=True, color=P_BLUE)
    add_bullets(s, Inches(0.6), Inches(4.5), Inches(12.0), Inches(2.5),
                [
                    "Free — no additional API call per turn.",
                    "Auditable — the same prompt always routes the same way.",
                    "Sufficient — the visual vocabulary in real questions is narrow.",
                    "Trade-off: lower recall on paraphrases; we accept this as an explicit limitation.",
                ], size=17, color=P_GRAY)


def slide_sandbox():
    s = prs.slides.add_slide(BLANK)
    add_slide_chrome(s, 8, TOTAL, "Sandboxed Execution & Enterprise Guardrails")

    # Left: sandbox namespace
    add_text(s, Inches(0.6), Inches(1.1), Inches(6.0), Inches(0.5),
             "exec() sandbox namespace", size=22, bold=True, color=P_BLUE)
    add_rect(s, Inches(0.6), Inches(1.7), Inches(6.0), Inches(2.6),
             P_BG, line=P_BLUE)
    # Allowed pills
    names_ok = ["st", "pd", "px", "go", "plt", "df"]
    px_ = Inches(0.85)
    py_ = Inches(1.95)
    for n in names_ok:
        add_pill(s, px_, py_, Inches(0.9), Inches(0.45), n, fill=P_TEAL)
        px_ += Inches(0.95)
    add_text(s, Inches(0.6), Inches(2.55), Inches(6.0), Inches(0.4),
             "allowed", size=14, italic=True, color=P_TEAL,
             align=PP_ALIGN.CENTER)
    # Separator
    add_rect(s, Inches(0.8), Inches(3.05), Inches(5.6), Inches(0.02), P_GRAY)
    # Blocked pills
    names_bad = ["os", "sys", "open", "eval", "subprocess", "requests"]
    px_ = Inches(0.85)
    py_ = Inches(3.25)
    for n in names_bad:
        add_pill(s, px_, py_, Inches(0.85), Inches(0.45), n, fill=P_ORANGE)
        px_ += Inches(0.9)
    add_text(s, Inches(0.6), Inches(3.85), Inches(6.0), Inches(0.4),
             "blocked / not in scope", size=14, italic=True, color=P_ORANGE,
             align=PP_ALIGN.CENTER)

    # Right: three-layer defense
    add_text(s, Inches(6.9), Inches(1.1), Inches(6.0), Inches(0.5),
             "Three-layer defense", size=22, bold=True, color=P_BLUE)
    items = [
        ("1. Prompt-level", "System prompt forbids imports, os, sys, subprocess, open, eval, network APIs."),
        ("2. Namespace-level", "exec() only sees six names; everything else simply doesn’t exist."),
        ("3. Exception-level", "Broad try/except converts crashes into a friendly Streamlit error card."),
    ]
    y = Inches(1.75)
    for title, desc in items:
        add_rect(s, Inches(6.9), y, Inches(6.0), Inches(1.05),
                 P_BG, line=P_BLUE_LIGHT)
        add_text(s, Inches(7.05), y + Inches(0.07), Inches(5.8),
                 Inches(0.4), title, size=16, bold=True, color=P_BLUE)
        add_text(s, Inches(7.05), y + Inches(0.42), Inches(5.8),
                 Inches(0.6), desc, size=14, color=P_GRAY)
        y += Inches(1.18)

    # Memory + read-only note
    add_text(s, Inches(0.6), Inches(4.6), Inches(12.0), Inches(0.5),
             "Read-only SQL + Conversational memory",
             size=20, bold=True, color=P_BLUE)
    add_bullets(s, Inches(0.6), Inches(5.1), Inches(12.0), Inches(1.8),
                [
                    "System prefix enumerates and forbids every mutation verb.",
                    "Defense-in-depth: deploy with a read-only MySQL role too.",
                    "st.session_state.messages persists turns across reruns → true follow-ups.",
                ], size=17, color=P_GRAY)


def slide_chatbot_demo():
    s = prs.slides.add_slide(BLANK)
    add_slide_chrome(s, 9, TOTAL, "Chatbot — Sample Interaction")

    # Mock chat: user -> assistant turns
    def add_bubble(slide, x, y, w, who, text, who_color, bubble_fill):
        add_rect(slide, x, y, w, Inches(1.0), bubble_fill, line=who_color)
        add_text(slide, x + Inches(0.15), y + Inches(0.05), w - Inches(0.3),
                 Inches(0.35), who, size=13, bold=True, color=who_color)
        add_text(slide, x + Inches(0.15), y + Inches(0.4), w - Inches(0.3),
                 Inches(0.55), text, size=15, color=P_GRAY)

    bw = Inches(11.0)
    bx = Inches(1.2)
    y = Inches(1.2)
    gap = Inches(0.25)

    add_bubble(s, bx, y, bw, "USER",
               "Show me the top 10 customers by revenue for 2024.",
               P_BLUE, P_BG)
    y += Inches(1.0) + gap
    add_bubble(s, bx, y, bw, "ASSISTANT",
               "Returned a 10-row table sorted by total revenue (descending). Top customer: $48,212.",
               P_TEAL, P_BG)
    y += Inches(1.0) + gap
    add_bubble(s, bx, y, bw, "USER",
               "Now break that out by region and plot it as a bar chart.",
               P_BLUE, P_BG)
    y += Inches(1.0) + gap
    add_bubble(s, bx, y, bw, "ASSISTANT",
               "Generated Plotly bar chart — 4 regions x 10 customers, rendered in-line.",
               P_TEAL, P_BG)
    y += Inches(1.0) + gap
    add_bubble(s, bx, y, bw, "USER",
               "Change it to a line chart by month.",
               P_BLUE, P_BG)


def slide_dataset():
    s = prs.slides.add_slide(BLANK)
    add_slide_chrome(s, 10, TOTAL, "Churn Prediction — Dataset")

    add_text(s, Inches(0.6), Inches(1.1), Inches(7.5), Inches(0.5),
             "Synthetic 5,000-customer e-commerce dataset",
             size=22, bold=True, color=P_BLUE)
    add_text(s, Inches(0.6), Inches(1.6), Inches(7.5), Inches(0.5),
             "seed=42  •  fully reproducible  •  ~27% positive rate",
             size=16, italic=True, color=P_GRAY)

    rows = [
        ("Demographic", "age, gender, region"),
        ("Account",     "membership tier, payment, tenure_months"),
        ("Behavior",    "avg_order_value, orders_per_month"),
        ("Behavior",    "return_rate, support_tickets"),
        ("Behavior",    "days_since_last_order, discount_usage"),
        ("Target",      "churned (0/1)"),
    ]
    rx = Inches(0.6)
    ry = Inches(2.4)
    for label, val in rows:
        add_rect(s, rx, ry, Inches(2.4), Inches(0.45), P_BLUE_LIGHT)
        add_text(s, rx, ry, Inches(2.4), Inches(0.45), label,
                 size=14, bold=True, color=WHITE,
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        add_rect(s, rx + Inches(2.4), ry, Inches(5.0),
                 Inches(0.45), P_BG, line=P_BLUE_LIGHT)
        add_text(s, rx + Inches(2.5), ry, Inches(4.8), Inches(0.45), val,
                 size=14, color=P_GRAY, anchor=MSO_ANCHOR.MIDDLE,
                 font="Consolas")
        ry += Inches(0.5)

    # Right: churn formula
    add_text(s, Inches(8.4), Inches(1.1), Inches(4.5), Inches(0.5),
             "Churn label", size=22, bold=True, color=P_BLUE)
    add_rect(s, Inches(8.4), Inches(1.6), Inches(4.5), Inches(4.7),
             P_BG, line=P_ORANGE)
    formula = (
        "s = 0.020 · recency\n"
        "  + 1.500 · return_rate\n"
        "  + 0.150 · tickets\n"
        "  − 0.030 · tenure\n"
        "  − 0.400 · 1[Platinum]\n"
        "  − 0.200 · 1[Gold]\n"
        "  − 0.060 · orders/mo\n"
        "  + N(0, 0.5)\n\n"
        "y = 1{ s > 73rd percentile }"
    )
    add_text(s, Inches(8.55), Inches(1.75), Inches(4.2), Inches(4.4),
             formula, size=14, color=P_BLUE, font="Consolas")


def slide_pipeline():
    s = prs.slides.add_slide(BLANK)
    add_slide_chrome(s, 11, TOTAL, "Modeling Pipeline (leakage-free)")

    steps = [
        ("Synthetic\nDataset",       "5,000 rows"),
        ("Preprocess",               "Scale + OHE\n(in Pipeline)"),
        ("Train / Test",             "80 / 20\nstratified"),
        ("5-fold CV",                "LR / RF / GBM\nROC-AUC"),
        ("Grid Search",              "tune the\nwinner"),
        ("Evaluate",                 "ROC / PR\nCM / FI"),
    ]
    sx = Inches(0.4)
    sy = Inches(1.6)
    sw = Inches(2.0)
    sh = Inches(1.8)
    gap = Inches(0.12)
    colors = [P_BLUE, P_BLUE_LIGHT, P_TEAL, P_ORANGE, P_YELLOW, P_BLUE]
    for i, (title, sub) in enumerate(steps):
        add_rect(s, sx, sy, sw, sh, colors[i])
        add_text(s, sx, sy + Inches(0.15), sw, Inches(0.7), title,
                 size=16, bold=True, color=WHITE,
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        add_text(s, sx, sy + Inches(0.95), sw, Inches(0.7), sub,
                 size=13, italic=True, color=WHITE,
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        if i < len(steps) - 1:
            add_arrow_right(s, sx + sw - Inches(0.02),
                            sy + sh/2 - Inches(0.18))
        sx += sw + gap

    # Key insight box
    add_rect(s, Inches(0.6), Inches(4.0), Inches(12.0),
             Inches(2.6), P_BG, line=P_BLUE)
    add_text(s, Inches(0.8), Inches(4.1), Inches(11.6),
             Inches(0.5), "Why this is leakage-free",
             size=20, bold=True, color=P_BLUE)
    add_bullets(s, Inches(0.8), Inches(4.65), Inches(11.6), Inches(2.0),
                [
                    "ColumnTransformer (scaler + OHE) lives INSIDE the sklearn Pipeline.",
                    "scikit-learn re-fits the preprocessor on every CV fold separately.",
                    "Scaling parameters never leak from the validation fold into training.",
                    "If we fit the preprocessor once on all training data → optimistic CV scores.",
                ], size=17, color=P_GRAY)


def slide_results():
    s = prs.slides.add_slide(BLANK)
    add_slide_chrome(s, 12, TOTAL, "Results — 5-Fold Cross-Validation")

    # Bar chart drawn manually with rectangles
    chart_x = Inches(0.8)
    chart_y = Inches(1.4)
    chart_w = Inches(6.8)
    chart_h = Inches(5.4)

    add_rect(s, chart_x, chart_y, chart_w, chart_h, P_BG, line=P_GRAY)
    add_text(s, chart_x, chart_y + Inches(0.05), chart_w, Inches(0.5),
             "Mean CV ROC-AUC", size=18, bold=True, color=P_BLUE,
             align=PP_ALIGN.CENTER)

    # Y axis labels (0.5 baseline -> 1.0 top)
    bar_area_top = chart_y + Inches(0.8)
    bar_area_bottom = chart_y + chart_h - Inches(0.6)
    bar_area_h = bar_area_bottom - bar_area_top  # = ~3.5 inches

    def y_for(v):  # v in [0.5, 1.0]
        return bar_area_bottom - Emu(int((v - 0.5) / 0.5 * bar_area_h))

    # Grid lines + labels
    for v in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        gy = y_for(v)
        add_rect(s, chart_x + Inches(0.7), gy, chart_w - Inches(0.8),
                 Emu(9525), RGBColor(0xE0, 0xE5, 0xEA))
        add_text(s, chart_x + Inches(0.1), gy - Inches(0.13),
                 Inches(0.55), Inches(0.3), f"{v:.1f}",
                 size=11, color=P_GRAY, align=PP_ALIGN.RIGHT)

    # Bars
    bars = [("LR", 0.80, P_BLUE_LIGHT),
            ("RF", 0.85, P_BLUE),
            ("GBM", 0.87, P_TEAL)]
    bw = Inches(1.0)
    gap_b = Inches(0.6)
    start_x = chart_x + Inches(1.5)
    for label, val, color in bars:
        top_y = y_for(val)
        h = bar_area_bottom - top_y
        add_rect(s, start_x, top_y, bw, h, color)
        add_text(s, start_x, top_y - Inches(0.4), bw, Inches(0.35),
                 f"{val:.2f}", size=14, bold=True, color=P_BLUE,
                 align=PP_ALIGN.CENTER)
        add_text(s, start_x, bar_area_bottom + Inches(0.05),
                 bw, Inches(0.4), label,
                 size=14, bold=True, color=P_GRAY,
                 align=PP_ALIGN.CENTER)
        start_x += bw + gap_b

    # Right: results table
    add_text(s, Inches(8.0), Inches(1.4), Inches(5.0), Inches(0.5),
             "Cross-validation summary", size=20, bold=True, color=P_BLUE)
    hdr_y = Inches(2.0)
    cols = [("Model", Inches(2.4)), ("ROC-AUC", Inches(1.3)),
            ("Std", Inches(1.0))]
    cx = Inches(8.0)
    for name, w in cols:
        add_rect(s, cx, hdr_y, w, Inches(0.5), P_BLUE)
        add_text(s, cx, hdr_y, w, Inches(0.5), name,
                 size=14, bold=True, color=WHITE,
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        cx += w
    rows = [
        ("Gradient Boosting", "0.87", "0.010", True),
        ("Random Forest",     "0.85", "0.011", False),
        ("Logistic Reg.",     "0.80", "0.012", False),
    ]
    ry = hdr_y + Inches(0.5)
    for model, auc, std, win in rows:
        cx = Inches(8.0)
        fill = P_TEAL if win else P_BG
        text_color = WHITE if win else P_GRAY
        for w, val in zip([Inches(2.4), Inches(1.3), Inches(1.0)],
                          [model, auc, std]):
            add_rect(s, cx, ry, w, Inches(0.5), fill, line=P_BLUE_LIGHT)
            add_text(s, cx, ry, w, Inches(0.5), val,
                     size=13, bold=win, color=text_color,
                     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
            cx += w
        ry += Inches(0.5)

    add_text(s, Inches(8.0), Inches(4.4), Inches(5.0), Inches(2.2),
             "Tuned Gradient Boosting wins. Ensembles beat the linear baseline by a clear margin on the held-out test set as well.",
             size=15, italic=True, color=P_GRAY)


def slide_feature_importance():
    s = prs.slides.add_slide(BLANK)
    add_slide_chrome(s, 13, TOTAL, "Top Churn Drivers — Permutation Importance")

    features = [
        ("recency",         0.155),
        ("return_rate",     0.110),
        ("tier=Platinum",   0.065),
        ("tier=Gold",       0.055),
        ("support_tickets", 0.040),
        ("tenure",          0.025),
        ("orders / month",  0.020),
        ("payment",         0.012),
        ("region",          0.010),
        ("gender",          0.008),
        ("age",             0.007),
        ("discount_usage",  0.005),
    ]
    chart_x = Inches(0.8)
    chart_y = Inches(1.2)
    label_w = Inches(2.4)
    bar_max_w = Inches(7.5)
    row_h = Inches(0.38)
    max_val = max(v for _, v in features)
    for name, v in features:
        add_text(s, chart_x, chart_y, label_w, row_h, name,
                 size=13, color=P_GRAY, anchor=MSO_ANCHOR.MIDDLE,
                 align=PP_ALIGN.RIGHT, font="Consolas")
        bw = Emu(int(v / max_val * bar_max_w))
        add_rect(s, chart_x + label_w + Inches(0.1), chart_y + Inches(0.07),
                 bw, row_h - Inches(0.14), P_BLUE)
        add_text(s,
                 chart_x + label_w + Inches(0.15) + bw,
                 chart_y, Inches(1.2), row_h,
                 f"{v:.3f}", size=12, bold=True, color=P_BLUE,
                 anchor=MSO_ANCHOR.MIDDLE)
        chart_y += row_h

    add_text(s, Inches(0.8), Inches(6.05), Inches(11.5), Inches(0.5),
             "Recency and return rate dominate; loyalty tier (Gold, Platinum) protects.",
             size=16, italic=True, color=P_BLUE, bold=True)


def slide_discussion():
    s = prs.slides.add_slide(BLANK)
    add_slide_chrome(s, 14, TOTAL, "Discussion — Why the Two Halves Reinforce")

    add_bullets(s, Inches(0.6), Inches(1.2), Inches(12.0), Inches(5.5),
                [
                    "Part I lets the retention manager ASK: 'top 200 at-risk customers in Q4, by region.'",
                    "Part II PROVIDES the predictive signal behind that ranking.",
                    "Same data domain → a virtuous loop between exploration and prediction.",
                    "Read-only guardrails + sandboxed exec satisfy enterprise security teams.",
                    "Two architectural decisions paid off the most:",
                    "  → splitting Phase A (SQL) from Phase B (viz) instead of fusing them.",
                    "  → parsing SQL output to a real DataFrame before invoking the visualization agent.",
                    "Modular artifacts (one app.py, one .ipynb) maximize portability and reviewability.",
                ], size=18, color=P_GRAY)


def slide_future():
    s = prs.slides.add_slide(BLANK)
    add_slide_chrome(s, 15, TOTAL, "Limitations & Future Work")

    add_text(s, Inches(0.6), Inches(1.1), Inches(6.0), Inches(0.5),
             "Limitations", size=22, bold=True, color=P_ORANGE)
    add_bullets(s, Inches(0.6), Inches(1.65), Inches(6.0), Inches(5.0),
                [
                    "exec() is not a true sandbox — trust the LLM provider.",
                    "Synthetic data, not yet validated on a live warehouse.",
                    "Keyword router misses paraphrased visual intent.",
                    "Default 0.5 probability threshold is not cost-tuned.",
                ], size=17, color=P_GRAY)

    add_text(s, Inches(6.9), Inches(1.1), Inches(6.0), Inches(0.5),
             "Future Work", size=22, bold=True, color=P_TEAL)
    add_bullets(s, Inches(6.9), Inches(1.65), Inches(6.0), Inches(5.0),
                [
                    "Replace keyword router with an LLM-as-judge intent classifier.",
                    "Retrain on the live MySQL warehouse via the same connection.",
                    "Add per-customer SHAP attributions for individualized offers.",
                    "Add a 'narrate this chart' step closing the loop with the LLM.",
                    "Container-isolated execution for truly untrusted environments.",
                    "Wire up LangSmith / Helicone observability with token + latency tracking.",
                ], size=17, color=P_GRAY)


def slide_thankyou():
    s = prs.slides.add_slide(BLANK)
    # Full-bleed background
    add_rect(s, 0, 0, SLIDE_W, SLIDE_H, P_BLUE)
    add_rect(s, 0, Inches(5.4), SLIDE_W, Inches(2.1), P_BLUE_LIGHT)

    # Logos
    if os.path.exists(LOGO_GLOBAL):
        s.shapes.add_picture(LOGO_GLOBAL, Inches(0.6), Inches(0.5),
                             height=Inches(1.0))
    if os.path.exists(LOGO_CREST):
        s.shapes.add_picture(LOGO_CREST,
                             SLIDE_W - Inches(2.4), Inches(0.5),
                             height=Inches(1.0))

    add_text(s, Inches(0.5), Inches(2.2), SLIDE_W - Inches(1.0),
             Inches(1.4),
             "Thank You",
             size=80, bold=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    add_text(s, Inches(0.5), Inches(3.6), SLIDE_W - Inches(1.0),
             Inches(0.6),
             "Questions • Discussion • Feedback",
             size=24, italic=True, color=P_YELLOW,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    # Authors panel
    add_text(s, Inches(0.5), Inches(5.6), SLIDE_W - Inches(1.0),
             Inches(0.4),
             "Tuyiramye Christian  (2517025)   •   Dushime Pacifique  (2517004)",
             size=20, bold=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, Inches(0.5), Inches(6.05), SLIDE_W - Inches(1.0),
             Inches(0.4),
             "Supervisor:  Prof. Dr. Jebran Khan",
             size=18, color=P_YELLOW,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    add_text(s, Inches(0.5), Inches(6.5), SLIDE_W - Inches(1.0),
             Inches(0.4),
             "Kyungdong University Global  •  Department of AI  •  Spring 2025",
             size=16, italic=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


# ===========================================================================
# Build all slides
# ===========================================================================

slide_title()                  # 1
slide_outline()                # 2
slide_motivation()             # 3
slide_objectives()             # 4
slide_architecture()           # 5
slide_phaseA()                 # 6
slide_phaseB()                 # 7
slide_sandbox()                # 8
slide_chatbot_demo()           # 9
slide_dataset()                # 10
slide_pipeline()               # 11
slide_results()                # 12
slide_feature_importance()     # 13
slide_discussion()             # 14
slide_future()                 # 15
slide_thankyou()               # 16

prs.save("presentation.pptx")
print("Wrote presentation.pptx with", len(prs.slides), "slides")
