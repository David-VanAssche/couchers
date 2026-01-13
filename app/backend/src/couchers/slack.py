import logging

import requests

from couchers.config import config

logger = logging.getLogger(__name__)


def send_slack_message(text: str, channel: str | None = None) -> None:
    """
    Sends a message to Slack using the Bot API.

    Args:
        text: The message text to send
        channel: The channel ID or name to post to. If None, the message is logged but not sent.

    If Slack is disabled, logs the message instead.
    """
    if not config["ENABLE_SLACK"]:
        logger.info(f"Slack disabled, would have sent to {channel}: {text}")
        return

    if not channel:
        logger.warning(f"No Slack channel specified, not sending: {text}")
        return

    try:
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {config['SLACK_BOT_TOKEN']}"},
            json={"channel": channel, "text": text},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            logger.error(f"Slack API error: {data.get('error')}")
    except requests.RequestException:
        logger.exception("Failed to send Slack message")
