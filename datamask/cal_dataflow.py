import os
import sys
from scipy.spatial import distance
from typing import Dict, List, Tuple

from place_db import PlaceDB
from utils import Record, get_m2m_flow, read_placement
from common import grid_setting, my_inf


class DataflowLoss:
    def __init__(self) -> None:
        self.origin: float = 0
        self.wiremask: float = 0
        self.datamask: float = 0
        self.mixedmask: float = 0


def cal_dataflow(placedb: PlaceDB, place_record: Dict[str, Record], m2m_flow: List[List[int]]):
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


def db2record(placedb: PlaceDB, grid_size: int) -> Dict[str, Record]:
    place_record: Dict[str, Record] = {}
    for node_name in placedb.node_info:
        chosen_loc_x = int(placedb.node_info[node_name].bottom_left_x / grid_size)
        chosen_loc_y = int(placedb.node_info[node_name].bottom_left_y / grid_size)
        place_record[node_name] = Record(
            placedb.node_info[node_name].width, placedb.node_info[node_name].height, chosen_loc_x, chosen_loc_y, grid_size
        )
    return place_record


if __name__ == "__main__":
    assert len(sys.argv) >= 2
    benchmark = sys.argv[1]
    print(benchmark)
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    m2m_file = "benchmarks/{}/macro2macro.csv".format(benchmark)
    m2m_flow = get_m2m_flow(m2m_file)

    df_loss = DataflowLoss()

    origin_record = db2record(placedb, grid_size)
    df_loss.origin = cal_dataflow(placedb, origin_record, m2m_flow)

    wiremask_placement_file = "result/EA_swap_only/placement/{}_seed_2027_wiremask_iter.csv".format(benchmark)
    wiremask_record = read_placement(placedb, grid_size, wiremask_placement_file)
    df_loss.wiremask = cal_dataflow(placedb, wiremask_record, m2m_flow)

    datamask_placement_file = "result/EA_swap_only/placement/{}_seed_2027_datamask_iter3.csv".format(benchmark)
    datamask_record = read_placement(placedb, grid_size, datamask_placement_file)
    df_loss.datamask = cal_dataflow(placedb, datamask_record, m2m_flow)

    datamask_placement_file = "result/EA_swap_only/placement/{}_seed_2027_mixedmask_iter.csv".format(benchmark)
    datamask_record = read_placement(placedb, grid_size, datamask_placement_file)
    df_loss.mixedmask = cal_dataflow(placedb, datamask_record, m2m_flow)

    dataflow_file = "result/dataflow_{}_iter.txt".format(benchmark)
    with open(dataflow_file, "w") as f:
        f.write(
            f"origin: {df_loss.origin}\nwiremask: {df_loss.wiremask}\ndatamask: {df_loss.datamask}\nmixedmask: {df_loss.mixedmask}\n"
        )
