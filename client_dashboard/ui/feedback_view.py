"""
Feedback display widgets:
  - ``feedback`` : the inline "Immediate feedback" markdown panel under the chat
  - ``add_conversation_feedback_item`` / ``add_clinical_feedback_item``: rows
    inserted into the final-feedback dialog when MIRS / clinical results arrive.
"""

from nicegui import ui

from . import state


@ui.refreshable
def feedback(message: str = None):
    if message is None:
        ui.markdown("*Awaiting connection...*")
    else:
        ui.markdown(message)


def add_conversation_feedback_item(criterium, mark, i, feedback_message, evidence):
    def _color(score):
        return {
            1: "bg-red-700 text-white",
            2: "bg-red-500 text-white",
            3: "bg-yellow-500 text-white",
            4: "bg-green-500 text-white",
            5: "bg-green-700 text-white",
        }.get(score, "bg-gray-300 text-white")

    if state.dialog_conversation_feedback_content is None:
        return

    with state.dialog_conversation_feedback_content:
        with ui.item().props("dense"):
            with ui.element("div").classes("flex flex-row gap-4 no-wrap"):
                with ui.element("div").classes("basis-2/4 flex justify-center content-start gap-3 pt-2 pb-2"):
                    with ui.element("div").classes(
                        f"w-10 h-10 rounded-full inline-flex items-center justify-center {_color(mark)}"
                    ):
                        ui.label(f"{mark}")
                    ui.markdown(f"{i+1} -- **{criterium}**")
                with ui.element("div").classes("basis-2/4 pt-2 pb-2"):
                    ui.label(feedback_message).classes("text-justify")
                    if len(evidence) > 0:
                        for e in evidence:
                            ui.markdown(f"> {e}")


def add_clinical_feedback_item(fb):
    if state.dialog_clinical_feedback_content is None:
        return
    for entry in fb:
        with state.dialog_clinical_feedback_content:
            with ui.item().props("dense"):
                with ui.element("div").classes("flex flex-row gap-4 no-wrap"):
                    with ui.element("div").classes("basis-1/4 pt-2 pb-2"):
                        ui.markdown(f"**{entry['criterium']}**")
                    with ui.element("div").classes("basis-3/4 pt-2 pb-2"):
                        ui.label(entry["feedback"]).classes("text-justify")
