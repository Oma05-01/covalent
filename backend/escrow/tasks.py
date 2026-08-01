# accounts/tasks.py
from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

@shared_task(name="auto_release_escrow_task")
def run_auto_release_worker():
    """
    Executes the auto_release_escrow management command.
    """
    try:
        call_command('auto_release_escrow')
        logger.info("Successfully executed auto_release_escrow command.")
    except Exception as e:
        logger.error(f"Error executing auto_release_escrow command: {str(e)}")