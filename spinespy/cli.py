"""Console entrypoints for Poetry scripts."""

from menubar_app import main as app_main
from test_phone_detection import main as phone_test_main


def start():
    """Run the menubar app."""
    app_main()


def test_phone():
    """Run live phone-detection camera test."""
    return phone_test_main()

