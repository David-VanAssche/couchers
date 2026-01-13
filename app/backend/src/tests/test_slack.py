from unittest.mock import patch

import pytest

from couchers.config import config
from couchers.slack import send_slack_message
from tests.test_fixtures import testconfig  # noqa


@pytest.fixture(autouse=True)
def _(testconfig):
    pass


def test_send_slack_message_disabled():
    """When Slack is disabled, messages should be logged but not sent."""
    with patch("couchers.slack.requests.post") as mock_post:
        send_slack_message("Test message", channel="test-channel")
        mock_post.assert_not_called()


def test_send_slack_message_no_channel():
    """When no channel is specified, message should be logged but not sent."""
    config["ENABLE_SLACK"] = True
    config["SLACK_BOT_TOKEN"] = "xoxb-test-token"

    with patch("couchers.slack.requests.post") as mock_post:
        send_slack_message("Test message")
        mock_post.assert_not_called()


def test_send_slack_message_enabled():
    """When Slack is enabled, messages should be sent via the Bot API."""
    config["ENABLE_SLACK"] = True
    config["SLACK_BOT_TOKEN"] = "xoxb-test-token"

    with patch("couchers.slack.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"ok": True}
        send_slack_message("Test message", channel="test-channel")
        mock_post.assert_called_once_with(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": "Bearer xoxb-test-token"},
            json={"channel": "test-channel", "text": "Test message"},
            timeout=10,
        )


def test_send_slack_message_handles_request_error():
    """When Slack request fails, it should log the error but not raise."""
    import requests

    config["ENABLE_SLACK"] = True
    config["SLACK_BOT_TOKEN"] = "xoxb-test-token"

    with patch("couchers.slack.requests.post") as mock_post:
        mock_post.side_effect = requests.RequestException("Connection failed")
        # Should not raise
        send_slack_message("Test message", channel="test-channel")


def test_send_slack_message_handles_api_error():
    """When Slack API returns an error, it should log it but not raise."""
    config["ENABLE_SLACK"] = True
    config["SLACK_BOT_TOKEN"] = "xoxb-test-token"

    with patch("couchers.slack.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"ok": False, "error": "channel_not_found"}
        # Should not raise
        send_slack_message("Test message", channel="nonexistent-channel")
