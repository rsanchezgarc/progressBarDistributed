"""Edge case tests for progressBarDistributed."""
import time
import pytest

from progressBarDistributed.shmProgressBar import (
    SharedMemoryProgressBarWorker,
    SharedMemoryProgressBar,
)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_single_worker(self):
        """Test with a single worker."""
        with SharedMemoryProgressBar(1) as pbar:
            worker = SharedMemoryProgressBarWorker(0, pbar.shm_name)
            worker.set_total_steps(5)

            for _ in range(5):
                worker.update(1)

            assert pbar.get_cum_steps() == 5
            assert pbar.get_total_steps() == 5
            worker.close()

    def test_zero_updates(self):
        """Test worker with no updates."""
        with SharedMemoryProgressBar(2) as pbar:
            worker0 = SharedMemoryProgressBarWorker(0, pbar.shm_name)
            worker1 = SharedMemoryProgressBarWorker(1, pbar.shm_name)

            worker0.set_total_steps(10)
            worker1.set_total_steps(10)

            # Don't update, just check initial state
            assert pbar.get_cum_steps() == 0

            worker0.close()
            worker1.close()

    def test_large_updates(self):
        """Test updating with large increments."""
        with SharedMemoryProgressBar(1) as pbar:
            worker = SharedMemoryProgressBarWorker(0, pbar.shm_name)
            worker.set_total_steps(1000000)

            worker.update(500000)
            assert pbar.get_cum_steps() == 500000

            worker.update(500000)
            assert pbar.get_cum_steps() == 1000000

            worker.close()

    def test_update_default_increment(self):
        """Test update with default increment of 1."""
        with SharedMemoryProgressBar(1) as pbar:
            worker = SharedMemoryProgressBarWorker(0, pbar.shm_name)
            worker.set_total_steps(10)

            for _ in range(10):
                worker.update()  # Default n=1

            assert pbar.get_cum_steps() == 10
            worker.close()

    def test_worker_context_manager(self):
        """Test worker using context manager."""
        with SharedMemoryProgressBar(1) as pbar:
            with SharedMemoryProgressBarWorker(0, pbar.shm_name) as worker:
                worker.set_total_steps(5)
                worker.update(5)
                assert pbar.get_cum_steps() == 5

    def test_multiple_close_calls(self):
        """Test that multiple close calls don't cause errors."""
        pbar = SharedMemoryProgressBar(1)
        pbar.close()
        pbar.close()  # Should not raise an error

    def test_worker_n_workers_property(self):
        """Test that worker can access n_workers property."""
        n_workers = 5
        with SharedMemoryProgressBar(n_workers) as pbar:
            worker = SharedMemoryProgressBarWorker(0, pbar.shm_name)
            assert worker.n_workers == n_workers
            worker.close()

    def test_set_total_steps_multiple_times(self):
        """Test setting total steps multiple times."""
        with SharedMemoryProgressBar(1) as pbar:
            worker = SharedMemoryProgressBarWorker(0, pbar.shm_name)

            worker.set_total_steps(10)
            assert worker.get_total_steps() == 10

            worker.set_total_steps(20)
            assert worker.get_total_steps() == 20

            worker.close()

    def test_many_workers(self):
        """Test with many workers."""
        n_workers = 10
        with SharedMemoryProgressBar(n_workers) as pbar:
            workers = []
            for i in range(n_workers):
                worker = SharedMemoryProgressBarWorker(i, pbar.shm_name)
                worker.set_total_steps(i + 1)
                workers.append(worker)

            # Total should be sum of 1+2+3+...+10 = 55
            assert pbar.get_total_steps() == sum(range(1, n_workers + 1))

            # Update each worker by 1
            for worker in workers:
                worker.update(1)

            assert pbar.get_cum_steps() == n_workers

            for worker in workers:
                worker.close()

    def test_reusing_shm_name(self):
        """Test creating a progress bar with an existing shm_name."""
        # Create first progress bar
        pbar1 = SharedMemoryProgressBar(2)
        shm_name = pbar1.shm_name

        # Create second progress bar with same shm_name
        pbar2 = SharedMemoryProgressBar(2, shm_name=shm_name)

        assert pbar2.shm_name == shm_name

        # Clean up
        pbar2.close()
        # Note: pbar1 cleanup will be handled by pbar2


class TestProgressBarThreading:
    """Test progress bar threading functionality."""

    def test_progress_bar_thread_completes(self):
        """Test that progress bar thread completes successfully."""
        n_workers = 2

        with SharedMemoryProgressBar(n_workers) as pbar:
            # Set totals
            for i in range(n_workers):
                pbar.set_total_steps(10, i)

            # Simulate work
            time.sleep(0.5)

            # Update progress
            for i in range(n_workers):
                for _ in range(10):
                    pbar.progress[1 + i] += 1

            time.sleep(0.5)

        # If we get here without hanging, test passes

    def test_early_exit(self):
        """Test exiting before workers complete."""
        n_workers = 2

        with SharedMemoryProgressBar(n_workers) as pbar:
            # Set only one worker's total
            pbar.set_total_steps(10, 0)
            # Don't set the second worker's total
            # Progress bar should handle this gracefully
            time.sleep(0.2)

        # Should exit cleanly


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
