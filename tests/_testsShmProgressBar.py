import multiprocessing
import os.path
import random
import sys
import tempfile
import time
from subprocess import Popen

import joblib

from progressBarDistributed.shmProgressBar import SharedMemoryProgressBarWorker, SharedMemoryProgressBar


def _test_locky(n_jobs):

    def worker(worker_id, steps, shm_name):
        with SharedMemoryProgressBarWorker(worker_id, shm_name) as pbar:
            pbar.set_total_steps(steps)
            for _ in range(steps):
                time.sleep(0.1)
                pbar.update(1)
            return steps

    args_list = [(i, random.randint(10, 20)) for i in range(n_jobs)]

    with SharedMemoryProgressBar(n_jobs) as pbar:
        results = joblib.Parallel(n_jobs=n_jobs)(
            joblib.delayed(worker)(i, steps, pbar.shm_name) for i, steps in args_list
        )

        assert  sum(results) == pbar.get_cum_steps()


def _multiprocessing_worker(worker_id, steps, shm_name):
    with SharedMemoryProgressBarWorker(worker_id, shm_name) as pbar:
        pbar.set_total_steps(steps)
        for _ in range(steps):
            time.sleep(0.1)
            pbar.update(1)
    return steps

def _test_multiprocessing_pool(n_jobs):

    with SharedMemoryProgressBar(n_jobs) as pbar:
        shm_name = pbar.shm_name
        args_list = [(i, random.randint(10, 20), shm_name) for i in range(n_jobs)]
        with multiprocessing.Pool(n_jobs) as pool:
            results = pool.starmap(_multiprocessing_worker, args_list)
        assert sum(results) == pbar.get_cum_steps()

def _test_multiprocessing_process(n_jobs):

    with SharedMemoryProgressBar(n_jobs) as pbar:
        shm_name = pbar.shm_name
        args_list = [(i, random.randint(10, 20), shm_name) for i in range(n_jobs)]
        processes = []
        for i in range(n_jobs):
            p = multiprocessing.Process(target=_multiprocessing_worker, args=args_list[i])
            p.start()
            processes.append(p)
        for p in processes:
            p.join()

def _test_subprocess(n_jobs):

    processes = []
    with SharedMemoryProgressBar(n_jobs) as pbar:
        for i in range(n_jobs):
            env = os.environ.copy()
            env["PROGRESS_BAR_WORKER_ID"] = str(i)
            cmd = [sys.executable, "-m", "tests._workerTestForPopen", "--die", "none", "--steps", str(1+i*10),
                   "--shm_name", pbar.shm_name]
            print(cmd)
            p = Popen(cmd, bufsize=32, universal_newlines=True, shell=False, env=env, )
            processes.append(p)
        # Wait for the processes to finish
        for i, p in enumerate(processes):
            out, err = p.communicate()


def _test_subprocess_death(n_jobs):

    for k in ["end", "start"]:
        processes = []
        with SharedMemoryProgressBar(n_jobs) as pbar:
            for i in range(n_jobs):
                env = os.environ.copy()
                env["PROGRESS_BAR_WORKER_ID"] = str(i)
                cmd = [sys.executable, "-m", "tests._workerTestForPopen",
                       "--die", "none" if i != 1 else k,
                       "--steps", str(1+i*10),
                       "--shm_name", pbar.shm_name]
                print(cmd)
                p = Popen(cmd, bufsize=32, universal_newlines=True, shell=False, env=env, )
                processes.append(p)
            # Wait for the processes to finish
            for i, p in enumerate(processes):
                out, err = p.communicate()


def _test_worker_death_locky(n_jobs):

    def unstable_worker(worker_id, steps, shm_name):
        print(f"worker_id {worker_id}")
        with SharedMemoryProgressBarWorker(worker_id, shm_name) as pbar:
            pbar.set_total_steps(steps)
            for _ in range(steps):
                if worker_id == 1:
                    raise Exception(f"Worker died ({worker_id})!")
                time.sleep(0.1)
                pbar.update(1)
            return steps

    with SharedMemoryProgressBar(n_jobs) as shared_progress_bar:
        shm_name = shared_progress_bar.shm_name
        args_list = [(i, random.randint(10, 20), shm_name) for i in range(n_jobs)]

        try:

            results = joblib.Parallel(n_jobs=n_jobs, return_as="generator")(
                joblib.delayed(unstable_worker)(*args) for args in args_list
            )

            completed_steps = 0
            for r in results:
                    completed_steps += r
        except Exception as e:
            print(f"A worker died: {str(e)}")
        assert completed_steps <= shared_progress_bar.get_cum_steps()

def _unstable_worker_multiprocessing(worker_id, steps, shm_name):
    print(f"worker_id {worker_id}")
    with SharedMemoryProgressBarWorker(worker_id, shm_name) as pbar:
        pbar.set_total_steps(steps)
        for _ in range(steps):
            if worker_id == 1:
                raise Exception(f"Worker died ({worker_id})!") #3/0

            time.sleep(0.1)
            pbar.update(1)
        return steps

def _test_worker_death_multiprocessing(n_jobs):

    was_captured = False
    with SharedMemoryProgressBar(n_jobs) as pbar:
        shm_name = pbar.shm_name
        args_list = [(i, random.randint(10, 20), shm_name) for i in range(n_jobs)]
        with multiprocessing.Pool(n_jobs) as pool:
            try:
                results = pool.starmap(_unstable_worker_multiprocessing, args_list)
                print(results)
                assert  False, "Error, the process should have died"
            except Exception as e:
                print(e)
                was_captured = True
    assert was_captured == True

def _test_deatch_multiprocessing_process(n_jobs):

    with SharedMemoryProgressBar(n_jobs) as pbar:
        shm_name = pbar.shm_name
        args_list = [(i, random.randint(10, 20), shm_name) for i in range(n_jobs)]
        processes = []
        for i in range(n_jobs):
            p = multiprocessing.Process(target=_unstable_worker_multiprocessing, args=args_list[i])
            p.start()
            processes.append(p)

        for i, p in enumerate(processes):
            p.join()
            if i == 1:
                assert p.exitcode == 1


if __name__ == "__main__":
    n_jobs = 4
    _test_locky(n_jobs)
    _test_multiprocessing_pool(n_jobs)
    _test_multiprocessing_process(n_jobs)
    _test_subprocess(n_jobs)
    _test_worker_death_locky(n_jobs)
    _test_worker_death_multiprocessing(n_jobs)
    _test_deatch_multiprocessing_process(n_jobs)
    _test_subprocess_death(n_jobs)