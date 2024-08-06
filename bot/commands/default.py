from aiogram.types import BotCommandScopeChat, BotCommand
from config.loader import bot_instance


def get_default_commands() -> list[BotCommand]:
    commands = [
        BotCommand(command="/start", description="(re)Start the bot."),
        BotCommand(command="/help", description="Get list of commands and their definitions")
    ]

    return commands

async def set_user_commands(user_id: int):
    """Sets default commands for everyone."""
    await bot_instance.set_my_commands(get_default_commands(), BotCommandScopeChat(chat_id=user_id))