# coding=utf-8

"""Запускает и организует викторину в telegram-чате."""

import logging
import os
import random
from functools import partial

import redis
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (CallbackContext, CallbackQueryHandler, CommandHandler, ConversationHandler,
                          Filters, MessageHandler, Updater)

from config_parser import create_parser
from quiz_tasks import generate_tasks_from_files, get_answer_comment
from telegram_log_handler import TelegramLogsHandler


KEYBOARD, ANSWER = range(2)


logger = logging.getLogger('quiz_bot.logger')


def run_telegram_bot(tg_bot_token, tasks, redis_client):
    """Запускает telegram-бота и организует его работу."""

    updater = Updater(tg_bot_token)
    dispatcher = updater.dispatcher

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', handle_start_command)],
        states={
            KEYBOARD: [
                CallbackQueryHandler(partial(handle_keyboard_request, tasks=tasks, redis_client=redis_client))
            ],
            ANSWER: [
                MessageHandler(Filters.text, partial(handle_solution_attempt, tasks=tasks, redis_client=redis_client))
            ]
        },
        fallbacks=[CommandHandler('cancel', handle_cancel_command)]
    )
    dispatcher.add_handler(conversation_handler)
    dispatcher.add_error_handler(handle_error)

    updater.start_polling()
    updater.idle()


def handle_start_command(update, context):
    """Посылает в telegram-чат приветствие, когда пользователь ввёл команду /start."""

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Привет! Я бот для викторин!\nДля начала викторины нажми «Новый вопрос»',
        reply_markup=get_keyboard_markup()
    )
    return KEYBOARD


def get_keyboard_markup():
    """Возвращает InlineKeyboardMarkup со встроенной клавиатурой."""

    keyboard = [
        [
            InlineKeyboardButton('Новый вопрос', callback_data='new_question'),
            InlineKeyboardButton('Сдаться', callback_data='capitulation'),
        ],      
    ]
    return InlineKeyboardMarkup(keyboard)


def handle_keyboard_request(update, context, tasks, redis_client):
    """Отвечает в telegram-чате на нажатие пользователем кнопки на клавиатуре."""

    buttons_handlers = {
        'new_question': handle_new_question_request,
        'capitulation': handle_capitulation_request
    }
    update.callback_query.answer()
    return buttons_handlers[update.callback_query.data](update, context, tasks, redis_client)


def handle_new_question_request(update, context, tasks, redis_client):
    """Отвечает в telegram-чате на нажатие пользователем кнопки «Новый вопрос»."""

    chat_id = update.effective_chat.id
    task_index = random.randrange(len(tasks))
    context.bot.send_message(
        chat_id=chat_id,
        text=tasks[task_index].question
    )
    redis_client.set(chat_id, task_index)
    return ANSWER


def handle_capitulation_request(update, context, tasks, redis_client):
    """Отвечает в telegram-чате на нажатие пользователем кнопки «Сдаться»."""

    chat_id = update.effective_chat.id
    task_index = redis_client.get(chat_id)
    if task_index:
        context.bot.send_message(
            chat_id=chat_id,
            text=tasks[int(task_index)].answer
        )
    return handle_new_question_request(update, context, redis_client)


def handle_solution_attempt(update, context, tasks, redis_client):
    """Отвечает в telegram-чате на сообщение пользователя."""

    chat_id = update.effective_chat.id
    task_index = redis_client.get(chat_id)
    if not task_index:
        return

    context.bot.send_message(
        chat_id=chat_id,
        text=get_answer_comment(user_answer=update.message.text, proper_answer=tasks[int(task_index)].answer),
        reply_markup=get_keyboard_markup()
    )
    return KEYBOARD


def handle_cancel_command(update, context):
    """Обрабатывает ввод пользователем команды /cancel в telegram-чате."""

    update.message.reply_text(
        f'До свидания, {update.message.from_user.first_name}!',
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def handle_error(update, context, error):
    """Обрабатывает возникающие ошибки."""

    logger.warning(f'Update "{update}" вызвал ошибку "{error}"')


def main():
    """Выполняет подготовительные операции и вызывает запуск telegram-бота."""

    options = create_parser('Запускает и организует викторину в telegram-чате.').parse_args()
    tasks = generate_tasks_from_files(options.quiz_folder)

    load_dotenv()
    tg_bot_token = os.environ['TELEGRAM_BOT_TOKEN']
    tg_moderator_chat_id = os.environ['TELEGRAM_MODERATOR_CHAT_ID']

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger.setLevel(logging.INFO)
    logger.addHandler(TelegramLogsHandler(tg_bot_token, tg_moderator_chat_id))
 
    redis_client = redis.StrictRedis(
        host=os.environ['REDIS_DB_HOST'],
        port=os.environ['REDIS_DB_PORT'],
        password=os.environ['REDIS_DB_PASSWORD'],
        decode_responses=True
    )

    run_telegram_bot(tg_bot_token, tasks, redis_client)


if __name__ == '__main__':
    main()
