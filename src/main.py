import logging
import re
from collections import defaultdict
from urllib.parse import urljoin

import requests_cache
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import (
    DOWNLOADS_DIR, EXPECTED_STATUS, MAIN_DOC_URL, MAIN_PEPS_URL
)
from exceptions import ParserFindTagException
from outputs import control_output
from utils import cook_soup, find_tag

ARCHIVE_LOAD_MESSAGE = 'Архив был загружен и сохранён: {}'
COMMAND_ARGUMENTS = 'Аргументы командной строки: {}'
PARSER_START = 'Парсер запущен!'
PARSER_FINISH = 'Парсер успешно завершил работу.'
PARSER_FINISH_WITH_ERROR = 'Парсер завершил работу c ошибкой.'
NOT_FOUND_ERROR = 'Ничего не нашлось'


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    try:
        soup = cook_soup(session, whats_new_url)
    except ConnectionError as error:
        logging.error(error)
        return
    sections_by_python = soup.select(
        '#what-s-new-in-python div.toctree-wrapper li.toctree-l1'
    )
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор')]
    errors = []
    for section in tqdm(sections_by_python):
        try:
            version_link = urljoin(
                whats_new_url, find_tag(section, 'a')['href']
            )
            soup = cook_soup(session, version_link)
            results.append(
                (
                    version_link, find_tag(soup, 'h1').text,
                    find_tag(soup, 'dl').text.replace('\n', ' ')
                )
            )
        except ConnectionError as error:
            errors.append(str(error))
            continue
        except ParserFindTagException as error:
            errors.append(f'{error} на {version_link}')
            continue
    if errors:
        logging.error('\n'.join(errors), stack_info=True)
    return results


def latest_versions(session):
    try:
        soup = cook_soup(session, MAIN_DOC_URL)
    except ConnectionError as error:
        logging.error(error)
        return
    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
        else:
            raise ValueError(NOT_FOUND_ERROR)
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        text_match = re.search(pattern, a_tag.text)
        if text_match:
            version, status = text_match.groups()
        else:
            version = a_tag.text
            status = ''
        results.append((a_tag['href'], version, status))
    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    try:
        soup = cook_soup(session, downloads_url)
    except ConnectionError as error:
        logging.error(error)
        return
    pdf_a4_link = soup.select_one(
        'div[role=main] table.docutils [href$="pdf-a4.zip"]'
    )['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    DOWNLOADS_DIR.mkdir(exist_ok=True)
    archive_path = DOWNLOADS_DIR / filename
    response = session.get(archive_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(ARCHIVE_LOAD_MESSAGE.format(archive_path))


def pep(session):
    try:
        soup = cook_soup(session, MAIN_PEPS_URL)
    except ConnectionError as error:
        logging.error(error)
        return
    tr_tags = soup.select('#numerical-index tbody tr')
    statuses = defaultdict(int)
    unexpected_statuses = []
    errors = []
    for tr_tag in tqdm(tr_tags):
        try:
            status_in_table = EXPECTED_STATUS[find_tag(tr_tag, 'td').text[1:]]
            pep_url = urljoin(
                MAIN_PEPS_URL, find_tag(
                    tr_tag, 'a', {'class': 'pep reference internal'}
                )['href']
            )
            soup = cook_soup(session, pep_url)
        except ConnectionError as error:
            errors.append(str(error))
            continue
        except ParserFindTagException as error:
            errors.append(f'{error} на {pep_url}')
            continue
        status_in_cart = soup.find(
            string='Status'
        ).find_parent('dt').find_next_sibling().text
        if status_in_cart not in status_in_table:
            unexpected_statuses.append('\n'.join([
                f'{pep_url}',
                f'Статус в карточке: {status_in_cart}',
                f'Ожидаемые статусы: {list(status_in_table)}'
            ]))
        statuses[status_in_cart] += 1
    if errors:
        logging.error('\n'.join(errors), stack_info=True)
    if unexpected_statuses:
        logging.error(
            '\n'.join(('Несовпадающие статусы:', *unexpected_statuses))
        )
    return [
        ('Статус', 'Количество'),
        *statuses.items(),
        ('Всего', sum(statuses.values())),
    ]


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    configure_logging()
    logging.info(PARSER_START)
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(COMMAND_ARGUMENTS.format(args))
    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    try:
        results = MODE_TO_FUNCTION[parser_mode](session)
        if results is not None:
            control_output(results, args)
        logging.info(PARSER_FINISH)
    except Exception as error:
        logging.exception(PARSER_FINISH_WITH_ERROR)
        logging.exception(error, stack_info=True)


if __name__ == '__main__':
    main()
