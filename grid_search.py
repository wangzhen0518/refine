import os
import pickle as pk
import numpy as np
import pandas as pd
from typing import List, Tuple, Dict
from extract_results import extract_all
from common import my_inf, method_list, benchmark_list


class Result:
    def __init__(self, hpwl: float, congestion: float) -> None:
        self._hpwl = hpwl
        self._congestion = congestion

    @property
    def hpwl(self) -> float:
        return self._hpwl

    @property
    def congestion(self) -> float:
        return self._congestion


ResultsRecord = Dict[str, Dict[str, Result]]


def extract_one_log(file_name: str) -> Tuple[float, float]:
    hpwl = 0
    overflow = 0
    with open(file_name, "r", encoding="utf8") as f:
        lines = f.readlines()
        lines.reverse()
        for line in lines:
            if "wHPWL" in line and "Overflow" in line and "MaxDensity" in line:
                line = line.split(",")
                for piece in line:
                    if "wHPWL" in piece:
                        hpwl = float(piece.split()[-1])
                    elif "Overflow" in piece:
                        overflow = float(piece.split()[-1])
                break
    return hpwl, overflow


def get_all_baselines(
    method_list: List[str], benchmark_list: List[str]
) -> ResultsRecord:
    if os.path.exists("baseline_results.pk"):
        with open("baseline_results.pk", "rb") as f:
            baseline_records = pk.load(f)
    else:
        baseline_records = {}
        for method in method_list:
            baseline_records[method] = {}
            dirname = f"results_detailed_front_{method}"
            for benchmark in benchmark_list:
                file_name = os.path.join(dirname, benchmark, "result.log")
                hpwl, overflow = extract_one_log(file_name)
                print(f"{method} {benchmark} hpwl {hpwl:e} overflow {overflow:e}")
                baseline_records[method][benchmark] = Result(hpwl, overflow)
        with open("baseline_results.pk", "wb") as f:
            pk.dump(baseline_records, f)
    return baseline_records


SearchRecord = Dict[str, Dict[str, np.ndarray]]


def run_all_cases(
    method_list: List[str], benchmark_list: List[str]
) -> Tuple[SearchRecord, SearchRecord]:
    left = 0
    right = 10
    step = 1
    candidates = np.arange(left, right + step, step)

    search_record_hpwl: SearchRecord = {}
    search_record_congestion: SearchRecord = {}
    for method in method_list:
        search_record_hpwl[method] = {}
        search_record_congestion[method] = {}
        for b in benchmark_list:
            search_record_hpwl[method][b] = np.ones((11, 11)) * my_inf
            search_record_congestion[method][b] = np.ones((11, 11)) * my_inf

    os.system("mkdir -p search_results")
    for i in candidates:
        for j in np.arange(0, right - i + step, step):
            k = 10 - i - j
            alpha = i / 10
            beta = j / 10
            gamma = k / 10
            pivot = str(i) + str(j) + str(k)
            dirname = f"results_v7_grid_search_{pivot}"
            if not os.path.exists(dirname):
                cmd = (
                    f"python auto_run.py --alpha {alpha} --beta {beta} --gamma {gamma}"
                )
                print(cmd)
                os.system(cmd)

                os.system(f"mkdir {dirname}")
                os.system(f"cp -r results_detailed_* {dirname}")
                os.system(f"cp -r results_macro_* {dirname}")
                os.system("rm -rf results_*_refine*")
                os.system(f"mv results_hpwl.csv {dirname}")
                os.system(f"mv results_congestion.csv {dirname}")
            # else:
            #     with open(f"search_results/search_record_hpwl_{pivot}.pk", "rb") as f:
            #         search_record_hpwl = pk.load(f)
            #     with open(
            #         f"search_results/search_record_congestion_{pivot}.pk", "rb"
            #     ) as f:
            #         search_record_congestion = pk.load(f)

            df_hpwl, df_congestion = extract_all(method_list, benchmark_list, dirname)
            idx = (i, j)
            for method in method_list:
                for b in benchmark_list:
                    search_record_hpwl[method][b][idx] = df_hpwl.loc[
                        "refine-EA_" + method, b
                    ]
                    search_record_congestion[method][b][idx] = df_congestion.loc[
                        "refine-EA_" + method, b
                    ]
            with open(f"search_results/search_record_hpwl_{pivot}.pk", "wb") as f:
                pk.dump(search_record_hpwl, f)
            with open(f"search_results/search_record_congestion_{pivot}.pk", "wb") as f:
                pk.dump(search_record_congestion, f)
    return search_record_hpwl, search_record_congestion


def grid_search(
    method_list: List[str],
    benchmark_list: List[str],
    search_record_hpwl: SearchRecord,
    search_record_congestion: SearchRecord,
):
    best_hyperparameters = pd.DataFrame(index=method_list, columns=benchmark_list)
    for method in method_list:
        for b in benchmark_list:
            min_hpwl, min_congestion = my_inf, my_inf
            for i, line in enumerate(search_record_hpwl[method][b]):
                for j, hpwl in enumerate(line):
                    congestion = search_record_congestion[method][b][i][j]
                    if hpwl < min_hpwl or (
                        hpwl == min_hpwl and congestion <= min_congestion
                    ):
                        min_hpwl = hpwl
                        min_congestion = congestion
                        k = 10 - i - j
                        best_hyperparameters.loc[method, b] = (i, j, k)
    best_hyperparameters.to_csv("best_hyperparameters.csv")
    return best_hyperparameters


if __name__ == "__main__":
    # method_list = [
    #     "bbo",
    #     "dreamplace-mixed",
    # ]
    # benchmark_list = [
    #     "adaptec1",
    #     "adaptec2",
    #     "adaptec3",
    #     "adaptec4",
    #     "bigblue1",
    #     "bigblue3",
    #     "bigblue4",
    # ]
    search_record_hpwl, search_record_congestion = run_all_cases(
        method_list, benchmark_list
    )
    grid_search(
        method_list, benchmark_list, search_record_hpwl, search_record_congestion
    )
