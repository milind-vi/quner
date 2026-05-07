"""
Dashboard entry point.

Layout: viewport-locked (100vh, no page scroll).

  ┌────────────────────────────────────────────────────────────────┐
  │  [logo] Quner                                  [avatar status] │  ← header (fixed)
  ├──────────────────────────────────────────────┬─────────────────┤
  │  Conversation                                │  Scenario       │
  │  ┌────────────────────────────────┐          │  ┌───────────┐  │
  │  │                                │          │  │  sliders  │  │
  │  │  chat scroll (flex-1)          │          │  │  buttons  │  │
  │  │                                │          │  └───────────┘  │
  │  └────────────────────────────────┘          │                 │
  │  [input] [mic] [hint] [send]                 │  [view vignette]│
  │  Speak responses · Continuous mic · Voice    │                 │
  │  [Pause] [Feedback] [Resume]                 │                 │
  │                                              │                 │
  │  Immediate feedback                          │                 │
  │  ┌────────────────────────────────┐          │                 │
  │  │  ...                           │          │                 │
  │  └────────────────────────────────┘          │                 │
  └──────────────────────────────────────────────┴─────────────────┘

  + right-slide vignette drawer (off-screen until "View vignette" clicked)
"""

from nicegui import app, ui
from fastapi import Response
from fastapi.responses import PlainTextResponse

import utils
import ui_utils


