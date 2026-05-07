"""
Public API facade for the dashboard UI.

The implementation lives in the ``ui/`` package (form, chat, dialogs, sidebar,
feedback_view, notifications, state). This file re-exports the functions that
``main.py`` and the WS consumer in ``utils.py`` call as ``ui_utils.X``, so no
existing call site has to change.
"""

from ui import (  # noqa: F401
    form,
    update_last_form_values,
    _set_last_launch_kind,
    _replay_last_launch,
    fresh_feedback_dialog,
    fresh_debug_dialog,
    fresh_patient_dialog,
    chat_input,
    messages,
    add_patient_message,
    add_doctor_message,
    messages_scroll_to_bottom,
    clear_messages,
    patient_control_buttons,
    furhat_status,
    vignette_panel,
    vignette_drawer,
    set_full_vignette,
    open_debug_dialog_button,
    open_patient_information_button,
    set_patient_info,
    add_generation_log_item,
    feedback,
    add_conversation_feedback_item,
    add_clinical_feedback_item,
    show_hint,
    progress_message,
    progress_step,
    progress_end,
    server_connection_lost_ui,
    server_connection_restored_ui,
    furhat_connection_lost_ui,
    furhat_connection_restored_ui,
    update_form_fields_running_patient,
    _start_patient_generation_ui,
    _start_patient_launching_ui,
    _start_notification,
)
from ui import state as _state


def __getattr__(name):
    """
    Forward attribute reads to ui.state so reads like ``ui_utils.conversation_id``
    still work unchanged. Note: module-level __setattr__ isn't a thing in Python,
    so plain assignment (``ui_utils.foo = X``) shadows the state value on this
    facade module rather than updating state — the WS consumer in utils.py uses
    ``ui_utils.conversation_id`` only as a read target, so this is fine.
    """
    if hasattr(_state, name):
        return getattr(_state, name)
    raise AttributeError(name)
