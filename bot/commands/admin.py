from aiogram.types import BotCommand, BotCommandScopeChat

from bot.commands.default import get_default_commands
from config.loader import bot_instance


def get_admin_commands() -> list[BotCommand]:
    commands = get_default_commands()

    commands.extend([
        BotCommand(command="/broadcast", description="Broadcast message to ALL registered users."),
        BotCommand(command="/whisper", description="Send message to a single user."),
        BotCommand(command="/ban", description="Block user by telegram ID or IP. Aliases: anathem"),
        BotCommand(command="/unban", description="Unblock user by telegram ID or IP. Aliases: pardon, mercy"),
        BotCommand(command="/get_user", description="Get user by telegram ID or IP. Keyboard included!"),
        BotCommand(command="/add_peer", description="Adds peer to DB and config file."),
        BotCommand(command="/disable_peer", description="Disables peer (wow)."),
        BotCommand(command="/enable_peer", description="Enables peer (wow).")
    ])

    return commands

async def set_admin_commands(user_id: int):
    """
    Sets commands menu for admin by user_id
    """
    await bot_instance.set_my_commands(get_admin_commands(), scope=BotCommandScopeChat(chat_id=user_id))
