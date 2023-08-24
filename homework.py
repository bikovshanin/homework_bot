import os
import sys
from sys import exit
import time
import logging
from http import HTTPStatus

import requests
from dotenv import load_dotenv
import telegram

from exceptions import DataBaseError, TelegramSendMessageError, HTTPStatusNotOk
from database import (db_insert_hw, db_select_hw,
                      db_select_error, db_insert_error)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens(practicum_token, tg_token, tg_chat_id):
    """
    Проверка токенов.
    Остановка скрипта
    в случае отсутствия хотя бы одного.
    """
    if not practicum_token or not tg_token or not tg_chat_id:
        logging.critical(
            'Отсутствует одна или несколько '
            'переменных окружения во время запуска бота'
        )
        exit(f'Токен практикума: {practicum_token}\n'
             f'Токен телеграм: {tg_token}\n'
             f'id телеграм: {tg_chat_id}\n')


def send_message(bot, message):
    """Отправка сообщение с обновлённым статусом домашней работы в Telegram."""
    data = db_select_hw()
    try:
        if HOMEWORK_VERDICTS[data.status] not in message:
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            logging.debug(f'В Telegram отправлено сообщение: {message}')
        else:
            raise ValueError('Статус проверки работы не поменялся')
    except Exception as error:
        raise TelegramSendMessageError(f'Сбой при отправке '
                                       f'сообщения в Telegram: {error}')


def get_api_answer(timestamp):
    """Получение и обработка ответа API."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            raise HTTPStatusNotOk(f'Код ошибки: {response}')
        return response.json()
    except Exception as error:
        raise ConnectionError(f'Ошибка при запросе к эндпоинту: {error}')


def check_response(response):
    """Проверка ответа на соответствие документации API."""
    if not isinstance(response, dict):
        raise TypeError(f'Вместо словаря функция принимает {type(response)}')
    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ "homeworks"')
    list_hw = response.get('homeworks')
    if not isinstance(list_hw, list):
        raise TypeError(f'Вместо списка функция возвращает {type(list_hw)}')
    return list_hw


def parse_status(homework):
    """Формирование строки для последующей отправки в Telegram."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует название домашней работы')
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'"{status}" - нераспознанный статус домашней работы')
    verdict = HOMEWORK_VERDICTS[status]
    return (f'Изменился статус проверки '
            f'работы "{homework_name}". {verdict}')


def get_current_date():
    """Получить timestamp для формирования ендпоинта."""
    try:
        timestamp = db_select_hw().current_date
    except Exception as error:
        logging.debug(f'База данных пуста: {error}')
        timestamp = int(time.time() - RETRY_PERIOD)
    return timestamp


def post_to_db(response):
    """Запись в базу полученных от API данных."""
    try:
        data = response['homeworks'][0]
        db_insert_hw(data['homework_name'], data['status'],
                     response['current_date'])
    except Exception as error:
        raise DataBaseError(f'Ошибка при записи в базу данных: {error}')


def main():
    """Основная логика работы бота."""
    check_tokens(PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    db_insert_error('Сбой в работе программы: '
                    'Сбой при отправке сообщения в Telegram: '
                    'Статус проверки работы не поменялся')

    while True:
        try:
            timestamp = get_current_date()
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if not homework:
                logging.debug('Новых работ для проверки пока нет')
            else:
                message = parse_status(homework[0])
                send_message(bot, message)
                post_to_db(response)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            db_message = db_select_error().message
            logging.error(message)
            if db_message != message:
                send_message(bot, message)
                db_insert_error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format=('%(asctime)s - %(levelname)s - '
                '%(name)s - %(funcName)s - %(message)s'),
        level=logging.DEBUG,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    main()
