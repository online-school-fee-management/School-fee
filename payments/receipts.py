import base64

from django.core import signing
from django.urls import reverse
from reportlab.graphics import renderSVG
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing


VERIFICATION_SALT = "school-fee-payment-receipt-verification"


def verification_token(payment):
    """Create a non-guessable token tied to this payment and school."""
    return signing.dumps(
        {
            "payment_id": payment.pk,
            "school_id": payment.school_id,
        },
        salt=VERIFICATION_SALT,
        compress=True,
    )


def verification_path(payment):
    return reverse(
        "receipts:verify",
        kwargs={
            "pk": payment.pk,
            "token": verification_token(payment),
        },
    )


def qr_data_uri(value):
    """Render a QR code as an inline SVG data URI."""
    code = QrCodeWidget(value, barLevel="M", barWidth=4, barHeight=4)
    bounds = code.getBounds()
    drawing = Drawing(
        bounds[2],
        bounds[3],
        transform=[1, 0, 0, 1, -bounds[0], -bounds[1]],
    )
    drawing.add(code)
    svg = renderSVG.drawToString(drawing)
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
