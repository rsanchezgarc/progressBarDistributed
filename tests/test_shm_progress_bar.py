"""Tests for SharedMemoryProgressBar and SharedMemoryProgressBarWorker."""
import multiprocessing
import os
import random
import sys
import time
from subprocess import Popen

import joblib
import pytest

from progressBarDistributed.shmProgressBar import (
    SharedMemoryProgressBarWorker,
    SharedMemoryProgressBar,
)


class TestJoblib:
    """Test SharedMemoryProgressBar with joblib backend."""

    def test_joblib_basic(self):
        """Test basic functionality with joblib parallel processing."""
        n_jobs = 4

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

            assert sum(results) == pbar.get_cum_steps()

    def test_worker_death_joblib(self):
        """Test handling of worker death with joblib."""
        n_jobs = 4

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
                completed_steps = 0

            assert completed_steps <= shared_progress_bar.get_cum_steps()


class TestMultiprocessing:
    """Test SharedMemoryProgressBar with multiprocessing backend."""

    @staticmethod
    def _multiprocessing_worker(worker_id, steps, shm_name):
        """Worker function for multiprocessing tests."""
        with SharedMemoryProgressBarWorker(worker_id, shm_name) as pbar:
            pbar.set_total_steps(steps)
            for _ in range(steps):
                time.sleep(0.1)
                pbar.update(1)
        return steps

    def test_multiprocessing_pool(self):
        """Test with multiprocessing.Pool."""
        n_jobs = 4

        with SharedMemoryProgressBar(n_jobs) as pbar:
            shm_name = pbar.shm_name
            args_list = [(i, random.randint(10, 20), shm_name) for i in range(n_jobs)]
            with multiprocessing.Pool(n_jobs) as pool:
                results = pool.starmap(self._multiprocessing_worker, args_list)
            assert sum(results) == pbar.get_cum_steps()

    def test_multiprocessing_process(self):
        """Test with multiprocessing.Process."""
        n_jobs = 4

        with SharedMemoryProgressBar(n_jobs) as pbar:
            shm_name = pbar.shm_name
            args_list = [(i, random.randint(10, 20), shm_name) for i in range(n_jobs)]
            processes = []
            for i in range(n_jobs):
                p = multiprocessing.Process(target=self._multiprocessing_worker, args=args_list[i])
                p.start()
                processes.append(p)
            for p in processes:
                p.join()

    @staticmethod
    def _unstable_worker_multiprocessing(worker_id, steps, shm_name):
        """Unstable worker that raises exception."""
        print(f"worker_id {worker_id}")
        with SharedMemoryProgressBarWorker(worker_id, shm_name) as pbar:
            pbar.set_total_steps(steps)
            for _ in range(steps):
                if worker_id == 1:
                    raise Exception(f"Worker died ({worker_id})!")

                time.sleep(0.1)
                pbar.update(1)
            return steps

    def test_worker_death_multiprocessing_pool(self):
        """Test handling of worker death with multiprocessing.Pool."""
        n_jobs = 4
        was_captured = False

        with SharedMemoryProgressBar(n_jobs) as pbar:
            shm_name = pbar.shm_name
            args_list = [(i, random.randint(10, 20), shm_name) for i in range(n_jobs)]
            with multiprocessing.Pool(n_jobs) as pool:
                try:
                    results = pool.starmap(self._unstable_worker_multiprocessing, args_list)
                    print(results)
                    assert False, "Error, the process should have died"
                except Exception as e:
                    print(e)
                    was_captured = True
        assert was_captured is True

    def test_worker_death_multiprocessing_process(self):
        """Test handling of worker death with multiprocessing.Process."""
        n_jobs = 4

        with SharedMemoryProgressBar(n_jobs) as pbar:
            shm_name = pbar.shm_name
            args_list = [(i, random.randint(10, 20), shm_name) for i in range(n_jobs)]
            processes = []
            for i in range(n_jobs):
                p = multiprocessing.Process(
                    target=self._unstable_worker_multiprocessing, args=args_list[i]
                )
                p.start()
                processes.append(p)

            for i, p in enumerate(processes):
                p.join()
                if i == 1:
                    assert p.exitcode == 1


