import datetime
import time
from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram.utils.media_group import MediaGroupBuilder

from bot.handlers.keyboards import (build_peer_configs_keyboard,
                                    build_user_actions_keyboard,
                                    cancel_keyboard)
from bot.utils.callback_data import (ConnectionPeerCallbackData,
                                     PreviewMessageCallbackData,
                                     UserActionsCallbackData, UserActionsEnum,
                                     YesOrNoEnum)
from bot.utils.message_utils import preview_message
from bot.utils.states import (ContactAdminStates, PreviewMessageStates,
                              RenamePeerStates, WhisperStates)
from bot.utils.user_helper import get_user_data_string
from config.loader import (bot_cfg, bot_instance, connections_observer,
                           interval_observer, server_cfg, wghub)
from core.db.db_works import Client, ClientFactory
from core.db.enums import ClientStatusChoices, PeerStatusChoices
from core.db.model_serializer import ConnectionPeer
from core.wg.wgconfig_helper import get_peer_config_str

router = Router(name="callbacks")

@connections_observer.timer_observer()
async def warn_user_timeout(client: Client, peer: ConnectionPeer, disconnect: bool):
    time_left = peer.peer_timer - datetime.datetime.now()
    delta_as_time = time.gmtime(time_left.total_seconds())
    await bot_instance.send_message(client.userdata.telegram_id,
        (f"⚠️ Подключение {peer.peer_name} будет разорвано через {delta_as_time.tm_min} минут. "
        if not disconnect else
        f"❗ Подключение {peer.peer_name} было разорвано из-за неактивности. ") +
        "Введи /unblock, чтобы обновить время действия подключения.")

@interval_observer.expire_date_warning_observer()
async def warn_user_expire_date(client: Client):
    await bot_instance.send_message(client.userdata.telegram_id,
        "⚠️ Твой аккаунт будет заблокирован через 24 часа из-за истечения оплаченного времени. "
        "Свяжись с администрацией для продления доступа."
    )

@interval_observer.expire_date_block_observer()
async def block_user_expire_date(client: Client):
    await bot_instance.send_message(client.userdata.telegram_id,
        "❌ Твой аккаунт заблокирован из-за истечения оплаченного времени. "
        "Если ты хочешь продлить доступ, свяжись с нами."
    )

@router.callback_query(F.data == "cancel_action")
async def cancel_action_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("❌ Действие отменено.")

@router.callback_query(ConnectionPeerCallbackData.filter(), default_state)
async def select_peer_callback(callback: CallbackQuery, callback_data: ConnectionPeerCallbackData, state: FSMContext):
    client = ClientFactory(tg_id=callback_data.user_id).get_client()
    peers = client.get_peers()
    media_group = MediaGroupBuilder()
    additional_interface_data = None
    await state.clear()

    if wghub.is_amnezia:
        additional_interface_data = {
            "Jc": peers[0].Jc,
            "Jmin": peers[0].Jmin,
            "Jmax": peers[0].Jmax,
            "Junk": server_cfg.junk
        }

    for peer in peers:
        if callback_data.peer_id == -1:
            media_group.add_document(
                media=BufferedInputFile(
                    file=bytes(get_peer_config_str(peer, additional_interface_data), encoding="utf-8"),
                    filename=f"{peer.peer_name or peer.id}_wg.conf"
                )
            )
        elif peer.id == callback_data.peer_id:
            media_group.add_document(
                BufferedInputFile(
                    file=bytes(get_peer_config_str(peer, additional_interface_data), encoding="utf-8"),
                    filename=f"{peer.peer_name or peer.id}_wg.conf"
                )
            )
            break

    await bot_instance.send_media_group(callback.from_user.id, media=media_group.build())
    await callback.message.delete()
    await callback.answer()

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.BAN_USER)
)
async def ban_user_callback(callback: CallbackQuery, callback_data: UserActionsCallbackData):
    client = ClientFactory(tg_id=callback_data.user_id).get_client()
    peers = client.get_peers()
    client.set_status(ClientStatusChoices.STATUS_ACCOUNT_BLOCKED)
    # if peer has no peers, it will raise KeyError, so we suppress it
    wghub.disable_peers(peers)
    for peer in peers:
        client.set_peer_status(peer.id, PeerStatusChoices.STATUS_BLOCKED)
    await callback.answer(f"✅ Пользователь {client.userdata.name} заблокирован.")
    await callback.message.edit_text(get_user_data_string(client))
    await callback.message.edit_reply_markup(reply_markup=build_user_actions_keyboard(client))

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.PARDON_USER)
)
async def pardon_user_callback(callback: CallbackQuery, callback_data: UserActionsCallbackData):
    client = ClientFactory(tg_id=callback_data.user_id).get_client()
    peers = client.get_peers()
    client.set_status(ClientStatusChoices.STATUS_CREATED)
    wghub.enable_peers(peers)
    for peer in peers:
        client.set_peer_status(peer.id, PeerStatusChoices.STATUS_DISCONNECTED)
    await callback.answer(f"✅ Пользователь {client.userdata.name} разблокирован.")
    await callback.message.edit_text(
        text=get_user_data_string(client),
        reply_markup=build_user_actions_keyboard(client)
    )

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.GET_CONFIGS)
)
async def get_user_configs_callback(callback: CallbackQuery, callback_data: UserActionsCallbackData):
    peers = ClientFactory(tg_id=callback_data.user_id).get_client().get_peers()

    await callback.answer()
    if peers:
        builder = build_peer_configs_keyboard(callback_data.user_id, peers)
        await callback.message.answer(
            text="Выбери конфиг, который ты хочешь получить из клавиатуры: ",
            reply_markup=builder
        )
    else:
        await callback.message.answer(
            text="❌ У этого пользователя нет доступных пиров."
        )

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.UPDATE_DATA)
)
async def update_user_message_data(callback: CallbackQuery, callback_data: UserActionsCallbackData):
    client = ClientFactory(tg_id=callback_data.user_id).get_client()
    await callback.answer(f"Данные пользователя {client.userdata.name} обновлены.")
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=get_user_data_string(client),
            reply_markup=build_user_actions_keyboard(client, is_admin=callback_data.is_admin)
        )

