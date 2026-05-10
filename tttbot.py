import asyncio
import logging
import random
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LabeledPrice,
    PreCheckoutQuery
)

# =====================================================
# CONFIG & INIT
# =====================================================

BOT_TOKEN = "8711862372:AAFLEeTFCFnXhsfhNc8PoDLEdrH_IogEKRc"

logging.basicConfig(level=logging.INFO)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
DB_NAME = "hakka_ttt.db"

# =====================================================
# PREMIUM EMOJI IDS
# =====================================================

EMOJI_HELLO = "5391006515731659274"
EMOJI_TROPHY = "5296450392643637863"
EMOJI_FIRST = "5805168154795578731"
EMOJI_STREAK = "5807501163850896476"
EMOJI_NOTTT = "5875285875314661639"
EMOJI_ERROR = "5463099040738600646"

EMOJI_X = "5348204890294350245"
EMOJI_O = "5348219901205048470"
EMOJI_EMPTY = "5465665476971471368"
EMOJI_BOT = "5397903838072033194"

EMOJI_RANK_STUDENT = "5391052390277348873"
EMOJI_RANK_EXPERIENCED = "5271929616896921139"
EMOJI_RANK_TEACHER = "5391023167319864522"
EMOJI_RANK_AI = "5951908499897193729"

EMOJI_TOP_1 = "5807717621612681091"
EMOJI_RICHEST = "5875257992386975465"
EMOJI_MOST_ACTIVE = "5875220484437579406"
EMOJI_ADMIN = "5807566301324907861"
EMOJI_OWNER = "5156877291397055163"  # Уникальный эмодзи Владельца
EMOJI_PREMIUM = "5805357434004313847"

EMOJI_BUCKS = "5251664488020604222"
EMOJI_PREMIUM_INFO = "5807587398204265606"
EMOJI_EVENT = "5366039913789672142"
EMOJI_PROMO_SUCCESS = "5463305474046715532"
EMOJI_SEP = "5467751241939429038"

# =====================================================
# ADMINS CONFIG
# =====================================================

ADMINS = {
    7652697216: {"title": "Админ", "emoji": EMOJI_ADMIN, "fallback": "👨‍💻"},
    6625239442: {"title": "Владелец", "emoji": EMOJI_OWNER, "fallback": "👑"}
}

# =====================================================
# IN-MEMORY STATES (Temporary)
# =====================================================

games = {}
admin_states = {}

