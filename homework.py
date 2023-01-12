import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

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
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


def check_tokens():
    """Проверка переменных окружения на доступность."""
    env_var = {PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN}

    for var in env_var:
        if not var or var == '':
            logger.error(f'Переменная {var} не найдена')
            return False
    return True


def send_message(bot, message):
    """Отправка сообщения пользователю."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение успешно отправлено')
    except Exception as error:
        logger.exception(error)


def get_api_answer(timestamp):
    """Отправка запроса к API с проверками ответа и декодирования."""
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT, headers=HEADERS,
                                         params=payload)
        if homework_statuses.status_code != HTTPStatus.OK:
            homework_statuses.raise_for_status()
    except requests.exceptions.RequestException:
        logger.exception('Неудачная попытка обращения к сервису')

    try:
        decoded_response = homework_statuses.json()
    except requests.JSONDecodeError:
        logger.exception('Ошибка декодирования списка домашек.')
    return decoded_response


def check_response(response):
    """Проверка ответа API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Тип данных ответа не соответсвует ожидаемому (dict)')
    if 'homeworks' not in response.keys():
        raise KeyError('В ответе не содержится ключ homeworks')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Содержимое ответа не соответсвует'
                        ' ожидаемому типу (list)')
    homeworks_list = response['homeworks']
    if type(homeworks_list) is not list:
        logger.error('В ответе API нет списка работ')
        raise Exception('В ответе API нет списка работ')
    return homeworks_list


def parse_status(homework: dict):
    """Получение статуса конкретной домашней работы."""
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise NameError('Получен невалидный статус домашней работы')
    try:
        homework_name = homework['homework_name']
    except Exception:
        logger.exception('Ключ homework_name не найден в теле ответа')
    finally:
        verdict = HOMEWORK_VERDICTS[homework_status]
        message = (f'Изменился статус проверки '
                   f'работы "{homework_name}".{verdict}')
        return message


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутсвуют переменные окружения')
        sys.exit('Отсутсвуют переменные окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    suc_message = []
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            homework = homeworks[0]
            message = parse_status(homework)
            timestamp = response.get('current_date')
            if message not in suc_message:
                send_message(bot, message)
                suc_message.append(message)
                print(suc_message)
                time.sleep(RETRY_PERIOD)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
