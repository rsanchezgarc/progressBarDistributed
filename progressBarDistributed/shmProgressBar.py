import threading
import time
from multiprocessing import shared_memory, resource_tracker

import numpy as np
from tqdm import tqdm

from progressBarDistributed.base import AbstractProgressBarWorker, AbstractProgressBar


class SharedMemoryProgressBarWorker(AbstractProgressBarWorker):
    def __init__(self, worker_id, shm_name):
        self.worker_id = worker_id
        self.shm_name = shm_name
        _remove_shm_from_resource_tracker()
        self.shm = shared_memory.SharedMemory(name=self.shm_name)
        self._progress = None
        self._n_workers = None

    @property
    def progress(self):
        if self._progress is None:
            self._progress = np.ndarray((1 + 2 * self.n_workers,), dtype=np.int64, buffer=self.shm.buf)
        return self._progress


    @property
    def n_workers(self):
        if self._n_workers is None:
            self._n_workers = np.ndarray((1,), dtype=np.int64, buffer=self.shm.buf)[0] #First elelemt of the array
        return self._n_workers


    def update(self, n=1):
        self.progress[1 + self.worker_id] += n

    def set_total_steps(self, n):
        self.progress[1 + self.n_workers + self.worker_id] = n

    def get_total_steps(self):
        return self.progress[1 + self.n_workers + self.worker_id]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self):
        try:
            self.shm.close()
        except IOError:
            pass

def _remove_shm_from_resource_tracker():
    """Monkey-patch multiprocessing.resource_tracker so SharedMemory won't be tracked

    More details at: https://bugs.python.org/issue38119
    """
    # Store the original functions
    original_register = resource_tracker.register
    original_unregister = resource_tracker.unregister

    def fix_register(name, rtype):
        if rtype == "shared_memory":
            return
        return original_register(name, rtype)  # Use original_register instead of self
    
    def fix_unregister(name, rtype):
        if rtype == "shared_memory":
            return
        return original_unregister(name, rtype)  # Use original_unregister instead of self
    
    # Apply the monkey patch
    resource_tracker.register = fix_register
    resource_tracker.unregister = fix_unregister

    if "shared_memory" in resource_tracker._CLEANUP_FUNCS:
        del resource_tracker._CLEANUP_FUNCS["shared_memory"]
        

class SharedMemoryProgressBar(AbstractProgressBar):
    def __init__(self, n_workers, shm_name=None):
        """

        :param n_workers:
        :param shm_name: The name of a pre-exisiting share_memory block
        """
        self.n_workers = n_workers
        self.shm = shared_memory.SharedMemory(create=shm_name is None,
                                              size=(1 + 2 * n_workers) * 8, name=shm_name)
        self.shm_name = self.shm.name
        self.stop_event = threading.Event()

        self.progress = np.ndarray((1 + 2 * n_workers,), dtype=np.int64, buffer=self.shm.buf)
        self.progress[0] = n_workers  # Store n_workers in the first element
        self.progress[1:1+n_workers] = 0  # Initialize step counters all to 0
        self.progress[1+n_workers:] = -1  # Initialize totals to -1

        self.progress_thread = None

    def get_cum_steps(self):
        return np.sum(self.progress[1:1+self.n_workers])

    def get_total_steps(self):
        return np.sum(self.progress[1+self.n_workers:])

    def are_workers_ready(self):
        return (self.progress[1+self.n_workers:] > 0).all()

    def set_total_steps(self, n, worker_id):
        self.progress[1 + self.n_workers + worker_id] = n
        
    def progress_bar_thread(self, refresh_seconds=0.5, *args, **kwargs):
        def _progress_bar_thread():
            while not self.stop_event.is_set() and not self.are_workers_ready():
                time.sleep(0.1 * refresh_seconds)
            total_steps = self.get_total_steps()

            with tqdm(total=total_steps, dynamic_ncols=True, *args, **kwargs) as pbar:
                while not self.stop_event.is_set() and self.get_cum_steps() < total_steps:
                    pbar.n = self.get_cum_steps()
                    pbar.refresh()
                    time.sleep(refresh_seconds)

                pbar.n = self.get_cum_steps()
                pbar.refresh()

        t = threading.Thread(target=_progress_bar_thread)
        t.start()
        return t

    def __enter__(self):
        self.progress_thread = self.progress_bar_thread()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        self.progress_thread = None
        return False

    def close(self):
        self.stop_event.set()
        if self.progress_thread and self.progress_thread.is_alive():
            self.progress_thread.join()
        self.cleanup()

    def cleanup(self):
        if hasattr(self, 'shm'):
            try:
                self.shm.close()
                self.shm.unlink()
            except IOError:
                pass  # The shared memory might already be unlinked

    @staticmethod
    def get_worker(worker_id, shm_name):
        return SharedMemoryProgressBarWorker(worker_id, shm_name)


def _test():
    def worker(worker_id, args, shm_name, **kwargs):

        pbar = SharedMemoryProgressBar.get_worker(worker_id, shm_name)
        n_steps = sum(args)
        pbar.set_total_steps(n_steps)

        # Simulate work
        for _ in range(n_steps):
            time.sleep(0.3)  # Simulating some work
            pbar.update(1)

        pbar.close()
        return sum(args)  # Return some result

    n_jobs = 4  # Number of parallel jobs
    args_list = [(i, i + 1, i + 2) for i in range(n_jobs)]


    # Run jobs in parallel
    import joblib
    with SharedMemoryProgressBar(n_jobs) as prBar:
        results = joblib.Parallel(n_jobs=n_jobs, return_as="generator", batch_size=1)(
            joblib.delayed(worker)(i, args, prBar.shm_name)
            for i, args in enumerate(args_list)
        )

        _results = []
        for r in results:
            _results.append(r)

    print("Results:", _results)

if __name__ == "__main__":
    _test()
