from tests.test_state_reducer import _reduce_state
from zivo.state import build_initial_app_state, dispatch_key_input
from zivo.state.actions import (
    ActivateNextTab,
    ActivatePreviousTab,
    FocusTransferPane,
    SetNotification,
    ToggleTransferMode,
    TransferCopyToOppositePane,
    TransferMoveToOppositePane,
)


def test_transfer_mode_uses_brackets_for_pane_focus() -> None:
    state = _reduce_state(build_initial_app_state(), ToggleTransferMode())

    assert dispatch_key_input(state, key="[") == (
        SetNotification(None),
        FocusTransferPane("left"),
    )
    assert dispatch_key_input(state, key="]") == (
        SetNotification(None),
        FocusTransferPane("right"),
    )


def test_transfer_mode_keeps_tab_keys_for_browser_tabs() -> None:
    state = _reduce_state(build_initial_app_state(), ToggleTransferMode())

    assert dispatch_key_input(state, key="tab") == (SetNotification(None), ActivateNextTab())
    assert dispatch_key_input(state, key="shift+tab") == (
        SetNotification(None),
        ActivatePreviousTab(),
    )


def test_transfer_mode_uses_non_function_keys_for_copy_and_move() -> None:
    state = _reduce_state(build_initial_app_state(), ToggleTransferMode())

    assert dispatch_key_input(state, key="y") == (
        SetNotification(None),
        TransferCopyToOppositePane(),
    )
    assert dispatch_key_input(state, key="m") == (
        SetNotification(None),
        TransferMoveToOppositePane(),
    )
