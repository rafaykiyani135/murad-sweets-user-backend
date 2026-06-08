import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

def send_email_notification(to_email: str, subject: str, html_content: str):
    """
    Sends an email notification via SMTP, or logs to console if credentials are not set.
    """
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASS:
        print("\n=== MOCK EMAIL NOTIFICATION ===")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Body:\n{html_content}")
        print("===============================\n")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_USER
        msg["To"] = to_email

        part = MIMEText(html_content, "html")
        msg.attach(part)

        # Connect to SMTP server
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
        print(f"Email successfully sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")

def send_order_confirmation_emails(
    customer_email: str,
    customer_name: str,
    order_number: str,
    total_cents: int,
    fulfillment_type: str,
    scheduled_date: str,
    scheduled_slot: str
):
    """Sends confirmation emails to the customer and the store owner."""
    total_dollars = total_cents / 100.0
    
    # Email to Customer
    customer_subject = f"Order Received - {order_number} | Murad Sweets"
    customer_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2 style="color: #681628;">Thank you for your order, {customer_name}!</h2>
        <p>We have received your order <strong>{order_number}</strong> and are reviewing the details.</p>
        <p><strong>Order Summary:</strong></p>
        <ul>
          <li>Fulfillment: {fulfillment_type.capitalize()}</li>
          <li>Scheduled Date: {scheduled_date}</li>
          <li>Scheduled Time Slot: {scheduled_slot}</li>
          <li>Total Amount: ${total_dollars:.2f}</li>
        </ul>
        <p><strong>Next Steps:</strong> We will contact you via email or phone within 24 hours to confirm your order and coordinate collection/delivery details.</p>
        <p>Warmly,<br/>The Murad Sweets Team</p>
      </body>
    </html>
    """
    send_email_notification(customer_email, customer_subject, customer_html)

    # Email to Owner
    if settings.OWNER_NOTIFICATION_EMAIL:
        owner_subject = f"[New Order] {order_number} - {customer_name}"
        owner_html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #681628;">New Order Placed: {order_number}</h2>
            <p><strong>Customer Details:</strong></p>
            <ul>
              <li>Name: {customer_name}</li>
              <li>Email: {customer_email}</li>
            </ul>
            <p><strong>Fulfillment Details:</strong></p>
            <ul>
              <li>Type: {fulfillment_type.capitalize()}</li>
              <li>Scheduled: {scheduled_date} ({scheduled_slot})</li>
              <li>Total: ${total_dollars:.2f}</li>
            </ul>
            <p>Please log in to the admin panel to view items and update order status.</p>
          </body>
        </html>
        """
        send_email_notification(settings.OWNER_NOTIFICATION_EMAIL, owner_subject, owner_html)
