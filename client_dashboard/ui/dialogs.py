"""Lazy modal dialogs (feedback, generation log, patient info)."""

from nicegui import ui

from . import state


def fresh_feedback_dialog():
    """(Re)build the final-feedback dialog: two tabs (MIRS communication + clinical)."""
    if state.dialog_dialog is None:
        state.dialog_dialog = ui.dialog().props("position=top")
    state.dialog_dialog.clear()

    with state.dialog_dialog:
        card = ui.card().classes("w-[1000px] h-[700px] !max-w-full")
        with card:
            with ui.row().classes("w-full"):
                ui.markdown("## Feedback")
                ui.space()
                ui.button("Close", on_click=state.dialog_dialog.close).classes("mt-5")
            with ui.tabs().classes("w-full") as tabs:
                conversation_tab = ui.tab("Feedback on conversation")
                clinical_tab = ui.tab("Feedback on clinical ability")
            with ui.tab_panels(tabs, value=conversation_tab):
                with ui.tab_panel(conversation_tab):
                    ui.markdown(
                        "This feedback uses the [MIRS]"
                        "(https://health.uconn.edu/principles-clinical-medicine-clinical-skills-assessment/master-interview-rating-scale-mirs/) "
                        "(master interview rating scale)."
                    )
                    state.dialog_conversation_feedback_content = ui.list().props("bordered separator")
                    with state.dialog_conversation_feedback_content:
                        with ui.item().classes("bg-slate-600"):
                            with ui.element("div").classes("flex flex-row w-full gap-5 flex-nowrap"):
                                with ui.element("div").classes("basis-2/4"):
                                    ui.item_label("Score out of 5 and criterium").props("header").classes("text-bold pl-0")
                                with ui.element("div").classes("basis-2/4"):
                                    ui.item_label("Feedback and evidence").props("header").classes("text-bold pl-0")
                with ui.tab_panel(clinical_tab):
                    state.dialog_clinical_feedback_content = ui.list().props("bordered separator")
                    with state.dialog_clinical_feedback_content:
                        with ui.item().classes("bg-slate-600"):
                            with ui.element("div").classes("flex flex-row w-full gap-5 flex-nowrap"):
                                with ui.element("div").classes("basis-1/4"):
                                    ui.item_label("Criterium").props("header").classes("text-bold pl-0")
                                with ui.element("div").classes("basis-3/4"):
                                    ui.item_label("Feedback").props("header").classes("text-bold pl-0")


def fresh_debug_dialog():
    """(Re)build the generation log dialog (raw prompts + LLM answers)."""
    if state.debug_dialog is None:
        state.debug_dialog = ui.dialog()
    state.debug_dialog.clear()

    with state.debug_dialog:
        card = ui.card().classes("w-[1000px] h-[700px] !max-w-full")
        with card:
            with ui.row().classes("w-full"):
                ui.markdown("## Generation log")
                ui.space()
                ui.button("Close", on_click=state.debug_dialog.close).classes("mt-5")
            scroll_area = ui.scroll_area().classes("w-full h-full")
            with scroll_area:
                state.debug_dialog_content = ui.list().props("separator")


def fresh_patient_dialog():
    """(Re)build the (legacy) patient-info dialog. Kept for backwards compat."""
    if state.patientinfo_dialog is None:
        state.patientinfo_dialog = ui.dialog()
    state.patientinfo_dialog.clear()

    with state.patientinfo_dialog:
        card = ui.card().classes("w-[1000px] h-[700px] !max-w-full")
        with card:
            with ui.row().classes("w-full"):
                ui.markdown("## Patient information")
                ui.space()
                ui.button("Close", on_click=state.patientinfo_dialog.close).classes("mt-5")
            scroll_area = ui.scroll_area().classes("w-full h-full")
            with scroll_area:
                state.patientinfo_content = ui.element("div")
