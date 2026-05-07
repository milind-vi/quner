"""
Module-level mutable state for the dashboard.

Other ui submodules read/write via ``from ui import state`` then ``state.foo``
or ``state.foo = ...``. This avoids the original ``global`` keyword sprinkled
across every function and keeps state in one place.
"""

from nicegui.elements.chat_message import ChatMessage  # noqa: F401
from nicegui.elements.dialog import Dialog
from nicegui.elements.notification import Notification
from nicegui.element import Element

# --- Notifications -----------------------------------------------------------
generation_progress_notification: Notification = None
server_connection_notification: Notification = None
furhat_connection_notification: Notification = None

# --- Conversation log --------------------------------------------------------
messages_container: Element = None
messages_scroll_container: Element = None
message_skeleton = None  # ChatMessage placeholder while waiting for patient reply

# --- Form values + launch tracking ------------------------------------------
last_form_values = {
    "disease_difficulty": 6,
    "neuroticism": 1,
    "extraversion": 4,
    "openness": 4,
    "agreeableness": 4,
    "conscientiousness": 4,
}
# "generated" or "predefined" — None until the first patient is launched.
last_launch_kind: str = None
last_predefined_nr: int = None

# --- Side panel + dialog visibility flags ------------------------------------
open_debug_dialog_button_shown: bool = False
open_patient_information_button_shown: bool = False
full_vignette_text: str = ""

# --- Conversation identity ---------------------------------------------------
conversation_id: str = None

# --- Lazy dialogs (created inside the page context, NiceGUI 2.x rule) -------
dialog_dialog: Dialog = None
dialog_conversation_feedback_content = None
dialog_clinical_feedback_content = None
debug_dialog: Dialog = None
debug_dialog_content = None
patientinfo_dialog: Dialog = None
patientinfo_content = None
vignette_drawer_dialog: Dialog = None
vignette_drawer_content: Element = None

# --- Speech I/O state (mirrors browser-side flags) --------------------------
# TTS uses the system default voice; the user can toggle it on/off via the switch.
tts_enabled: bool = False
auto_submit: bool = False  # When True, the chat input auto-sends after speech ends.
