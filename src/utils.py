from bs4 import BeautifulSoup
from requests import RequestException

from exceptions import ParserFindTagException

LOADING_URL_ERROR = 'Возникла ошибка при загрузке страницы {}'
TAG_NOT_FOUND_ERROR = 'Не найден тег {} {}'


def get_response(session, url, encoding='utf-8'):
    try:
        response = session.get(url)
        response.encoding = encoding
        return response
    except RequestException as error:
        raise ConnectionError(error, LOADING_URL_ERROR.format(url))


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=({} if attrs is None else attrs))
    if searched_tag is None:
        raise ParserFindTagException(TAG_NOT_FOUND_ERROR.format(tag, attrs))
    return searched_tag


def cook_soup(session, url):
    return BeautifulSoup(get_response(session, url).text, features='lxml')
