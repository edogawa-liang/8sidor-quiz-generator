"""Create a one-page-per-article SFI Kurs C quiz PDF."""

from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


FONT_PATHS = [
    Path('/System/Library/Fonts/Supplemental/Arial.ttf'),
    Path('/Library/Fonts/Arial.ttf'),
    Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
]


def register_font():
    """Register a TrueType font supporting Swedish characters."""
    font_path = next((path for path in FONT_PATHS if path.is_file()), None)
    if font_path is None:
        raise FileNotFoundError('No supported Swedish font was found.')
    pdfmetrics.registerFont(TTFont('SwedishFont', str(font_path)))


def create_styles():
    """Create styles for article headings, questions, and vocabulary."""
    return {
        'title': ParagraphStyle(
            'ArticleTitle', fontName='SwedishFont', fontSize=15,
            leading=20, textColor=colors.HexColor('#17365D'),
        ),
        'date': ParagraphStyle(
            'ArticleDate', fontName='SwedishFont', fontSize=8,
            leading=12, textColor=colors.grey,
        ),
        'question': ParagraphStyle(
            'Question', fontName='SwedishFont', fontSize=10,
            leading=15,
        ),
        'option': ParagraphStyle(
            'Option', fontName='SwedishFont', fontSize=9.5,
            leading=14, leftIndent=12,
        ),
        'section': ParagraphStyle(
            'Section', fontName='SwedishFont', fontSize=11,
            leading=16, textColor=colors.HexColor('#17365D'),
        ),
        'detail': ParagraphStyle(
            'Detail', fontName='SwedishFont', fontSize=9,
            leading=13,
        ),
        'url': ParagraphStyle(
            'ArticleURL',
            fontName='SwedishFont',
            fontSize=8,
            leading=12,
            textColor=colors.HexColor('#2563EB'),
            wordWrap='CJK',
        ),
    }


def add_block(blocks, text, style, gap=5):
    """Append a safe paragraph and its following spacing."""
    blocks.append((Paragraph(escape(str(text)), style), gap))


def build_blocks(article, styles, index):
    """Build the printable blocks, excluding transcript and answers."""
    blocks = []

    # Article title
    add_block(blocks, article['title'], styles['title'], 5)

    # Publication date
    add_block(
        blocks,
        f"Date: {article['date']}",
        styles['date'],
        4,
    )

    # Clickable article URL
    url = str(article.get('url', '')).strip()

    if url.startswith(('https://', 'http://')):
        safe_url = escape(url, {'"': '&quot;'})

        blocks.append(
            (
                Paragraph(
                    f'<link href="{safe_url}" color="#2563EB">'
                    f'{escape(url)}'
                    f'</link>',
                    styles['url'],
                ),
                12,
            )
        )
    else:
        blocks.append((None, 10))

    for number, item in enumerate(article['questions'], start=1):
        add_block(blocks, f"{number}. {item['question']}", styles['question'], 5)
        for letter in ('A', 'B', 'C'):
            add_block(
                blocks, f"{letter}. {item['options'][letter]}",
                styles['option'], 3,
            )
        blocks.append((None, 9))

    if article.get('vocabulary'):
        add_block(blocks, 'Vocabulary', styles['section'], 7)
        for item in article['vocabulary']:
            # The generator should use meaning_en, not meaning_zh.
            word = item['word_sv']
            meaning = item['meaning_en']
            forms = item.get('word_forms', '')
            text = f'{word} — {meaning}'
            if forms:
                text += f'  |  {forms}'
            add_block(blocks, text, styles['detail'], 5)

    if article.get('expressions'):
        blocks.append((None, 7))
        add_block(blocks, 'Useful Expressions', styles['section'], 7)
        for item in article['expressions']:
            add_block(
                blocks,
                f"{item['expression_sv']} — {item['meaning_en']}",
                styles['detail'], 5,
            )

    return blocks


def draw_article_page(pdf, article, styles, index):
    """Render exactly one A4 page, scaling content down if needed."""
    page_width, page_height = A4
    left = 1.8 * cm
    right = 1.8 * cm
    top = 1.7 * cm
    bottom = 2.3 * cm
    content_width = page_width - left - right
    available_height = page_height - top - bottom

    blocks = build_blocks(article, styles, index)
    measured = []
    total_height = 0
    for paragraph, gap in blocks:
        height = paragraph.wrap(content_width, page_height)[1] if paragraph else 0
        measured.append((paragraph, height, gap))
        total_height += height + gap

    scale = min(1.0, available_height / max(total_height, 1))
    pdf.saveState()
    pdf.translate(left, page_height - top)
    pdf.scale(scale, scale)
    y = 0
    for paragraph, height, gap in measured:
        if paragraph is not None:
            paragraph.drawOn(pdf, 0, y - height)
        y -= height + gap
    pdf.restoreState()

    answers = '   '.join(
        f"{number}.{question['correct_answer']}"
        for number, question in enumerate(article['questions'], start=1)
    )
    pdf.setFont('SwedishFont', 7)
    pdf.setFillColor(colors.grey)
    pdf.drawRightString(page_width - right, 1.1 * cm, f'Answers: {answers}')
    pdf.setFillColor(colors.black)
    pdf.showPage()


def create_quiz_pdf(articles, output_dir='output', category='varlden'):
    """Save one PDF with exactly one page per article."""
    if not articles:
        raise ValueError('No quiz data available.')

    register_font()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pdf_path = get_unique_pdf_path(
        output_path,
        category,
        articles
    )

    pdf = canvas.Canvas(str(pdf_path), pagesize=A4)
    pdf.setTitle('SFI Kurs C - Listening Practice')
    styles = create_styles()

    for index, article in enumerate(articles, start=1):
        print(f'Adding article {index}/{len(articles)} to PDF')
        draw_article_page(pdf, article, styles, index)

    pdf.save()
    print(f'\nPDF created: {pdf_path}')
    return pdf_path

def get_unique_pdf_path(output_dir, category, articles):
    """Build a unique PDF filename from the article date range."""

    dates = sorted({
        datetime.strptime(str(article["date"]), "%Y-%m-%d").date()
        for article in articles
        if article.get("date")
        and str(article["date"]).strip().lower() not in {"nan", "none"}
    })

    if not dates:
        date_range = datetime.now().strftime("%Y%m%d")

    else:
        first_date = dates[0]
        last_date = dates[-1]

        if first_date == last_date:
            date_range = first_date.strftime("%Y%m%d")

        elif first_date.year == last_date.year:
            if first_date.month == last_date.month:
                date_range = (
                    f"{first_date:%Y%m%d}-{last_date:%d}"
                )
            else:
                date_range = (
                    f"{first_date:%Y%m%d}-{last_date:%m%d}"
                )

        else:
            date_range = (
                f"{first_date:%Y%m%d}-{last_date:%Y%m%d}"
            )

    base_name = f"{category}_{date_range}"
    pdf_path = output_dir / f"{base_name}.pdf"

    # Avoid overwriting an existing PDF
    counter = 2

    while pdf_path.exists():
        pdf_path = output_dir / f"{base_name}_{counter}.pdf"
        counter += 1

    return pdf_path