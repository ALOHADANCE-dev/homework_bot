import os
import requests
import telegram
import time
import logging
import sys

from logging.handlers import RotatingFileHandler
from http import HTTPStatus
from dotenv import load_dotenv

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

ITERABLE = [TELEGRAM_CHAT_ID, TELEGRAM_TOKEN, PRACTICUM_TOKEN]


class ApiRequestError(Exception):
    pass


class HomeworkKeyError(Exception):
    pass


class JsonConvertError(Exception):
    pass


def check_tokens():
    """Проверяем переменные окружения."""
    if all([TELEGRAM_CHAT_ID, TELEGRAM_TOKEN, PRACTICUM_TOKEN]):
        return True
    else:
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
        return message


def get_api_answer(timestamp):
    """Запрос к API Практикум.Домашка."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except Exception.HTTPError as error:
        logging.warning(f"Ошибка: {error}, status code:{response.status_code}")
        raise ApiRequestError(
            f'Ошибка при запросе к API:{response.status_code}'
        )
    if response.status_code == HTTPStatus.OK:
        return response.json()
    else:
        logging.warning('Что-то не так с ответом от Практикум.Домашка')
        raise ApiRequestError(
            f'Ошибка при запросе к API:{response.status_code}'
        )
    try:
        response_json = response.json()
        logging.debug(f'Получен ответ от API: {response_json}')
        return response_json
    except ValueError as error:
        logger.warning(f"Ошибка при преобразовании ответа в JSON: {error}")
        raise JsonConvertError('Ошибка при преобразовании ответа в JSON')


def check_response(response):
    # Не совсем понял про комментарий с логированием, то есть,
    # я просто убираю отсюда логирование, оставляю только рейзы,
    # а затем пишу что то вроде try-except с выводом удаленных логов?
    """Проверяем ответ API Практикум.Домашка."""
    if not isinstance(response, dict):
        logging.error('Ответ Api не словарь')
        raise TypeError('Ответ Api не словарь')
    homework = response.get('homeworks')
    if homework is None:
        logging.error('В ответе нет ключа homeworks')
        raise HomeworkKeyError('В ответе нет ключа homeworks')
    if not isinstance(homework, list):
        logging.error('Домашние работы не в виде списка')
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
    first_message = ''
    second_message = ''
    while True:
        try:
            timestamp = int(time.time())
            response = get_api_answer(timestamp - RETRY_PERIOD)
            homework = check_response(response)[0]
            message = parse_status(homework)
            if first_message != message:
                send_message(bot, message)
                first_message = message
        except Exception as error:
            error_message = f'Сбой в работе программы: {error}'
            if second_message != error_message:
                send_message(bot, error_message)
                second_message = error_message
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)
    main()
