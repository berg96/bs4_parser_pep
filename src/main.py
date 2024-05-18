import logging
import re
from collections import defaultdict
from urllib.parse import urljoin

import requests_cache
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import (
    BASE_DIR, DOWNLOAD_MODE, EXPECTED_STATUS, LATEST_VERSIONS_MODE,
    MAIN_DOC_URL, MAIN_PEPS_URL, PEP_MODE, WHATS_NEW_MODE, get_downloads_dir
)
from exceptions import ElementNotFoundError, ParserFindTagException
from outputs import control_output
from utils import cook_soup, find_tag

ARCHIVE_LOAD_MESSAGE = 'Архив был загружен и сохранён: {}'
COMMAND_ARGUMENTS = 'Аргументы командной строки: {}'
PARSER_START = 'Парсер запущен!'
PARSER_FINISH = 'Парсер успешно завершил работу.'
PARSER_FINISH_WITH_ERROR = 'Парсер завершил работу c ошибкой.\n{}'
NOT_FOUND_ERROR = 'Ничего не нашлось.'
CONNECTION_ERROR_MESSAGE = 'При обработке {url} возникла ошибка: {error}'
NOT_FOUND_TAG_ON_URL = '{error} на {url}'
UNEXPECTED_STATUS = (
    '{url}\nСтатус в карточке: {status_in_cart}'
    '\nОжидаемые статусы: {statuses_in_table}'
)
UNEXPECTED_STATUSES = 'Несовпадающие статусы:\n{}'
HEADER_WHATS_NEW = ('Ссылка на статью', 'Заголовок', 'Редактор, Автор')
HEADER_LATEST_VERSION = ('Ссылка на документацию', 'Версия', 'Статус')
HEADER_PEP = ('Статус', 'Количество')
FOOTER_PEP = 'Всего'


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    soup = cook_soup(session, whats_new_url)
    a_tags = soup.select(
        '#what-s-new-in-python div.toctree-wrapper li.toctree-l1 > a'
    )
    results = [HEADER_WHATS_NEW]
    errors = []
    for a_tag in tqdm(a_tags):
        try:
            version_link = urljoin(whats_new_url, a_tag['href'])
            soup = cook_soup(session, version_link)
            results.append(
                (
                    version_link,
                    find_tag(soup, 'h1').text,
                    find_tag(soup, 'dl').text.replace('\n', ' ')
                )
            )
        except ConnectionError as error:
            errors.append(
                CONNECTION_ERROR_MESSAGE.format(url=version_link, error=error)
            )
        except ParserFindTagException as error:
            errors.append(
                NOT_FOUND_TAG_ON_URL.format(error=error, url=version_link)
            )
    if errors:
        logging.error('\n'.join(errors))
    return results


def latest_versions(session):
    soup = cook_soup(session, MAIN_DOC_URL)
    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise ElementNotFoundError(NOT_FOUND_ERROR)
    results = [HEADER_LATEST_VERSION]
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
    soup = cook_soup(session, downloads_url)
    pdf_a4_link = soup.select_one(
        'div[role=main] table.docutils [href$="pdf-a4.zip"]'
    )['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = get_downloads_dir(BASE_DIR)
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(ARCHIVE_LOAD_MESSAGE.format(archive_path))


def pep(session):
    soup = cook_soup(session, MAIN_PEPS_URL)
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
            errors.append(
                CONNECTION_ERROR_MESSAGE.format(url=pep_url, error=error)
            )
            continue
        except ParserFindTagException as error:
            errors.append(
                NOT_FOUND_TAG_ON_URL.format(error=error, url=pep_url)
            )
            continue
        status_in_cart = soup.find(
            string='Status'
        ).find_parent('dt').find_next_sibling().text
        if status_in_cart not in status_in_table:
            unexpected_statuses.append(
                UNEXPECTED_STATUS.format(
                    url=pep_url,
                    status_in_cart=status_in_cart,
                    statuses_in_table=list(status_in_table)
                )
            )
        statuses[status_in_cart] += 1
    if errors:
        logging.error('\n'.join(errors))
    if unexpected_statuses:
        logging.error(
            UNEXPECTED_STATUSES.format('\n'.join(unexpected_statuses))
        )
    return [
        HEADER_PEP,
        *statuses.items(),
        (FOOTER_PEP, sum(statuses.values())),
    ]


MODE_TO_FUNCTION = {
    WHATS_NEW_MODE: whats_new,
    LATEST_VERSIONS_MODE: latest_versions,
    DOWNLOAD_MODE: download,
    PEP_MODE: pep,
}


def main():
    configure_logging()
    logging.info(PARSER_START)
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(COMMAND_ARGUMENTS.format(args))
    try:
        session = requests_cache.CachedSession()
        if args.clear_cache:
            session.cache.clear()
        parser_mode = args.mode
        results = MODE_TO_FUNCTION[parser_mode](session)
        if results is not None:
            control_output(results, args)
        logging.info(PARSER_FINISH)
    except Exception as error:
        logging.exception(
            PARSER_FINISH_WITH_ERROR.format(error), stack_info=True
        )


if __name__ == '__main__':
    main()
