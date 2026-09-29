"""Native macOS welcome window. All answers are handed to the local settings store."""

from AppKit import (
    NSApplication,
    NSBackingStoreBuffered,
    NSBezelStyleRounded,
    NSBox,
    NSBoxSeparator,
    NSButton,
    NSColor,
    NSControlStateValueOn,
    NSFont,
    NSImage,
    NSImageScaleProportionallyUpOrDown,
    NSImageView,
    NSMakeRect,
    NSRadioButton,
    NSScreen,
    NSSegmentedControl,
    NSTextAlignmentCenter,
    NSTextField,
    NSView,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSObject

from spinespy.settings import INTERVAL_LABELS, PRIMARY_NEEDS, is_valid_interval


class _WelcomeActions(NSObject):
    def chooseNeed_(self, sender):
        self.owner.select_need(sender.tag())

    def chooseInterval_(self, sender):
        self.owner.update_continue()

    def submit_(self, sender):
        self.owner.submit()

    def windowWillClose_(self, notification):
        self.owner.on_close()


class WelcomeWindow:
    """Own a single reusable, keyboard-accessible AppKit window."""

    def __init__(self, image_path, on_complete, on_close):
        self.on_complete = on_complete
        self.on_close = on_close
        self.primary_need = None
        self.retained_interval = None
        self.window = None
        self.image_path = image_path
        self.need_buttons = []
        self.actions = _WelcomeActions.alloc().init()
        self.actions.owner = self

    def _label(self, text, frame, size=13, bold=False, centered=False, secondary=False):
        label = NSTextField.wrappingLabelWithString_(text)
        label.setFrame_(NSMakeRect(*frame))
        font = NSFont.boldSystemFontOfSize_ if bold else NSFont.systemFontOfSize_
        label.setFont_(font(size))
        if centered:
            label.setAlignment_(NSTextAlignmentCenter)
        if secondary:
            label.setTextColor_(NSColor.secondaryLabelColor())
        self.window.contentView().addSubview_(label)
        return label

    def _build(self):
        width, height = 560, 610
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, width, height),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("Welcome to SpineSpy")
        self.window.setReleasedWhenClosed_(False)
        self.window.setDelegate_(self.actions)
        content = self.window.contentView()

        mascot = NSImageView.alloc().initWithFrame_(NSMakeRect(232, 494, 96, 96))
        mascot.setImage_(NSImage.alloc().initWithContentsOfFile_(self.image_path))
        mascot.setImageScaling_(NSImageScaleProportionallyUpOrDown)
        mascot.setAccessibilityElement_(False)
        content.addSubview_(mascot)

        self._label("Meet SpineSpy", (32, 450, 496, 38), 28, True, True)
        self._label(
            "Your posture buddy for more movement and less pain :)",
            (42, 406, 476, 36), 14, centered=True, secondary=True,
        )
        self._label(
            "Let’s get you set up.",
            (38, 359, 484, 26), centered=True,
        )

        self._label("What do you need most help with?", (38, 312, 484, 23), 14, True)
        # Separate container keeps AppKit's radio-button group self-contained.
        need_group = NSView.alloc().initWithFrame_(NSMakeRect(38, 209, 484, 99))
        need_group.setAccessibilityLabel_("What do you need most help with?")
        content.addSubview_(need_group)
        for index, title in enumerate(PRIMARY_NEEDS.values()):
            button = NSButton.alloc().initWithFrame_(NSMakeRect(0, 68 - index * 32, 484, 28))
            button.setButtonType_(NSRadioButton)
            button.setTitle_(title)
            button.setFont_(NSFont.systemFontOfSize_(14))
            button.setTag_(index)
            button.setTarget_(self.actions)
            button.setAction_("chooseNeed:")
            need_group.addSubview_(button)
            self.need_buttons.append(button)

        self._label("How often should I check in?", (38, 174, 484, 23), 14, True)
        self.interval_control = NSSegmentedControl.alloc().initWithFrame_(
            NSMakeRect(38, 133, 484, 32)
        )
        self.interval_control.setSegmentCount_(len(INTERVAL_LABELS))
        for index, label in enumerate(INTERVAL_LABELS.values()):
            self.interval_control.setLabel_forSegment_(label.replace("minutes", "min"), index)
            self.interval_control.setWidth_forSegment_(116, index)
            self.interval_control.setToolTip_forSegment_(
                f"Check every {label}", index
            )
        self.interval_control.setSelectedSegment_(-1)
        self.interval_control.setTarget_(self.actions)
        self.interval_control.setAction_("chooseInterval:")
        self.interval_control.setAccessibilityLabel_("Camera posture check interval")
        content.addSubview_(self.interval_control)

        self._label(
            "Brief camera checks. Images processed on your Mac.\n"
            "Preferences saved locally. No account needed.",
            (38, 82, 484, 38), 11, secondary=True,
        )
        divider = NSBox.alloc().initWithFrame_(NSMakeRect(38, 70, 484, 1))
        divider.setBoxType_(NSBoxSeparator)
        content.addSubview_(divider)

        self.status_label = self._label("", (38, 18, 310, 40), 12)
        self.continue_button = NSButton.alloc().initWithFrame_(NSMakeRect(365, 24, 162, 36))
        self.continue_button.setTitle_("Get started")
        self.continue_button.setBezelStyle_(NSBezelStyleRounded)
        self.continue_button.setKeyEquivalent_("\r")
        self.continue_button.setTarget_(self.actions)
        self.continue_button.setAction_("submit:")
        content.addSubview_(self.continue_button)
        self.window.setInitialFirstResponder_(self.need_buttons[0])
        self.window.recalculateKeyViewLoop()

    def show(self, primary_need=None, interval=None, completed=False):
        if self.window is None:
            self._build()
        self.primary_need = primary_need
        for key, button in zip(PRIMARY_NEEDS, self.need_buttons):
            button.setState_(int(key == primary_need))
        intervals = tuple(INTERVAL_LABELS)
        self.retained_interval = interval if is_valid_interval(interval) else None
        self.interval_control.setSelectedSegment_(
            intervals.index(interval) if interval in intervals else -1
        )
        self.continue_button.setTitle_("Save changes" if completed else "Get started")
        self.update_continue()

        # Center in the usable screen area, including on external displays.
        screen = NSScreen.mainScreen()
        if screen is not None:
            visible = screen.visibleFrame()
            frame = self.window.frame()
            self.window.setFrameOrigin_((
                visible.origin.x + (visible.size.width - frame.size.width) / 2,
                visible.origin.y + (visible.size.height - frame.size.height) / 2,
            ))
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        self.window.makeKeyAndOrderFront_(None)

    def select_need(self, index):
        self.primary_need = tuple(PRIMARY_NEEDS)[index]
        for current, button in enumerate(self.need_buttons):
            button.setState_(NSControlStateValueOn if current == index else 0)
        self.update_continue()

    def update_continue(self):
        index = self.interval_control.selectedSegment()
        retaining = index < 0 and self.retained_interval is not None
        self.status_label.setStringValue_(
            f"Keeping your {self.retained_interval // 60}-minute interval." if retaining else ""
        )
        self.continue_button.setEnabled_(
            self.primary_need in PRIMARY_NEEDS and (index >= 0 or retaining)
        )

    def submit(self):
        index = self.interval_control.selectedSegment()
        interval = tuple(INTERVAL_LABELS)[index] if index >= 0 else self.retained_interval
        if self.primary_need not in PRIMARY_NEEDS or not is_valid_interval(interval):
            return
        if not self.on_complete(self.primary_need, interval):
            self.status_label.setStringValue_("Couldn’t save. Please try again.")

    def hide(self):
        if self.window is not None:
            self.window.orderOut_(None)
