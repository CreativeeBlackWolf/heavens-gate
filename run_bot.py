import asyncio
import os
import random
import signal
import sys

from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.commands import (get_admin_commands, get_default_commands,
                          set_admin_commands, set_user_commands)
from bot.handlers import get_handlers_router
from config.loader import (bot_cfg, bot_dispatcher, bot_instance,
                           connections_observer, db_instance)
from core.db.db_works import Client, ClientFactory
from core.db.model_serializer import ConnectionPeer


def graceful_shutdown(sig, frame):
    print("Shutdowning gracefully...")
    sys.exit(0)

@bot_dispatcher.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if message.chat.id in bot_cfg.admins:
        await set_admin_commands(message.chat.id)
    else:
        await set_user_commands(message.chat.id)

    with db_instance.atomic():
        # just in case.
        ClientFactory(tg_id=message.chat.id).get_or_create_client(
            name=message.chat.full_name # ? retrieving a @username will be a better option, maybe
        )

    await message.answer("Привет. Не знаю, как ты здесь оказался.")

@bot_dispatcher.message(Command("help"))
async def cmd_help(message: Message) -> None:
    text = "🛟 Помощь в командах:\n"
    default_commands = get_default_commands()
    for command in default_commands:
        text += f"{command.command} -> {command.description}\n"

    if message.chat.id in bot_cfg.admins:
        text += "\n\n🛠️ Список команд администратора:\n"
        for command in get_admin_commands()[len(default_commands)::]:
            text += f"{command.command} -> {command.description}\n"

    await message.answer(text)

@bot_dispatcher.startup()
async def on_startup(*args):
    if os.path.exists(".reboot"):
        with open(".reboot", encoding="utf-8") as f:
            chat_id = int(f.read())
            stickerset = await bot_instance.get_sticker_set("chunkytext")
            await bot_instance.send_sticker(chat_id, random.choice(stickerset.stickers).file_id)
            await bot_instance.send_message(chat_id, "Бот перезапущен.")
        os.remove(".reboot")
    print("Bot started!")

@connections_observer.startup()
async def on_connections_observer_startup():
    print("Observer started!")

@connections_observer.connected()
async def on_connected(client: Client, peer: ConnectionPeer):
    print(f"{client} connected, Peer: {peer}")

@connections_observer.disconnected()
async def on_disconnected(client: Client, peer: ConnectionPeer):
    print(f"{client} disconnected, Peer: {peer}")

async def main() -> None:
    bot_dispatcher.include_router(get_handlers_router())

    signal.signal(signal.SIGINT, graceful_shutdown)

    async with asyncio.TaskGroup() as group:
        group.create_task(connections_observer.listen_events())
        group.create_task(bot_dispatcher.start_polling(bot_instance, handle_signals=False))

if __name__ == "__main__":
    asyncio.run(main())
