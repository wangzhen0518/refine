import argparse
import os
import subprocess
from multiprocessing import Pool
from typing import List
from draw_placement import (
    draw_macro_front_bbo,
    draw_macro_refine_bbo,
    draw_detailed_front_bbo,
    draw_detailed_refine_bbo,
    draw_macro_front_dreamplace_mixed,
    draw_macro_refine_dreamplace_mixed,
    draw_detailed_front_dreamplace_mixed,
    draw_detailed_refine_dreamplace_mixed,
    draw_macro_front_dreamplace_macro,
    draw_macro_refine_dreamplace_macro,
    draw_detailed_front_dreamplace_macro,
    draw_detailed_refine_dreamplace_macro,
)
from common import method_list, benchmark_list


def refine_macros(
    method_list: List[str],
    benchmark_list: List[str],
    alpha: float,
    beta: float,
    gamma: float,
):
    p = Pool(16)
    task_list = []
    for method in method_list:
        for b in benchmark_list:
            cmd = [
                "python",
                "-u",
                "mixedmask.py",
                "--seed",
                "2027",
                "--iter_rounds",
                "5" if b == "bigblue4" else "20",
                "--front",
                method,
                "--dataset",
                b,
                "--alpha",
                str(alpha),
                "--beta",
                str(beta),
                "--gamma",
                str(gamma),
            ]
            print(cmd)
            task_list.append(p.apply_async(subprocess.call, (cmd,)))
    p.close()
    p.join()


def detailed_placement(method_list: List[str], benchmark_list: List[str]):
    for method in method_list:
        if os.path.exists(f"results_detailed_refine-EA_{method}"):
            raise FileExistsError

        for b in benchmark_list:
            os.system(f"mkdir -p results/{b}")
            cmd = " ".join(
                [
                    "python -u dreamplace/Placer.py",
                    f"--config test/ispd2005/{b}.json",
                    "--type refine",
                    f"--method {method}",
                    "2>&1",
                    "|",
                    f"tee results/{b}/result.log",
                ]
            )
            print(cmd)
            os.system(cmd)
        os.system(f"mv results results_detailed_refine-EA_{method}")


def run_one_hyperparameter(alpha: float, beta: float, gamma: float):
    print(f"alpha {alpha:.1f}, beta {beta:.1f}, gamma {gamma:.1f}")
    refine_macros(method_list, benchmark_list, alpha, beta, gamma)
    detailed_placement(method_list, benchmark_list)
    for b in benchmark_list:
        if "bbo" in method_list:
            draw_macro_refine_bbo(b)
            draw_detailed_refine_bbo(b)

        if "dreamplace-mixed" in method_list:
            draw_macro_refine_dreamplace_mixed(b)
            draw_detailed_refine_dreamplace_mixed(b)

        if "dreamplace-macro" in method_list:
            draw_macro_refine_dreamplace_macro(b)
            draw_detailed_refine_dreamplace_macro(b)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="argparse testing")
    parser.add_argument("--alpha", default=0.3)
    parser.add_argument("--beta", default=0.3)
    parser.add_argument("--gamma", default=0.4)

    args = parser.parse_args()
    alpha = float(args.alpha)
    beta = float(args.beta)
    gamma = float(args.gamma)
    print(f"alpha {alpha:.1f}, beta {beta:.1f}, gamma {gamma:.1f}")

    # benchmark_list = [
    #     "adaptec1",
    #     "adaptec2",
    #     "adaptec3",
    #     "adaptec4",
    #     "bigblue1",
    #     "bigblue3",
    #     "bigblue4",
    # ]
    # method_list = [
    #     "bbo",
    #     "dreamplace-mixed",
    # ]
    refine_macros(method_list, benchmark_list, alpha, beta, gamma)
    detailed_placement(method_list, benchmark_list)
    for b in benchmark_list:
        if "bbo" in method_list:
            draw_macro_refine_bbo(b)
            draw_detailed_refine_bbo(b)

        if "dreamplace-mixed" in method_list:
            draw_macro_refine_dreamplace_mixed(b)
            draw_detailed_refine_dreamplace_mixed(b)

        if "dreamplace-macro" in method_list:
            draw_macro_refine_dreamplace_macro(b)
            draw_detailed_refine_dreamplace_macro(b)
