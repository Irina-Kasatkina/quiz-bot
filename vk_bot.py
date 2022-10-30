# coding=utf-8

"""Запускает и организует викторину в VK-чате."""

import logging
import os
import random

import redis
from dotenv import load_dotenv
from vk_api import VkApi
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType

from config_parser import create_parser
from telegram_log_handler import TelegramLogsHandler
from quiz_tasks import generate_tasks_from_files, get_answer_comment


logger = logging.getLogger('support_bot.logger')


def run_vk_bot(vk_group_token, tasks, redis_client):
    """Запускает vk-бота и организует его работу."""

    try:
        vk_session = VkApi(token=vk_group_token)
        vk_api = vk_session.get_api()
        longpoll = VkLongPoll(vk_session)

        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                handle_event(event, vk_api, tasks, redis_client)
    except Exception as error:
        logger.exception(f'Ошибка {error} в vk-боте.')


def handle_event(event, vk_api, tasks, redis_client):
    """Отвечает в чате VK на сообщение пользователя."""

    if event.text.endswith('Новый вопрос'):
        return handle_new_question_request(event, vk_api, tasks, redis_client)

    if event.text.endswith('Сдаться'):
        return handle_capitulation_request(event, vk_api, tasks, redis_client)

    return handle_solution_attempt(event, vk_api, tasks, redis_client)


def handle_new_question_request(event, vk_api, tasks, redis_client):
    """Отвечает в vk-чате на нажатие пользователем кнопки «Новый вопрос»."""

    peer_id = event.peer_id
    task_index = random.randrange(len(tasks))
    vk_api.messages.send(
        peer_id=peer_id,
        message=tasks[task_index].question,
        random_id=random.randint(1, 1000)
    )
    redis_client.set(peer_id, task_index)


def handle_capitulation_request(event, vk_api, tasks, redis_client):
    """Отвечает в vk-чате на нажатие пользователем кнопки «Сдаться»."""

    peer_id = event.peer_id
    task_index = redis_client.get(peer_id)
    if task_index:
        vk_api.messages.send(
            peer_id=peer_id,
            message=tasks[int(task_index)].answer,
            random_id=random.randint(1, 1000)
        )
    return handle_new_question_request(event, vk_api, tasks, redis_client)


def handle_solution_attempt(event, vk_api, tasks, redis_client):
    """Отвечает в telegram-чате на сообщение пользователя."""

    peer_id = event.peer_id
    task_index = redis_client.get(peer_id)
    if task_index:
        message = get_answer_comment(
            user_answer=event.text,
            proper_answer=tasks[int(task_index)].answer
        )
    else:
        message = 'Для получения вопроса нажми «Новый вопрос»'

    vk_api.messages.send(
        peer_id=peer_id,
        keyboard=get_keyboard(),
        message=message,
        random_id=random.randint(1, 1000)
    )


def get_keyboard():
    """Возвращает клавиатуру для VK."""

    keyboard = VkKeyboard(one_time=True)

    keyboard.add_button('Новый вопрос', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('Сдаться', color=VkKeyboardColor.POSITIVE)

    return keyboard.get_keyboard()


def main():
    """Запускает vk-бота, организующего викторину."""

    options = create_parser('Запускает и организует викторину в VK-чате.').parse_args()
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

    run_vk_bot(os.environ['VK_GROUP_TOKEN'], tasks, redis_client)


if __name__ == '__main__':
    main()
