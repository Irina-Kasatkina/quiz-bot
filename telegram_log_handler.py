# coding=utf-8

"""Направляет сообщения об ошибках в telegram-чат модератора."""

import logging

import telegram


class TelegramLogsHandler(logging.Handler):
    """Перенаправляет логи бота в чат Telegram."""

    def __init__(self, telegram_bot_token, telegram_chat_id):
        super().__init__()
        self.bot = telegram.Bot(token=telegram_bot_token)
        self.chat_id = telegram_chat_id

    def emit(self, record):
        log_entry = self.format(record)
        self.bot.send_message(chat_id=self.chat_id, text=log_entry)
