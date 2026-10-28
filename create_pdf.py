import re
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    KeepTogether
)

from reportlab.lib import colors
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont


from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont


# Configure fonts for macOS
FONT_PATH = Path(
    "/System/Library/Fonts/Supplemental/Arial.ttf"
)

if not FONT_PATH.exists():
    raise FileNotFoundError(
        f"Font file not found: {FONT_PATH}"
    )

# Register Swedish font
pdfmetrics.registerFont(
    TTFont("SwedishFont", str(FONT_PATH))
)

# Register Traditional Chinese font
pdfmetrics.registerFont(
    UnicodeCIDFont("MSung-Light")
)


def format_text(text):
    """
    Escape XML characters and apply a Chinese font
    to Chinese text.

    Args:
        text (str): Input text.

    Returns:
        str: ReportLab-compatible formatted text.
    """

    text = escape(str(text))

    # Use a Chinese font for CJK characters
    pattern = r"([\u3400-\u9fff]+)"

    text = re.sub(
        pattern,
        r'<font name="MSung-Light">\1</font>',
        text
    )

    return text.replace("\n", "<br/>")


def create_styles():
    """
    Create PDF paragraph styles.

    Returns:
        dict: PDF styles.
    """

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="QuizTitle",
            fontName="SwedishFont",
            fontSize=20,
            leading=28,
            alignment=TA_CENTER,
            spaceAfter=20
        )
    )

    styles.add(
        ParagraphStyle(
            name="ArticleTitle",
            fontName="SwedishFont",
            fontSize=15,
            leading=23,
            textColor=colors.HexColor("#17365D"),
            spaceAfter=12
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            fontName="SwedishFont",
            fontSize=12,
            leading=18,
            textColor=colors.HexColor("#17365D"),
            spaceBefore=14,
            spaceAfter=8
        )
    )

    styles.add(
        ParagraphStyle(
            name="QuizBody",
            fontName="SwedishFont",
            fontSize=10,
            leading=17,
            spaceAfter=9,
            wordWrap="CJK"
        )
    )

    styles.add(
        ParagraphStyle(
            name="QuizSmall",
            fontName="SwedishFont",
            fontSize=8,
            leading=13,
            textColor=colors.grey,
            spaceAfter=8,
            wordWrap="CJK"
        )
    )

    return styles


def add_paragraph(story, text, style):
    """
    Add formatted text to the PDF story.
    """

    story.append(
        Paragraph(
            format_text(text),
            style
        )
    )


def add_article(story, article, styles, index):
    """
    Add an article and its exercises to the PDF.
    """

    # Article title
    add_paragraph(
        story,
        f"{index}. {article['title']}",
        styles["ArticleTitle"]
    )

    # Publication date
    add_paragraph(
        story,
        f"Date: {article['date']}",
        styles["QuizSmall"]
    )

    # Article URL
    add_paragraph(
        story,
        f"Source: {article['url']}",
        styles["QuizSmall"]
    )

    # Original article
    add_paragraph(
        story,
        "Reading Text",
        styles["SectionTitle"]
    )

    for paragraph in article["text"].split("\n\n"):
        if paragraph.strip():
            add_paragraph(
                story,
                paragraph,
                styles["QuizBody"]
            )

    # Reading comprehension questions
    add_paragraph(
        story,
        "Reading Comprehension",
        styles["SectionTitle"]
    )

    for number, item in enumerate(
        article["questions"],
        start=1
    ):
        add_paragraph(
            story,
            f"{number}. {item['question']}",
            styles["QuizBody"]
        )

        story.append(Spacer(1, 0.4 * cm))

    # Vocabulary
    add_paragraph(
        story,
        "Important Vocabulary",
        styles["SectionTitle"]
    )

    for item in article["vocabulary"]:

        text = (
            f"{item['word']} - {item['meaning']}\n"
            f"Example: {item['example']}"
        )

        add_paragraph(
            story,
            text,
            styles["QuizBody"]
        )

    # Grammar
    add_paragraph(
        story,
        "Grammar and Sentence Patterns",
        styles["SectionTitle"]
    )

    for item in article["grammar"]:

        text = (
            f"{item['pattern']}\n"
            f"{item['explanation']}\n"
            f"Example: {item['example']}"
        )

        add_paragraph(
            story,
            text,
            styles["QuizBody"]
        )


def add_answer_key(story, articles, styles):
    """
    Add answers for all articles at the end of the PDF.
    """

    story.append(PageBreak())

    add_paragraph(
        story,
        "Answer Key",
        styles["QuizTitle"]
    )

    for index, article in enumerate(articles, start=1):

        add_paragraph(
            story,
            f"{index}. {article['title']}",
            styles["ArticleTitle"]
        )

        for number, item in enumerate(
            article["questions"],
            start=1
        ):

            add_paragraph(
                story,
                f"{number}. {item['answer']}",
                styles["QuizBody"]
            )


def add_page_number(canvas, doc):
    """
    Add page numbers to each PDF page.
    """

    canvas.saveState()

    canvas.setFont("SwedishFont", 8)

    canvas.drawRightString(
        A4[0] - 2 * cm,
        1.5 * cm,
        f"Page {doc.page}"
    )

    canvas.restoreState()


def create_quiz_pdf(articles, output_dir="quiz"):
    """
    Generate a PDF containing all article exercises.

    Args:
        articles (list[dict]): Generated quiz data.
        output_dir (str): PDF output directory.

    Returns:
        Path: Generated PDF path.
    """

    if not articles:
        raise ValueError("No quiz data available.")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate filename using today's date
    today = datetime.now().strftime("%Y-%m-%d")

    filename = f"Quiz_{today}.pdf"

    pdf_path = output_path / filename

    # Configure PDF
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    styles = create_styles()

    story = []

    # Cover page
    add_paragraph(
        story,
        "SFI Kurs C - Reading Practice",
        styles["QuizTitle"]
    )

    add_paragraph(
        story,
        f"Generated: {today}",
        styles["QuizBody"]
    )

    add_paragraph(
        story,
        f"Total articles: {len(articles)}",
        styles["QuizBody"]
    )

    story.append(PageBreak())

    # Add all articles
    for index, article in enumerate(articles, start=1):

        print(
            f"Adding article {index}/{len(articles)} to PDF"
        )

        add_article(
            story,
            article,
            styles,
            index
        )

        if index < len(articles):
            story.append(PageBreak())

    # Add answer key
    add_answer_key(
        story,
        articles,
        styles
    )

    # Generate PDF
    doc.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number
    )

    print(f"\nPDF created: {pdf_path}")

    return pdf_path