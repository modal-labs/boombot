from fastapi import Request, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import aiohttp
import json
import io
from pathlib import Path

from modal import Secret, asgi_app, Mount

from src.main import stub, Audiocraft

static_path = Path(__file__).parent / "frontend"


async def send_file(
    output: io.BytesIO,
    prompt: str,
    application_id: str,
    interaction_token: str,
    user_id: str,
    format: str,
    melody: io.BytesIO = None,
):
    interaction_url = (
        f"https://discord.com/api/v10/webhooks/{application_id}/{interaction_token}"
    )
    output_filename = f"output.{format}"
    melody_filename = f"original_melody.{format}" if melody else None

    if melody:
        json_payload = {
            "content": f"<@{user_id}> {prompt}",
            "tts": False,
            "attachments": [
                {"id": 0, "description": "Output file", "filename": output_filename},
                {
                    "id": 1,
                    "description": "Original Melody",
                    "filename": melody_filename,
                },
            ],
        }
    else:
        json_payload = {
            "content": f"<@{user_id}> {prompt}",
            "tts": False,
            "attachments": [
                {"id": 0, "description": "Output file", "filename": output_filename},
            ],
        }

    payload = aiohttp.FormData()
    payload.add_field(
        "payload_json", json.dumps(json_payload), content_type="application/json"
    )
    payload.add_field(
        "files[0]",
        output,
        filename=output_filename,
        content_type=f"audio/{format}",
    )
    if melody:
        payload.add_field(
            "files[1]",
            melody,
            filename=melody_filename,
            content_type=f"audio/{format}",
        )

    async with aiohttp.ClientSession() as session:
        async with session.post(interaction_url, data=payload) as resp:
            print(await resp.text())


async def send_error(
    application_id: str, interaction_token: str, error_message: str = ""
):
    interaction_url = f"https://discord.com/api/v10/webhooks/{application_id}/{interaction_token}/messages/@original"
    json_payload = {"content": error_message, "tts": False}
    async with aiohttp.ClientSession() as session:
        async with session.patch(interaction_url, json=json_payload) as resp:
            print(await resp.text())


@stub.function()
async def generate_audio(
    prompt: str,
    application_id: str,
    interaction_token: str,
    user_id: str,
    duration: int,
    format: str,
    melody_url: str,
):
    try:
        audiocraft = Audiocraft()
        melody_clip, clip = audiocraft.generate.call(
            prompt, duration=duration, format=format, melody_url=melody_url
        )
        await send_file(
            clip,
            prompt,
            application_id,
            interaction_token,
            user_id,
            format,
            melody=melody_clip,
        )
    except ValueError as e:
        error_message = "*Sorry, an error occured while generating your audio. Please check the format of your melody file.*"
        await send_error(application_id, interaction_token, error_message)
    except Exception as e:
        error_message = "*Sorry, an error occured while generating your audio. Please try again in a bit.*"
        await send_error(application_id, interaction_token, error_message)


@stub.function(
    mounts=[Mount.from_local_dir(static_path, remote_path="/assets")],
    secrets=[Secret.from_name("boombot-discord-secret")],
    keep_warm=1,
)
@asgi_app()
def app():
    import asyncio

    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/generate")
    async def generate_from_command(request: Request):
        from nacl.signing import VerifyKey
        from nacl.exceptions import BadSignatureError

        public_key = os.getenv("DISCORD_PUBLIC_KEY")
        verify_key = VerifyKey(bytes.fromhex(public_key))

        signature = request.headers.get("X-Signature-Ed25519")
        timestamp = request.headers.get("X-Signature-Timestamp")
        body = await request.body()

        message = timestamp.encode() + body
        try:
            verify_key.verify(message, bytes.fromhex(signature))
        except BadSignatureError:
            raise HTTPException(status_code=401, detail="Invalid request")

        data = json.loads(body.decode())
        if data.get("type") == 1:  # ack ping from Discord
            return {"type": 1}

        if data.get("type") == 2:  # triggered by slash command interaction
            duration = 10
            format = "wav"
            melody_url = ""

            options = data["data"]["options"]
            for option in options:
                name = option["name"]
                if name == "prompt":
                    prompt = option["value"]
                elif name == "duration":
                    duration = option["value"]
                elif name == "format":
                    format = option["value"]
            if "resolved" in data["data"]:
                for attachment in data["data"]["resolved"]["attachments"]:
                    melody_url = data["data"]["resolved"]["attachments"][
                        f"{attachment}"
                    ]["url"]

            app_id = data["application_id"]
            interaction_token = data["token"]
            user_id = data["member"]["user"]["id"]

            generate_audio.spawn(
                prompt, app_id, interaction_token, user_id, duration, format, melody_url
            )

            return {
                "type": 5,  # respond immediately with defer message
            }

        raise HTTPException(status_code=400, detail="Bad request")

    app.mount("/", StaticFiles(directory="/assets", html=True))

    return app
