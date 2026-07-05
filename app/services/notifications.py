from typing import Optional

import resend

from app.core.config import settings


def send_email_notification(to_email: str, subject: str, html_content: str) -> None:
    """Send an email via Resend, or log to console if the API key is not set."""
    if not settings.RESEND_API_KEY:
        print("\n=== MOCK EMAIL NOTIFICATION ===")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Body:\n{html_content}")
        print("===============================\n")
        return

    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        })
        print(f"Email successfully sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")


def _order_items_table_html(items: list[dict]) -> str:
    if not items:
        return ""

    rows = "".join(
        f"<tr>"
        f"<td style='padding: 8px; border-bottom: 1px solid #eee;'>{item['name']}</td>"
        f"<td style='padding: 8px; border-bottom: 1px solid #eee; text-align: center;'>{item['quantity']}</td>"
        f"<td style='padding: 8px; border-bottom: 1px solid #eee; text-align: right;'>${item['line_total']:.2f}</td>"
        f"</tr>"
        for item in items
    )
    return f"""
    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
      <thead>
        <tr style="background-color: #f9f9f9;">
          <th style="padding: 8px; text-align: left;">Item</th>
          <th style="padding: 8px; text-align: center;">Qty</th>
          <th style="padding: 8px; text-align: right;">Total</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    """


def send_inquiry_emails(
    full_name: str,
    email: str,
    phone: str,
    message: str,
    subject: Optional[str] = None,
) -> None:
    """Send inquiry notification to the store owner and a confirmation copy to the customer."""
    inquiry_subject = subject or "General Inquiry"

    owner_subject = f"[New Inquiry] {inquiry_subject} - {full_name}"
    owner_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #681628;">New Contact Inquiry</h2>
        <p><strong>From:</strong> {full_name}</p>
        <p><strong>Email:</strong> {email}</p>
        <p><strong>Phone:</strong> {phone}</p>
        <p><strong>Subject:</strong> {inquiry_subject}</p>
        <p><strong>Message:</strong></p>
        <p style="white-space: pre-wrap; background: #f9f9f9; padding: 12px; border-radius: 4px;">{message}</p>
      </body>
    </html>
    """
    send_email_notification(settings.OWNER_NOTIFICATION_EMAIL, owner_subject, owner_html)

    customer_subject = "We received your inquiry | Murad Sweets"
    customer_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #681628;">Thank you for reaching out, {full_name}!</h2>
        <p>We have received your inquiry and will get back to you within 24 hours.</p>
        <p><strong>Your message:</strong></p>
        <p style="white-space: pre-wrap; background: #f9f9f9; padding: 12px; border-radius: 4px;">{message}</p>
        <p>If you need immediate assistance, feel free to call us.</p>
        <p>Warmly,<br/>The Murad Sweets Team</p>
      </body>
    </html>
    """
    send_email_notification(email, customer_subject, customer_html)


def send_order_confirmation_emails(
    customer_email: str,
    customer_name: str,
    order_number: str,
    total_cents: int,
    fulfillment_type: str,
    scheduled_date: str,
    scheduled_slot: str,
    items: Optional[list[dict]] = None,
    customer_phone: Optional[str] = None,
    delivery_address: Optional[str] = None,
) -> None:
    """Send order confirmation emails to the customer and the store owner."""
    total_dollars = total_cents / 100.0
    items_html = _order_items_table_html(items or [])
    phone_line = f"<li>Phone: {customer_phone}</li>" if customer_phone else ""

    customer_subject = f"Order Received - {order_number} | Murad Sweets"
    customer_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #681628;">Thank you for your order, {customer_name}!</h2>
        <p>We have received your order <strong>{order_number}</strong> and are reviewing the details.</p>
        <p><strong>Order Summary:</strong></p>
        <ul>
          <li>Fulfillment: {delivery_address if fulfillment_type == 'delivery' and delivery_address else fulfillment_type.capitalize()}</li>
          <li>Scheduled Date: {scheduled_date}</li>
          <li>Scheduled Time Slot: {scheduled_slot}</li>
          <li>Total Amount: ${total_dollars:.2f}</li>
        </ul>
        {items_html}
        <p><strong>Next Steps:</strong> We will contact you via email or phone within 24 hours to confirm your order and coordinate collection/delivery details.</p>
        <p>Warmly,<br/>The Murad Sweets Team</p>
      </body>
    </html>
    """
    send_email_notification(customer_email, customer_subject, customer_html)

    owner_subject = f"[New Order] {order_number} - {customer_name}"
    owner_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #681628;">New Order Placed: {order_number}</h2>
        <p><strong>Customer Details:</strong></p>
        <ul>
          <li>Name: {customer_name}</li>
          <li>Email: {customer_email}</li>
          {phone_line}
        </ul>
        <p><strong>Fulfillment Details:</strong></p>
        <ul>
          <li>Type: {delivery_address if fulfillment_type == 'delivery' and delivery_address else fulfillment_type.capitalize()}</li>
          <li>Scheduled: {scheduled_date} ({scheduled_slot})</li>
          <li>Total: ${total_dollars:.2f}</li>
        </ul>
        {items_html}
        <p>Please log in to the admin panel to view items and update order status.</p>
      </body>
    </html>
    """
    send_email_notification(settings.OWNER_NOTIFICATION_EMAIL, owner_subject, owner_html)
