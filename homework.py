import os
import sys
import time
import logging
from http import HTTPStatus

import telegram
import requests
from dotenv import load_dotenv

from exceptions import NoMessageError, NoMessageDebug

load_dotenv()

TELEGRAM_TOKEN = '5246909891:AAGJ3YOJffZqDoV7x6jDNA6Fk04jRXPpe8Y'
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_CHECK_RESULTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения в телеграмм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        raise NoMessageError()


def get_api_answer(current_timestamp):
    """Получает ответ от API сервиса Практикум.Домашка."""
    try:
        timestamp = current_timestamp or int(time.time())
        params = {'from_date': timestamp}

        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise requests.RequestException
        return response.json()
    except Exception:
        raise


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError()
    if (response.get('homeworks') is None
       or response.get('current_date') is None):
        raise KeyError
    if not isinstance(response.get('homeworks'), list):
        raise TypeError
    if not response.get('homeworks'):
        raise NoMessageDebug()
    return response.get('homeworks')


def parse_status(homework):
    """Проверка статуса.

    Извлекает из информации о конкретной
    домашней работе статус этой работы.
    """
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    try:
        verdict = HOMEWORK_CHECK_RESULTS[homework_status]
    except KeyError:
        raise KeyError
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
    last_error_message = ''

    if not check_tokens():
        message = 'Отсутствуют переменные окружения'
        logger.critical(message)
        sys.exit(message)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            message = parse_status(homeworks[0])
            send_message(bot, message)
            logger.info(message)
            current_timestamp = response['current_date']
        except NoMessageDebug():
            message = 'Отсутствуют в ответе новые статусы'
            logger.debug(message)
        except NoMessageError():
            message = 'API Telegram не отвечает'
            logger.error(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if last_error_message != message:
                last_error_message = message
                send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
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

    main()
