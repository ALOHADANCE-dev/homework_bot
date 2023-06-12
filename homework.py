import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
from http import HTTPStatus

import requests
from dotenv import load_dotenv

from my_exception import ApiRequestError, HomeworkKeyError, JsonConvertError

import telegram

load_dotenv()   

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('bot.log', maxBytes=50000000, backupCount=5)
logger.addHandler(handler)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')

TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяем переменные окружения."""
    if all([TELEGRAM_CHAT_ID, TELEGRAM_TOKEN, PRACTICUM_TOKEN]):
        return True
    logging.critical('Не все перемемнные окружения доступны')
    sys.exit()


def send_message(bot, message):
    """Отправляем сообщение с помощью бота."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение отправлено')
    except Exception as error:
        message = f'Сообщение не отправлено, возникла ошибка: {error}'
        logging.error(message)


def get_api_answer(timestamp):
    """Запрос к API Практикум.Домашка."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except Exception.HTTPError:
        raise ApiRequestError(
            f'Ошибка при запросе к API:{response.status_code}'
        )
    if response.status_code == HTTPStatus.OK:
        try:
            return response.json()
        except ValueError:
            raise JsonConvertError('Ошибка при преобразовании ответа в JSON')
    raise ApiRequestError(
        f'Ошибка при запросе к API:{response.status_code}'
    )


def check_response(response):
    """Проверяем ответ API Практикум.Домашка."""
    if not isinstance(response, dict):
        raise TypeError('Ответ Api не словарь')
    homework = response.get('homeworks')
    if homework is None:
        raise HomeworkKeyError('В ответе нет ключа homeworks')
    if not isinstance(homework, list):
        raise TypeError('Домашние работы не в виде списка')
    return homework


def parse_status(homework):
    """Соотношение статуса ответа и HOMEWORK_VERDICT."""
    status = homework.get('status')
    if status is None:
        error_message = 'Ошибка, в статусе API отсутствует ключ "status"'
        raise ValueError(error_message)
    verdict = HOMEWORK_VERDICTS.get(status)
    if verdict is None:
        error_message = 'Ошибка, статус домашней работы неизвестен'
        raise ValueError(error_message)
    homework_name = homework.get('homework_name')
    if homework_name is None:
        error_message = 'Ошибка, в ответе API отсутствует ключ "homework_name"'
        raise ValueError(error_message)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    save_error_message = ''
    timestamp = 0
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)[0]
            if not homework:
                pass
            else:
                message = parse_status(homework)
                send_message(bot, message)
                print(response)
                timestamp = int(response['current_date'])
                save_error_message = ''
        except Exception as error:
            error_message = f'Сбой в работе программы: {error}'
            logging.error(str(error_message))
            if save_error_message != error_message:
                send_message(bot, error_message)
                save_error_message = error_message
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)
    main()
