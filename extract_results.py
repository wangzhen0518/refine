import os
import pandas as pd
from typing import List, Tuple
from common import method_list, benchmark_list


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


def extract_all(method_list: List[str], benchmark_list: List[str], dirbase: str = ""):
    tmp = []
    for method in method_list:
        tmp.append(method)
        tmp.append("refine-EA" + "_" + method)
    method_list = tmp
    df_hpwl = pd.DataFrame(index=method_list, columns=benchmark_list)
    df_congestion = pd.DataFrame(index=method_list, columns=benchmark_list)
    for method in method_list:
        if "refine" in method:
            dirname = os.path.join(dirbase, f"results_detailed_{method}")
        else:
            dirname = os.path.join(dirbase, f"results_detailed_front_{method}")
        for benchmark in benchmark_list:
            file_name = os.path.join(dirname, benchmark, "result.log")
            hpwl, overflow = extract_one_log(file_name)
            print(f"{method} {benchmark} hpwl {hpwl:e} overflow {overflow:e}")
            df_hpwl.loc[method, benchmark] = hpwl
            df_congestion.loc[method, benchmark] = overflow
    df_hpwl.to_csv("results_hpwl.csv")
    df_congestion.to_csv("results_congestion.csv")
    return df_hpwl, df_congestion


if __name__ == "__main__":
    df_hpwl, df_congestion = extract_all(method_list, benchmark_list)
