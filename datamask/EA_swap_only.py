import random
import argparse
import time
import csv
import os

from place_db import PlaceDB
from utils import (
    random_guiding,
    datamask_placer,
    wiremask_placer,
    mix_placer,
    write_final_placement,
    rank_macros,
    get_m2m_flow,
)
from common import grid_setting, my_inf


def swap(x, y):
    x, y = y, x


def placer(
    init_round,
    stop_round,
    placedb,
    grid_num,
    grid_size,
    placer_func,
    hpwl_save_file,
    placement_save_file,
    m2m_flow_file,
):
    hpwl_save_file = open(hpwl_save_file, "a+")
    hpwl_writer = csv.writer(hpwl_save_file)
    best_hpwl = my_inf
    node_id_ls = rank_macros(placedb)
    m2m_flow = get_m2m_flow(m2m_flow_file)  #!TODO

    for _ in range(init_round):
        print("init")
        place_record = random_guiding(node_id_ls, placedb, grid_num, grid_size)
        placed_macros, hpwl = placer_func(node_id_ls, placedb, grid_num, grid_size, place_record, m2m_flow)
        if hpwl < best_hpwl:
            best_place_record = place_record
            best_hpwl = hpwl
            best_placed_macro = placed_macros
            write_final_placement(best_placed_macro, placement_save_file)
        hpwl_writer.writerow([hpwl, time.time(), "init"])
        hpwl_save_file.flush()
    place_record = best_place_record
    write_final_placement(best_placed_macro, placement_save_file)

    for _ in range(stop_round):
        node_id_ls = list(place_record.keys())
        node_a, node_b = random.sample(node_id_ls, 2)
        node_a_loc_x, node_a_loc_y = place_record[node_a]["loc_x"], place_record[node_a]["loc_y"]
        node_b_loc_x, node_b_loc_y = place_record[node_b]["loc_x"], place_record[node_b]["loc_y"]
        place_record[node_a]["loc_x"], place_record[node_a]["loc_y"] = node_b_loc_x, node_b_loc_y
        place_record[node_b]["loc_x"], place_record[node_b]["loc_y"] = node_a_loc_x, node_a_loc_y

        placed_macro, hpwl = placer_func(node_id_ls, placedb, grid_num, grid_size, place_record, m2m_flow)
        if hpwl >= best_hpwl:
            # 没有优化，恢复原状
            node_a_loc_x, node_a_loc_y = place_record[node_a]["loc_x"], place_record[node_a]["loc_y"]
            node_b_loc_x, node_b_loc_y = place_record[node_b]["loc_x"], place_record[node_b]["loc_y"]
            place_record[node_a]["loc_x"], place_record[node_a]["loc_y"] = node_b_loc_x, node_b_loc_y
            place_record[node_b]["loc_x"], place_record[node_b]["loc_y"] = node_a_loc_x, node_a_loc_y
        else:
            best_hpwl = hpwl
            best_placed_macro = placed_macro
            write_final_placement(best_placed_macro, placement_save_file)
        hpwl_writer.writerow([hpwl, time.time()])
        hpwl_save_file.flush()

    hpwl_writer.writerow([best_hpwl, time.time()])
    hpwl_save_file.flush()


def main(place_func):
    parser = argparse.ArgumentParser(description="argparse testing")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--init_round", default=100)
    parser.add_argument("--stop_round", default=my_inf)
    args = parser.parse_args()
    dataset = args.dataset
    seed1 = args.seed
    stop_round = int(args.stop_round)
    init_round = int(args.init_round)
    random.seed(seed1)
    placedb = PlaceDB(dataset)

    hpwl_save_dir = "result/EA_swap_only/curve/"
    placement_save_dir = "result/EA_swap_only/placement/"

    if not os.path.exists(hpwl_save_dir):
        os.makedirs(hpwl_save_dir)
    if not os.path.exists(placement_save_dir):
        os.makedirs(placement_save_dir)

    grid_num = grid_setting[dataset]["grid_num"]
    grid_size = grid_setting[dataset]["grid_size"]

    hpwl_save_dir += "{}_seed_{}.csv".format(dataset, seed1)
    placement_save_dir += "{}_seed_{}.csv".format(dataset, seed1)
    m2m_flow_file = "benchmarks/ispd2005/{}/macro2macro.csv".format(dataset)

    placer(
        init_round,
        stop_round,
        placedb,
        grid_num,
        grid_size,
        place_func,
        hpwl_save_dir,
        placement_save_dir,
        m2m_flow_file,
    )


if __name__ == "__main__":
    main(datamask_placer)
    # main(wiremask_placer)
    # main(mix_placer)
