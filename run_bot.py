import argparse
import asyncio
import os
import random
import signal
import sys

from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.commands import (get_admin_commands, get_default_commands,
                          set_admin_commands, set_user_commands)
from bot.handlers import get_handlers_router
from config.loader import (bot_cfg, bot_dispatcher, bot_instance,
                           connections_observer, db_instance,
                           interval_observer, wghub)
from core.db.db_works import Client, ClientFactory
from core.db.model_serializer import ConnectionPeer
from core.logs import bot_logger


def graceful_shutdown(sig, frame):
    bot_logger.critical("Recieved SIGINT signal, shutting down...")
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
            name=message.chat.username
        )

    keyboard = None
    faq_str = ""
    if bot_cfg.faq_url is not None:
        faq_button = InlineKeyboardButton(text="FAQ", url=bot_cfg.faq_url)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[faq_button]])
        faq_str = "\nПрежде чем приступить к работе с ботом, ознакомься с FAQ, нажав на кнопку ниже." \

    msg = f"""👋 Привет!
{faq_str}
Если у тебя будут вопросы к администрации, воспользуйся командой /contact или кнопкой в меню /me.

Основные команды (также доступны в меню):
/help -- Получить помощь по командам
/me -- Отобразить информацию о себе
/config -- Получить конфиги для WireGuard
/contact -- Связаться с администрацией
/unblock -- Разблокировать/продлить доступ
/change_peer_name -- Изменить имя конфига (пира)

⚠️ На текущий момент бот находится в стадии разработки и тестирования, поэтому возможны недоработки, ошибки и прочее непонятное поведение. Если ты нашел какую-то ошибку, пожалуйста, сообщи об этом администрации бота."""
    await message.answer(text=msg, reply_markup=keyboard)

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
    bot_logger.info("Bot is running!")

@connections_observer.startup()
async def on_connections_observer_startup():
    bot_logger.info("Observer is running!")

@connections_observer.connected()
async def on_connected(client: Client, peer: ConnectionPeer):
    with bot_logger.contextualize(client=client, peer=peer):
        bot_logger.info("Client connected")

@connections_observer.disconnected()
async def on_disconnected(client: Client, peer: ConnectionPeer):
    with bot_logger.contextualize(client=client, peer=peer):
        bot_logger.info("Client disconnected")

async def main() -> None:
    bot_dispatcher.include_router(get_handlers_router())

    signal.signal(signal.SIGINT, graceful_shutdown)

    async with asyncio.TaskGroup() as group:
        group.create_task(connections_observer.listen_events())
        group.create_task(interval_observer.run_checkers())
        group.create_task(bot_dispatcher.start_polling(bot_instance, handle_signals=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="heavens-gate", description="Run bot with core service.")
    parser.add_argument("-awg", "--amnezia",
                        default=False,
                        help="Enable amnezia-wg functionality.",
                        action=argparse.BooleanOptionalAction)

    args = parser.parse_args()

    if args.amnezia:
        wghub.change_command_mode(is_amnezia=True)

    asyncio.run(main())
