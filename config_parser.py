# coding=utf-8

"""Функции для работы с аргументами командной строки, файлами конфигурации и переменными среды.."""

import sys

import configargparse


QUIZ_FOLDER = 'quiz_questions'


def create_parser(app_description):
    default_config_files = []
    if '-c' not in sys.argv and '--config' not in sys.argv:
        default_config_files = ['config/config.ini']

    parser = configargparse.ArgParser(default_config_files=default_config_files, description=app_description)
    parser.add_argument('-c', '--config', is_config_file=True, help='Путь к файлу config.ini')
    parser.add_argument(
        '-f',
        '--quiz_folder',
        type=str,
        env_var='QUIZ_FOLDER',
        default=QUIZ_FOLDER,
        help='Путь к папке с файлами вопросов и ответов викторины.'
    )
    return parser
