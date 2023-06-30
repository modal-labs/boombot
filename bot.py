from fastapi import Request, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread

import os
from main import stub, Audiocraft

from modal import Secret, asgi_app

import aiohttp
import json
import io


async def send_file_to_endpoint(
    file: io.BytesIO,
    prompt: str,
    application_id: str,
    interaction_token: str,
    user_id: str,
    format: str,
):
    interaction_url = (
        f"https://discord.com/api/v10/webhooks/{application_id}/{interaction_token}"
    )
    json_payload = {"content": f"<@{user_id}> {prompt}", "tts": False}

    payload = aiohttp.FormData()
    payload.add_field(
        "payload_json", json.dumps(json_payload), content_type="application/json"
    )
    payload.add_field(
        "file", file, filename=f"output.{format}", content_type=f"audio/{format}"
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(interaction_url, data=payload) as resp:
            print(await resp.text())


@stub.function(secrets=[Secret.from_name("boombot-discord-secret")], keep_warm=1)
@asgi_app()
def app():
    import asyncio

    fastapi_app = FastAPI()

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    async def generate_clip(
        prompt: str,
        application_id: str,
        interaction_token: str,
        user_id: str,
        duration: int,
        format: str,
    ):
        audiocraft = Audiocraft()
        clip = audiocraft.generate.call(prompt, duration=duration, format=format)
        await send_file_to_endpoint(
            clip, prompt, application_id, interaction_token, user_id, format
        )

    def generate_clip_wrapper(
        prompt: str,
        application_id: str,
        interaction_token: str,
        user_id: str,
        duration: int,
        format: str,
    ):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            generate_clip(
                prompt, application_id, interaction_token, user_id, duration, format
            )
        )
        loop.close()

    @fastapi_app.post("/")
    async def generate_from_command(request: Request):
        from nacl.signing import VerifyKey
        from nacl.exceptions import BadSignatureError

        public_key = os.getenv("DISCORD_PUBLIC_KEY")
        verify_key = VerifyKey(bytes.fromhex(public_key))

        signature = request.headers.get("X-Signature-Ed25519")
        timestamp = request.headers.get("X-Signature-Timestamp")
        body = await request.body()

        print(body)

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

            options = data["data"]["options"]
            for option in options:
                name = option["name"]
                if name == "prompt":
                    prompt = option["value"]
                elif name == "duration":
                    duration = option["value"]
                elif name == "format":
                    format = option["value"]
            app_id = data["application_id"]
            interaction_token = data["token"]
            user_id = data["member"]["user"]["id"]

            thread = Thread(
                target=generate_clip_wrapper,
                args=(
                    prompt,
                    app_id,
                    interaction_token,
                    user_id,
                    duration,
                    format,
                ),
            )
            thread.start()

            return {
                "type": 5,  # respond immediately with defer message
            }

        raise HTTPException(status_code=400, detail="Bad request")

    return fastapi_app
