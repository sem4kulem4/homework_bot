import logging
import os
import requests
import time

from dotenv import load_dotenv
from telegram import Bot


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


def send_message(bot, message):
    """"Функция отправляет сообщение через telegram-бота."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Сообщение отправлено успешно!')

    except Exception:
        logging.error('Сообщение не отправлено!')
        raise Exception('Сообщение не отправлено!')


def get_api_answer(current_timestamp):
    """"Функция получает ответ от API для заданного времени."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if homework_statuses.status_code == 200:
        return homework_statuses.json()
    else:
        logging.error('Недоступен ENDPOINT')
        raise Exception('Код ответа отличен от 200')


def check_response(response):
    """"Функция проверяет полученный ответ от API на корректность."""
    if not isinstance(response, dict):
        logging.error('API не выдал словарь')
        raise TypeError('API не выдал словарь')
    if len(response.get('homeworks')) == 0:
        logging.error('API выдал пустой словарь')
        raise Exception('API выдал пустой словарь')
    if 'homeworks' not in response:
        logging.error('API не выдал список домашних работ')
        raise Exception('API не выдал список домашних работ')
    if not isinstance(response['homeworks'], list):
        logging.error('Получен элемент отличный от списка')
        raise TypeError('Получен элемент отличный от списка')
    return response.get('homeworks')


def parse_status(homework):
    """"Функция парсит полученный от API ответ."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """"Функция проверяет наличие переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    logging.critical('Один из токенов недоступен')
    return False


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        filename='log_file_name.log',
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    current_timestamp = int(time.time())
    bot = Bot(token=TELEGRAM_TOKEN)
    cached_status = None

    while True:
        try:
            response = get_api_answer(current_timestamp)
            last_hw = check_response(response)[0]
            if last_hw.get('status') != cached_status:
                cached_status = last_hw.get('status')
                send_message(bot, message=parse_status(last_hw))
            else:
                logging.debug('Статус ДЗ не изменился')
                current_timestamp = int(time.time())
                time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message=message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
