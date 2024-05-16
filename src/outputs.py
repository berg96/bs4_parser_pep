import csv
import datetime as dt
import logging

from prettytable import PrettyTable

from constants import (
    BASE_DIR, DATETIME_FORMAT, FILE_OUTPUT, PRETTY_OUTPUT, get_results_dir
)

FILE_SAVE_INFO = 'Файл с результатами был сохранён: {}'


def default_output(results, cli_args):
    for row in results:
        print(*row)


def pretty_output(results, cli_args):
    table = PrettyTable()
    table.field_names = results[0]
    table.align = 'l'
    table.add_rows(results[1:])
    print(table)


def file_output(results, cli_args):
    parser_mode = cli_args.mode
    now_formatted = dt.datetime.now().strftime(DATETIME_FORMAT)
    file_name = f'{parser_mode}_{now_formatted}.csv'
    results_dir = get_results_dir(BASE_DIR)
    results_dir.mkdir(exist_ok=True)
    file_path = results_dir / file_name
    with open(file_path, 'w', encoding='utf-8') as f:
        writer = csv.writer(f, dialect=csv.unix_dialect)
        writer.writerows(results)
    logging.info(FILE_SAVE_INFO.format(file_path))


OUTPUT_METHODS = {
    PRETTY_OUTPUT: pretty_output,
    FILE_OUTPUT: file_output,
    None: default_output,
}


def control_output(results, cli_args):
    return OUTPUT_METHODS[cli_args.output](results, cli_args)
