import time
import numpy as np
import cv2
import math
import csv
import random
import heapq
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from typing import Dict, Tuple, List
from scipy.spatial import distance

from place_db import PlaceDB, Node
from common import my_inf, grid_setting


class Record:
    def __init__(self, _width, _height, grid_x, grid_y, grid_size) -> None:
        self.width: int = _width
        self.height: int = _height
        self.scaled_width: int = math.ceil(_width / grid_size)
        self.scaled_height: int = math.ceil(_height / grid_size)
        self.grid_x: int = grid_x
        self.grid_y: int = grid_y
        self.center_x: float = grid_x * grid_size + 0.5 * _width
        self.center_y: float = grid_y * grid_size + 0.5 * _height
        self.bottom_left_x: int = grid_x * grid_size
        self.bottom_left_y: int = grid_y * grid_size


M2MFlow = Dict[str, Dict[str, float]]
PlaceRecord = Dict[str, Record]


def is_float(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def normalize(x: np.ndarray) -> np.ndarray:
    std = np.std(x)
    if abs(std) > 1e-5:
        x = (x - np.average(x)) / std
    else:
        x = np.zeros_like(x)
    return x


def l1_normalize(x: List) -> List:
    s = sum(x)
    return [xi / s for xi in x]


def random_guiding(node_name_list, placedb: PlaceDB, grid_size) -> PlaceRecord:  # 将所有macro随机放置
    place_record: PlaceRecord = {}
    for node_name in node_name_list:
        width = placedb.node_info[node_name].width
        height = placedb.node_info[node_name].height
        if placedb.node_info[node_name].is_port:
            loc_x = placedb.node_info[node_name].bottom_left_x // grid_size
            loc_y = placedb.node_info[node_name].bottom_left_y // grid_size
        else:
            loc_x = np.random.randint(0, grid_size)
            loc_y = np.random.randint(0, grid_size)
        place_record[node_name] = Record(width, height, loc_x, loc_y, grid_size)
    return place_record


def rank_macros_area(placedb: PlaceDB) -> List[str]:  # 将macro按照固定顺序（net面积总和）从大到小排列，输出排序后的macro序列。
    for net_name in placedb.net_info:
        sum = 0
        for node_name in placedb.net_info[net_name]["nodes"].keys():
            sum += placedb.node_info[node_name].area
        placedb.net_info[net_name]["area"] = sum

    rank_area = {node_name: 0 for node_name in placedb.macro_name}
    for net_name in placedb.net_info:
        for node_name in placedb.net_info[net_name]["nodes"].keys():
            rank_area[node_name] += placedb.net_info[net_name]["area"]  # 自己的面积被算了 #net 次？

    node_name_ls = list(placedb.port_name) + sorted(
        placedb.macro_name, key=lambda x: rank_area[x], reverse=True
    )
    return node_name_ls


def cal_hpwl(place_record: PlaceRecord, placedb) -> float:
    hpwl = 0
    net_hpwl = {}
    for net_id in placedb.net_info.keys():
        for node_id in placedb.net_info[net_id]["nodes"]:
            if node_id in place_record.keys():
                center_x = (
                    place_record[node_id].center_x
                    + placedb.net_info[net_id]["nodes"][node_id]["x_offset"]
                )
                center_y = (
                    place_record[node_id].center_y
                    + placedb.net_info[net_id]["nodes"][node_id]["y_offset"]
                )
                if net_id not in net_hpwl.keys():
                    net_hpwl[net_id] = {
                        "x_max": center_x,
                        "x_min": center_x,
                        "y_max": center_y,
                        "y_min": center_y,
                    }
                else:
                    if net_hpwl[net_id]["x_max"] < center_x:
                        net_hpwl[net_id]["x_max"] = center_x
                    elif net_hpwl[net_id]["x_min"] > center_x:
                        net_hpwl[net_id]["x_min"] = center_x
                    if net_hpwl[net_id]["y_max"] < center_y:
                        net_hpwl[net_id]["y_max"] = center_y
                    elif net_hpwl[net_id]["y_min"] > center_y:
                        net_hpwl[net_id]["y_min"] = center_y
    for net_id in net_hpwl.keys():
        hpwl += (
            net_hpwl[net_id]["x_max"]
            - net_hpwl[net_id]["x_min"]
            + net_hpwl[net_id]["y_max"]
            - net_hpwl[net_id]["y_min"]
        )
    return hpwl


def cal_positionmask(node_name1: str, placedb: PlaceDB, place_record: PlaceRecord, grid_num):
    scaled_width = placedb.node_info[node_name1].scaled_width
    scaled_height = placedb.node_info[node_name1].scaled_height

    position_mask = np.zeros((grid_num, grid_num), dtype=bool)
    position_mask[: grid_num - scaled_width, : grid_num - scaled_height] = True

    for node_name2 in place_record.keys():
        bottom_left_x = max(0, place_record[node_name2].grid_x - scaled_width + 1)
        bottom_left_y = max(0, place_record[node_name2].grid_y - scaled_height + 1)
        top_right_x = min(
            grid_num, place_record[node_name2].grid_x + place_record[node_name2].scaled_width
        )
        top_right_y = min(
            grid_num, place_record[node_name2].grid_y + place_record[node_name2].scaled_height
        )

        position_mask[bottom_left_x:top_right_x, bottom_left_y:top_right_y] = False
    return position_mask


def chose_position(
    node_name, value_mask: np.ndarray, position_mask: np.ndarray, place_record: PlaceRecord
) -> Tuple[int, int]:
    min_ele = np.min(value_mask[position_mask])
    chosen_loc_x, chosen_loc_y = np.where(value_mask == min_ele)
    distance_ls = []
    pos_ls = []
    for grid_xi, grid_yi in zip(chosen_loc_x, chosen_loc_y):
        if position_mask[grid_xi, grid_yi]:
            pos_ls.append((grid_xi, grid_yi))
            distance_ls.append(
                distance.euclidean(
                    (grid_xi, grid_yi),
                    (place_record[node_name].grid_x, place_record[node_name].grid_y),
                )
            )
    idx = np.argmin(distance_ls)
    chosen_loc_x, chosen_loc_y = pos_ls[idx]
    return chosen_loc_x, chosen_loc_y


def cal_wiremask(node_id, placedb: PlaceDB, grid_num, grid_size, net_ls, hpwl_info_for_each_net):
    wire_mask = np.zeros((grid_num, grid_num))
    for net_id in net_ls.keys():
        if net_id in hpwl_info_for_each_net.keys():
            x_offset = (
                net_ls[net_id]["nodes"][node_id]["x_offset"]
                + 0.5 * placedb.node_info[node_id].width
            )
            y_offset = (
                net_ls[net_id]["nodes"][node_id]["y_offset"]
                + 0.5 * placedb.node_info[node_id].height
            )
            for col in range(grid_num):
                x_co = col * grid_size + x_offset
                y_co = col * grid_size + y_offset
                if x_co < hpwl_info_for_each_net[net_id]["x_min"]:
                    wire_mask[col, :] += hpwl_info_for_each_net[net_id]["x_min"] - x_co
                elif x_co > hpwl_info_for_each_net[net_id]["x_max"]:
                    wire_mask[col, :] += x_co - hpwl_info_for_each_net[net_id]["x_max"]
                if y_co < hpwl_info_for_each_net[net_id]["y_min"]:
                    wire_mask[:, col] += hpwl_info_for_each_net[net_id]["y_min"] - y_co
                elif y_co > hpwl_info_for_each_net[net_id]["y_max"]:
                    wire_mask[:, col] += y_co - hpwl_info_for_each_net[net_id]["y_max"]
    return wire_mask


def update_info(
    node_name,
    placedb: PlaceDB,
    grid_size,
    chosen_loc_x,
    chosen_loc_y,
    net_ls,
    hpwl_info_for_each_net,
):
    center_loc_x = grid_size * chosen_loc_x + 0.5 * placedb.node_info[node_name].width
    center_loc_y = grid_size * chosen_loc_y + 0.5 * placedb.node_info[node_name].height
    for net_id in net_ls.keys():
        x_offset = net_ls[net_id]["nodes"][node_name]["x_offset"]
        y_offset = net_ls[net_id]["nodes"][node_name]["y_offset"]
        if net_id not in hpwl_info_for_each_net.keys():
            hpwl_info_for_each_net[net_id] = {
                "x_max": center_loc_x + x_offset,
                "x_min": center_loc_x + x_offset,
                "y_max": center_loc_y + y_offset,
                "y_min": center_loc_y + y_offset,
            }
        else:
            if hpwl_info_for_each_net[net_id]["x_max"] < center_loc_x + x_offset:
                hpwl_info_for_each_net[net_id]["x_max"] = center_loc_x + x_offset
            elif hpwl_info_for_each_net[net_id]["x_min"] > center_loc_x + x_offset:
                hpwl_info_for_each_net[net_id]["x_min"] = center_loc_x + x_offset
            if hpwl_info_for_each_net[net_id]["y_max"] < center_loc_y + y_offset:
                hpwl_info_for_each_net[net_id]["y_max"] = center_loc_y + y_offset
            elif hpwl_info_for_each_net[net_id]["y_min"] > center_loc_y + y_offset:
                hpwl_info_for_each_net[net_id]["y_min"] = center_loc_y + y_offset
    return hpwl_info_for_each_net


# wire-based 贪心策略
def wiremask_placer(
    node_name_ls: List[str], placedb: PlaceDB, grid_num, grid_size, place_record: PlaceRecord
):
    shuffle = 0
    new_place_record: PlaceRecord = {}
    hpwl_info_for_each_net = {}

    time_start = time.time()
    N2_time = 0
    for node_name in node_name_ls:
        net_ls = {}
        for net_id in placedb.net_info.keys():
            if node_name in placedb.net_info[net_id]["nodes"].keys():
                net_ls[net_id] = placedb.net_info[net_id]
        if placedb.node_info[node_name].is_port:
            chosen_loc_x = placedb.node_info[node_name].bottom_left_x // grid_size
            chosen_loc_y = placedb.node_info[node_name].bottom_left_y // grid_size
        else:
            position_mask = cal_positionmask(node_name, placedb, new_place_record, grid_num)
            if not np.any(position_mask == 1):
                print("no_legal_place")
                print("\n")
                return {}, my_inf

            time0 = time.time()
            wire_mask = cal_wiremask(
                node_name, placedb, grid_num, grid_size, net_ls, hpwl_info_for_each_net
            )
            chosen_loc_x, chosen_loc_y = chose_position(
                node_name, wire_mask, position_mask, place_record
            )
            N2_time += time.time() - time0

            hpwl_info_for_each_net = update_info(
                node_name,
                placedb,
                grid_size,
                chosen_loc_x,
                chosen_loc_y,
                net_ls,
                hpwl_info_for_each_net,
            )
        width, height = placedb.node_info[node_name].width, placedb.node_info[node_name].height
        new_place_record[node_name] = Record(width, height, chosen_loc_x, chosen_loc_y, grid_size)
    time_end = time.time()

    hpwl = cal_hpwl(new_place_record, placedb)
    # print("time: {}\nN2_time: {}\nhpwl: {}\nshuffle or not: {}".format(time_end - time_start, N2_time, hpwl, shuffle))
    print("time:", time_end - time_start)
    print("N2_time:", N2_time)
    print("hpwl:", hpwl)
    print("shuffle or not: ", shuffle)
    print("\n")
    return new_place_record, hpwl


def write_final_placement(best_placed_macro: PlaceRecord, best_hpwl, dir):
    csv_file2 = open(dir, "a+")
    csv_writer2 = csv.writer(csv_file2)
    csv_writer2.writerow([best_hpwl, time.time()])
    for node_id in list(best_placed_macro.keys()):
        csv_writer2.writerow(
            [
                node_id,
                best_placed_macro[node_id].bottom_left_x,
                best_placed_macro[node_id].bottom_left_y,
            ]
        )
    csv_writer2.writerow([])
    csv_file2.close()


def write_pl(place_record: PlaceRecord, pl_file: str):
    with open(pl_file, "w", encoding="utf8") as f:
        f.write("UCLA pl 1.0\n\n")
        for node, record in place_record.items():
            f.write(f"{node}\t{record.bottom_left_x}\t{record.bottom_left_y} : N /FIXED\n")
