from pathlib import Path

MAIN_DOC_URL = 'https://docs.python.org/3/'
MAIN_PEPS_URL = 'https://peps.python.org/'

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'parser.log'
RESULTS_DIR = BASE_DIR / 'results'
DOWNLOADS_DIR = BASE_DIR / 'downloads'

DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'

EXPECTED_STATUS = {
    'A': ('Active', 'Accepted'),
    'D': ('Deferred',),
    'F': ('Final',),
    'P': ('Provisional',),
    'R': ('Rejected',),
    'S': ('Superseded',),
    'W': ('Withdrawn',),
    '': ('Draft', 'Active'),
}

PRETTY_OUTPUT = 'pretty'
FILE_OUTPUT = 'file'
NAME_RESULTS_DIR = 'results'
NAME_DOWNLOADS_DIR = 'downloads'


def get_results_dir(base_dir):
    return base_dir / NAME_RESULTS_DIR


def get_downloads_dir(base_dir):
    return base_dir / NAME_DOWNLOADS_DIR
