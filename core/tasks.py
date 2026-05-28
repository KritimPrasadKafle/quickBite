from core.celery_app import celery_app
from core.email import send_reset_email
import logging

logger = logging.getLogger(__name__)

@celery_app.task(
    bind = True,
    max_retries = 3,
    default_retry_delay=10,
    name = "task.send_reset_email",
)

def send_reset_email_task(self, to_email:str, reset_token:str) -> None:
    try:
        send_reset_email(to_email, reset_token)
        logger.info(f"Reset email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send reset email to {to_email}: {e}")
        raise self.retry(e=e)