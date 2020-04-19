import os
from multiprocessing import Pool

import sys


def run_process(process):
    os.system(f'{sys.executable} {process}')


def main():
    pool = Pool(processes=4)
    pool.map(run_process, ('-m otp.messagedirector', '-m otp.dbserver', '-m otp.stateserver', '-m otp.clientagent'))


if __name__ == "__main__":
    main()
