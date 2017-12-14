import corelib.util as util
import csv
import ctypes
import itertools
import json
import os
import pickle
import pickletools
import sqlite3
import threading

csv.field_size_limit(2**31 - 1)

database_path = util.relative_path(__file__, "../datasets/datasets.sql")
settings = json.load(open(util.relative_path(__file__, "../datasets/index.json")))

helper_dll_path = util.relative_path(__file__, "libdatabase.so")
helper_dll = None


class ThreadLocalConnection(threading.local):
    connection = sqlite3.connect(database_path)

tlc = ThreadLocalConnection()


def setup_dll():
    dll = ctypes.CDLL(helper_dll_path)

    dll.build_iindex_database.argtypes = [ctypes.c_char_p]
    dll.build_iindex_database.restype = None
    dll.translate_string.argtypes = [ctypes.c_int, ctypes.c_char_p]
    dll.translate_string.restype = ctypes.c_int
    dll.load_runtime_data.restype = None

    return dll


@util.run_once
def create_tables():
    cursor = tlc.connection.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS data (file_id integer, key integer primary key, contents text)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS iindex (file_id integer, key integer primary key, contents text)''')


def _rows(table, dataset_name):
    create_tables()
    cursor = tlc.connection.cursor()

    dataset_name = os.path.basename(dataset_name)
    dataset_id = settings[dataset_name]["id"]

    cursor.execute('''SELECT count(*) FROM {} WHERE file_id = :file_id'''.format(table),
                   {"table": table, "file_id": dataset_id})

    res = cursor.fetchone()

    if res is None:
        return 0

    return res[0]


def data_rows(dataset_name):
    return _rows("data", dataset_name)


def iindex_rows(dataset_name):
    return _rows("iindex", dataset_name)


def iterate_over_file(dataset_name):
    create_tables()
    cursor = tlc.connection.cursor()

    dataset_name = os.path.basename(dataset_name)
    dataset_id = settings[dataset_name]["id"]

    cursor.execute('''SELECT key, contents FROM data WHERE filename = :filename''',
                   {"filename": dataset_id})

    while True:
        res = cursor.fetchone()

        if (res is None):
            break

        ident = res[0]

        try:
            contents = json.loads(res[1])
        except UnicodeDecodeError:
            print("The ****in decoder don't work")
            continue

        yield (ident, contents)


def lookup_data_id(dataset_id, ident):
    create_tables()
    cursor = tlc.connection.cursor()

    cursor.execute('''SELECT contents FROM data WHERE file_id = :file_id and key = :ident''',
                   {"file_id": dataset_id, "ident": ident})

    res = cursor.fetchone()

    if (res is None):
        return ValueError("No data id found")

    contents = json.loads(res[0])

    return contents


def lookup_iindex_id(dataset_id, ident):
    if ident is None:
        return []

    create_tables()

    cursor = tlc.connection.cursor()

    cursor.execute('''SELECT contents FROM iindex WHERE file_id = :file_id and key = :ident''',
                   {"file_id": dataset_id, "ident": ident})

    res = cursor.fetchone()

    if (res is None):
        return ValueError("No iindex id found")

    contents = json.loads(res[0])

    return contents


def lookup_data_range(dataset_id):
    create_tables()
    cursor = tlc.connection.cursor()

    cursor.execute('''SELECT max(key) FROM data WHERE file_id = :file_id''',
                   {"file_id": dataset_id})

    res_max = cursor.fetchone()

    cursor.execute('''SELECT min(key) FROM data WHERE file_id = :file_id''',
                   {"file_id": dataset_id})

    res_min = cursor.fetchone()

    return (res_min[0], res_max[0])


@util.run_once
def load_runtime_data():
    global helper_dll
    create_tables()
    if helper_dll is None:
        helper_dll = setup_dll()

    helper_dll.load_runtime_data()


def build_iindex_database(filename):
    global helper_dll
    create_tables()
    if helper_dll is None:
        helper_dll = setup_dll()

    helper_dll.build_iindex_database(bytes(filename, encoding='utf8'))


def translate_string(dataset_id, string):
    global helper_dll
    create_tables()
    load_runtime_data()
    if helper_dll is None:
        helper_dll = setup_dll()

    res = helper_dll.translate_string(ctypes.c_int(dataset_id), bytes(string, encoding='utf8'))

    if res == -1:
        return None
    return res


def commit():
    create_tables()
    tlc.connection.commit()
