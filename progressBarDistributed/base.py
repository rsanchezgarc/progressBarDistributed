from abc import ABC, abstractmethod
import numpy as np
from multiprocessing import shared_memory
import threading
import time
from tqdm import tqdm
import joblib

class AbstractProgressBarWorker(ABC):
    @abstractmethod
    def update(self, n=1):
        pass

    @abstractmethod
    def set_total_steps(self, n):
        pass

    @abstractmethod
    def close(self):
        pass

    @property
    @abstractmethod
    def n_workers(self):
        pass

class AbstractProgressBar(ABC):
    @abstractmethod
    def get_cum_steps(self):
        pass

    @abstractmethod
    def get_total_steps(self):
        pass

    @abstractmethod
    def are_workers_ready(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def progress_bar_thread(self, refresh_seconds=0.5, *args, **kwargs):
        pass

