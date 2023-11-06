import argparse
import csv
import os
import random
import time

from common import grid_setting, my_inf
from place_db import PlaceDB
from utils import (
    Record,
    random_guiding,
    rank_macros_area,
    wiremask_placer,
    write_final_placement,
    write_pl_for_refine,
    draw_macros,
)


def swap(node1: Record, node2: Record, grid_size: int):
    node1.bottom_left_x, node2.bottom_left_x = node2.bottom_left_x, node1.bottom_left_x
    node1.bottom_left_y, node2.bottom_left_y = node2.bottom_left_y, node1.bottom_left_y

    node1.grid_x, node2.grid_x = node2.grid_x, node1.grid_x
    node1.grid_y, node2.grid_y = node2.grid_y, node1.grid_y

    node1.refresh(grid_size)
    node2.refresh(grid_size)


def bbo(
    init_round,
    stop_round,
    placedb: PlaceDB,
    grid_num,
    grid_size,
    curve_file,
    placement_file,
):
    curve_fp = open(curve_file, "a+")
    hpwl_writer = csv.writer(curve_fp)
    node_id_ls = rank_macros_area(placedb)

    # initialize
    best_hpwl = my_inf
    for cnt in range(init_round):
        print(f"init {cnt}")
        place_record = random_guiding(node_id_ls, placedb, grid_size)
        placed_macros, hpwl = wiremask_placer(
            node_id_ls, placedb, grid_num, grid_size, place_record
        )
        if hpwl < best_hpwl:
            best_hpwl = hpwl
            best_placed_macro = placed_macros
            write_final_placement(best_placed_macro, best_hpwl, placement_file)
        hpwl_writer.writerow([hpwl, time.time(), "init"])
        curve_fp.flush()
    # EA
    candidates = sorted(placedb.macro_name)
    if best_hpwl != my_inf:
        write_final_placement(best_placed_macro, best_hpwl, placement_file)
        place_record = best_placed_macro
        for cnt in range(stop_round):
            print(cnt)
            node_a, node_b = random.sample(candidates, 2)
            swap(place_record[node_a], place_record[node_b], grid_size)

            placed_macro, hpwl = wiremask_placer(
                node_id_ls, placedb, grid_num, grid_size, place_record
            )
            if hpwl >= best_hpwl:
                # 没有优化，恢复原状
                swap(place_record[node_a], place_record[node_b], grid_size)
            else:
                best_hpwl = hpwl
                best_placed_macro = place_record = placed_macro
                write_final_placement(best_placed_macro, best_hpwl, placement_file)
            hpwl_writer.writerow([hpwl, time.time()])
            curve_fp.flush()
        hpwl_writer.writerow([best_hpwl, time.time()])
        curve_fp.flush()
    else:
        place_record = {}
    return place_record, best_hpwl


def main():
    parser = argparse.ArgumentParser(description="argparse testing")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--init_round", default=100)
    parser.add_argument("--stop_round", default=my_inf)
    args = parser.parse_args()
    benchmark = args.dataset
    seed1 = args.seed
    stop_round = int(args.stop_round)
    init_round = int(args.init_round)
    random.seed(seed1)

    grid_num = grid_setting[benchmark]["grid_num"]
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)

    result_dir = os.path.join("results_macro_front_bbo", benchmark)
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    curve_file = os.path.join(result_dir, f"curve_seed_{seed1}.csv")
    placement_file = os.path.join(result_dir, f"placement_seed_{seed1}.csv")
    # pl_file_for_detailed = os.path.join(result_dir, f"{benchmark}_for_detailed.gp.pl")
    pl_file_for_refine = os.path.join(result_dir, f"{benchmark}.gp.pl")

    place_record, hpwl = bbo(
        init_round, stop_round, placedb, grid_num, grid_size, curve_file, placement_file
    )
    if place_record:
        pic_file = os.path.join(result_dir, f"{benchmark}.png")
        draw_macros(placedb, placement_file, grid_size, None, pic_file)
        # write_pl_for_detailed(place_record, pl_file_for_detailed)
        write_pl_for_refine(place_record, placedb, pl_file_for_refine)


if __name__ == "__main__":
    main()
