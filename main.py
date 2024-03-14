import aiosqlite
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import F

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

API_TOKEN = '7154590285:AAFX2JOkYwLI7p7Y8f4Urpg-jPibfjNkeRA'

# Объект бота
bot = Bot(token=API_TOKEN)
# Диспетчер
dp = Dispatcher()

# Зададим имя базы данных
DB_NAME = 'quiz_bot.db'

# Структура квиза
quiz_data = [
    {
        'question': 'Что такое Python?',
        'options': ['Язык программирования', 'Тип данных', 'Музыкальный инструмент', 'Змея на английском'],
        'correct_option': 0
    },
    {
        'question': 'Какой тип данных используется для хранения целых чисел?',
        'options': ['int', 'float', 'str', 'natural'],
        'correct_option': 0
    },
    {
        'question': 'Какой тип данных используется для хранения строковых значений?',
        'options': ['int', 'float', 'str', 'natural'],
        'correct_option': 2
    },
    # Добавьте другие вопросы
]


# Функция для генерации клавиатуры с вариантами ответов
def generate_options_keyboard(answer_options, right_answer):
    # Создаем объект InlineKeyboardBuilder для построения клавиатуры
    builder = InlineKeyboardBuilder()

    # Перебираем все варианты ответов
    for option in answer_options:
        # Создаем кнопку для каждого варианта ответа
        builder.add(types.InlineKeyboardButton(
            # Устанавливаем текст кнопки равным варианту ответа
            text=option,
            # Устанавливаем callback_data в зависимости от того, является ли вариант ответа правильным
            callback_data="right_answer" if option == right_answer else "wrong_answer")
        )

    # Выравниваем кнопки по одной в ряд
    builder.adjust(1)

    # Возвращаем сгенерированную клавиатуру
    return builder.as_markup()


# Хэндлер для обработки нажатия на кнопку с правильным ответом
@dp.callback_query(F.data == "right_answer")
async def right_answer(callback: types.CallbackQuery):
    # Удаляем клавиатуру с вариантами ответов
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,  # Идентификатор чата
        message_id=callback.message.message_id,  # Идентификатор сообщения
        reply_markup=None  # Удаляем клавиатуру
    )

    # Отправляем сообщение с подтверждением правильного ответа
    await callback.message.answer("Верно!")

    # Получаем индекс текущего вопроса из базы данных
    current_question_index = await get_quiz_index(callback.from_user.id)

    # Обновляем номер текущего вопроса в базе данных
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index)

    # Если текущий вопрос не последний, задаем следующий вопрос
    if current_question_index < len(quiz_data):
        await get_question(callback.message, callback.from_user.id)
    else:
        # Если текущий вопрос последний, сообщаем об окончании квиза
        await callback.message.answer("Это был последний вопрос. Квиз завершен!")


# Хэндлер для обработки нажатия на кнопку с неправильным ответом
@dp.callback_query(F.data == "wrong_answer")
async def wrong_answer(callback: types.CallbackQuery):
    # Удаляем клавиатуру с вариантами ответов
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,  # Идентификатор чата
        message_id=callback.message.message_id,  # Идентификатор сообщения
        reply_markup=None  # Удаляем клавиатуру
    )

    # Получаем индекс текущего вопроса из базы данных
    current_question_index = await get_quiz_index(callback.from_user.id)

    # Определяем правильный ответ
    correct_option = quiz_data[current_question_index]['correct_option']

    # Отправляем сообщение с указанием правильного ответа
    await callback.message.answer(
        f"Неправильно. Правильный ответ: {quiz_data[current_question_index]['options'][correct_option]}")

    # Обновляем номер текущего вопроса в базе данных
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index)

    # Если текущий вопрос не последний, задаем следующий вопрос
    if current_question_index < len(quiz_data):
        await get_question(callback.message, callback.from_user.id)
    else:
        # Если текущий вопрос последний, сообщаем об окончании квиза
        await callback.message.answer("Это был последний вопрос. Квиз завершен!")


# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Создаем клавиатуру с кнопкой "Начать игру"
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Начать игру"))

    # Приветствуем пользователя и отправляем сообщение с клавиатурой
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup(resize_keyboard=True))


# Функция для получения текущего вопроса
async def get_question(message, user_id):
    # Получаем индекс текущего вопроса из базы данных
    current_question_index = await get_quiz_index(user_id)

    # Определяем правильный ответ
    correct_index = quiz_data[current_question_index]['correct_option']

    # Получаем варианты ответов
    opts = quiz_data[current_question_index]['options']

    # Генерируем клавиатуру с вариантами ответов
    kb = generate_options_keyboard(opts, opts[correct_index])

    # Отправляем текущий вопрос с клавиатурой
    await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)


# Функция для старта нового квиза
async def new_quiz(message):
    # Получаем идентификатор пользователя
    user_id = message.from_user.id

    # Обнуляем номер текущего вопроса в базе данных
    current_question_index = 0
    await update_quiz_index(user_id, current_question_index)

    # Задаем первый вопрос
    await get_question(message, user_id)


async def get_quiz_index(user_id):
    # Подключаемся к базе данных
    async with aiosqlite.connect(DB_NAME) as db:
        # Получаем запись для заданного пользователя
        async with db.execute('SELECT question_index FROM quiz_state WHERE user_id = (?)', (user_id,)) as cursor:
            # Возвращаем результат
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0


async def update_quiz_index(user_id, index):
    # Создаем соединение с базой данных (если она не существует, она будет создана)
    async with aiosqlite.connect(DB_NAME) as db:
        # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
        await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index) VALUES (?, ?)', (user_id, index))
        # Сохраняем изменения
        await db.commit()


# Хэндлер на команду /quiz
@dp.message(F.text == "Начать игру")
@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):
    await message.answer(f"Давайте начнем квиз!")
    await new_quiz(message)


async def create_table():
    # Создаем соединение с базой данных (если она не существует, она будет создана)
    async with aiosqlite.connect(DB_NAME) as db:
        # Создаем таблицу
        await db.execute(
            '''CREATE TABLE IF NOT EXISTS quiz_state (user_id INTEGER PRIMARY KEY, question_index INTEGER)''')
        # Сохраняем изменения
        await db.commit()


# Запуск процесса поллинга новых апдейтов
async def main():
    # Запускаем создание таблицы базы данных
    await create_table()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
