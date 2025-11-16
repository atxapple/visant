"""Email service for hardware order notifications using SendGrid."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content


# Email templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "email_templates"

# SendGrid configuration
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("ALERT_FROM_EMAIL", "noreply@visant.ai")


def load_email_template(template_name: str) -> str:
    """Load email template from file."""
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Email template not found: {template_name}")
    return template_path.read_text(encoding="utf-8")


def send_order_confirmation_email(
    to_email: str,
    order_number: str,
    plan_type: str,
    amount_paid: float,
    activation_code: str,
    shipping_address: dict,
    order_date: datetime
) -> bool:
    """
    Send order confirmation email with activation code.

    Args:
        to_email: Customer's email address
        order_number: Order number (e.g., "ORD-20241115-001")
        plan_type: "6month" or "1month"
        amount_paid: Amount paid (e.g., 297.00)
        activation_code: Activation code (e.g., "VISANT-ABC123")
        shipping_address: Dictionary with shipping details
        order_date: Order creation datetime

    Returns:
        True if email sent successfully, False otherwise
    """
    if not SENDGRID_API_KEY:
        print("Warning: SENDGRID_API_KEY not set, skipping email")
        return False

    try:
        # Load and populate template
        template = load_email_template("order_confirmation.html")

        plan_name = "6-Month Camera Bundle" if plan_type == "6month" else "1-Month Camera Bundle"

        # Format shipping address line 2 (may be empty)
        address_line2 = f"{shipping_address.get('line2', '')}<br>" if shipping_address.get('line2') else ""

        # Replace placeholders
        html_content = template.replace("{{ORDER_NUMBER}}", order_number)
        html_content = html_content.replace("{{PLAN_NAME}}", plan_name)
        html_content = html_content.replace("{{AMOUNT_PAID}}", f"{amount_paid:.2f}")
        html_content = html_content.replace("{{ACTIVATION_CODE}}", activation_code)
        html_content = html_content.replace("{{ORDER_DATE}}", order_date.strftime("%B %d, %Y"))
        html_content = html_content.replace("{{SHIPPING_NAME}}", shipping_address.get("name", ""))
        html_content = html_content.replace("{{SHIPPING_ADDRESS_LINE1}}", shipping_address.get("line1", ""))
        html_content = html_content.replace("{{SHIPPING_ADDRESS_LINE2}}", address_line2)
        html_content = html_content.replace("{{SHIPPING_CITY}}", shipping_address.get("city", ""))
        html_content = html_content.replace("{{SHIPPING_STATE}}", shipping_address.get("state", ""))
        html_content = html_content.replace("{{SHIPPING_POSTAL_CODE}}", shipping_address.get("postal_code", ""))
        html_content = html_content.replace("{{SHIPPING_COUNTRY}}", shipping_address.get("country", ""))

        # Create email message
        message = Mail(
            from_email=Email(FROM_EMAIL, "Visant"),
            to_emails=To(to_email),
            subject=f"Order Confirmation - {order_number}",
            html_content=Content("text/html", html_content)
        )

        # Send email
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        print(f"Order confirmation email sent to {to_email}, status: {response.status_code}")
        return response.status_code in [200, 201, 202]

    except Exception as e:
        print(f"Error sending order confirmation email: {e}")
        return False


def send_shipping_notification_email(
    to_email: str,
    order_number: str,
    tracking_number: str,
    activation_code: str,
    shipping_address: dict,
    shipped_date: datetime,
    estimated_delivery_days: int = 5
) -> bool:
    """
    Send shipping notification email with tracking information.

    Args:
        to_email: Customer's email address
        order_number: Order number
        tracking_number: Shipping tracking number
        activation_code: Activation code (reminder)
        shipping_address: Dictionary with shipping details
        shipped_date: Date when order was shipped
        estimated_delivery_days: Estimated delivery time in days

    Returns:
        True if email sent successfully, False otherwise
    """
    if not SENDGRID_API_KEY:
        print("Warning: SENDGRID_API_KEY not set, skipping email")
        return False

    try:
        # Load and populate template
        template = load_email_template("shipping_notification.html")

        # Calculate estimated delivery date
        from datetime import timedelta
        estimated_delivery = shipped_date + timedelta(days=estimated_delivery_days)

        # Create tracking URL (assuming USPS for now - can be made configurable)
        tracking_url = f"https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}"

        # Format shipping address line 2 (may be empty)
        address_line2 = f"{shipping_address.get('line2', '')}<br>" if shipping_address.get('line2') else ""

        # Replace placeholders
        html_content = template.replace("{{ORDER_NUMBER}}", order_number)
        html_content = html_content.replace("{{TRACKING_NUMBER}}", tracking_number)
        html_content = html_content.replace("{{TRACKING_URL}}", tracking_url)
        html_content = html_content.replace("{{ACTIVATION_CODE}}", activation_code)
        html_content = html_content.replace("{{SHIPPED_DATE}}", shipped_date.strftime("%B %d, %Y"))
        html_content = html_content.replace("{{ESTIMATED_DELIVERY}}", estimated_delivery.strftime("%B %d, %Y"))
        html_content = html_content.replace("{{SHIPPING_NAME}}", shipping_address.get("name", ""))
        html_content = html_content.replace("{{SHIPPING_ADDRESS_LINE1}}", shipping_address.get("line1", ""))
        html_content = html_content.replace("{{SHIPPING_ADDRESS_LINE2}}", address_line2)
        html_content = html_content.replace("{{SHIPPING_CITY}}", shipping_address.get("city", ""))
        html_content = html_content.replace("{{SHIPPING_STATE}}", shipping_address.get("state", ""))
        html_content = html_content.replace("{{SHIPPING_POSTAL_CODE}}", shipping_address.get("postal_code", ""))
        html_content = html_content.replace("{{SHIPPING_COUNTRY}}", shipping_address.get("country", ""))

        # Create email message
        message = Mail(
            from_email=Email(FROM_EMAIL, "Visant"),
            to_emails=To(to_email),
            subject=f"Your Order Has Shipped! - {order_number}",
            html_content=Content("text/html", html_content)
        )

        # Send email
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        print(f"Shipping notification sent to {to_email}, status: {response.status_code}")
        return response.status_code in [200, 201, 202]

    except Exception as e:
        print(f"Error sending shipping notification email: {e}")
        return False


def send_payment_failed_email(to_email: str, org_name: str) -> bool:
    """
    Send payment failed notification.

    Args:
        to_email: Customer's email address
        org_name: Organization name

    Returns:
        True if email sent successfully, False otherwise
    """
    if not SENDGRID_API_KEY:
        print("Warning: SENDGRID_API_KEY not set, skipping email")
        return False

    try:
        subject = "Payment Failed - Action Required"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #dc2626;">Payment Failed</h2>
            <p>Hello,</p>
            <p>We were unable to process your recent payment for your Visant subscription.</p>
            <p><strong>Organization:</strong> {org_name}</p>
            <p>Please update your payment method to avoid service interruption.</p>
            <p>
                <a href="https://app.visant.ai/ui/billing"
                   style="display: inline-block; padding: 12px 24px; background: #2563eb; color: white; text-decoration: none; border-radius: 6px; margin-top: 10px;">
                    Update Payment Method
                </a>
            </p>
            <p style="margin-top: 30px; color: #6b7280; font-size: 14px;">
                If you have any questions, please contact support@visant.ai
            </p>
        </body>
        </html>
        """

        message = Mail(
            from_email=Email(FROM_EMAIL, "Visant"),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content)
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        print(f"Payment failed email sent to {to_email}, status: {response.status_code}")
        return response.status_code in [200, 201, 202]

    except Exception as e:
        print(f"Error sending payment failed email: {e}")
        return False
