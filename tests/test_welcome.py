"""Welcome selections must preserve stored intervals when editing the need."""

from unittest.mock import MagicMock, patch

import pytest

from spinespy.onboarding import WelcomeWindow


@pytest.fixture
def welcome():
    view = WelcomeWindow("", MagicMock(return_value=True), MagicMock())
    view.window = MagicMock()
    view.need_buttons = [MagicMock() for _ in range(3)]
    view.interval_control = MagicMock()
    view.interval_control.setSelectedSegment_.side_effect = (
        lambda index: setattr(view.interval_control.selectedSegment, "return_value", index)
    )
    view.continue_button = MagicMock()
    view.status_label = MagicMock()
    with (
        patch("spinespy.onboarding.NSApplication"),
        patch("spinespy.onboarding.NSScreen") as screen,
    ):
        screen.mainScreen.return_value = None
        yield view


@pytest.mark.parametrize("interval", [900, 7200])
def test_editing_need_keeps_preview_interval(welcome, interval):
    welcome.show(primary_need="posture", interval=interval, completed=True)
    welcome.select_need(1)
    welcome.submit()

    welcome.continue_button.setEnabled_.assert_called_with(True)
    welcome.status_label.setStringValue_.assert_called_with(
        f"Keeping your {interval // 60}-minute interval.",
    )
    welcome.on_complete.assert_called_once_with("movement", interval)


def test_choosing_preset_replaces_retained_interval(welcome):
    welcome.show(primary_need="posture", interval=7200, completed=True)
    welcome.interval_control.setSelectedSegment_(1)
    welcome.update_continue()
    welcome.submit()

    welcome.status_label.setStringValue_.assert_called_with("")
    welcome.on_complete.assert_called_once_with("posture", 1200)


def test_reopening_without_interval_clears_previous_retained_value(welcome):
    welcome.show(primary_need="posture", interval=900, completed=True)
    welcome.show(primary_need="posture", interval=None)
    welcome.submit()

    welcome.continue_button.setEnabled_.assert_called_with(False)
    welcome.on_complete.assert_not_called()


@pytest.mark.parametrize("interval, index", [(600, 0), (1200, 1), (1800, 2), (3600, 3)])
def test_current_preset_is_preselected(welcome, interval, index):
    welcome.show(primary_need="posture", interval=interval)

    assert welcome.interval_control.selectedSegment() == index
    welcome.continue_button.setEnabled_.assert_called_with(True)