@app.get("/conversation_id", response_class=PlainTextResponse)
def conversation_id(response: Response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return ui_utils.conversation_id


# ---------------------------------------------------------------------------
# Theme + viewport lock
# ---------------------------------------------------------------------------
ui.dark_mode().enable()
ui.colors(primary="#10b981", secondary="#6366f1", accent="#8b5cf6",
          positive="#10b981", negative="#ef4444", warning="#f59e0b", info="#3b82f6")

ui.query("html").style("overflow:hidden; height:100vh")
ui.query("body").style("overflow:hidden; height:100vh; background:#0b1120")
ui.query(".nicegui-content") \
    .classes("p-0") \
    .style("height:100vh; display:flex; flex-direction:column; overflow:hidden")


# ---------------------------------------------------------------------------
# Header (fixed)
# ---------------------------------------------------------------------------
with ui.row().classes(
    "w-full items-center justify-between px-8 py-3 border-b border-slate-800 shrink-0"
).style("background:#0f172a"):
    with ui.row().classes("items-center gap-3"):
        ui.icon("medical_services").classes("text-emerald-400 text-3xl")
        ui.label("Quner").classes("text-2xl font-semibold text-white")
    ui_utils.furhat_status()


# ---------------------------------------------------------------------------
# Body — flex row that fills the remaining viewport
# ---------------------------------------------------------------------------
with ui.row().classes(
    "w-full flex-1 px-6 pt-4 pb-4 gap-6 items-stretch"
).style("min-height:0; overflow:hidden"):

    # ------------------ LEFT: chat + feedback (flex column) ----------------
    with ui.column().classes("flex-1 min-w-0 gap-2 h-full") \
            .style("min-height:0; display:flex"):
        with ui.row().classes("w-full items-center shrink-0"):
            ui.icon("forum").classes("text-emerald-400 text-2xl")
            ui.label("Conversation").classes("text-lg font-semibold text-white")

        # Chat scroll fills remaining space.
        ui_utils.messages()

        # Input + speech controls + control buttons (all shrink-0 so they don't squeeze chat).
        ui_utils.chat_input()
        ui_utils.patient_control_buttons()

        # Immediate feedback — capped height so it never pushes anything off-screen.
        with ui.row().classes("w-full items-center mt-2 shrink-0"):
            ui.icon("psychology").classes("text-amber-400 text-2xl")
            ui.label("Immediate feedback").classes("text-base font-semibold text-white")
        with ui.card().classes(
            "w-full !bg-slate-900 border border-slate-800 shrink-0 p-3"
        ).style("max-height:130px; min-height:80px; overflow-y:auto"):
            ui_utils.feedback()

    # ------------------ RIGHT: scenario settings + vignette button ---------
    with ui.column().classes("w-[400px] shrink-0 gap-2 h-full") \
            .style("min-height:0; overflow-y:auto"):
        with ui.card().classes("w-full !bg-slate-900 border border-slate-800 p-4"):
            with ui.row().classes("w-full items-center mb-1"):
                ui.icon("tune").classes("text-indigo-400 text-2xl")
                ui.label("Scenario settings").classes("text-lg font-semibold text-white")
            ui_utils.form()
        ui_utils.vignette_panel()


# ---------------------------------------------------------------------------
# Right-slide vignette drawer (built once, opened on demand)
# ---------------------------------------------------------------------------
ui_utils.vignette_drawer()


# ---------------------------------------------------------------------------
# Startup hooks
# ---------------------------------------------------------------------------
app.on_startup(utils.consumer)
app.on_startup(ui_utils.fresh_feedback_dialog)
app.on_startup(ui_utils.fresh_debug_dialog)
app.on_startup(ui_utils.fresh_patient_dialog)
app.on_connect(ui_utils.messages_scroll_to_bottom)


# ---------------------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------------------
ui.add_css("""
pre {
    white-space: pre-wrap;
    white-space: -moz-pre-wrap;
    white-space: -pre-wrap;
    white-space: -o-pre-wrap;
    word-wrap: break-word;
}
#cowork-mic-btn.cowork-mic-active {
    background-color: #ef4444 !important;
    color: white !important;
    box-shadow: 0 0 0 6px rgba(239, 68, 68, .2);
}
.q-message-name { color: #94a3b8 !important; }
.q-message-stamp { color: #64748b !important; }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #475569; }
/* Quasar slider labels can overflow form column when the page is narrow. */
.q-slider__pin { z-index: 1; }
""")


# ---------------------------------------------------------------------------
# Browser-side speech I/O (STT + TTS + voice picker).
# ---------------------------------------------------------------------------
ui.add_body_html("""
<script>
(function() {
    window.coworkTtsEnabled = false;
    window.coworkAutoSubmit = false;
    let recognition = null;
    let listening = false;
    let userWantsListening = false;
    let userManuallyStopped = false;

    // TTS — system default voice. Gated on the "Speak responses" toggle.
    window.coworkSpeak = function(text) {
        if (!window.coworkTtsEnabled || !window.speechSynthesis) return;
        try {
            window.speechSynthesis.cancel();
            const utter = new SpeechSynthesisUtterance(text);
            utter.rate = 1.0;
            utter.pitch = 1.0;
            window.speechSynthesis.speak(utter);
        } catch (e) {
            console.warn('[Quner TTS] speak failed:', e);
        }
    };

    window.coworkSetAutoSubmit = function(enabled) {
        window.coworkAutoSubmit = !!enabled;
        console.log('[Quner STT] auto-submit set to', window.coworkAutoSubmit);
    };

    function clickSend() {
        const btn = document.getElementById('cowork-send-btn');
        if (!btn) {
            console.error('[Quner STT] Send button not found.');
            return;
        }
        btn.click();
    }

    function findChatInput() {
        // The chat input lives inside a wrapper div with id="cowork-chat-input-wrap".
        // The real native <input> is several Quasar layers deep, so we querySelector for it.
        const wrap = document.getElementById('cowork-chat-input-wrap');
        if (!wrap) {
            console.error('[Quner STT] Could not find #cowork-chat-input-wrap. Is the page fully loaded?');
            return null;
        }
        const real = wrap.querySelector('input');
        if (!real) {
            console.error('[Quner STT] Wrapper found but no <input> child element inside.');
            return null;
        }
        return real;
    }

    function setInputValue(value) {
        const real = findChatInput();
        if (!real) return;
        // Bypass React/Vue's value setter caching by going through the prototype setter.
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(real, value);
        // Fire both input and change so Quasar's v-model picks up the new value.
        real.dispatchEvent(new Event('input', { bubbles: true }));
        real.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function buildRecognition() {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) {
            alert("Your browser doesn't support speech recognition. Try Chrome, Edge, or Safari (Firefox does not support it).");
            console.error('[Quner STT] No SpeechRecognition API in this browser.');
            return null;
        }
        const r = new SR();
        r.continuous = false;        // push-to-talk only
        r.interimResults = true;
        r.lang = 'en-US';
        let finalTranscript = '';
        r.onresult = function(event) {
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript + ' ';
                } else {
                    interim += event.results[i][0].transcript;
                }
            }
            setInputValue((finalTranscript + interim).trim());
        };
        r.onstart = function() {
            listening = true;
            const btn = document.getElementById('cowork-mic-btn');
            if (btn) btn.classList.add('cowork-mic-active');
        };
        r.onend = function() {
            listening = false;
            const btn = document.getElementById('cowork-mic-btn');
            if (btn) btn.classList.remove('cowork-mic-active');
            // Auto-submit: only fire if the recognition ended on its own (user did
            // not click the mic to abort) and there's actually some text to send.
            const real = findChatInput();
            const hasText = real && real.value && real.value.trim().length > 0;
            console.log('[Quner STT] onend. autoSubmit=', window.coworkAutoSubmit,
                        'manualStop=', userManuallyStopped, 'hasText=', hasText);
            if (window.coworkAutoSubmit && !userManuallyStopped && hasText) {
                // Brief delay so the v-model has a chance to flush before clicking Send.
                setTimeout(clickSend, 150);
            }
            userManuallyStopped = false;
        };
        r.onerror = function(e) {
            console.error('[Quner STT] error:', e.error);
            if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
                userWantsListening = false;
                alert("Microphone permission denied. Allow it in your browser's site settings (the 🎤 icon in the address bar) and try again.");
            } else if (e.error === 'no-speech') {
                // Common; not worth alerting.
            } else if (e.error === 'audio-capture') {
                alert("No microphone detected. Check your system audio settings.");
            } else if (e.error === 'network') {
                alert("Speech recognition needs network access. Check your connection.");
            }
        };
        return r;
    }

    window.coworkToggleMic = function() {
        console.log('[Quner STT] mic toggle clicked. listening=', listening);
        if (listening && recognition) {
            // User clicked mic to abort — never auto-submit in this case.
            userManuallyStopped = true;
            userWantsListening = false;
            try { recognition.stop(); } catch (e) {}
            return;
        }
        // Sanity-check that the input the recognition will write to actually exists.
        if (!findChatInput()) {
            alert("Voice input is wired up but could not find the chat input box on the page. Open DevTools console for details.");
            return;
        }
        userWantsListening = true;
        userManuallyStopped = false;
        recognition = buildRecognition();
        if (recognition) {
            try {
                recognition.start();
                console.log('[Quner STT] recognition.start() called.');
            } catch (e) {
                console.error('[Quner STT] Could not start recognition:', e);
                alert("Voice input failed to start: " + e.message + ". Check browser microphone permission.");
            }
        }
    };
})();
</script>
""")

ui.run(port=8501, show=False)
