import re
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from bot.utils.user_helper import get_client_by_id_or_ip


class ClientGettersMiddleware(BaseMiddleware):
    GETTERS_COMMANDS = [
        "ban", "anathem", # ban func
        "unban", "pardon", "mercy", # unban
        "whisper", # broadcast
        "get_user", # get_user
        "add_peer", # add_peer
    ]

    async def __call__(
            self,
            handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: dict[str, Any],
    ) -> Any:
        command: str = re.findall(r"\/(\w+)", event.text)[0]
        if command in self.GETTERS_COMMANDS:
            args = event.text.split()
            if len(args) <= 1:
                await event.answer("❌ Сообщение должно содержать IP-адрес пользователя или его Telegram ID.")
                return

            client, err = get_client_by_id_or_ip(args[1])
            if err:
                await event.answer(err)
                return

            data["client"] = client

        return await handler(event, data)
