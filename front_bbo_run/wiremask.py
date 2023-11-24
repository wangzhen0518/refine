import random
import argparse
import time
import csv
import os
import sys
from typing import Dict, List, Tuple

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from place_db import PlaceDB
from utils import (
    random_guiding,
    wiremask_placer,
    write_final_placement,
    rank_macros_area,
    cal_hpwl,
    Record,
    write_pl_for_detailed,
)
from common import grid_setting, my_inf


def swap(record1: Record, record2: Record, grid_size):
    return Record(record1.width, record1.height, record2.grid_x, record2.grid_y, grid_size), Record(
        record2.width, record2.height, record1.grid_x, record1.grid_y, grid_size
    )


def db2record(placedb: PlaceDB, grid_size: int) -> Dict[str, Record]:
    place_record: Dict[str, Record] = {}
    for node_name in placedb.node_info:
        chosen_loc_x = int(placedb.node_info[node_name].bottom_left_x / grid_size)
        chosen_loc_y = int(placedb.node_info[node_name].bottom_left_y / grid_size)
        place_record[node_name] = Record(
            placedb.node_info[node_name].width,
            placedb.node_info[node_name].height,
            chosen_loc_x,
            chosen_loc_y,
            grid_size,
        )
    return place_record


def hot_start(
    init_round,
    stop_round,
    placedb,
    grid_num,
    grid_size,
    curve_file,
    placement_file,
):
    curve_fp = open(curve_file, "a+")
    hpwl_writer = csv.writer(curve_fp)
    best_hpwl = my_inf
    node_id_ls = rank_macros_area(placedb)

    # initialize
    place_record = db2record(placedb, grid_size)
    origin_hpwl = cal_hpwl(place_record, placedb)
    print("origin hpwl: ", origin_hpwl)
    hpwl_writer.writerow([origin_hpwl, time.time()])
    best_placed_record, best_hpwl = dict(), my_inf
    # for i in range(stop_round):
    #     print(i)
    place_record, hpwl = wiremask_placer(node_id_ls, placedb, grid_num, grid_size, place_record)
    hpwl_writer.writerow([hpwl, time.time()])
    # hpwl_save_file.flush()
    #     if hpwl < best_hpwl:
    #         best_hpwl = hpwl
    #         best_placed_record = place_record
    #         write_final_placement(best_placed_record, placement_save_file)
    # hpwl_writer.writerow([best_hpwl, time.time(), "\n"])
    hpwl_writer.writerow([])
    curve_fp.flush()
    write_final_placement(place_record, placement_file)
    return place_record


def bbo(
    init_round,
    stop_round,
    placedb,
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
            best_place_record = place_record
            best_hpwl = hpwl
            best_placed_macro = placed_macros
            write_final_placement(best_placed_macro, best_hpwl, placement_file)
        hpwl_writer.writerow([hpwl, time.time(), "init"])
        curve_fp.flush()
    # EA
    for cnt in range(stop_round):
        print(cnt)
        node_id_ls = list(place_record.keys())
        node_a, node_b = random.sample(node_id_ls, 2)
        place_record[node_a], place_record[node_b] = swap(
            place_record[node_a], place_record[node_b], grid_size
        )

        placed_macro, hpwl = wiremask_placer(node_id_ls, placedb, grid_num, grid_size, place_record)
        if hpwl >= best_hpwl:
            # 没有优化，恢复原状
            place_record[node_a], place_record[node_b] = swap(
                place_record[node_a], place_record[node_b], grid_size
            )
        else:
            best_hpwl = hpwl
            best_placed_macro = place_record = placed_macro
            write_final_placement(best_placed_macro, best_hpwl, placement_file)
        hpwl_writer.writerow([hpwl, time.time()])
        curve_fp.flush()

    hpwl_writer.writerow([best_hpwl, time.time()])
    curve_fp.flush()
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

    result_dir = os.path.join("front_bbo_results", benchmark)
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    curve_file = os.path.join(result_dir, f"curve_seed_{seed1}.csv")
    placement_file = os.path.join(result_dir, f"placement_seed_{seed1}.csv")
    pl_file = os.path.join(result_dir, f"{benchmark}.gp.pl")

    place_record, hpwl = bbo(
        init_round, stop_round, placedb, grid_num, grid_size, curve_file, placement_file
    )
    write_pl_for_detailed(place_record, pl_file)


if __name__ == "__main__":
    main()
