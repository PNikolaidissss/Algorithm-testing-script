
import csv
import multiprocessing as mp
import random
import statistics
import time
import traceback
from pathlib import Path

SIZES = [100, 1000, 5000]
REPETITIONS = 5
TIMEOUT = 3
OUTPUT_FILE = Path("comparison_results.csv")


def read_algorithm(label):
    print(f"\nPaste Algorithm {label}")
    print("Define a function named algorithm(data).")
    print("Type END on a new line when finished:\n")

    lines = []

    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)

    source = "\n".join(lines).strip()

    if not source:
        raise ValueError("Algorithm cannot be empty.")

    return source


def child_execute(source, data, connection):
    try:
        namespace = {"__builtins__": __builtins__}

        exec(compile(source, "<user_algorithm>", "exec"), namespace)

        algorithm = namespace.get("algorithm")

        if not callable(algorithm):
            raise ValueError(
                "Your code must define def algorithm(data):"
            )

        start = time.perf_counter()
        result = algorithm(data)
        elapsed = time.perf_counter() - start

        connection.send(("ok", result, elapsed))

    except BaseException:
        connection.send(("error", traceback.format_exc()))

    finally:
        connection.close()


def run_algorithm(source, data):
    parent, child = mp.Pipe(duplex=False)

    process = mp.Process(
        target=child_execute,
        args=(source, data, child)
    )

    process.start()
    child.close()
    process.join(TIMEOUT)

    if process.is_alive():
        process.terminate()
        process.join()
        parent.close()
        raise TimeoutError("Algorithm exceeded the time limit.")

    if not parent.poll():
        parent.close()
        raise RuntimeError("Algorithm returned no result.")

    message = parent.recv()
    parent.close()

    if message[0] == "error":
        raise RuntimeError(message[1])

    return message[1], message[2]


def create_datasets():
    rng = random.Random(42)

    return {
        size: [
            rng.randint(-10000, 10000)
            for _ in range(size)
        ]
        for size in SIZES
    }


def benchmark(source, datasets):
    results = {}

    for size, original in datasets.items():
        expected = sorted(original)
        times = []

        for _ in range(REPETITIONS):
            output, elapsed = run_algorithm(
                source,
                original.copy()
            )

            if output != expected:
                raise ValueError(
                    f"Incorrect result for input size {size}. "
                    "Both algorithms must sort in ascending order."
                )

            times.append(elapsed)

        results[size] = {
            "median": statistics.median(times),
            "minimum": min(times),
            "maximum": max(times)
        }

    return results


def save_results(a, b):
    with OUTPUT_FILE.open(
        "w", newline="", encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "input_size",
            "algorithm_a_median",
            "algorithm_b_median",
            "faster_algorithm"
        ])

        for size in SIZES:
            time_a = a[size]["median"]
            time_b = b[size]["median"]

            if time_a < time_b:
                winner = "A"
            elif time_b < time_a:
                winner = "B"
            else:
                winner = "Tie"

            writer.writerow([
                size,
                time_a,
                time_b,
                winner
            ])


def main():
    print("=" * 55)
    print("                  ALGOFORGE")
    print("           Algorithm Comparison Lab")
    print("=" * 55)

    print("\nBoth algorithms must solve the same problem.")
    print("For this version, both must sort lists in ascending order.")
    print("\nWARNING: Only run code you trust.")
    print("This prototype is NOT a secure sandbox.")

    source_a = read_algorithm("A")
    source_b = read_algorithm("B")

    datasets = create_datasets()

    print("\nRunning experiments...")

    results_a = benchmark(source_a, datasets)
    results_b = benchmark(source_b, datasets)

    print("\n" + "=" * 65)
    print("RESULTS — MEDIAN EXECUTION TIME")
    print("=" * 65)

    print(
        f"{'Size':>8} | {'Algorithm A':>15} | "
        f"{'Algorithm B':>15} | {'Winner':>8}"
    )

    print("-" * 65)

    for size in SIZES:
        a = results_a[size]["median"]
        b = results_b[size]["median"]

        if a < b:
            winner = "A"
        elif b < a:
            winner = "B"
        else:
            winner = "Tie"

        print(
            f"{size:>8} | {a:>12.8f} s | "
            f"{b:>12.8f} s | {winner:>8}"
        )

    save_results(results_a, results_b)

    print(f"\nResults saved to: {OUTPUT_FILE.resolve()}")
    print("\nExperiments completed.")
    print("Performance depends on hardware and input data.")


if __name__ == "__main__":
    mp.freeze_support()

    try:
        main()
    except (ValueError, RuntimeError, TimeoutError) as error:
        print(f"\nERROR: {error}")
    except KeyboardInterrupt:
        print("\nExperiment cancelled.")




