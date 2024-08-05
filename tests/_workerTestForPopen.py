import os
import sys
import time
from typing import Literal

from progressBarDistributed.shmProgressBar import SharedMemoryProgressBarWorker



def main(shm_name:str, die:Literal["none", "start", "end", "middle"]="none", steps:int=1):

    worker_id = int(os.environ.get("PROGRESS_BAR_WORKER_ID"))
    if die == "start":
        print(f"Died! (worker {worker_id})")
        sys.exit(1)
    time.sleep(1)
    with SharedMemoryProgressBarWorker(worker_id, shm_name) as pbar:
        pbar.set_total_steps(steps)
        for _ in range(steps):
            time.sleep(0.1)
            pbar.update(1)

    if die == "end":
        print(f"Died! (worker {worker_id})")
        sys.exit(1)

    print(f"Done (worker {worker_id})")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--shm_name", type=str)
    parser.add_argument("--die", choices=["none", "start", "end"])
    parser.add_argument("--steps", type=int)

    args = parser.parse_args()
    main(**vars(args))