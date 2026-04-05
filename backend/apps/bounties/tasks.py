"""Bounties Celery tasks (timeout detection, etc.)."""
from celery import shared_task

from apps.bounties.services import BountyService


@shared_task
def process_bounty_automations():
    BountyService.process_automations()
    return "ok"
