import os
import sys
from scipy.spatial import distance
from typing import Dict, List, Tuple

from place_db import PlaceDB
from utils import Record, get_m2m_flow, read_placement, draw
from utils import PlaceRecord, M2MFlow
from common import grid_setting, my_inf


def cal_dataflow(placedb: PlaceDB, place_record: PlaceRecord, m2m_flow: M2MFlow):
    dataflow_total = 0
    for node_name1 in placedb.node_info:
        for node_name2 in m2m_flow[node_name1]:
            dataflow_total += (
                distance.euclidean(
                    (place_record[node_name1].center_x, place_record[node_name1].center_y),
                    (place_record[node_name2].center_x, place_record[node_name2].center_y),
                )
                * m2m_flow[node_name1][node_name2]
            )
    return dataflow_total


def db2record(placedb: PlaceDB, grid_size: int) -> PlaceRecord:
    place_record: PlaceRecord = {}
    for node_name in placedb.node_info:
        chosen_loc_x = int(placedb.node_info[node_name].bottom_left_x / grid_size)
        chosen_loc_y = int(placedb.node_info[node_name].bottom_left_y / grid_size)
        place_record[node_name] = Record(
            placedb.node_info[node_name].width, placedb.node_info[node_name].height, chosen_loc_x, chosen_loc_y, grid_size
        )
    return place_record


def draw_origin(benchmark: str):
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    m2m_file = "benchmarks/{}/macro2macro.csv".format(benchmark)
    m2m_flow = get_m2m_flow(m2m_file)

    origin_pic = "result/EA_swap_only/pic/{}_seed_2027_origin_noid.png".format(benchmark)
    origin_record = db2record(placedb, grid_size)
    draw(origin_record, origin_pic, placedb, m2m_flow)


def draw_wiremask(benchmark: str):
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    m2m_file = "benchmarks/{}/macro2macro.csv".format(benchmark)
    m2m_flow = get_m2m_flow(m2m_file)
    pl_file = "result/EA_swap_only/placement/{}_seed_2027_wiremask_hot.csv".format(benchmark)
    place_record = read_placement(placedb, grid_size, pl_file)
    pic_file = "result/EA_swap_only/pic/{}_seed_2027_wiremask_hot.png".format(benchmark)
    draw(place_record, pic_file, placedb, m2m_flow)


def draw_datamask(benchmark):
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    m2m_file = "benchmarks/{}/macro2macro.csv".format(benchmark)
    m2m_flow = get_m2m_flow(m2m_file)
    pl_file = "result/EA_swap_only/placement/{}_seed_2027_datamask_hot.csv".format(benchmark)
    place_record = read_placement(placedb, grid_size, pl_file)
    pic_file = "result/EA_swap_only/pic/{}_seed_2027_datamask_hot.png".format(benchmark)
    draw(place_record, pic_file, placedb, m2m_flow)


if __name__ == "__main__":
    assert len(sys.argv) >= 2
    benchmark = sys.argv[1]
    print(benchmark)
    draw_origin(benchmark)
    # draw_datamask(benchmark)
    # draw_wiremask(benchmark)
