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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

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
PAYLOAD = {'from_date': 1549962000}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяем переменные окружения."""
    if TELEGRAM_TOKEN and PRACTICUM_TOKEN and TELEGRAM_CHAT_ID is not None:
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
    PAYLOAD = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=PAYLOAD)
        if response.status_code == HTTPStatus.OK:
            return response.json()
        else:
            logging.warning('Что-то не так с ответом от Практикум.Домашка')
            raise Exception(f'Ошибка при запросе к API:{response.status_code}')
    except Exception.HTTPError as error:
        print(f"Ошибка: {error}, status code: {response.status_code}")
    response = response.json()
    return response


def check_response(response):
    """Проверяем ответ API Практикум.Домашка."""
    if not isinstance(response, dict):
        logging.error('Ответ Api не словарь')
        raise TypeError('Ответ Api не словарь')
    homeworks = response.get('homeworks')
    if homeworks is None:
        logging.error('В ответе нет ключа homeworks')
        raise Exception('В ответе нет ключа homeworks')
    if not isinstance(homeworks, list):
        logging.error('Домашние работы не в виде списка')
        raise TypeError('Домашние работы не в виде списка')
    else:
        return homeworks


def parse_status(homework):
    """Соотношение статуса ответа и HOMEWORK_VERDICT."""
    try:
        status = homework['status']
        verdict = HOMEWORK_VERDICTS[status]
        homework_name = homework['homework_name']
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError:
        error_message = 'Ошибка, в ответе API отсутствует ключ "homework_name"'
        raise ValueError(error_message)
    except Exception as error:
        error_message = f'Ошибка, статус домашней работы неизвестен {error}'
        return (error_message)


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            timestamp = int(time.time())
            response = get_api_answer(timestamp)
            homework = check_response(response)[0]
            message = parse_status(homework)
            send_message(bot, message)
        except Exception as error:
            error_message = f'Сбой в работе программы: {error}'
            send_message(bot, error_message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
