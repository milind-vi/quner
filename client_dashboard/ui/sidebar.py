"""
Right-column / control widgets: Pause/Resume buttons, the avatar status icon,
the patient-vignette panel, and the open-modal-dialog buttons.
"""

from nicegui import ui

import utils as dashboard_utils
from . import state


@ui.refreshable
def patient_control_buttons(disable_connection_buttons: bool = False):
    """Pause / Resume / Feedback row, plus the patient-info dialog button."""
    with ui.row().classes("shrink-0"):
        open_patient_information_button(override=False, shown=False)
        terminate_button = ui.button(
            "Pause",
            on_click=lambda: [
                dashboard_utils.stop_and_get_final_feedback(),
                patient_control_buttons.refresh(disable_connection_buttons=True),
            ],
        ).classes("mt-2")
        if disable_connection_buttons:
            terminate_button.disable()
        if not dashboard_utils.is_patient_running and dashboard_utils.is_patient_in_system:
            ui.button("Feedback", on_click=state.dialog_dialog.open).classes("mt-2")
        if not dashboard_utils.is_patient_running and dashboard_utils.is_patient_in_system:
            resume_button = ui.button(
                "Resume",
                on_click=lambda: [
                    dashboard_utils.resume_patient(),
                    patient_control_buttons.refresh(disable_connection_buttons=True),
                ],
            ).classes("mt-2")
            if disable_connection_buttons:
                resume_button.disable()
    if not dashboard_utils.is_patient_running:
        terminate_button.disable()


@ui.refreshable
def furhat_status(status: str = None):
    icons = {
        "listening": "hearing",
        "speaking": "record_voice_over",
        "started_idle": "play_circle",
        "ready": "not_started",
        "terminated": "pause_circle",
        "thinking": "psychology",
    }
    if status in icons:
        ui.icon(icons[status]).classes("mb-[0.9rem] ml-[-0.5rem]")
    elif status == "disconnected":
        ui.icon("wifi_off").classes("text-red-500 mb-[0.9rem] ml-[-0.5rem]")
    elif status == "text-mode":
        ui.icon("chat").classes("mb-[0.9rem] ml-[-0.5rem]") \
            .tooltip("Text-chat mode (no avatar connected)")
    else:
        ui.spinner().classes("mb-[0.9rem] ml-[-0.5rem]")


def vignette_drawer():
    """
    Right-slide drawer that holds the full patient vignette.

    Uses ``ui.dialog().props("position=right seamless")`` so it slides in from
    the right edge instead of opening a centered modal. Built lazily inside the
    page context (NiceGUI 2.x rule); refreshed in place via ``set_full_vignette``.
    """
    if state.vignette_drawer_dialog is None:
        state.vignette_drawer_dialog = ui.dialog().props(
            "position=right maximized=false"
        )
        with state.vignette_drawer_dialog:
            with ui.card().classes("h-screen w-[480px] !max-w-full !rounded-none !shadow-2xl") \
                    .style("background:#0f172a"):
                # Header
                with ui.row().classes("w-full items-center px-4 pt-4 pb-2 border-b border-slate-700"):
                    ui.icon("badge").classes("text-emerald-400 text-2xl")
                    with ui.column().classes("flex-1 gap-0"):
                        ui.label("Patient vignette").classes("text-lg font-semibold text-white leading-tight")
                        ui.label("Full case file — visible only to you").classes("text-xs text-slate-400")
                    ui.button(icon="close", on_click=state.vignette_drawer_dialog.close) \
                        .props("flat round dense color=white") \
                        .tooltip("Close")
                # Body — scrollable markdown
                with ui.scroll_area().classes("w-full flex-1 px-5 py-4"):
                    state.vignette_drawer_content = ui.element("div").classes("w-full")
                    with state.vignette_drawer_content:
                        ui.markdown(
                            state.full_vignette_text
                            or "*No patient loaded yet — generate or launch one to see the vignette here.*"
                        )


@ui.refreshable
def vignette_panel():
    """
    A small visible button that opens the slide-out vignette drawer.

    Lives in the right column (where the inline expansion used to be) and is
    always visible so the doctor can pop the vignette open mid-chat without
    hunting for it.
    """
    has_patient = bool(state.full_vignette_text)
    btn = ui.button(
        "View patient vignette",
        icon="badge",
        on_click=lambda: state.vignette_drawer_dialog and state.vignette_drawer_dialog.open(),
    ).props("color=secondary outline").classes("w-full mt-4")
    if not has_patient:
        btn.disable()
        btn.tooltip("Generate or launch a patient first.")


def set_full_vignette(text: str):
    """Update the cached vignette and re-render the drawer's content in place."""
    state.full_vignette_text = text or ""
    try:
        vignette_panel.refresh()
    except Exception:
        pass
    # Refresh drawer content if it exists.
    if state.vignette_drawer_content is not None:
        try:
            state.vignette_drawer_content.clear()
            with state.vignette_drawer_content:
                ui.markdown(state.full_vignette_text or "*No patient loaded.*")
        except Exception:
            pass




@ui.refreshable
def open_debug_dialog_button(override: bool = False, shown: bool = False):
    if (override and shown) or state.open_debug_dialog_button_shown:
        ui.button("Generation log", on_click=state.debug_dialog.open) \
            .classes("mt-2").props("color=secondary")
    if override:
        state.open_debug_dialog_button_shown = shown


@ui.refreshable
def open_patient_information_button(override: bool = False, shown: bool = False):
    if (override and shown) or state.open_patient_information_button_shown:
        ui.button("Patient information", on_click=state.patientinfo_dialog.open) \
            .classes("mt-2").props("color=standard")
    if override:
        state.open_patient_information_button_shown = shown


def set_patient_info(info):
    if state.patientinfo_content is not None:
        with state.patientinfo_content:
            ui.markdown(info)


def add_generation_log_item(log):
    if state.debug_dialog_content is not None:
        with state.debug_dialog_content:
            with ui.item().classes("w-[900px]"):
                ui.markdown(log)
