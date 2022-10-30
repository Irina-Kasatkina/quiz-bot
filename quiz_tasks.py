# coding=utf-8

"""Функции для работы с вопросами и ответами викторины."""

import os
from collections import namedtuple


def generate_tasks_from_files(quiz_folder):
    """Формирует словарь из файлов с вопросами и ответами викторины."""

    tasks = []
    for quiz_filename in os.listdir(quiz_folder):
        with open(os.path.join(quiz_folder, quiz_filename), 'r', encoding='KOI8-R') as quiz_file:
            texts = quiz_file.read().split('\n\n')

        file_tasks = generate_tasks_from_texts(texts)
        tasks.extend(file_tasks)
    return tasks


def generate_tasks_from_texts(texts):
    """Формирует словарь из заданных текстов с вопросами викторины."""

    Task = namedtuple('Task', 'question answer')
    task_question = ''
    question_search = True

    tasks = []
    for text in texts:
        if text.startswith(('Вопрос', 'вопрос', 'ВОПРОС')):
            task_question = ' '.join(text.split('\n')[1:])
            question_search = False
        elif text.startswith(('Ответ', 'ответ', 'ОТВЕТ')):
            if not question_search:
                task_answer = ' '.join(text.split('\n')[1:])
                if task_question and task_answer:
                    tasks.append(Task(task_question, task_answer))

            task_question = ''
            question_search = True
    return tasks


def get_answer_comment(user_answer, proper_answer):
    """Формирует комментарий на ответ пользователя, сравнивая его с правильным ответом."""

    user_answer = user_answer.strip().lower()
    sufficient_answer = proper_answer.split('.')[0].split('(')[0].lower()

    if user_answer in sufficient_answer and len(user_answer) > 3:
        return 'Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»'

    return 'Неправильно… Попробуешь ещё раз?'
