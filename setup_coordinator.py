import enum
import json
import os
import subprocess
import sys
import tarfile

python_modules_needed = ['anytree', 'flask']
packages_needed = ['libsqlite3-dev', 'libicu-dev', 'make', 'g++', 'rsync']


def status(name, success):
    return print("\t{} -- {}".format(name,
                                     "\u001b[32;1mSuccess\u001b[0m" if success else "\u001b[31;1mFailure\u001b[0m"))


def error(text):
    print("\u001b[31;1mERROR:\u001b[0m {}".format(text))
    exit(1)


def check_python_version():
    print("Checking python version:")

    success = sys.version_info.major == 3 and sys.version_info.minor >= 5
    name = "{}.{}".format(sys.version_info.major, sys.version_info.minor)
    status(name, success)

    if (not success):
        error("Please install Python 3.5 or greater")


def check_python_modules():
    print("Checking python modules:")

    successes = {}
    for module in python_modules_needed:
        successes[module] = subprocess.run([sys.executable, '-c', 'import {}'.format(module)],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0

    for name, result in sorted(successes.items()):
        status(name, result)

    if (False in successes.values()):
        error("Please install {}".format(" ".join([name for name, result in successes.items() if not result])))


def check_system_packages():
    print("Checking system packages:")
    dpkg_query = subprocess.run(['dpkg-query', '--list'], stdout=subprocess.PIPE)

    names = [row.split()[1].partition(':')[0]
             for row in dpkg_query.stdout.decode('utf8').split('\n')[5:] if len(row) >= 2]

    successes = {package: package in names for package in packages_needed}

    for name, result in sorted(successes.items()):
        status(name, result)

    if (False in successes.values()):
        error("Please install {}".format(" ".join([name for name, result in successes.items() if not result])))


def check_submodules():
    print("Checking submodules:")
    submodule_status = subprocess.run(['git', 'submodule', 'status', '--recursive'], stdout=subprocess.PIPE)

    successes = {row.split()[1]: row[0] == ' '
                 for row in submodule_status.stdout.decode('utf8').split('\n') if len(row)}

    for name, result in sorted(successes.items()):
        status(name, result)

    if (False in successes.values()):
        error("Please run 'git submodule update --init --recursive'")


def run_make():
    print("Building libdatabase.so:")
    make_ret = subprocess.run(['make', 'OPTIMIZATION=-O3'])

    status("libdatabase.so", make_ret.returncode == 0)

    if (make_ret.returncode != 0):
        error("Make failed.")


class CSVStatus(enum.Enum):
    OK = 1
    MISSING = 2
    ZIPPED = 3
    IGNORE = 4


def print_csv_status(name, status):
    if (status == CSVStatus.OK):
        status_msg = "\u001b[32;1mFound"
    elif (status == CSVStatus.MISSING):
        status_msg = "\u001b[31;1mMissing"
    elif (status == CSVStatus.ZIPPED):
        status_msg = "\u001b[33;1mZipped"
    elif (status == CSVStatus.IGNORE):
        status_msg = "\u001b[31mToo Big"

    print("\t{} -- {}\u001b[0m".format(name, status_msg))


def check_list_of_csvs(mb_limit):
    print("Checking status of CSVs")

    byte_limit = 1024 * 1024 * mb_limit

    settings = json.load(open("datasets/index.json"))

    csvs = [os.path.basename(file) for file in os.listdir("datasets") if file.endswith(".csv")]
    tars = [os.path.basename(file)[:-7] for file in os.listdir("datasets") if file.endswith(".tar.gz")]

    res = {}
    for csv in settings:
        if csv not in csvs:
            tar_wo_extent = os.path.splitext(csv)[0]
            tar_full_path = os.path.join("datasets/", tar_wo_extent + ".tar.gz")
            tar_usable = (tar_wo_extent in tars) and (os.stat(tar_full_path).st_size == settings[csv]["tar_size"])

            res[csv] = CSVStatus.ZIPPED if tar_usable else CSVStatus.MISSING
        elif settings[csv]["size"] > byte_limit:
            res[csv] = CSVStatus.IGNORE
        else:
            res[csv] = CSVStatus.OK

    for name, result in res.items():
        print_csv_status(name, result)

    return res


def download_csv(csv_list):
    if CSVStatus.MISSING not in csv_list.values():
        return

    print("Downloading CSVs:")

    prefix = 'www.static.connorwfitzgerald.com/csv_cache/'

    files = [prefix + os.path.splitext(name)[0] + ".tar.gz"
             for name, status in csv_list.items()
             if status == CSVStatus.MISSING]
    wget = subprocess.run(['wget', '--continue', '-P', 'datasets' '', *files])

    for name, result in csv_list.items():
        if result == CSVStatus.MISSING:
            csv_list[name] = CSVStatus.ZIPPED
            status(name, True)


def unzip_csv(csv_list):
    if CSVStatus.ZIPPED not in csv_list.values():
        return

    print("Unzipping CSVs:")

    for name, status in csv_list.items():
        if status == CSVStatus.ZIPPED:
            sys.stdout.write("\t{}... ".format(name))
            sys.stdout.flush()
            tar_loc = os.path.join("datasets/", os.path.splitext(name)[0] + ".tar.gz")

            file = tarfile.open(tar_loc, 'r')

            file.extractall(".")

            print("\u001b[32;1mSuccess\u001b[0m")


def main():
    print("Search Engine Setup Coordinator")
    check_python_version()
    check_python_modules()
    check_system_packages()
    check_submodules()
    run_make()
    csv_list = check_list_of_csvs(200)
    download_csv(csv_list)
    unzip_csv(csv_list)


if __name__ == "__main__":
    main()