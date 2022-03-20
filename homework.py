import os
import sys
import requests
import time
import logging
import telegram

from http import HTTPStatus
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    stream=sys.stdout,
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
handler.setFormatter(formatter)
logger.addHandler(handler)

BOT = telegram.Bot(token=TELEGRAM_TOKEN)


def send_message(bot, message):
    """Отправка сообщения в телеграмм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение отправлено')
    except Exception as error:
        logger.error(f'Сбой при отправке сообщения. Ошибка: {error}')


def get_api_answer(current_timestamp):
    """Получает ответ от API сервиса Практикум.Домашка."""
    LAST_ERROR_MESSAGE_API = ''

    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)

    except Exception as error:
        message = f'Сбой при доступе к эндпоинту. Ошибка: {error}'
        logger.error(message)
        if LAST_ERROR_MESSAGE_API != message:
            LAST_ERROR_MESSAGE_API = message
            send_message(BOT, message)
    if response.status_code != HTTPStatus.OK:
        message = 'Эндпоинт недоступен'
        logger.error(message)
        if LAST_ERROR_MESSAGE_API != message:
            LAST_ERROR_MESSAGE_API = message
            send_message(BOT, message)
        raise AssertionError('Эндпоинт недоступен')
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    LAST_ERROR_MESSAGE_RESPONSE = ''

    if not isinstance(response, dict):
        message = 'Ответ не является словарем'
        logger.error(message)
        if LAST_ERROR_MESSAGE_RESPONSE != message:
            LAST_ERROR_MESSAGE_RESPONSE = message
            send_message(BOT, message)
        raise TypeError(message)
    if (not ('homeworks' in response)
            or not ('current_date' in response)):
        message = 'В ответе нет необходимых ключей'
        logger.error(message)
        if LAST_ERROR_MESSAGE_RESPONSE != message:
            LAST_ERROR_MESSAGE_RESPONSE = message
            send_message(BOT, message)
        raise KeyError(message)
    if not isinstance(response.get('homeworks'), list):
        message = 'Сервер недоступен'
        logger.error(message)
        if LAST_ERROR_MESSAGE_RESPONSE != message:
            LAST_ERROR_MESSAGE_RESPONSE = message
            send_message(BOT, message)
        raise TypeError(message)
    return response.get('homeworks')


def parse_status(homework):
    """Проверка статуса.

    Извлекает из информации о конкретной
    домашней работе статус этой работы.
    """
    LAST_ERROR_MESSAGE_STATUS = ''

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except Exception:
        message = 'Недокументированный статус домашней работы'
        logger.error(message)
        if LAST_ERROR_MESSAGE_STATUS != message:
            LAST_ERROR_MESSAGE_STATUS = message
            send_message(BOT, message)
        raise KeyError(message)
    else:
        if verdict == 'approved':
            message = 'Работа проверена: ревьюеру всё понравилось. Ура!'
            return message
        else:
            message = 'Изменился статус проверки работы'
            return f'{message} "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота.

    Обращается к API сервиса Практикум.Домашка и
    узнает статус домашней работы.
    """
    LAST_ERROR_MESSAGE = ''

    if not check_tokens():
        logger.critical('Отсутствуют переменные окружения')
        raise SystemExit()

    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if LAST_ERROR_MESSAGE != message:
                LAST_ERROR_MESSAGE = message
                send_message(BOT, message)
            time.sleep(RETRY_TIME)
        else:
            if not homeworks:
                message = 'Отсутствуют в ответе новые статусы'
                logger.debug(message)
                raise AssertionError(message)
            else:
                message = parse_status(homeworks[0])
                send_message(BOT, message)
            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
