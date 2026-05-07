"""
Top-of-screen notifications, connection-state UI, and the
``update_form_fields_running_patient`` orchestration helper.
"""

import asyncio

from nicegui import ui

import utils as dashboard_utils
from . import state


# --- Generation progress -----------------------------------------------------
def _start_notification(message="Loading..."):
    state.generation_progress_notification = ui.notification(
        message, spinner=True, position="top-right", type="ongoing", timeout=0,
    )


def _start_patient_generation_ui():
    """Reflect that patient generation has begun."""
    from .form import form  # local import to avoid circular
    _start_notification(message="Launching patient generation...")
    form.refresh(disabled=True)


def _start_patient_launching_ui():
    """Reflect that a predefined patient is being launched."""
    from .form import form
    _start_notification(message="Launching patient...")
    form.refresh(disabled=True)


def progress_message(message):
    if state.generation_progress_notification is None:
        _start_notification()
    state.generation_progress_notification.message = f"{message}"


def progress_step(message, step, total_steps):
    if state.generation_progress_notification is None:
        _start_notification()
    state.generation_progress_notification.message = f"{message} ({step}/{total_steps})"


def progress_end(state_str, message):
    async def _wait_and_close():
        temp = state.generation_progress_notification
        state.generation_progress_notification = None
        await asyncio.sleep(5)
        if temp is not None:
            temp.dismiss()

    if state.generation_progress_notification is None:
        _start_notification()
    if state_str == "success":
        state.generation_progress_notification.type = "positive"
    if state_str == "error":
        state.generation_progress_notification.type = "negative"
        update_form_fields_running_patient()
    if state_str == "warning":
        state.generation_progress_notification.type = "warning"
        update_form_fields_running_patient()

    state.generation_progress_notification.message = message
    state.generation_progress_notification.close_button = True
    state.generation_progress_notification.spinner = False
    asyncio.create_task(_wait_and_close())


# --- Hint --------------------------------------------------------------------
def show_hint(hint: str):
    """Display a coaching hint as a top notification with a dismiss button."""
    if not hint:
        return
    try:
        ui.notification(
            f"💡 {hint}",
            type="info",
            position="top",
            timeout=15,
            close_button=True,
            multi_line=True,
        )
    except Exception as e:
        print(f"show_hint failed: {e}")


# --- Connection lifecycle ---------------------------------------------------
def server_connection_lost_ui():
    """Show a 'connecting...' notification, disable inputs, clear feedback panes."""
    from .form import form
    from .sidebar import patient_control_buttons
    from .chat import chat_input, clear_messages
    from .feedback_view import feedback
    from .dialogs import fresh_feedback_dialog, fresh_debug_dialog, fresh_patient_dialog

    if state.server_connection_notification is None:
        state.server_connection_notification = ui.notification(
            "Connecting to the intermediate server...", spinner=True,
            position="bottom-left", type="ongoing", timeout=0,
        )
        form.refresh(disabled=True)
        patient_control_buttons.refresh(disable_connection_buttons=True)
        chat_input.refresh()
        clear_messages()
        fresh_feedback_dialog()
        fresh_debug_dialog()
        fresh_patient_dialog()
        if state.messages_container is not None:
            with state.messages_container:
                ui.markdown("*Awaiting connection...*")
        feedback.refresh("*Awaiting connection...*")
    if state.furhat_connection_notification is not None:
        state.furhat_connection_notification.dismiss()
        state.furhat_connection_notification = None
    if state.generation_progress_notification is not None:
        state.generation_progress_notification.dismiss()
        state.generation_progress_notification = None


def server_connection_restored_ui():
    from .chat import clear_messages
    if state.server_connection_notification is not None:
        state.server_connection_notification.dismiss()
        state.server_connection_notification = None
    clear_messages()


def furhat_connection_lost_ui():
    from .form import form
    from .sidebar import patient_control_buttons, furhat_status
    if state.furhat_connection_notification is None:
        state.furhat_connection_notification = ui.notification(
            "Connecting to the avatar...", spinner=True,
            position="bottom-left", type="ongoing", timeout=0,
        )
        form.refresh(disabled=True)
        patient_control_buttons.refresh(disable_connection_buttons=True)
    furhat_status.refresh(None)


def furhat_connection_restored_ui():
    if state.furhat_connection_notification is not None:
        state.furhat_connection_notification.dismiss()
        state.furhat_connection_notification = None
    update_form_fields_running_patient()


# --- Whole-form refresh helper ----------------------------------------------
def update_form_fields_running_patient():
    """Refresh form, control buttons, chat input, and side panel buttons."""
    from .form import form
    from .sidebar import (
        patient_control_buttons,
        open_debug_dialog_button,
        open_patient_information_button,
    )
    from .chat import chat_input

    patient_control_buttons.refresh(disable_connection_buttons=False)
    form.refresh(disabled=dashboard_utils.is_patient_running)
    chat_input.refresh()
    open_debug_dialog_button.refresh(override=True, shown=dashboard_utils.is_patient_in_system)
    open_patient_information_button.refresh(override=True, shown=dashboard_utils.is_patient_in_system)
