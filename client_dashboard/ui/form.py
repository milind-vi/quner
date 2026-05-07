"""
Patient generation form (sliders + buttons) and the Restart-with-same-settings
launcher logic.
"""

from nicegui import ui

import utils as dashboard_utils
from . import state
from .notifications import _start_patient_generation_ui, _start_patient_launching_ui


def update_last_form_values(disease_difficulty, neuroticism, extraversion,
                            openness, agreeableness, conscientiousness):
    state.last_form_values = {
        "disease_difficulty": disease_difficulty,
        "neuroticism": neuroticism,
        "extraversion": extraversion,
        "openness": openness,
        "agreeableness": agreeableness,
        "conscientiousness": conscientiousness,
    }


def _set_last_launch_kind(kind: str, predefined_nr: int = None):
    state.last_launch_kind = kind
    if kind == "predefined":
        state.last_predefined_nr = predefined_nr


def _replay_last_launch():
    if state.last_launch_kind == "generated":
        v = state.last_form_values
        _start_patient_generation_ui()
        dashboard_utils.generate_patient(
            v["disease_difficulty"], v["neuroticism"], v["extraversion"],
            v["openness"], v["agreeableness"], v["conscientiousness"],
        )
    elif state.last_launch_kind == "predefined" and state.last_predefined_nr is not None:
        _start_patient_launching_ui()
        dashboard_utils.launch_predefined_patient(state.last_predefined_nr)


@ui.refreshable
def form(disabled: bool = True):
    from .sidebar import open_debug_dialog_button  # avoid cycle

    ui.markdown("### Disease parameters")
    with ui.element("div").classes("flex gap-20 w-full no-wrap"):
        with ui.element("div").classes("w-1/2"):
            ui.label("Disease difficulty")
            disease_difficulty = ui.slider(
                min=1, max=10, value=state.last_form_values["disease_difficulty"]
            ).props('label-always switch-label-side snap markers :markers="1,10" marker-labels')

    ui.markdown("### Patient personality parameters")
    with ui.element("div").classes("flex gap-20 w-full no-wrap pr-5"):
        with ui.element("div").classes("w-1/2"):
            ui.label("Neuroticism")
            neuroticism = ui.slider(
                min=0, max=5, value=state.last_form_values["neuroticism"]
            ).props('label-always switch-label-side snap markers :markers="0,5" marker-labels')
            ui.label("Extraversion").classes("mt-5")
            extraversion = ui.slider(
                min=0, max=5, value=state.last_form_values["extraversion"]
            ).props('label-always switch-label-side snap markers :markers="0,5" marker-labels')
            ui.label("Openness").classes("mt-5")
            openness = ui.slider(
                min=0, max=5, value=state.last_form_values["openness"]
            ).props('label-always switch-label-side snap markers :markers="0,5" marker-labels')
        with ui.element("div").classes("w-1/2"):
            ui.label("Agreeableness")
            agreeableness = ui.slider(
                min=0, max=5, value=state.last_form_values["agreeableness"]
            ).props('label-always switch-label-side snap markers :markers="0,5" marker-labels')
            ui.label("Conscientiousness").classes("mt-5")
            conscientiousness = ui.slider(
                min=0, max=5, value=state.last_form_values["conscientiousness"]
            ).props('label-always switch-label-side snap markers :markers="0,5" marker-labels')

    def _do_generate():
        update_last_form_values(disease_difficulty.value, neuroticism.value, extraversion.value,
                                openness.value, agreeableness.value, conscientiousness.value)
        _set_last_launch_kind("generated")
        _start_patient_generation_ui()
        dashboard_utils.generate_patient(
            disease_difficulty.value, neuroticism.value, extraversion.value,
            openness.value, agreeableness.value, conscientiousness.value,
        )

    def _do_predefined(nr):
        _set_last_launch_kind("predefined", predefined_nr=nr)
        _start_patient_launching_ui()
        dashboard_utils.launch_predefined_patient(nr)

    with ui.element("div").classes("flex flex-row gap-4 w-full flex-wrap"):
        with ui.element("div"):
            submit_button = ui.button("Generate patient", on_click=_do_generate).classes("mt-5")
        with ui.element("div"):
            open_debug_dialog_button(override=False, shown=False)
        with ui.element("div"):
            prefab = ui.dropdown_button("Launch predef. patient", auto_close=True, color="accent").classes("mt-5")
            with prefab:
                ui.item("Eleanor Vance, 68", on_click=lambda: _do_predefined(1))
                ui.item("Cassian Bellwether, 48", on_click=lambda: _do_predefined(2))
                ui.item("Marcus Williams, 34", on_click=lambda: _do_predefined(3))

        if state.last_launch_kind is not None:
            with ui.element("div"):
                if state.last_launch_kind == "generated":
                    label = "Restart (same sliders)"
                else:
                    label = f"Restart predef. #{state.last_predefined_nr}"
                restart_btn = ui.button(label, on_click=_replay_last_launch) \
                    .classes("mt-5").props("color=secondary outline")
                if disabled:
                    restart_btn.disable()

    if disabled:
        disease_difficulty.disable()
        neuroticism.disable()
        extraversion.disable()
        openness.disable()
        agreeableness.disable()
        conscientiousness.disable()
        submit_button.disable()
        prefab.disable()
