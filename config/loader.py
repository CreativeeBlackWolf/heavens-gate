from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import Config
from core.db.models import init_db
from core.watchdog.events import ConnectionEvents
from core.wg.wg_work import WGHub

PATH_TO_CONFIG = "config.conf"

cfg = Config(PATH_TO_CONFIG)
db_cfg = cfg.get_database_config()
bot_cfg = cfg.get_bot_config()
server_cfg = cfg.get_server_config()

bot_instance = Bot(
    token=bot_cfg.token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
bot_dispatcher = Dispatcher(storage=MemoryStorage())

db_instance = init_db(db_cfg.path)

connections_observer = ConnectionEvents(listen_timer=30, update_timer=30)

wghub = WGHub(server_cfg.path)
