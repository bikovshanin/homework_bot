import os
import sys
import time
import logging
from sys import exit
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import TelegramSendMessageError, HTTPStatusNotOk


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


def check_tokens(*args):
    """
    Проверка токенов.
    Остановка скрипта в случае отсутствия хотя бы одного.
    """
    for token in args:
        if not token:
            logging.critical(
                'Отсутствует одна или несколько '
                'переменных окружения во время запуска бота'
            )
            exit(f'Токен практикума: {args[0]}\n'
                 f'Токен телеграм: {args[1]}\n'
                 f'id телеграм: {args[2]}\n')


def send_message(bot, message):
    """Отправка сообщение с обновлённым статусом домашней работы в Telegram."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'В Telegram отправлено сообщение: {message}')
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


def main():
    """Основная логика работы бота."""
    check_tokens(PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    session_data = {
        'status': 'status',
        'current_date': 0,
        'error_msg': '',
    }

    while True:
        try:
            timestamp = session_data['current_date']
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if not homework:
                logging.debug('Статус последней работы не поменялся')
            elif session_data['status'] == homework[0].get('status'):
                logging.debug('Статус работы не поменялся')
            else:
                message = parse_status(homework[0])
                send_message(bot, message)
                session_data.update(
                    status=homework[0].get('status'),
                    current_date=response['current_date'],
                )

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if session_data['error_msg'] != message:
                send_message(bot, message)
                session_data.update(error_msg=message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format=('%(asctime)s - %(levelname)s - '
                '%(name)s - %(funcName)s - %(lineno)d - %(message)s'),
        level=logging.DEBUG,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    main()
