import os, subprocess


def front_run_bbo(benchmark):
    print(f"front_run_bbo {benchmark}")
    init_round = 1
    stop_round = 3
    seed = 2027
    cmd = f"python wiremask.py --dataset {benchmark} --seed {seed} --init_round {init_round} --stop_round {stop_round} "
    print(cmd)
    # # res, out = subprocess.getstatusoutput(cmd)
    # if res != 0:
    #     print(out)
    os.system("mkdir -p front_bbo_results")
    os.system(cmd)


if __name__ == "__main__":
    benchmark = "adaptec1"
    front_run_bbo(benchmark)
