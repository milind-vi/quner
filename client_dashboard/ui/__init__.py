"""
Dashboard UI package.

Originally one 650-line ``ui_utils.py``; split by concern:

  - state         : module-level mutable state shared between components
  - dialogs       : feedback, debug-log, patient-info modal dialogs
  - form          : patient generation form + Restart button
  - chat          : chat scroll area, message bubbles, mic + send input
  - sidebar       : control buttons, furhat status icon, vignette panel
  - feedback_view : "Immediate feedback" inline display + final-feedback rows
  - notifications : progress / connection / hint notifications and form refresh

The previous flat namespace is preserved by ``ui_utils.py`` re-exporting
everything from this package.
"""

# Re-export the public API so callers can do `from ui import foo` if they want.
from .form import (
    form,
    update_last_form_values,
    _set_last_launch_kind,
    _replay_last_launch,
)
from .dialogs import (
    fresh_feedback_dialog,
    fresh_debug_dialog,
    fresh_patient_dialog,
)
from .chat import (
    chat_input,
    messages,
    add_patient_message,
    add_doctor_message,
    messages_scroll_to_bottom,
    clear_messages,
)
from .sidebar import (
    patient_control_buttons,
    furhat_status,
    vignette_panel,
    vignette_drawer,
    set_full_vignette,
    open_debug_dialog_button,
    open_patient_information_button,
    set_patient_info,
    add_generation_log_item,
)
from .feedback_view import (
    feedback,
    add_conversation_feedback_item,
    add_clinical_feedback_item,
)
from .notifications import (
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

# `conversation_id` is a module-level attribute of state; expose it here too so
# ``import ui_utils; ui_utils.conversation_id`` keeps working transparently.
from . import state as _state


def __getattr__(name):
    # Forwarding shim so reads like ``ui_utils.conversation_id`` still work and
    # always reflect the latest value in state.
    if hasattr(_state, name):
        return getattr(_state, name)
    raise AttributeError(name)
