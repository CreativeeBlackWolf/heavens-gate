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
                                    cancel_keyboard, extend_time_keyboard)
from bot.utils.callback_data import (ConnectionPeerCallbackData,
                                     PreviewMessageCallbackData,
                                     TimeExtenderCallbackData,
                                     UserActionsCallbackData, UserActionsEnum,
                                     YesOrNoEnum)
from bot.utils.states import (ContactAdminStates, ExtendTimeStates,
                              PreviewMessageStates, RenamePeerStates)
from bot.utils.user_helper import extend_users_usage_time, get_user_data_string
from config.loader import (bot_cfg, bot_instance, connections_observer,
                           interval_observer, wghub)
from core.db.db_works import Client, ClientFactory
from core.db.enums import ClientStatusChoices, PeerStatusChoices
from core.db.model_serializer import ConnectionPeer
from core.logs import bot_logger
from core.utils.date_utils import parse_time
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
    await state.clear()

    for peer in peers:
        if callback_data.peer_id == -1:
            media_group.add_document(
                media=BufferedInputFile(
                    file=bytes(get_peer_config_str(peer), encoding="utf-8"),
                    filename=f"{peer.peer_name or peer.id}_wg.conf"
                )
            )
        elif peer.id == callback_data.peer_id:
            media_group.add_document(
                BufferedInputFile(
                    file=bytes(get_peer_config_str(peer), encoding="utf-8"),
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

    msg = "🤫 <b>Сообщение от администрации</b>:\n\n" \
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
    UserActionsCallbackData.filter(F.action == UserActionsEnum.EXTEND_USAGE_TIME)
)
async def extend_usage_time_dialog_callback(callback: CallbackQuery, callback_data: UserActionsCallbackData):
    client = ClientFactory(tg_id=callback_data.user_id).get_client()
    keyboard = extend_time_keyboard(client.userdata.telegram_id)
    keyboard.inline_keyboard.append(cancel_keyboard().inline_keyboard[0])
    await callback.answer()
    await callback.message.answer("🕒 На сколько продлить время использования?", reply_markup=keyboard)

@router.callback_query(
    TimeExtenderCallbackData.filter(F.extend_for != "custom")
)
async def extend_usage_time_callback(callback: CallbackQuery, callback_data: TimeExtenderCallbackData):
    client = ClientFactory(tg_id=callback_data.user_id).get_client()
    time_to_add = parse_time(callback_data.extend_for)

    if not time_to_add:
        bot_logger.warning(f"Invalid time format, couldn't parse: {callback_data.extend_for}")
        await callback.answer(f"❌ Неправильный формат времени: {callback_data.extend_for}")
        return

    if extend_users_usage_time(client, time_to_add):
        await callback.answer(f"✅ Время использования продлено на {callback_data.extend_for}.")
    else:
        await callback.answer(f"❓ Что-то пошло не так во время операции. Проверь логи.")

@router.callback_query(
    TimeExtenderCallbackData.filter(F.extend_for == "custom")
)
async def extend_usage_time_custom(callback: CallbackQuery, callback_data: TimeExtenderCallbackData, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer(f"📅 Введи время, на которое ты хочешь продлить доступ в формате "
                                  "<code>число</code> + <code>(d -- дни, w -- недели, M -- месяцы, Y -- годы)</code>: ",
                                  reply_markup=cancel_keyboard())
    await state.set_data({"user_id": callback_data.user_id, "extend_for": callback_data.extend_for})
    await state.set_state(ExtendTimeStates.time_entering)

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.CONTACT_ADMIN)
)
async def contact_admin_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("✏️ Напиши сообщение, которое хочешь отправить администраторам"
                                  " (или <code>отмена</code>, если передумал):", reply_markup=cancel_keyboard())
    await state.set_state(ContactAdminStates.message_entering)

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

@router.message(ExtendTimeStates.time_entering)
async def extend_usage_time_custom_entered(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id, _ = data.values()

    await state.clear()

    time_to_add = parse_time(message.text)

    if not time_to_add:
        await message.answer(f"❌ Неправильный формат времени: {message.text}")
        return

    client = ClientFactory(tg_id=user_id).get_client()

    if extend_users_usage_time(client, time_to_add):
        await message.answer(f"✅ Время использования продлено на {message.text}.")
    else:
        await message.answer(f"❓ Что-то пошло не так во время операции. Проверь логи.")
