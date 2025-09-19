# progressBarDistributed

progressBarDistributed is a Python library that provides a tqdm-based progress bar for distributed tasks using shared memory.
It allows you to track the progress of multiple workers across different processes.

## Features

- Distributed progress tracking using shared memory
- Compatible with multiprocessing and joblib parallel processing
- Customizable progress bar display using tqdm

## Installation

To install SharedMemoryProgressBar, you can use pip:
```
pip install .
```

## Usage


### Usage multiprocessing
Here's a basic example of how to use SharedMemoryProgressBar using multiprocessing

```python

import multiprocessing
def _multiprocessing_worker(worker_id, steps, shm_name):
    import time
    from progressBarDistributed import SharedMemoryProgressBarWorker
    with SharedMemoryProgressBarWorker(worker_id, shm_name) as pbar:
        pbar.set_total_steps(steps)
        for _ in range(steps):
            time.sleep(0.1)
            pbar.update(1)
    raise NotImplementedError()

def main(n_jobs):
    from progressBarDistributed import SharedMemoryProgressBar
    import random
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
if __name__ == "__main__":
    main(4)
```

### Usage subprocess
Here's a basic example of how to use SharedMemoryProgressBar using subprocesses

```python

### worker.py
import sys, os
import random
import time
from progressBarDistributed import SharedMemoryProgressBarWorker

def compute_steps():
    random.randint(0, 1000)
    
if __name__ == "__main__":
    shm_name = sys.argv[1]
    worker_id = int(os.environ.get("PROGRESS_BAR_WORKER_ID"))
    steps = compute_steps() #Compute the number of steps that this worker is going to do
    with SharedMemoryProgressBarWorker(worker_id, shm_name) as pbar:
        pbar.set_total_steps(steps)
        for _ in range(steps):
            time.sleep(0.1)
            pbar.update(1)
### END OF worker.py
### main.py
from subprocess import Popen
from progressBarDistributed import SharedMemoryProgressBar

def main(n_jobs):
    processes = []
    with SharedMemoryProgressBar(n_jobs) as pbar:
        for i in range(n_jobs):
            env = os.environ.copy()
            env["PROGRESS_BAR_WORKER_ID"] = str(i)
            cmd = [sys.executable, "worker.py", pbar.shm_name]
            print(cmd)
            p = Popen(cmd, universal_newlines=True, shell=False, env=env)
            processes.append(p)
        # Wait for the processes to finish
        for i, p in enumerate(processes):
            out, err = p.communicate()
if __name__ == "__main__":
    main(4)
### END OF main.py
```

## API Reference
### SharedMemoryProgressBar

```
__init__(n_workers, shm_name=None): Initialize the progress bar
get_worker(worker_id, shm_name): Get a worker instance
close(): Clean up resources
```

### SharedMemoryProgressBarWorker

update(n=1): Update progress
set_total_steps(n): Set the total number of steps for the worker
