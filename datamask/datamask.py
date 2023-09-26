import random
import argparse
import time
import csv
import os
from typing import Dict, List, Tuple

from place_db import PlaceDB
from utils import (
    datamask_placer,
    write_final_placement,
    rank_macros_area,
    rank_macros_mixed,
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


def hot_start(
    init_round,
    stop_round,
    placedb,
    grid_num,
    grid_size,
    hpwl_save_file,
    placement_save_file,
    m2m_flow_file,
):
    hpwl_save_file = open(hpwl_save_file, "a+")
    hpwl_writer = csv.writer(hpwl_save_file)
    best_hpwl = my_inf
    m2m_flow = get_m2m_flow(m2m_flow_file)
    node_id_ls = rank_macros_mixed(placedb, m2m_flow, 0.8, 0.2)

    place_record = db2record(placedb, grid_size)
    print("origin hpwl: ", cal_hpwl(place_record, placedb))
    best_placed_record, best_hpwl = dict(), my_inf
    for i in range(stop_round):
        print(i)
        place_record, hpwl = datamask_placer(node_id_ls, placedb, grid_num, grid_size, place_record, m2m_flow)
        hpwl_writer.writerow([hpwl, time.time()])
        hpwl_save_file.flush()
        if hpwl < best_hpwl:
            best_hpwl = hpwl
            best_placed_record = place_record
            write_final_placement(best_placed_record, placement_save_file)
    hpwl_writer.writerow([best_hpwl, time.time()])
    hpwl_save_file.flush()
    return best_placed_record


def main():
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

    hpwl_save_dir += "{}_seed_{}_datamask_iter3.csv".format(dataset, seed1)
    placement_save_dir += "{}_seed_{}_datamask_iter3.csv".format(dataset, seed1)
    m2m_flow_file = "benchmarks/{}/macro2macro.csv".format(dataset)

    best_placed_macro = hot_start(
        init_round,
        stop_round,
        placedb,
        grid_num,
        grid_size,
        hpwl_save_dir,
        placement_save_dir,
        m2m_flow_file,
    )

    m2m_flow = get_m2m_flow(m2m_flow_file)
    pic_save_dir += "{}_seed_{}_datamask_iter3.png".format(dataset, seed1)
    draw_macros(placedb, placement_save_dir, grid_size, m2m_flow, pic_save_dir)


if __name__ == "__main__":
    main()
