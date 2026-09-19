import os
from io import BytesIO

from django.conf import settings
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import RectangleObject
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

TEMPLATE_PDF = os.path.join(settings.BASE_DIR, 'static', 'img', 'Centro Integral version22.pdf')
PAGE_W = 720
PAGE_H = 504
MEDIA_Y0 = 7.9199977
MEDIA_Y1 = 511.91998
CREAM = HexColor('#FFFEF5')
INK = HexColor('#1a1a1a')
TURQUESA = HexColor('#18b1a3')
NARANJA = HexColor('#E7A56C')

_FONTS_READY = False
FONT = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
FONT_SCRIPT = 'Times-Italic'


def _register_fonts():
    global _FONTS_READY, FONT, FONT_BOLD, FONT_SCRIPT
    if _FONTS_READY:
        return
    regular_candidates = [
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans.ttf'),
        r'C:\Windows\Fonts\arial.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
    ]
    bold_candidates = [
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans-Bold.ttf'),
        r'C:\Windows\Fonts\arialbd.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    ]
    script_candidates = [
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DancingScript.ttf'),
        r'C:\Windows\Fonts\segoesc.ttf',
        r'C:\Windows\Fonts\BRUSHSCI.TTF',
        r'C:\Windows\Fonts\MTCORSVA.TTF',
    ]
    regular = next((path for path in regular_candidates if os.path.exists(path)), None)
    bold = next((path for path in bold_candidates if os.path.exists(path)), None)
    script = next((path for path in script_candidates if os.path.exists(path)), None)
    if regular and bold:
        pdfmetrics.registerFont(TTFont('CarnetSans', regular))
        pdfmetrics.registerFont(TTFont('CarnetSans-Bold', bold))
        FONT = 'CarnetSans'
        FONT_BOLD = 'CarnetSans-Bold'
    if script:
        pdfmetrics.registerFont(TTFont('CarnetScript', script))
        FONT_SCRIPT = 'CarnetScript'
    _FONTS_READY = True


def _nombre_completo(paciente):
    parts = [paciente.nombre, paciente.apellido_paterno]
    if paciente.apellido_materno:
        parts.append(paciente.apellido_materno)
    return ' '.join(part for part in parts if part).strip() or paciente.nombre


def _fit_font_size(text, font, max_width, start=16, minimum=9):
    size = start
    while size > minimum and pdfmetrics.stringWidth(text, font, size) > max_width:
        size -= 0.5
    return size


def _static_img(*parts):
    path = os.path.join(settings.BASE_DIR, 'static', *parts)
    return path if os.path.exists(path) else None


def _make_overlay(draw_callback):
    buf = BytesIO()
    pdf = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    draw_callback(pdf)
    pdf.save()
    buf.seek(0)
    overlay_page = PdfReader(buf).pages[0]
    overlay_page.add_transformation(Transformation().translate(0, MEDIA_Y0))
    overlay_page.mediabox = RectangleObject([0.0, MEDIA_Y0, PAGE_W, MEDIA_Y1])
    overlay_page.cropbox = overlay_page.mediabox
    return overlay_page


def _draw_cover_overlay(pdf, paciente):
    # Tapa el logo original (derecha) sin recortar título ni doctora.
    pdf.setFillColor(CREAM)
    pdf.rect(428, 198, 215, 105, fill=1, stroke=0)

    pdf.setStrokeColor(NARANJA)
    pdf.setLineWidth(2.2)
    pdf.line(430, 308, 628, 308)

    # Tapa teléfonos, pin y dirección originales para redibujar el bloque alineado.
    pdf.setFillColor(CREAM)
    pdf.rect(48, 78, 320, 270, fill=1, stroke=0)

    left_center = 205
    logo_path = _static_img('img', 'logo.png')
    if logo_path:
        logo_w, logo_h = 400, 212
        pdf.drawImage(
            ImageReader(logo_path),
            left_center - logo_w / 2, 300, width=logo_w, height=logo_h,
            mask='auto', preserveAspectRatio=True, anchor='c',
        )

    pdf.setFillColor(TURQUESA)
    pdf.setFont(FONT_SCRIPT, 32)
    pdf.drawCentredString(left_center, 288, 'Ojos vemos, Columnas')
    pdf.drawCentredString(left_center, 256, 'no Sabemos')

    pdf.setFillColor(INK)
    pdf.setFont(FONT, 12)
    pdf.drawCentredString(left_center, 228, '(55) 1309-8145')
    pdf.drawCentredString(left_center, 212, '(55) 2231-5535')

    pin_path = _static_img('img', 'location_icon.png')
    if pin_path:
        pdf.drawImage(ImageReader(pin_path), left_center - 7, 186, width=14, height=18, mask='auto')

    address_lines = [
        'Prolongación Emiliano',
        'Zapata sin número barrio',
        'la luz, Santiago',
        'Cuautlalpan Tepotzotlan',
        'Estado de México',
    ]
    pdf.setFont(FONT, 11)
    y = 168
    for line in address_lines:
        pdf.drawCentredString(left_center, y, line)
        y -= 14

    nombre = _nombre_completo(paciente)
    size = _fit_font_size(nombre, FONT_BOLD, 250, start=16)
    pdf.setFillColor(INK)
    pdf.setFont(FONT_BOLD, size)
    pdf.drawCentredString(529, 235, nombre)


def _draw_paciente_line(pdf, paciente):
    nombre = _nombre_completo(paciente)
    size = _fit_font_size(nombre, FONT, 290, start=16)
    pdf.setFillColor(CREAM)
    pdf.rect(98, 450, 310, 22, fill=1, stroke=0)
    pdf.setFillColor(INK)
    pdf.setFont(FONT, size)
    pdf.drawString(102, 456, nombre)


def build_carnet_pdf(paciente):
    _register_fonts()
    template = PdfReader(TEMPLATE_PDF)
    writer = PdfWriter()

    for index, template_page in enumerate(template.pages):
        page = template_page
        if index == 0:
            page.merge_page(_make_overlay(lambda pdf: _draw_cover_overlay(pdf, paciente)))
        elif index == 1:
            page.merge_page(_make_overlay(lambda pdf: _draw_paciente_line(pdf, paciente)))
        writer.add_page(page)

    output = BytesIO()
    writer.write(output)
    output.seek(0)
    return output
