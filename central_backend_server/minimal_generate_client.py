#!/usr/bin/env python3
"""
Minimal WebSocket client: trigger patient/scenario generation only (no dashboard, no Furhat, no conversation).

Prerequisites:
  - central_backend_server running:  python ws_server.py
  - config.py with OPENAI_API_KEY (and other keys required at server import)

WebSocket contract (same as dashboard):
  1) First message after connect — required:
     {"action": "setRole", "role": "dashboard"}

  2a) LLM vignette generation + avatar selection:
     {
       "action": "generatePatient",
       "diseaseDifficulty": 5,
       "neuroticism": 2, "extraversion": 3, "openness": 2,
       "agreeableness": 3, "conscientiousness": 2
     }
     Personality fields are integers 0–5.

  2b) Predefined patient only (no LLM generation):
     {"action": "launchPredefinedPatient", "patient_nr": 1}
     patient_nr: 1, 2, or 3 (see predefined_patients.mapping).

Do NOT send getPatientResponse or stopAndGetFinalFeedback if you want to avoid VSP/critic.

Usage:
  python minimal_generate_client.py
  python minimal_generate_client.py --host localhost --port 8085 --difficulty 7
  python minimal_generate_client.py --predefined 2
  python minimal_generate_client.py --debug-only
"""
import argparse
import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("Install websockets: pip install websockets", file=sys.stderr)
    sys.exit(1)


DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8085


def build_generate_payload(args):
    return {
        "action": "generatePatient",
        "diseaseDifficulty": args.difficulty,
        "neuroticism": args.neuroticism,
        "extraversion": args.extraversion,
        "openness": args.openness,
        "agreeableness": args.agreeableness,
        "conscientiousness": args.conscientiousness,
    }


async def run_client(uri, payload_predefined, payload_generate, debug_only):
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"action": "setRole", "role": "dashboard"}))

        if payload_predefined is not None:
            await ws.send(json.dumps(payload_predefined))
        else:
            await ws.send(json.dumps(payload_generate))

        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=600)
            except asyncio.TimeoutError:
                print("Timeout waiting for messages.", file=sys.stderr)
                break
            except websockets.exceptions.ConnectionClosed:
                break

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                print(raw)
                continue

            action = data.get("action", "")

            if debug_only and action != "updateDebugLog":
                if action == "generationStop":
                    print(json.dumps(data, indent=2))
                continue

            print(json.dumps(data, indent=2))
            if action == "generationStop" and data.get("state") == "error":
                break
            if action == "generationStop" and data.get("state") in ("success", "warning"):
                break


def main():
    p = argparse.ArgumentParser(description="Minimal WS client for generatePatient / launchPredefinedPatient")
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--predefined", type=int, metavar="N", help="Use launchPredefinedPatient with patient_nr N (1–3)")
    p.add_argument("--difficulty", type=int, default=5, help="diseaseDifficulty for generatePatient")
    for name in ("neuroticism", "extraversion", "openness", "agreeableness", "conscientiousness"):
        p.add_argument(f"--{name}", type=int, default=2, metavar="0-5")
    p.add_argument("--debug-only", action="store_true", help="Print only updateDebugLog and final generationStop")
    args = p.parse_args()

    uri = f"ws://{args.host}:{args.port}/"

    if args.predefined is not None:
        payload_predefined = {"action": "launchPredefinedPatient", "patient_nr": args.predefined}
        payload_generate = None
    else:
        payload_predefined = None
        payload_generate = build_generate_payload(args)

    asyncio.run(run_client(uri, payload_predefined, payload_generate, args.debug_only))


if __name__ == "__main__":
    main()
