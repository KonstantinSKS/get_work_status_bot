import logging
import os
import sys
import time

import requests
import telegram

from logging import StreamHandler
from http import HTTPStatus
from dotenv import load_dotenv
from exceptions import SendMessageError, ApiAnswerError

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

logging.basicConfig(
    level=logging.ERROR,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler = StreamHandler(sys.stdout)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверка доступности переменных окружения."""
    tokens = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    return all(tokens)


def send_message(bot, message):
    """Отправка сообщений в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logging.error(f'Не удалось отправить сообщение {error}')
        raise SendMessageError(message)
    else:
        logger.debug('Сообщение успешно отправлено')


def get_api_answer(timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            raise ConnectionError('Ошибка при запросе к API')
    except requests.RequestException as error:
        raise ApiAnswerError(f'Возникла ошибка: {error}')
    return response.json()


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('В ответе API отсутствует словарь')
    if response.get('homeworks') is None:
        raise KeyError('Отсутствуют домашние работы')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Значения данных словаря не в виде списка')
    return homeworks


def parse_status(homework):
    """Извлечение статуса домашней работы из информации о ней."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if homework_name is None:
        raise KeyError('Отсутствует название')
    if status is None:
        raise KeyError('Отсутствует статус')
    verdict = HOMEWORK_VERDICTS.get(status)
    if verdict is None:
        raise ValueError('Отсутсвует вердикт')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует переменная, '
                         'необходимая для работы программы')
        sys.exit('Отсутствуют необходимые токены')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    previous_status = ''
    timestamp = 0
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                status = parse_status(homeworks[0])
                if status != previous_status:
                    send_message(bot, message=status)
                    previous_status = status
                    timestamp = response.get('current_date')
                else:
                    logger.debug('Обновления статуса работы нет')
            else:
                logger.info('Новых работ нет')
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