# =====================================================
# DATABASE SETUP & HELPERS
# =====================================================

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT,
            wins INTEGER DEFAULT 0,
            loses INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            bucks REAL DEFAULT 0.0,
            premium INTEGER DEFAULT 0,
            disabled_duels INTEGER DEFAULT 0,
            active_hours INTEGER DEFAULT 0
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            type TEXT,
            val INTEGER,
            uses INTEGER
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS promo_used (
            code TEXT,
            user_id INTEGER,
            PRIMARY KEY (code, user_id)
        )''')
        await db.commit()

async def get_profile(user_id: int, name: str, username: str):
    """Получает профиль из БД или создает новый."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                active_hours = random.randint(1, 10)
                await db.execute(
                    "INSERT INTO users (user_id, name, username, active_hours) VALUES (?, ?, ?, ?)",
                    (user_id, name, username, active_hours)
                )
                await db.commit()
                # Возвращаем дефолтные данные в виде словаря
                return {
                    "user_id": user_id, "name": name, "username": username,
                    "wins": 0, "loses": 0, "streak": 0, "bucks": 0.0,
                    "premium": 0, "disabled_duels": 0, "active_hours": active_hours
                }
            return dict(row)

async def update_user_field(user_id: int, field: str, value):
    """Обновляет одно поле пользователя."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()

def e(emoji_id, fallback="🙂"):
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

def get_separator():
    return (e(EMOJI_SEP, "⭐️") * 8)

def get_rank_info(wins):
    if wins >= 5000: return f"{e(EMOJI_RANK_AI)} Искусственный Интеллект"
    elif wins >= 1000: return f"{e(EMOJI_RANK_TEACHER)} Учитель"
    elif wins >= 250: return f"{e(EMOJI_RANK_EXPERIENCED)} Опытный"
    else: return f"{e(EMOJI_RANK_STUDENT)} Ученик"

# =====================================================
# GAME LOGIC
# =====================================================

def check_winner(board):
    wins = [
        [0,1,2], [3,4,5], [6,7,8], [0,3,6], [1,4,7], [2,5,8], [0,4,8], [2,4,6]
    ]
    for a,b,c in wins:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    if all(board): return "draw"
    return None

def get_bot_move(board, difficulty):
    empty_cells = [i for i, v in enumerate(board) if v is None]
    if not empty_cells: return None
    if difficulty == "bot_easy": return random.choice(empty_cells)

    def find_move(player):
        wins = [[0,1,2], [3,4,5], [6,7,8], [0,3,6], [1,4,7], [2,5,8], [0,4,8], [2,4,6]]
        for a, b, c in wins:
            line = [board[a], board[b], board[c]]
            if line.count(player) == 2 and line.count(None) == 1:
                if board[a] is None: return a
                if board[b] is None: return b
                if board[c] is None: return c
        return None

    win_move = find_move("O")
    if win_move is not None: return win_move
    block_move = find_move("X")
    if block_move is not None: return block_move
    if difficulty == "bot_medium": return random.choice(empty_cells)

    if board[4] is None: return 4
    corners = [x for x in [0, 2, 6, 8] if board[x] is None]
    if corners: return random.choice(corners)
    return random.choice(empty_cells)

def button(value, index, game_id):
    if value == "X": return InlineKeyboardButton(text="ㅤ", callback_data="ignore", icon_custom_emoji_id=EMOJI_X)
    if value == "O": return InlineKeyboardButton(text="ㅤ", callback_data="ignore", icon_custom_emoji_id=EMOJI_O)
    return InlineKeyboardButton(text="ㅤ", callback_data=f"move:{game_id}:{index}", icon_custom_emoji_id=EMOJI_EMPTY)

def game_keyboard(board, game_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [button(board[0], 0, game_id), button(board[1], 1, game_id), button(board[2], 2, game_id)],
            [button(board[3], 3, game_id), button(board[4], 4, game_id), button(board[5], 5, game_id)],
            [button(board[6], 6, game_id), button(board[7], 7, game_id), button(board[8], 8, game_id)]
        ]
    )

# =====================================================
# COMMANDS
# =====================================================

@dp.message(CommandStart())
async def start(message: Message):
    await get_profile(message.from_user.id, message.from_user.first_name, message.from_user.username)
    text = (
        f"<blockquote>{e(EMOJI_HELLO)} Добро пожаловать в Hakka TTT!</blockquote>\n\n"
        "/ttt — дуэль\n"
        "/tttbot — игра с ботом\n"
        "/tops — топ игроков\n"
        "/me — профиль\n"
        "/nottt — отключить дуэли\n"
        "/premium — купить Premium\n"
        "/promo [код] — активировать промокод\n\n"
        "<i>Используйте команды меню для управления.</i>"
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("me"))
async def me(message: Message):
    profile = await get_profile(message.from_user.id, message.from_user.first_name, message.from_user.username)
    user_id = message.from_user.id
    
    status_tags = []
    # Проверка на наличие юзера в списке администраторов
    if user_id in ADMINS: 
        admin_info = ADMINS[user_id]
        status_tags.append(f"{e(admin_info['emoji'], admin_info['fallback'])} {admin_info['title']}")
        
    if profile.get("premium"): 
        status_tags.append(f"{e(EMOJI_PREMIUM)} Premium")
        
    status_str = f" | {' | '.join(status_tags)}" if status_tags else ""
    rank_str = get_rank_info(profile["wins"])
    sep = get_separator()
    
    text = (
        f"{sep}\n"
        f"<b>Профиль Игрока</b>\n"
        f"{sep}\n\n"
        f"👤 <b>{profile['name']}</b>{status_str}\n"
        f"🎖 <b>Ранг:</b> {rank_str}\n\n"
        f"{e(EMOJI_TROPHY)} Побед: {profile['wins']}\n"
        f"❌ Поражений: {profile['loses']}\n"
        f"{e(EMOJI_STREAK)} Серия: {profile['streak']}\n"
        f"{e(EMOJI_BUCKS)} Hakka Bucks: {round(profile['bucks'], 2)}\n\n"
        f"{sep}"
    )

    photos = await bot.get_user_profile_photos(user_id)
    if photos.total_count > 0:
        await message.answer_photo(photo=photos.photos[0][-1].file_id, caption=text, parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")

@dp.message(Command("tops"))
async def tops(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        # Получаем топ 10
        async with db.execute("SELECT * FROM users ORDER BY wins DESC LIMIT 10") as cursor:
            top_users = await cursor.fetchall()
            
        if not top_users:
            return await message.answer("Топ пока пуст.")

        # Получаем самого богатого и самого активного для значков
        async with db.execute("SELECT user_id FROM users ORDER BY bucks DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            richest_id = row["user_id"] if row else None
            
        async with db.execute("SELECT user_id FROM users ORDER BY active_hours DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            active_id = row["user_id"] if row else None

    text = f"{e(EMOJI_TROPHY)} <b>Топ игроков</b>\n{get_separator()}\n\n"

    for place, profile in enumerate(top_users, start=1):
        uid = profile["user_id"]
        tag = ""
        if place == 1: tag = e(EMOJI_TOP_1)
        elif uid == richest_id: tag = e(EMOJI_RICHEST)
        elif uid == active_id: tag = e(EMOJI_MOST_ACTIVE)
            
        tag_str = f"{tag} " if tag else ""
        text += f"<b>{place}.</b> {tag_str}{profile['name']} — {profile['wins']} побед\n"

    await message.answer(text, parse_mode="HTML")

@dp.message(Command("nottt"))
async def nottt(message: Message):
    profile = await get_profile(message.from_user.id, message.from_user.first_name, message.from_user.username)
    new_status = 0 if profile["disabled_duels"] else 1
    await update_user_field(message.from_user.id, "disabled_duels", new_status)
    
    if new_status == 0:
        text = f"{e(EMOJI_NOTTT)} Вы снова можете получать дуэли."
    else:
        text = (
            f"{e(EMOJI_NOTTT)} Вы отключили предложения на дуэли "
            "в Крестики и Нолики!\n\n"
            "Введите эту команду ещё раз чтобы включить их."
        )
    await message.answer(text, parse_mode="HTML")

# =====================================================
# BOT GAME INITIALIZATION
# =====================================================

@dp.message(Command("tttbot"))
async def tttbot(message: Message):
    text = f"{e(EMOJI_BOT)} <b>Выберите сложность</b>"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Easy", callback_data="bot_easy")],
            [InlineKeyboardButton(text="Medium", callback_data="bot_medium")],
            [InlineKeyboardButton(text="Hard", callback_data="bot_hard")]
        ]
    )
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data.in_(["bot_easy", "bot_medium", "bot_hard"]))
async def start_bot_game(callback: CallbackQuery):
    game_id = random.randint(100000, 999999)
    games[game_id] = {
        "board": [None] * 9,
        "turn": "X",
        "x_player": callback.from_user.id,
        "o_player": callback.data,
        "ended": False,
        "is_bot": True
    }
    
    text = "🤖 <b>Игра с ботом началась!</b>\n\nТвой ход: X"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=game_keyboard(games[game_id]["board"], game_id))
    await callback.answer()

# =====================================================
# TTT DUEL
# =====================================================

@dp.message(Command("ttt"))
async def ttt(message: Message):
    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    args = message.text.split()
    
    if len(args) > 1:
        username = args[1].replace("@", "")
        target = {"username": username, "id": username}

    if not target:
        return await message.answer(
            f"{e(EMOJI_ERROR)} Вы не ответили на сообщение Игрока! Или не ввели его @username.",
            parse_mode="HTML"
        )

    game_id = random.randint(100000, 999999)
    games[game_id] = {
        "board": [None] * 9,
        "turn": "X",
        "x_player": message.from_user.id,
        "o_player": target.id if hasattr(target, "id") else target["id"],
        "ended": False,
        "is_bot": False
    }

    text = f"🎮 Дуэль началась!\n\nХод: X"
    await message.answer(text, reply_markup=game_keyboard(games[game_id]["board"], game_id))

# =====================================================
# PREMIUM PAYMENT (Telegram Stars)
# =====================================================

@dp.message(Command("premium"))
async def buy_premium(message: Message):
    await get_profile(message.from_user.id, message.from_user.first_name, message.from_user.username)
    text = (
        f"<blockquote>{e(EMOJI_PREMIUM_INFO)} <b>PREMIUM СТАТУС</b>\n\n"
        f"Стоимость: 95 Telegram Stars ⭐️\n"
        f"• Выделяющийся значок {e(EMOJI_PREMIUM)} в профиле\n"
        f"• Бонус +2.5% к выигрышу Hakka Bucks {e(EMOJI_BUCKS)}</blockquote>"
    )
    
    prices = [LabeledPrice(label="Premium Hakka TTT", amount=95)]
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="Premium Status",
        description="Покупка Premium статуса",
        payload="premium_purchase",
        provider_token="", 
        currency="XTR",
        prices=prices,
        reply_to_message_id=message.message_id
    )
    await message.answer(text, parse_mode="HTML")

@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: Message):
    await update_user_field(message.from_user.id, "premium", 1)
    await message.answer(
        f"<blockquote>{e(EMOJI_PREMIUM_INFO)} Вы успешно приобрели Premium статус!</blockquote>",
        parse_mode="HTML"
    )

# =====================================================
# ADMIN & PROMOCODES
# =====================================================

@dp.message(Command("adminhelp"))
async def admin_help(message: Message):
    if message.from_user.id not in ADMINS: return
    
    admin_info = ADMINS[message.from_user.id]
    text = (
        f"{e(admin_info['emoji'], admin_info['fallback'])} <b>Панель Администратора</b>\n"
        f"{get_separator()}\n"
        "/createpromo — создать промокод\n"
        "/event [текст] — запустить ивент\n"
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("createpromo"))
async def create_promo_start(message: Message):
    if message.from_user.id not in ADMINS: return
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Premium", callback_data="promo_type:premium")],
            [InlineKeyboardButton(text="💰 Hakka Bucks", callback_data="promo_type:bucks")],
            [InlineKeyboardButton(text="🏆 Победы", callback_data="promo_type:wins")]
        ]
    )
    await message.answer("Выберите тип промокода:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("promo_type:"))
async def promo_type_selected(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in ADMINS: return await callback.answer("Нет прав!")
    
    p_type = callback.data.split(":")[1]
    admin_states[user_id] = {"action": "promo_val", "type": p_type}
    
    msg = "Введите кол-во дней премиума (0 для вечного):" if p_type == "premium" else ("Введите кол-во Hakka Bucks:" if p_type == "bucks" else "Введите кол-во побед:")
    await callback.message.edit_text(msg)

@dp.message(lambda msg: msg.from_user.id in ADMINS and admin_states.get(msg.from_user.id, {}).get("action") in ["promo_val", "promo_uses", "promo_code"])
async def promo_wizard(message: Message):
    user_id = message.from_user.id
    state = admin_states[user_id]
    
    if state["action"] == "promo_val":
        state["val"] = int(message.text)
        state["action"] = "promo_uses"
        await message.answer("Введите лимит активаций:")
    elif state["action"] == "promo_uses":
        state["uses"] = int(message.text)
        state["action"] = "promo_code"
        await message.answer("Отправьте название промокода (напр. HAKKA2026):")
    elif state["action"] == "promo_code":
        code = message.text.upper()
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("INSERT OR REPLACE INTO promocodes (code, type, val, uses) VALUES (?, ?, ?, ?)",
                             (code, state["type"], state["val"], state["uses"]))
            await db.commit()
        del admin_states[user_id]
        await message.answer(f"✅ Промокод <b>{code}</b> успешно создан!", parse_mode="HTML")

@dp.message(Command("promo"))
async def activate_promo(message: Message):
    args = message.text.split()
    if len(args) < 2: return await message.answer("Использование: /promo [КОД]")
        
    code = args[1].upper()
    user_id = message.from_user.id
    
    # Создаем юзера если нет
    profile = await get_profile(user_id, message.from_user.first_name, message.from_user.username)
    
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        
        async with db.execute("SELECT * FROM promocodes WHERE code = ?", (code,)) as cursor:
            promo = await cursor.fetchone()
        
        if not promo:
            return await message.answer(f"{e(EMOJI_ERROR)} Промокод не найден.", parse_mode="HTML")
            
        async with db.execute("SELECT COUNT(*) FROM promo_used WHERE code = ?", (code,)) as cursor:
            used_count = (await cursor.fetchone())[0]
            
        if promo["uses"] <= used_count:
            return await message.answer(f"{e(EMOJI_ERROR)} Лимит активаций исчерпан.", parse_mode="HTML")
            
        async with db.execute("SELECT 1 FROM promo_used WHERE code = ? AND user_id = ?", (code, user_id)) as cursor:
            if await cursor.fetchone():
                return await message.answer(f"{e(EMOJI_ERROR)} Вы уже активировали этот код.", parse_mode="HTML")
                
        # Активация
        await db.execute("INSERT INTO promo_used (code, user_id) VALUES (?, ?)", (code, user_id))
        
        if promo["type"] == "premium":
            await db.execute("UPDATE users SET premium = 1 WHERE user_id = ?", (user_id,))
            desc = "Premium статус"
        elif promo["type"] == "bucks":
            await db.execute("UPDATE users SET bucks = bucks + ? WHERE user_id = ?", (promo["val"], user_id))
            desc = f'{promo["val"]} Hakka Bucks'
        else:
            await db.execute("UPDATE users SET wins = wins + ? WHERE user_id = ?", (promo["val"], user_id))
            desc = f'{promo["val"]} Побед'
            
        await db.commit()

    await message.answer(
        f"<blockquote>{e(EMOJI_PROMO_SUCCESS)} Вы успешно активировали промокод!\nПолучено: {desc}</blockquote>",
        parse_mode="HTML"
    )

@dp.message(Command("event"))
async def create_event(message: Message):
    if message.from_user.id not in ADMINS: return
    text = message.text.replace("/event", "").strip()
    if not text: return await message.answer("Введите текст ивента.")
        
    event_msg = f"<blockquote>{e(EMOJI_EVENT)} <b>НОВОЕ СОБЫТИЕ!</b>\n\n{text}</blockquote>"
    
    count = 0
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            users = await cursor.fetchall()
            
    for row in users:
        try:
            await bot.send_message(row[0], event_msg, parse_mode="HTML")
            count += 1
        except: pass
    await message.answer(f"✅ Ивент разослан {count} пользователям.")

# =====================================================
# GAME MOVE HANDLER
# =====================================================

async def process_end_game(callback, game, result, game_id):
    game["ended"] = True
    if result == "draw":
        text = "🤝 Ничья"
    else:
        winner_id = game["x_player"] if result == "X" else game["o_player"]
        loser_id = game["o_player"] if result == "X" else game["x_player"]

        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            
            # Награда победителю
            if isinstance(winner_id, int):
                async with db.execute("SELECT premium FROM users WHERE user_id = ?", (winner_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        base_win = random.randint(5, 50)
                        if row["premium"]: base_win *= 1.025
                        await db.execute("UPDATE users SET wins = wins + 1, streak = streak + 1, bucks = bucks + ? WHERE user_id = ?", (base_win, winner_id))

            # Штраф проигравшему
            if isinstance(loser_id, int):
                await db.execute("UPDATE users SET loses = loses + 1, streak = 0 WHERE user_id = ?", (loser_id,))
                
            await db.commit()

        if str(winner_id).startswith("bot_"): text = f"🤖 Победил Бот!"
        else: text = f"{e(EMOJI_TROPHY)} Победил {result}!"

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=game_keyboard(game["board"], game_id))

def is_player_turn(game, user):
    if game["turn"] == "X": return game["x_player"] == user.id
    else:
        if game.get("is_bot"): return False
        if game["o_player"] == user.id: return True
        if user.username and str(game["o_player"]).lower() == user.username.lower():
            game["o_player"] = user.id
            return True
        return False

@dp.callback_query(F.data.startswith("move:"))
async def move(callback: CallbackQuery):
    parts = callback.data.split(":")
    game_id = int(parts[1])
    index = int(parts[2])
    
    game = games.get(game_id)
    if not game or game["ended"]: return await callback.answer("Игра не найдена или завершена.")
    if not is_player_turn(game, callback.from_user): return await callback.answer("Сейчас не твой ход!", show_alert=True)
    if game["board"][index]: return await callback.answer("Эта клетка уже занята!")

    # Ход Игрока
    game["board"][index] = game["turn"]
    result = check_winner(game["board"])

    if result:
        await process_end_game(callback, game, result, game_id)
        return await callback.answer()

    game["turn"] = "O" if game["turn"] == "X" else "X"

    # Ход Бота
    if game.get("is_bot") and game["turn"] == "O":
        bot_idx = get_bot_move(game["board"], game["o_player"])
        if bot_idx is not None:
            game["board"][bot_idx] = "O"
            result = check_winner(game["board"])
            
            if result:
                await process_end_game(callback, game, result, game_id)
                return await callback.answer()
                
            game["turn"] = "X"

    await callback.message.edit_text(f'Ход: {game["turn"]}', reply_markup=game_keyboard(game["board"], game_id))
    await callback.answer()

@dp.callback_query(F.data == "ignore")
async def ignore(callback: CallbackQuery):
    await callback.answer()

# =====================================================
# RUN
# =====================================================

async def main():
    await init_db() # Инициализация базы данных при старте
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
