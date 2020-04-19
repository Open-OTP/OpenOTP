import os
from multiprocessing import Pool


def run_process(process):
    os.system('python3.7 {}'.format(process))


def main():
    pool = Pool(processes=3)
    pool.map(run_process, ('messagedirector.py',))


if __name__ == "__main__":
    main()
