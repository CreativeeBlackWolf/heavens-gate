import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message

from bot.handlers.keyboards import (build_peer_configs_keyboard,
                                    build_user_actions_keyboard,
                                    cancel_keyboard)
from bot.utils.states import ContactAdminStates, RenamePeerStates
from bot.utils.user_helper import get_user_data_string
from config.loader import core_cfg, server_cfg, wghub
from core.db.db_works import ClientFactory
from core.db.enums import PeerStatusChoices
from core.wg.wgconfig_helper import get_peer_config_str

router = Router(name="user")


@router.message(Command("me"))
async def me(message: Message):
    client = ClientFactory(tg_id=message.chat.id).get_client()

    await message.answer(
        get_user_data_string(client),
        reply_markup=build_user_actions_keyboard(client, is_admin=False)
    )

@router.message(Command("config"))
async def get_config(message: Message):
    client = ClientFactory(tg_id=message.from_user.id).get_client()
    peers = client.get_peers()
    additional_interface_data = None

    if not peers:
        await message.answer("❌ У тебя нет активных пиров.")
        return

    if len(peers) >= 2:
        keyboard = build_peer_configs_keyboard(message.from_user.id, peers)
        await message.answer(
            text="Выбери конфиг, который ты хочешь получить из клавиатуры: ",
            reply_markup=keyboard)
    else:
        if wghub.is_amnezia:
            additional_interface_data = {
                "Jc": peers[0].Jc,
                "Jmin": peers[0].Jmin,
                "Jmax": peers[0].Jmax,
                "Junk": server_cfg.junk
            }
        config = BufferedInputFile(
            file=bytes(get_peer_config_str(peers[0], additional_interface_data), encoding="utf-8"),
            filename=f"{peers[0].peer_name or peers[0].id}_wg.conf")
        await message.answer_document(config, caption="Вот твой конфиг. Не распространяй его куда попало.")

@router.message(Command("unblock"))
async def unblock_timeout_connections(message: Message):
    client = ClientFactory(tg_id=message.from_user.id).get_client()
    peers = client.get_peers()
    for peer in peers:
        if peer.peer_status != PeerStatusChoices.STATUS_TIME_EXPIRED:
            wghub.enable_peer(peer)
            client.set_peer_status(peer.id, PeerStatusChoices.STATUS_DISCONNECTED)
        elif peer.peer_status == PeerStatusChoices.STATUS_CONNECTED:
            new_time = datetime.datetime.now() + datetime.timedelta(hours=core_cfg.peer_active_time)
            client.set_peer_timer(peer.id, peer_timer=new_time)

    await message.answer("✅ Соединения были разблокированы/обновлены. Можешь продолжать пользоваться VPN!")

@router.message(Command("change_peer_name"))
async def change_peer_name(message: Message, state: FSMContext):
    client = ClientFactory(tg_id=message.from_user.id).get_client()
    keyboard = build_peer_configs_keyboard(client.userdata.telegram_id, client.get_peers(), display_all=False)
    keyboard.inline_keyboard.append(cancel_keyboard().inline_keyboard[0])
    await message.answer(
        text="Выбери конфиг, который хочешь переименовать:",
        reply_markup=keyboard
    )
    await state.set_state(RenamePeerStates.peer_selection)

@router.message(Command("contact"))
async def contact(message: Message, state: FSMContext):
    await message.answer("✏️ Напиши сообщение, которое хочешь отправить администраторам"
                         " (или <code>отмена</code>, если передумал):", reply_markup=cancel_keyboard())
    await state.set_state(ContactAdminStates.message_entering)
