import telebot
from telebot import types
import random
import datetime
import uuid
import aiosqlite
import gettext
from pathlib import Path
import asyncio

# Установка пути к каталогу с файлами переводов
locales_dir = Path(__file__).parent / 'locales'
locale = gettext.translation('messages', localedir=locales_dir, languages=['en'])
locale.install()

# Функция для перевода текста
def _(msg):
    return locale.gettext(msg)

# Создание объекта бота
TOKEN = 'YOUR_TOKEN'
bot = telebot.TeleBot(TOKEN)

# Функция для создания базы данных, если она не существует
async def create_database():
    async with aiosqlite.connect('cards.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                language TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                card_type TEXT,
                card_number TEXT,
                exp_date TEXT,
                cvv TEXT,
                country TEXT,
                currency TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        await db.commit()

# Функция для получения идентификатора пользователя
def get_user_id(message):
    if message.chat.type == 'private':
        return message.chat.id
    elif message.chat.type in ['group', 'supergroup']:
        return message.from_user.id
    else:
        return None

# Функция для добавления пользователя в базу данных
async def add_user(user_id, username, language):
    async with aiosqlite.connect('cards.db') as db:
        await db.execute("INSERT INTO users (user_id, username, language) VALUES (?, ?, ?)", (user_id, username, language))
        await db.commit()

# Функция для получения пользователя из базы данных
async def get_user(user_id):
    async with aiosqlite.connect('cards.db') as db:
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = await cursor.fetchone()
        return user

# Функция для обновления информации о пользователе в базе данных
async def update_user(user_id, username, language):
    async with aiosqlite.connect('cards.db') as db:
        await db.execute("UPDATE users SET username=?, language=? WHERE user_id=?", (username, language, user_id))
        await db.commit()

# Функция для удаления пользователя и его карт из базы данных
async def delete_user(user_id):
    async with aiosqlite.connect('cards.db') as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM cards WHERE user_id = ?", (user_id,))
        await db.commit()

# Функция для получения списка карт пользователя из базы данных
async def get_user_cards(user_id):
    async with aiosqlite.connect('cards.db') as db:
        cursor = await db.execute("SELECT * FROM cards WHERE user_id = ?", (user_id,))
        cards = await cursor.fetchall()
        return cards

# Функция для добавления карты пользователя в базу данных
async def add_card(user_id, card):
    async with aiosqlite.connect('cards.db') as db:
        await db.execute("INSERT INTO cards (id, user_id, card_type, card_number, exp_date, cvv, country, currency) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (card.id, user_id, card.card_type, card.card_number, card.exp_date, card.cvv, card.country, card.currency))
        await db.commit()

# Функция для удаления карты пользователя из базы данных
async def delete_card(card_id):
    async with aiosqlite.connect('cards.db') as db:
        await db.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        await db.commit()

# Функция для обновления информации о карте пользователя в базе данных
async def update_card(card):
    async with aiosqlite.connect('cards.db') as db:
        await db.execute("UPDATE cards SET card_type=?, card_number=?, exp_date=?, cvv=?, country=?, currency=? WHERE id=?", (card.card_type, card.card_number, card.exp_date, card.cvv, card.country, card.currency, card.id))
        await db.commit()

# Класс для представления карты пользователя
class Card:
    def __init__(self, card_type, card_number, exp_date, cvv, country, currency):
        self.card_type = card_type
        self.card_number = card_number
        self.exp_date = exp_date
        self.cvv = cvv
        self.country = country
        self.currency = currency
        self.created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.id = self.generate_id()

    def generate_id(self):
        return str(uuid.uuid4())

    def __str__(self):
        return f"ID: {self.id}\n{_('Тип карты')}: {self.card_type}\n{_('Номер карты')}: {self.card_number}\n{_('Срок действия')}: {self.exp_date}\nCVV: {self.cvv}\n{_('Страна')}: {self.country}\n{_('Валюта')}: {self.currency}\n"

# Функция для асинхронного получения списка карт пользователя из базы данных
async def get_user_cards_async(user_id):
    async with aiosqlite.connect('cards.db') as db:
        cursor = await db.execute("SELECT * FROM cards WHERE user_id = ?", (user_id,))
        cards = await cursor.fetchall()
        return cards

# Функция для отправки уведомления пользователю
async def send_notification(user_id, text):
    await bot.send_message(user_id, text)

# Обработчик команды /start и /help
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    commands_info = _("Список доступных команд:\n"
                      "/start - {_('начать работу с ботом')}\n"
                      "/help - {_('получить справку о доступных командах')}\n"
                      "/generate - {_('сгенерировать новую карту')}\n"
                      "/view - {_('просмотреть список сгенерированных карт')}\n"
                      "/buy_ad - {_('купить рекламу')}")
    bot.reply_to(message, f"{_('Приветствую!')}\n{commands_info}")

# Обработчик команды /generate
@bot.message_handler(commands=['generate'])
def generate_card(message):
    user_id = get_user_id(message)
    if user_id:
        card_types = [_('Visa'), _('MasterCard'), _('American Express'), _('Discover'), _('JCB')]
        country_keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        for country in countries.keys():
            country_keyboard.add(types.KeyboardButton(country))

        msg = bot.send_message(message.chat.id, _('Выберите страну выпуска карты:'), reply_markup=country_keyboard)
        bot.register_next_step_handler(msg, process_country_step, user_id)
    else:
        bot.send_message(message.chat.id, _("К сожалению, не удалось определить ваш идентификатор. Пожалуйста, попробуйте снова."))

# Обработчик выбора страны выпуска карты
def process_country_step(message, user_id):
    try:
        country_code = countries[message.text]
        bot.send_message(message.chat.id, f"{_('Вы выбрали')} {message.text}. {_('Теперь отправьте мне тип карты (Visa, MasterCard, American Express, Discover, JCB).')}")
        bot.register_next_step_handler(message, process_card_type_step, user_id, country_code)
    except KeyError:
        bot.send_message(message.chat.id, _("Пожалуйста, выберите страну из списка."))

# Обработчик выбора типа карты
def process_card_type_step(message, user_id, country_code):
    if message.text.capitalize() in [_('Visa'), _('MasterCard'), _('American Express'), _('Discover'), _('JCB')]:
        card_type = message.text.capitalize()
        bot.send_message(message.chat.id, f"{_('Вы выбрали')} {card_type}. {_('Теперь отправьте мне валюту карты (USD, CAD, GBP, AUD, EUR).')}")
        bot.register_next_step_handler(message, process_currency_step, user_id, country_code, card_type)
    else:
        bot.reply_to(message, _("Пожалуйста, выберите тип карты из предложенных вариантов."))

# Обработчик выбора валюты карты
def process_currency_step(message, user_id, country_code, card_type):
    if message.text.upper() in currencies.keys():
        currency_code = currencies[message.text.upper()]
        card_number = generate_card_number()
        exp_date = f"{random.randint(1, 12)}/{str(random.randint(22, 30))}"  # MM/YY
        cvv = generate_cvv()
        country = next((k for k, v in countries.items() if v == country_code), None)
        currency = next((k for k, v in currencies.items() if v == currency_code), None)

        new_card = Card(card_type, card_number, exp_date, cvv, country, currency)
        generated_cards.append(new_card)

        bot.reply_to(message, str(new_card))
    else:
        bot.reply_to(message, _("Пожалуйста, выберите валюту из предложенных вариантов."))

# Обработчик команды /view
@bot.message_handler(commands=['view'])
def view_cards(message):
    user_id = get_user_id(message)
    if user_id:
        user_cards = await get_user_cards_async(user_id)
        if user_cards:
            cards_info = "\n\n".join(str(card) for card in user_cards)
            bot.send_message(message.chat.id, cards_info)
        else:
            bot.send_message(message.chat.id, _("У вас пока нет сгенерированных карт."))
    else:
        bot.send_message(message.chat.id, _("К сожалению, не удалось определить ваш идентификатор. Пожалуйста, попробуйте снова."))

# Обработчик команды /buy_ad
@bot.message_handler(commands=['buy_ad'])
def buy_ad(message):
    # Отправляем пользователю инструкцию о покупке рекламы и переадресуем его к @kuertov_avito
    bot.send_message(message.chat.id, _("Для покупки рекламы, пожалуйста, свяжитесь с нашим менеджером @kuertov_avito."))

# Функция для генерации номера карты
def generate_card_number():
    # Ваша логика для генерации номера карты
    pass

# Функция для генерации CVV кода
def generate_cvv():
    # Ваша логика для генерации CVV кода
    pass

# Функция для отправки уведомления о ближайшей дате истечения срока действия карты
async def send_expiry_notification(user_id, card):
    exp_date = datetime.datetime.strptime(card.exp_date, "%m/%y")
    delta = exp_date - datetime.datetime.now()
    if delta.days <= 7:  # Отправляем уведомление за неделю до истечения срока действия
        await send_notification(user_id, f"{_('Внимание!')} {card.card_type} {_('истекает через')} {delta.days} {_('дней')}")

# Планировщик задач для отправки уведомлений о ближайших датах истечения срока действия карт
async def expiry_notification_scheduler():
    while True:
        await asyncio.sleep(3600)  # Проверяем каждый час
        for user_id in users:  # Перебираем всех пользователей
            user_cards = await get_user_cards_async(user_id)  # Получаем карты пользователя
            for card in user_cards:  # Перебираем все карты пользователя
                await send_expiry_notification(user_id, card)  # Отправляем уведомление о ближайшей дате истечения срока действия

# Запускаем планировщик задач
async def main():
    await create_database()
    bot.polling()

if __name__ == "__main__":
    asyncio.create_task(main())
    asyncio.create_task(expiry_notification_scheduler())
    asyncio.get_event_loop().run_forever()
