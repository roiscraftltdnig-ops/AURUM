from typing import Any
import httpx
from app.core.config import get_settings


class TelegramService:
    def __init__(self) -> None:
        settings = get_settings()
        self.token = settings.telegram_bot_token
        self.api = f"https://api.telegram.org/bot{self.token}" if self.token else ""

    async def send_message(
        self,
        chat_id: str | int,
        text: str,
        buttons: list[list[dict[str, str]]] | None = None,
        parse_mode: str | None = None,
    ) -> None:
        if not self.api:
            return
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{self.api}/sendMessage", json=payload)
            response.raise_for_status()

    async def send_document_bytes(
        self,
        chat_id: str | int,
        filename: str,
        content: bytes,
        caption: str | None = None,
    ) -> None:
        if not self.api:
            return
        data: dict[str, Any] = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = caption[:1024]
        files = {"document": (filename, content, "application/pdf")}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{self.api}/sendDocument", data=data, files=files)
            response.raise_for_status()

    async def get_file_path(self, file_id: str) -> str | None:
        if not self.api:
            return None
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{self.api}/getFile", json={"file_id": file_id})
            response.raise_for_status()
            payload = response.json()
            return payload.get("result", {}).get("file_path")

    async def download_file_bytes(self, file_id: str) -> bytes | None:
        if not self.api or not self.token:
            return None
        file_path = await self.get_file_path(file_id)
        if not file_path:
            return None
        url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    async def answer_callback(self, callback_query_id: str, text: str = "") -> None:
        if not self.api:
            return
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(f"{self.api}/answerCallbackQuery", json={"callback_query_id": callback_query_id, "text": text})
                response.raise_for_status()
        except Exception:
            return

    async def set_webhook(self, url: str, secret: str) -> dict[str, Any]:
        if not self.api:
            return {"ok": False, "description": "Missing TELEGRAM_BOT_TOKEN"}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{self.api}/setWebhook", json={"url": url, "secret_token": secret, "allowed_updates": ["message", "callback_query"]})
            response.raise_for_status()
            return response.json()


telegram = TelegramService()