@router.callback_query(PreviewMessageCallbackData.filter(), PreviewMessageStates.preview)
async def preview_message_callback(callback: CallbackQuery, callback_data: PreviewMessageCallbackData, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    if callback_data.answer == YesOrNoEnum.ANSWER_NO:
        await callback.message.answer("❌ Отправка отменена")
        return

    # ? message_data = {message="<message_to_broadcast>", user_ids=[<telegram_ids>, ...]}
    message_data = await state.get_data()
    await state.clear()

    msg = "📨 <b>Сообщение от администрации</b>:\n\n" \
          if len(message_data["user_ids"]) <= 1 \
          else "✉️ <b>Рассылка от администрации</b>:\n\n"

    for tg_id in message_data["user_ids"]:
        await callback.bot.send_message(tg_id, msg + message_data["message"])

    await callback.message.answer("✅ Сообщение отправлено!")

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.CHANGE_PEER_NAME)
)
async def change_peer_name_callback(callback: CallbackQuery, callback_data: UserActionsCallbackData, state: FSMContext):
    client = ClientFactory(tg_id=callback.from_user.id).get_client()
    keyboard = build_peer_configs_keyboard(client.userdata.telegram_id, client.get_peers(), display_all=False)
    keyboard.inline_keyboard.append(cancel_keyboard().inline_keyboard[0])
    await callback.answer()
    await callback.message.answer(
        text="Выбери конфиг, который хочешь переименовать:",
        reply_markup=keyboard
    )
    await state.set_state(RenamePeerStates.peer_selection)

@router.callback_query(ConnectionPeerCallbackData.filter(), RenamePeerStates.peer_selection)
async def change_peer_name_entering_callback(callback: CallbackQuery, callback_data: ConnectionPeerCallbackData, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer("🔤 Введи новое имя для конфига (или <code>отмена</code>, если передумал):",
                                  reply_markup=cancel_keyboard())
    await state.set_state(RenamePeerStates.name_entering)
    await state.set_data({"tg_id": callback_data.user_id, "peer_id": callback_data.peer_id})

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.CONTACT_ADMIN)
)
async def contact_admin_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("✏️ Напиши сообщение, которое хочешь отправить администраторам"
                                  " (или <code>отмена</code>, если передумал):", reply_markup=cancel_keyboard())
    await state.set_state(ContactAdminStates.message_entering)

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.WHISPER_USER)
)
async def whisper_user_callback(callback: CallbackQuery, callback_data: UserActionsCallbackData, state: FSMContext):
    await callback.answer()
    await state.set_data({"user_id": callback_data.user_id})
    await state.set_state(WhisperStates.message_entering)
    await callback.message.answer("✏️ Введи сообщение:", reply_markup=cancel_keyboard())

# tecnically it is not a callback, but who cares...
# idk how to call this func properly, so yes
@router.message(RenamePeerStates.name_entering)
async def finally_change_peer_name(message: Message, state: FSMContext):
    new_name = message.text

    if new_name.lower() in ["отмена", "cancel"]:
        await state.clear()
        await message.answer("❌ Действие отменено.")
        return

    if len(new_name) >= 16:
        await message.answer("❌ Название конфига должно содержать меньше 16 символов!")
        await state.clear()
        return

    data = await state.get_data()
    user_id, peer_id = data.values()
    client = ClientFactory(tg_id=user_id).get_client()
    client.change_peer_name(peer_id, new_name)
    await state.clear()
    await message.answer("✅ Конфиг был успешно переименован!")

@router.message(ContactAdminStates.message_entering)
async def contact_admin(message: Message, state: FSMContext):
    await state.clear()
    if message.text.lower() in ["отмена", "cancel"]:
        await message.answer("❌ Действие отменено.")
        return

    for admin_id in bot_cfg.admins:
        await bot_instance.send_message(
            chat_id=admin_id,
            text=f"📩 Сообщение от пользователя {message.from_user.username} ({message.from_user.id}):\n\n{message.text}"
            f"\n\n🔗 Ответить на сообщение: <code>/whisper {message.from_user.id}</code>"
        )
    await message.answer("✅ Сообщение отправлено администраторам. Ожидай обратной связи.")

@router.message(WhisperStates.message_entering)
async def whisper_state(message: Message, state: FSMContext):
    user_id = (await state.get_data())["user_id"]
    if message.text.lower() in ["отмена", "cancel"]:
        await message.answer("❌ Действие отменено.")
        await state.clear()
        return

    await preview_message(message.text, message.from_user.id, state, [user_id])
