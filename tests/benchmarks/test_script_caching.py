import time
from statistics import fmean
import cProfile
import pstats
import io
from pstats import SortKey

from fle.env import FactorioInstance

INVENTORY = {
    "coal": 50,
    "copper-plate": 50,
    "iron-plate": 50,
    "iron-chest": 2,
    "burner-mining-drill": 3,
    "electric-mining-drill": 1,
    "assembling-machine-1": 1,
    "stone-furnace": 9,
    "transport-belt": 50,
    "boiler": 1,
    "burner-inserter": 32,
    "pipe": 15,
    "steam-engine": 1,
    "small-electric-pole": 10,
}


def profile(func):
    def wrapper(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        result = func(*args, **kwargs)
        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats(SortKey.CUMULATIVE)
        ps.print_stats(20)  # Print top 20 time-consuming functions
        print(s.getvalue())
        return result

    return wrapper


@profile
def test_script_caching():
    uncached_times = []
    cached_times = []
    RUNS = 10

    def print_running_average(times, run, category):
        avg = fmean(times)
        print(f"Run {run + 1} - {category} running average: {avg:.4f} seconds")

    print("\nTesting cached performance:")
    for i in range(RUNS):
        start_time = time.time()
        instance = FactorioInstance(
            address="localhost",
            bounding_box=200,
            tcp_port=27000,
            inventory=INVENTORY,
            cache_scripts=True,
        )
        end_time = time.time() - start_time
        cached_times.append(end_time)
        print(f"Run {i + 1} - Cached time: {end_time:.4f} seconds")
        print_running_average(cached_times, i, "Cached")
        print()

    print("Testing uncached performance:")
    for i in range(RUNS):
        start_time = time.time()
        instance = FactorioInstance(  # noqa
            address="localhost",
            bounding_box=200,
            tcp_port=27000,
            inventory=INVENTORY,
            cache_scripts=False,
        )
        end_time = time.time() - start_time
        uncached_times.append(end_time)
        print(f"Run {i + 1} - Uncached time: {end_time:.4f} seconds")
        print_running_average(uncached_times, i, "Uncached")
        print()

    mean_uncached = fmean(uncached_times)
    mean_cached = fmean(cached_times)

    print("Final Results:")
    print(f"Mean Uncached Time: {mean_uncached:.4f} seconds")
    print(f"Mean Cached Time: {mean_cached:.4f} seconds")
    print(
        f"Performance Improvement: {(mean_uncached - mean_cached) / mean_uncached * 100:.2f}%"
    )

    assert mean_cached < mean_uncached, (
        "Caching did not improve performance as expected."
    )


if __name__ == "__main__":
    test_script_caching()
