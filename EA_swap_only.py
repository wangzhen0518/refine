import random
import argparse
import time
import csv
import os
from typing import Dict, List, Tuple

from place_db import PlaceDB
from utils import (
    random_guiding,
    datamask_placer,
    wiremask_placer,
    mixed_placer,
    write_final_placement,
    rank_macros_area,
    rank_macros_mixed_port,
    get_m2m_flow,
    cal_hpwl,
    draw_macros,
    Record,
)
from common import grid_setting, my_inf


def db2record(placedb: PlaceDB, grid_size: int) -> Dict[str, Record]:
    place_record: Dict[str, Record] = {}
    for node_name in placedb.node_info:
        chosen_loc_x = int(placedb.node_info[node_name].bottom_left_x / grid_size)
        chosen_loc_y = int(placedb.node_info[node_name].bottom_left_y / grid_size)
        place_record[node_name] = Record(
            placedb.node_info[node_name].width, placedb.node_info[node_name].height, chosen_loc_x, chosen_loc_y, grid_size
        )
    return place_record


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
    node_id_ls = rank_macros_area(placedb)
    m2m_flow = get_m2m_flow(m2m_flow_file)  #!TODO

    for cnt in range(init_round):
        print(f"init {cnt}")
        place_record = random_guiding(node_id_ls, placedb, grid_num, grid_size)
        # write_final_placement(place_record, placement_save_file)
        # draw_macros(
        #     placedb,
        #     "adaptec1",
        #     placement_save_file,
        #     grid_size,
        #     "/home/wangzhen/Project/refine/datamask/result/EA_swap_only/pic/adaptec1_seed_2027_random.png",
        # )
        print("origin hpwl: ", cal_hpwl(place_record, placedb))
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

    for cnt in range(stop_round):
        print(f"swap {cnt}")
        node_id_ls = list(place_record.keys())
        node_a, node_b = random.sample(node_id_ls, 2)
        place_record[node_a].grid_x, place_record[node_b].grid_x = place_record[node_b].grid_x, place_record[node_b].grid_x
        place_record[node_a].grid_y, place_record[node_b].grid_y = place_record[node_b].grid_y, place_record[node_b].grid_y
        placed_macro, hpwl = placer_func(node_id_ls, placedb, grid_num, grid_size, place_record, m2m_flow)
        if hpwl >= best_hpwl:
            # 没有优化，恢复原状
            place_record[node_a].grid_x, place_record[node_b].grid_x = place_record[node_b].grid_x, place_record[node_b].grid_x
            place_record[node_a].grid_y, place_record[node_b].grid_y = place_record[node_b].grid_y, place_record[node_b].grid_y
        else:
            best_hpwl = hpwl
            best_placed_macro = placed_macro
            write_final_placement(best_placed_macro, placement_save_file)
        hpwl_writer.writerow([hpwl, time.time()])
        hpwl_save_file.flush()

    hpwl_writer.writerow([best_hpwl, time.time()])
    hpwl_save_file.flush()
    return best_placed_macro


def hot_start(
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
    m2m_flow = get_m2m_flow(m2m_flow_file)
    node_id_ls = rank_macros_mixed_port(placedb, m2m_flow, 0.7, 0.3)

    place_record = db2record(placedb, grid_size)
    print("origin hpwl: ", cal_hpwl(place_record, placedb))
    placed_macros, hpwl = placer_func(node_id_ls, placedb, grid_num, grid_size, place_record, m2m_flow)
    hpwl_writer.writerow([hpwl, time.time(), "ispd2005"])
    write_final_placement(placed_macros, placement_save_file)


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

    grid_num = grid_setting[dataset]["grid_num"]
    grid_size = grid_setting[dataset]["grid_size"]
    placedb = PlaceDB(dataset, grid_size)

    hpwl_save_dir = "result/EA_swap_only/curve/"
    placement_save_dir = "result/EA_swap_only/placement/"
    pic_save_dir = "result/EA_swap_only/pic/"

    if not os.path.exists(hpwl_save_dir):
        os.makedirs(hpwl_save_dir)
    if not os.path.exists(placement_save_dir):
        os.makedirs(placement_save_dir)
    if not os.path.exists(pic_save_dir):
        os.makedirs(pic_save_dir)

    hpwl_save_dir += "{}_seed_{}.csv".format(dataset, seed1)
    placement_save_dir += "{}_seed_{}.csv".format(dataset, seed1)
    m2m_flow_file = "benchmarks/{}/macro2macro.csv".format(dataset)

    best_placed_macro = hot_start(
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

    m2m_flow = get_m2m_flow(m2m_flow_file)
    pic_save_dir += "{}_seed_{}_datamask_hot_mixed2.png".format(dataset, seed1)
    draw_macros(placedb, placement_save_dir, grid_size, m2m_flow, pic_save_dir)


if __name__ == "__main__":
    main(datamask_placer)
    # main(wiremask_placer)
    # main(mix_placer)
