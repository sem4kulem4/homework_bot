import json
import http
import logging
import os
import requests
import time

from dotenv import load_dotenv
from telegram import Bot, TelegramError

import app_logger


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = app_logger.get_logger(__name__)


class APIHomeworkError(Exception):
    """Исключение, если API по какой-либо причине не выдал список ДЗ."""

    pass


class EmptyDictError(Exception):
    """Исключение, если в ответе API список ДЗ оказалася пустым."""

    pass


def send_message(bot, message):
    """Функция отправляет сообщение через telegram-бота."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение отправлено успешно!')

    except TelegramError as error:
        logger.error(f'Сообщение не отправлено! {error}')
        raise Exception(f'Сообщение не отправлено! {error}')


def get_api_answer(current_timestamp):
    """Функция получает ответ от API для заданного времени."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except requests.ConnectionError:
        logger.error('URL недоступен')
    if homework_statuses.status_code == http.HTTPStatus.OK:
        try:
            homework_statuses = homework_statuses.json()
            return homework_statuses
        except json.decoder.JSONDecodeError as error:
            logger.error(f'Ответ API не преобразуется в JSON. {error}')
            raise Exception(f'Ответ API не преобразуется в JSON. {error}')
    else:
        logger.error('Недоступен ENDPOINT')
        raise Exception('Код ответа отличен от 200')


def check_response(response):
    """Функция проверяет полученный ответ от API на корректность."""
    if not isinstance(response, dict):
        logger.error('API не выдал словарь')
        raise TypeError('API не выдал словарь')
    if 'homeworks' not in response:
        logger.error('API не выдал список домашних работ')
        raise APIHomeworkError('API не выдал список домашних работ')
    homeworks = response.get('homeworks')
    if len(homeworks) == 0:
        logger.error('API выдал пустой словарь')
        raise EmptyDictError('API выдал пустой словарь')
    if not isinstance(homeworks, list):
        logger.error('Получен элемент отличный от списка')
        raise TypeError('Получен элемент отличный от списка')
    return response.get('homeworks')


def parse_status(homework):
    """Функция парсит полученный от API ответ."""
    print(homework)
    if not isinstance(homework, dict):
        logger.error('Данные о ДЗ не в виде словаря!')
        raise Exception('Данные о ДЗ не в виде словаря!')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция проверяет наличие переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    logger.critical('Один из токенов недоступен')
    return False


def main():
    """Основная логика работы бота."""
    current_timestamp = int(time.time())
    bot = Bot(token=TELEGRAM_TOKEN)
    cached_status = None

    while True:
        try:
            check_tokens()
            response = get_api_answer(current_timestamp)
            last_hw = check_response(response)[0]
            if last_hw.get('status') == cached_status:
                logging.debug('Статус ДЗ не изменился')
                print('Статус ДЗ не изменился')
                current_timestamp = int(time.time())
                time.sleep(RETRY_TIME)
            else:
                cached_status = last_hw.get('status')
                send_message(bot, message=parse_status(last_hw))

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message=message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
