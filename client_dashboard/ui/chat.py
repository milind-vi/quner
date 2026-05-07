"""Chat scroll area, message bubbles, and the doctor input row (text + mic + hint + send)."""

import json

from nicegui import ui

import utils as dashboard_utils
from . import state


def messages():
    """
    The scrollable conversation log.

    Flexes to fill whatever vertical space is left in its parent column. The
    parent column must be ``display:flex; flex-direction:column`` with
    ``min-height:0`` set, otherwise the scroll area won't shrink correctly.
    """
    state.messages_scroll_container = ui.scroll_area() \
        .classes("w-full border border-slate-800 rounded flex-1") \
        .style("min-height:0; background:#0f172a")
    with state.messages_scroll_container:
        state.messages_container = ui.element("div").classes("flow-root w-full p-2")
        with state.messages_container:
            ui.markdown("*Awaiting connection...*")


def messages_scroll_to_bottom():
    if state.messages_scroll_container is not None:
        state.messages_scroll_container.scroll_to(percent=100)


def clear_messages():
    if state.messages_container is not None:
        state.messages_container.clear()


def add_patient_message(message, time):
    if state.message_skeleton is not None:
        state.message_skeleton.delete()
        state.message_skeleton = None

    with state.messages_container:
        ui.chat_message(
            message, name="Patient", stamp=time,
            avatar="https://robohash.org/ui",
        ).props("sent")
    messages_scroll_to_bottom()

    # If TTS is on (browser-side), speak the line.
    safe_text = json.dumps(message)
    try:
        ui.run_javascript(f"window.coworkSpeak && window.coworkSpeak({safe_text});")
    except Exception:
        pass


def add_doctor_message(message, time):
    with state.messages_container:
        ui.chat_message(
            message, name="Doctor", stamp=time,
            avatar="https://static.vecteezy.com/ti/gratis-vector/p3/8957222-mannelijke-dokter-avatar-beroep-clipart-pictogram-in-flat-design-vector.jpg",
        )
        state.message_skeleton = ui.skeleton().classes("w-96 float-right mr-4 mb-2").props("type=QInput")
    messages_scroll_to_bottom()


@ui.refreshable
def chat_input():
    """
    Doctor input row: text input + mic toggle + hint button + send.
    Below: TTS toggle, STT mode toggle, and a browser-voice picker.
    """
    enabled = dashboard_utils.is_patient_running

    def _send():
        text = (textbox.value or "").strip()
        if not text:
            return
        dashboard_utils.send_doctor_message(text)
        textbox.value = ""

    def _toggle_tts(e):
        state.tts_enabled = bool(e.value)
        ui.run_javascript(f"window.coworkTtsEnabled = {str(state.tts_enabled).lower()};")
        if not state.tts_enabled:
            ui.run_javascript("window.speechSynthesis && window.speechSynthesis.cancel();")

    def _toggle_auto_submit(e):
        state.auto_submit = bool(e.value)
        ui.run_javascript(
            f"window.coworkSetAutoSubmit && window.coworkSetAutoSubmit({str(state.auto_submit).lower()});"
        )

    def _toggle_mic():
        ui.run_javascript("window.coworkToggleMic && window.coworkToggleMic();")

    def _request_hint():
        dashboard_utils.request_hint()

    with ui.row().classes("w-full items-center gap-2 mt-2 shrink-0"):
        # Wrap the input in a div with an ID we control. NiceGUI/Quasar's q-input
        # doesn't reliably expose the inner native <input> via .props('id=...'),
        # so the STT JS targets this wrapper and queries for the inner input.
        with ui.element("div").props('id="cowork-chat-input-wrap"').classes("flex-1"):
            textbox = ui.input(placeholder="Type your message to the patient, or click the mic to speak…") \
                .props('outlined dense clearable') \
                .classes("w-full")
            textbox.on("keydown.enter", _send)
        mic_btn = ui.button(icon="mic", on_click=_toggle_mic) \
            .props('id="cowork-mic-btn" round flat color=primary') \
            .tooltip("Click to start/stop voice input")
        hint_btn = ui.button(icon="lightbulb", on_click=_request_hint) \
            .props("round flat color=warning") \
            .tooltip("Ask the critic agent for a hint about what to ask next")
        send_btn = ui.button("Send", on_click=_send) \
            .props('id="cowork-send-btn"') \
            .classes("h-10")
        if not enabled:
            textbox.disable()
            mic_btn.disable()
            hint_btn.disable()
            send_btn.disable()

    with ui.row().classes("w-full items-center gap-4 mt-1 flex-wrap shrink-0"):
        tts_switch = ui.switch("Speak responses", value=state.tts_enabled, on_change=_toggle_tts) \
            .tooltip("Read the patient's replies aloud using your browser's default voice.")
        auto_submit_switch = ui.switch("Auto-submit after speaking", value=state.auto_submit, on_change=_toggle_auto_submit) \
            .tooltip("When on, the message is sent automatically after the mic finishes hearing you.")
        if not enabled:
            tts_switch.disable()
            auto_submit_switch.disable()