class TestSubprocess:
    """Test SharedMemoryProgressBar with subprocess."""

    def test_subprocess_basic(self):
        """Test basic functionality with subprocess."""
        n_jobs = 4
        processes = []

        with SharedMemoryProgressBar(n_jobs) as pbar:
            for i in range(n_jobs):
                env = os.environ.copy()
                env["PROGRESS_BAR_WORKER_ID"] = str(i)
                cmd = [
                    sys.executable,
                    "-m",
                    "tests._workerTestForPopen",
                    "--die",
                    "none",
                    "--steps",
                    str(1 + i * 10),
                    "--shm_name",
                    pbar.shm_name,
                ]
                print(cmd)
                p = Popen(cmd, bufsize=32, universal_newlines=True, shell=False, env=env)
                processes.append(p)
            # Wait for the processes to finish
            for i, p in enumerate(processes):
                out, err = p.communicate()

    @pytest.mark.parametrize("die_mode", ["end", "start"])
    def test_subprocess_death(self, die_mode):
        """Test handling of subprocess death at different stages."""
        n_jobs = 4
        processes = []

        with SharedMemoryProgressBar(n_jobs) as pbar:
            for i in range(n_jobs):
                env = os.environ.copy()
                env["PROGRESS_BAR_WORKER_ID"] = str(i)
                cmd = [
                    sys.executable,
                    "-m",
                    "tests._workerTestForPopen",
                    "--die",
                    "none" if i != 1 else die_mode,
                    "--steps",
                    str(1 + i * 10),
                    "--shm_name",
                    pbar.shm_name,
                ]
                print(cmd)
                p = Popen(cmd, bufsize=32, universal_newlines=True, shell=False, env=env)
                processes.append(p)
            # Wait for the processes to finish
            for i, p in enumerate(processes):
                out, err = p.communicate()


class TestProgressBarBasics:
    """Test basic progress bar functionality."""

    def test_create_and_close(self):
        """Test creating and closing a progress bar."""
        n_workers = 4
        pbar = SharedMemoryProgressBar(n_workers)

        assert pbar.n_workers == n_workers
        assert pbar.get_cum_steps() == 0
        assert pbar.get_total_steps() == -n_workers

        pbar.close()

    def test_context_manager(self):
        """Test using progress bar as context manager."""
        n_workers = 2

        with SharedMemoryProgressBar(n_workers) as pbar:
            assert pbar.n_workers == n_workers
            assert pbar.shm_name is not None

    def test_worker_basic_operations(self):
        """Test basic worker operations."""
        n_workers = 2

        with SharedMemoryProgressBar(n_workers) as pbar:
            worker = SharedMemoryProgressBarWorker(0, pbar.shm_name)

            # Set total steps
            worker.set_total_steps(10)
            assert worker.get_total_steps() == 10

            # Update progress
            worker.update(5)
            assert pbar.get_cum_steps() == 5

            worker.update(3)
            assert pbar.get_cum_steps() == 8

            worker.close()

    def test_multiple_workers(self):
        """Test multiple workers updating progress."""
        n_workers = 3

        with SharedMemoryProgressBar(n_workers) as pbar:
            workers = [
                SharedMemoryProgressBarWorker(i, pbar.shm_name) for i in range(n_workers)
            ]

            # Set total steps for each worker
            for i, worker in enumerate(workers):
                worker.set_total_steps((i + 1) * 10)

            assert pbar.get_total_steps() == 60  # 10 + 20 + 30

            # Update progress
            workers[0].update(5)
            workers[1].update(10)
            workers[2].update(15)

            assert pbar.get_cum_steps() == 30

            # Cleanup
            for worker in workers:
                worker.close()

    def test_are_workers_ready(self):
        """Test checking if workers are ready."""
        n_workers = 2

        with SharedMemoryProgressBar(n_workers) as pbar:
            # Initially workers are not ready (totals are -1)
            assert not pbar.are_workers_ready()

            # Set totals for workers
            worker0 = SharedMemoryProgressBarWorker(0, pbar.shm_name)
            worker0.set_total_steps(10)

            # Still not ready (only one worker set)
            assert not pbar.are_workers_ready()

            worker1 = SharedMemoryProgressBarWorker(1, pbar.shm_name)
            worker1.set_total_steps(20)

            # Now all workers are ready
            assert pbar.are_workers_ready()

            worker0.close()
            worker1.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
