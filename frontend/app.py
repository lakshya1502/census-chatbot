import requests
import chainlit as cl
import uuid
import base64


BACKEND_URL = "http://backend:8000/chat"


@cl.on_chat_start
async def start():

    cl.user_session.set("session_id", str(uuid.uuid4()))

    await cl.Message(
        content="Lakshya Bot is ready."
    ).send()


@cl.on_message
async def main(message: cl.Message):

    try:
        response = requests.post(
            BACKEND_URL,
            json={
                "question": message.content,
                "session_id": cl.user_session.get("session_id")
            },
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        await cl.Message(
            content=f"Backend error: {exc}"
        ).send()
        return

    answer = data["answer"]
    sources = data.get("sources", [])
    sources_text = ", ".join(sources[:3])

    citations = data.get("citations", [])
    citation_text = "\n".join(
        f"[{c['id']}] {c['source']} p. {c['page']}"
        for c in citations[:3]
    )

    artifact = data.get("artifact") or {}

    final_response = f"""
{answer}

Sources:
{sources_text}

Citations:
{citation_text}
    """

    await cl.Message(
        content=final_response
    ).send()

    if artifact.get("image_base64"):
        image_bytes = base64.b64decode(artifact["image_base64"])
        await cl.Image(
            name=artifact.get("title", "chart"),
            content=image_bytes,
            display="inline"
        ).send()
    elif artifact.get("table_markdown"):
        await cl.Message(
            content=f"```markdown\n{artifact['table_markdown']}\n```"
        ).send()
