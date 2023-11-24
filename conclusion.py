import pandas as pd
import os
from typing import List
from extract_results import extract_one_log
from common import method_list, benchmark_list


def conclude(method_list: List[str], benchmark_list: List[str]):
    tmp = []
    for method in method_list:
        tmp.append(method)
        tmp.append("refine-EA" + "_" + method)
    df_hpwl = pd.DataFrame(index=tmp, columns=benchmark_list)
    df_congestion = pd.DataFrame(index=tmp, columns=benchmark_list)

    best_hyperparameters = pd.read_csv("best_hyperparameters.csv", index_col=0)

    for method in method_list:
        # 统计 baseline 的结果
        front_dirname = f"results_detailed_front_{method}"
        for benchmark in benchmark_list:
            front_filename = os.path.join(front_dirname, benchmark, "result.log")
            hpwl, overflow = extract_one_log(front_filename)
            print(f"{benchmark} {method} hpwl {hpwl:e} overflow {overflow:e}")
            df_hpwl.loc[method, benchmark] = hpwl
            df_congestion.loc[method, benchmark] = overflow

            alpha, beta, gamma = eval(best_hyperparameters.loc[method, benchmark])
            # pivot = str(int(10 * alpha)) + str(int(10 * beta)) + str(int(10 * gamma))
            pivot = str(alpha) + str(beta) + str(gamma)
            refine_filename = os.path.join(
                f"results_v11_grid_search_{pivot}",
                f"results_detailed_refine-EA_{method}",
                benchmark,
                "result.log",
            )
            hpwl, overflow = extract_one_log(refine_filename)
            print(f"{benchmark} refine-EA_{method} hpwl {hpwl:e} overflow {overflow:e}")
            df_hpwl.loc["refine-EA_" + method, benchmark] = hpwl
            df_congestion.loc["refine-EA_" + method, benchmark] = overflow
    df_hpwl.to_csv("conclude_hpwl.csv")
    df_congestion.to_csv("conclude_congestion.csv")


if __name__ == "__main__":
    conclude(method_list, benchmark_list)
