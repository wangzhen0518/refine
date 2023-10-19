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
        self.bottom_left_x: int = grid_x * grid_size  # + 452  #! 保持原有计算方式，为何要 +452
        self.bottom_left_y: int = grid_y * grid_size  # + 452  #! 保持原有计算方式，为何要 +452


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


def write_placement_and_overlap(place_record: PlaceRecord, net_hpwl, placedb: PlaceDB, method, dataset):
    length = placedb.max_height + 500
    congestion = np.zeros((length, length))
    canvas = np.ones((length, length, 3)) * 255
    margin = 5
    for node_id in place_record.keys():
        bottom_left_x = math.ceil(place_record[node_id].center_x - placedb.node_info[node_id].width / 2)
        bottom_left_y = math.ceil(place_record[node_id].center_y - placedb.node_info[node_id].height / 2)
        top_left_y = bottom_left_y + placedb.node_info[node_id].height
        bottom_right_x = bottom_left_x + placedb.node_info[node_id].width
        canvas[bottom_left_x:bottom_right_x, bottom_left_y:top_left_y] = [135, 206, 250]

        canvas[bottom_left_x:bottom_right_x, bottom_left_y : bottom_left_y + margin] = [0, 0, 0]
        canvas[bottom_left_x:bottom_right_x, top_left_y - margin : top_left_y] = [0, 0, 0]
        canvas[bottom_left_x : bottom_left_x + margin, bottom_left_y:top_left_y] = [0, 0, 0]
        canvas[bottom_right_x - margin : bottom_right_x, bottom_left_y:top_left_y] = [0, 0, 0]

    for net_id in net_hpwl.keys():
        x_max = math.ceil(net_hpwl[net_id]["x_max"])
        x_min = math.ceil(net_hpwl[net_id]["x_min"])
        y_max = math.ceil(net_hpwl[net_id]["y_max"])
        y_min = math.ceil(net_hpwl[net_id]["y_min"])
        delta_x = x_max - x_min
        delta_y = y_max - y_min
        if delta_x == 0 or delta_y == 0:
            continue
        congestion[x_min:x_max, y_min:y_max] += 1 / delta_x + 1 / delta_y

    g = canvas[:, :, 1] == 255
    extra_count = length**2 - placedb.max_height**2
    blank_count = len(canvas[g]) - extra_count
    all_count = placedb.max_height**2
    occupied_count = all_count - blank_count
    macro_all_count = 0
    for node_id in list(placedb.node_info.keys()):
        macro_all_count += placedb.node_info[node_id].area
    overlap_count = macro_all_count - occupied_count
    overlap_ratio = overlap_count / macro_all_count
    macro_util_ratio = blank_count / all_count
    congestion_list = congestion.reshape(1, -1).tolist()[0]
    congestion_mean = np.mean(heapq.nlargest(math.ceil(len(congestion_list) / 10), congestion_list))
    print(
        "overlap_ratio: ",
        round(overlap_ratio, 2),
        "congestion: ",
        round(congestion_mean * 100, 2),
        "macro_util_ratio: ",
        round(macro_util_ratio, 2),
    )

    cv2.imwrite("placement_visualization/{}_{}.pdf".format(method, dataset), canvas)
    return congestion_mean


def random_guiding(node_name_list, placedb: PlaceDB, grid_num, grid_size) -> PlaceRecord:  # 将所有macro随机放置
    N2_time = 0
    place_record: PlaceRecord = {}

    for node_name in node_name_list:
        width = placedb.node_info[node_name].width
        height = placedb.node_info[node_name].height

        position_mask = np.ones((grid_num, grid_num))

        loc_x_ls, loc_y_ls = np.where(position_mask == 1)
        place_record[node_name] = {}
        time0 = time.time()
        idx = random.choice(range(len(loc_x_ls)))
        place_record[node_name] = Record(width, height, loc_x_ls[idx], loc_y_ls[idx], grid_size)
        N2_time += time.time() - time0

    return place_record


def rank_macros_area(placedb: PlaceDB) -> List[str]:  # 将macro按照固定顺序（net面积总和）从大到小排列，输出排序后的macro序列。
    for net_name in placedb.net_info:
        sum = 0
        for node_name in placedb.net_info[net_name]["nodes"].keys():
            sum += placedb.node_info[node_name].area
        placedb.net_info[net_name]["area"] = sum

    rank_are = {node_name: 0 for node_name in placedb.node_info}
    for net_name in placedb.net_info:
        for node_name in placedb.net_info[net_name]["nodes"].keys():
            rank_are[node_name] += placedb.net_info[net_name]["area"]  # 自己的面积被算了 #net 次？

    node_name_ls = sorted(placedb.node_info, key=lambda x: rank_are[x], reverse=True)
    return node_name_ls


def rank_macros_mixed_port(
    placedb: PlaceDB, m2m_flow: M2MFlow, alpha=0.8, beta=0.2
) -> List[str]:  # 将macro按照固定顺序（net面积总和）从大到小排列，输出排序后的macro序列。
    for net_name in placedb.net_info:
        sum = 0
        for node_name in placedb.net_info[net_name]["nodes"].keys():
            sum += placedb.node_info[node_name].area
        placedb.net_info[net_name]["area"] = sum

    rank_area = {node_name: 0 for node_name in placedb.macro_name}
    if alpha > 0:
        for net_name in placedb.net_info:
            for node_name in placedb.net_info[net_name]["nodes"].keys():
                if node_name in rank_area:
                    rank_area[node_name] += placedb.net_info[net_name]["area"]  # 自己的面积被算了 #net 次？
        nomalize_list = np.array(list(rank_area.values()))
        aver = np.average(nomalize_list)
        std = np.std(nomalize_list)
        for node in rank_area:
            rank_area[node] = (rank_area[node] - aver) / std

    rank_dataflow = {node_name: 0 for node_name in placedb.macro_name}
    if beta > 0:
        for node_name1 in m2m_flow:
            for node_name2 in m2m_flow[node_name1]:
                if node_name1 in rank_dataflow:
                    rank_dataflow[node_name1] += m2m_flow[node_name1][node_name2]
        nomalize_list = np.array(list(rank_dataflow.values()))
        aver = np.average(nomalize_list)
        std = np.std(nomalize_list)
        for node in rank_dataflow:
            rank_dataflow[node] = (rank_dataflow[node] - aver) / std

    alpha, beta = alpha / (alpha + beta), beta / (alpha + beta)

    node_name_ls = sorted(placedb.macro_name, key=lambda x: alpha * rank_area[x] + beta * rank_dataflow[x], reverse=True)
    node_name_ls = list(placedb.port_name) + node_name_ls
    return node_name_ls


def rank_macros_mixed(
    placedb: PlaceDB, m2m_flow: M2MFlow, alpha=0.8, beta=0.2
) -> List[str]:  # 将macro按照固定顺序（net面积总和）从大到小排列，输出排序后的macro序列。
    for net_name in placedb.net_info:
        sum = 0
        for node_name in placedb.net_info[net_name]["nodes"].keys():
            sum += placedb.node_info[node_name].area
        placedb.net_info[net_name]["area"] = sum

    rank_area = {node_name: 0 for node_name in placedb.node_info}
    if alpha > 0:
        for net_name in placedb.net_info:
            for node_name in placedb.net_info[net_name]["nodes"].keys():
                if node_name in rank_area:
                    rank_area[node_name] += placedb.net_info[net_name]["area"]  # 自己的面积被算了 #net 次？
        nomalize_list = np.array(list(rank_area.values()))
        aver = np.average(nomalize_list)
        std = np.std(nomalize_list)
        for node in rank_area:
            rank_area[node] = (rank_area[node] - aver) / std

    rank_dataflow = {node_name: 0 for node_name in placedb.node_info}
    if beta > 0:
        for node_name1 in m2m_flow:
            for node_name2 in m2m_flow[node_name1]:
                if node_name1 in rank_dataflow:
                    rank_dataflow[node_name1] += m2m_flow[node_name1][node_name2]
        nomalize_list = np.array(list(rank_dataflow.values()))
        aver = np.average(nomalize_list)
        std = np.std(nomalize_list)
        for node in rank_dataflow:
            rank_dataflow[node] = (rank_dataflow[node] - aver) / std

    alpha, beta = alpha / (alpha + beta), beta / (alpha + beta)# TODO

    node_name_ls = sorted(placedb.node_info, key=lambda x: alpha * rank_area[x] + beta * rank_dataflow[x], reverse=True)
    return node_name_ls


def cal_hpwl(place_record: PlaceRecord, placedb) -> float:
    hpwl = 0
    net_hpwl = {}
    for net_id in placedb.net_info.keys():
        for node_id in placedb.net_info[net_id]["nodes"]:
            if node_id in place_record.keys():
                center_x = place_record[node_id].center_x + placedb.net_info[net_id]["nodes"][node_id]["x_offset"]
                center_y = place_record[node_id].center_y + placedb.net_info[net_id]["nodes"][node_id]["y_offset"]
                if net_id not in net_hpwl.keys():
                    net_hpwl[net_id] = {"x_max": center_x, "x_min": center_x, "y_max": center_y, "y_min": center_y}
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
        hpwl += net_hpwl[net_id]["x_max"] - net_hpwl[net_id]["x_min"] + net_hpwl[net_id]["y_max"] - net_hpwl[net_id]["y_min"]
    return hpwl


def get_m2m_flow(m2m_flow_file, err=1e-2) -> M2MFlow:
    df = pd.read_csv(m2m_flow_file)
    # m2m_flow_matrix = df.values
    m2m_flow_matrix = df.iloc[:, 1:]

    # num_macro = len(df.index)
    # m2m_flow = [[] for _ in range(num_macro)]
    m2m_flow = {}
    for mi in df.columns[1:]:
        m2m_flow[mi] = {}
    x, y = np.where(df.iloc[:, 1:] >= err)
    y += 1  # 0列是 macro name
    # for id1, id2 in zip(*np.where(m2m_flow_matrix >= err)):
    for id1, id2 in zip(x, y):
        m1_name = df.columns[id1 + 1]
        m2_name = df.columns[id2]
        m2m_flow[m1_name][m2_name] = df.iloc[id1, id2]

    # m2m_flow = m2m_flow_matrix
    return m2m_flow


def df_mul(d, df):
    return d * df


def df_div(d, df):
    return d / df


def cal_datamask(
    node_name1: str,
    placedb: PlaceDB,
    grid_num,
    grid_size,
    place_record: PlaceRecord,
    place_record_old: PlaceRecord,
    m2m_flow,
    df_func=df_mul,
):
    data_mask = np.zeros((grid_num, grid_num))
    for node_name2 in m2m_flow[node_name1]:
        if node_name2 in place_record.keys():
            pos_x2, pos_y2 = place_record[node_name2].center_x, place_record[node_name2].center_y
        else:
            pos_x2, pos_y2 = place_record_old[node_name2].center_x, place_record_old[node_name2].center_y
        for col in range(grid_num):  # 改为使用曼哈顿距离，减少对 row 的遍历，降低计算量
            row = col
            pos_x = row * grid_size + 0.5 * placedb.node_info[node_name1].width
            pos_y = col * grid_size + 0.5 * placedb.node_info[node_name1].height
            data_mask[row, :] += df_func(abs(pos_x2 - pos_x), m2m_flow[node_name1][node_name2])
            data_mask[:, col] += df_func(abs(pos_y2 - pos_y), m2m_flow[node_name1][node_name2])

        # for row in range(grid_num):  # 欧氏距离需要对row和col进行遍历，计算量较大
        #     pos_x = row * grid_size + 0.5 * placedb.node_info[node_name1].width
        #     for col in range(grid_num):
        #         pos_y = col * grid_size + 0.5 * placedb.node_info[node_name1].height
        #         data_mask[row, col] += df_func(
        #             distance.euclidean(
        #                 (pos_x, pos_y),
        #                 (pos_x2, pos_y2),
        #             ),
        #             m2m_flow[node_name1][node_name2],
        #         )
    return data_mask


# def cal_positionmask(node_name1: str, placedb: PlaceDB, place_record: PlaceRecord, grid_num):
#     scaled_width = placedb.node_info[node_name1].scaled_width
#     scaled_height = placedb.node_info[node_name1].scaled_height

#     position_mask = np.ones((grid_num, grid_num)) * my_inf
#     position_mask[: grid_num - scaled_width, : grid_num - scaled_height] = 1  #! TODO 确定是赋1吗

#     for node_name2 in place_record.keys():
#         bottom_left_x = max(0, place_record[node_name2].grid_x - scaled_width + 1)
#         bottom_left_y = max(0, place_record[node_name2].grid_y - scaled_height + 1)
#         top_right_x = min(grid_num, place_record[node_name2].grid_x + place_record[node_name2].scaled_width)
#         top_right_y = min(grid_num, place_record[node_name2].grid_y + place_record[node_name2].scaled_height)

#         position_mask[bottom_left_x:top_right_x, bottom_left_y:top_right_y] = my_inf  #! TODO 哪些位置需要赋0
#     return position_mask


# def cal_positionmask_port(placedb: PlaceDB, grid_num: int):
#     position_mask = np.zeros((grid_num, grid_num), dtype=bool)
#     for node_name, node_info in placedb.node_info.items():
#         if node_info.is_port:
#             pass


def cal_positionmask(node_name1: str, placedb: PlaceDB, place_record: PlaceRecord, grid_num):
    scaled_width = placedb.node_info[node_name1].scaled_width
    scaled_height = placedb.node_info[node_name1].scaled_height

    position_mask = np.zeros((grid_num, grid_num), dtype=bool)
    position_mask[: grid_num - scaled_width, : grid_num - scaled_height] = True

    for node_name2 in place_record.keys():
        bottom_left_x = max(0, place_record[node_name2].grid_x - scaled_width + 1)
        bottom_left_y = max(0, place_record[node_name2].grid_y - scaled_height + 1)
        top_right_x = min(grid_num, place_record[node_name2].grid_x + place_record[node_name2].scaled_width)
        top_right_y = min(grid_num, place_record[node_name2].grid_y + place_record[node_name2].scaled_height)

        position_mask[bottom_left_x:top_right_x, bottom_left_y:top_right_y] = False
    return position_mask


# def chose_position(node_id, value_mask, position_mask, place_record: PlaceRecord) -> Tuple[int, int]:
#     value_mask = value_mask * position_mask
#     min_ele = np.min(value_mask)
#     chosen_loc_x, chosen_loc_y = np.where(value_mask == min_ele)
#     distance_ls = []
#     for grid_xi, grid_yi in zip(chosen_loc_x, chosen_loc_y):
#         distance_ls.append(distance.euclidean((grid_xi, grid_yi), (place_record[node_id].grid_x, place_record[node_id].grid_y)))
#     idx = np.argmin(distance_ls)
#     chosen_loc_x = chosen_loc_x[idx]
#     chosen_loc_y = chosen_loc_y[idx]
#     return chosen_loc_x, chosen_loc_y


def chose_position(node_name, value_mask: np.ndarray, position_mask: np.ndarray, place_record: PlaceRecord) -> Tuple[int, int]:
    min_ele = np.min(value_mask[position_mask])
    chosen_loc_x, chosen_loc_y = np.where(value_mask == min_ele)
    distance_ls = []
    pos_ls = []
    for grid_xi, grid_yi in zip(chosen_loc_x, chosen_loc_y):
        if position_mask[grid_xi, grid_yi]:
            pos_ls.append((grid_xi, grid_yi))
            distance_ls.append(
                distance.euclidean((grid_xi, grid_yi), (place_record[node_name].grid_x, place_record[node_name].grid_y))
            )
    idx = np.argmin(distance_ls)
    chosen_loc_x, chosen_loc_y = pos_ls[idx]
    return chosen_loc_x, chosen_loc_y


#! 实现 data-based 贪心策略
def datamask_placer(node_id_ls, placedb: PlaceDB, grid_num, grid_size, place_record: PlaceRecord, m2m_flow):
    shuffle = 0
    new_place_record: PlaceRecord = {}

    time_start = time.time()
    N2_time = 0
    for cnt, node_name in enumerate(node_id_ls):
        # print(cnt, node_id)
        if placedb.node_info[node_name].is_port:
            chosen_loc_x = placedb.node_info[node_name].bottom_left_x // grid_size
            chosen_loc_y = placedb.node_info[node_name].bottom_left_y // grid_size
        else:
            #! 这部分为什么不直接用 place_record 里的结果？line 294-300
            position_mask = cal_positionmask(node_name, placedb, new_place_record, grid_num)
            if not np.any(position_mask == 1):
                print("no_legal_place")
                print("\n")
                return {}, my_inf

            # TODO !
            time0 = time.time()
            data_mask = cal_datamask(node_name, placedb, grid_num, grid_size, new_place_record, place_record, m2m_flow)
            data_mask = normalize(data_mask)
            chosen_loc_x, chosen_loc_y = chose_position(node_name, data_mask, position_mask, place_record)
            N2_time += time.time() - time0

        width, height = placedb.node_info[node_name].width, placedb.node_info[node_name].height
        new_place_record[node_name] = Record(width, height, chosen_loc_x, chosen_loc_y, grid_size)
    time_end = time.time()

    verified_hpwl = cal_hpwl(new_place_record, placedb)
    # print("time: {}\nN2_time: {}\nhpwl: {}\nshuffle or not: {}".format(time_end - time_start, N2_time, hpwl, shuffle))
    print("verified hpwl: ", verified_hpwl)
    print("time:", time_end - time_start)
    print("N2_time:", N2_time)
    # print("hpwl:", hpwl)
    print("shuffle or not: ", shuffle)
    print("\n")
    return new_place_record, verified_hpwl


def cal_wiremask(node_id, placedb: PlaceDB, grid_num, grid_size, net_ls, hpwl_info_for_each_net):
    wire_mask = np.zeros((grid_num, grid_num))
    for net_id in net_ls.keys():
        if net_id in hpwl_info_for_each_net.keys():
            x_offset = net_ls[net_id]["nodes"][node_id]["x_offset"] + 0.5 * placedb.node_info[node_id].width
            y_offset = net_ls[net_id]["nodes"][node_id]["y_offset"] + 0.5 * placedb.node_info[node_id].height
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


def update_info(node_name, placedb: PlaceDB, grid_size, chosen_loc_x, chosen_loc_y, net_ls, hpwl_info_for_each_net):
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
def wiremask_placer(node_name_ls: List[str], placedb: PlaceDB, grid_num, grid_size, place_record: PlaceRecord, m2m_flow=None):
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
        # if placedb.node_info[node_name].is_port:
        #     chosen_loc_x = placedb.node_info[node_name].bottom_left_x // grid_size
        #     chosen_loc_y = placedb.node_info[node_name].bottom_left_y // grid_size
        # else:
        #! 这部分为什么不直接用 place_record 里的结果？line 294-300
        position_mask = cal_positionmask(node_name, placedb, new_place_record, grid_num)
        if not np.any(position_mask == 1):
            print("no_legal_place")
            print("\n")
            return {}, my_inf

        time0 = time.time()
        wire_mask = cal_wiremask(node_name, placedb, grid_num, grid_size, net_ls, hpwl_info_for_each_net)
        chosen_loc_x, chosen_loc_y = chose_position(node_name, wire_mask, position_mask, place_record)
        N2_time += time.time() - time0

        hpwl_info_for_each_net = update_info(
            node_name, placedb, grid_size, chosen_loc_x, chosen_loc_y, net_ls, hpwl_info_for_each_net
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


def cal_regularity_mask(node_name1: str, placedb: PlaceDB, grid_num: int, grid_size: int):
    regu_mask = np.zeros((grid_num, grid_num))
    for row in range(grid_num):  # 欧氏距离需要对row和col进行遍历，计算量较大
        pos_x = row * grid_size + 0.5 * placedb.node_info[node_name1].width
        for col in range(grid_num):
            pos_y = col * grid_size + 0.5 * placedb.node_info[node_name1].height
            regu_mask[row, col] = min(pos_x, placedb.max_width - pos_x) + min(pos_y, placedb.max_height - pos_y)
    return regu_mask


def mixed_placer(
    node_name_ls: List[str],
    placedb: PlaceDB,
    grid_num,
    grid_size,
    place_record: PlaceRecord,
    m2m_flow,
    alpha=0.6,
    beta=0.3,
    gamma=0.1,
):
    alpha, beta, gamma = l1_normalize([alpha, beta, gamma])
    shuffle = 0
    new_place_record: PlaceRecord = {}
    hpwl_info_for_each_net = {}
    total_regu_mask = {}

    time_start = time.time()
    N2_time = 0
    for node_name in node_name_ls:
        if alpha > 0:
            net_ls = {}
            for net_id in placedb.net_info.keys():
                if node_name in placedb.net_info[net_id]["nodes"].keys():
                    net_ls[net_id] = placedb.net_info[net_id]
        # if placedb.node_info[node_name].is_port:
        #     chosen_loc_x = placedb.node_info[node_name].bottom_left_x // grid_size
        #     chosen_loc_y = placedb.node_info[node_name].bottom_left_y // grid_size
        # else:
        #! 这部分为什么不直接用 place_record 里的结果？line 294-300
        position_mask = cal_positionmask(node_name, placedb, new_place_record, grid_num)
        if not np.any(position_mask == 1):
            print("no_legal_place")
            print("\n")
            return [], my_inf

        time0 = time.time()
        if alpha > 0:
            wiremask = cal_wiremask(node_name, placedb, grid_num, grid_size, net_ls, hpwl_info_for_each_net)
            wiremask = normalize(wiremask)
        else:
            wiremask = np.zeros((grid_num, grid_num))
        if beta > 0:
            datamask = cal_datamask(node_name, placedb, grid_num, grid_size, new_place_record, place_record, m2m_flow)
            datamask = normalize(datamask)
        else:
            datamask = np.zeros((grid_num, grid_num))
        if gamma > 0:
            if node_name not in total_regu_mask:
                total_regu_mask[node_name] = normalize(cal_regularity_mask(node_name, placedb, grid_num, grid_size))
            regu_mask = total_regu_mask[node_name]
        else:
            regu_mask = np.zeros((grid_num, grid_num))
        mask = alpha * wiremask + beta * datamask + gamma * regu_mask
        chosen_loc_x, chosen_loc_y = chose_position(node_name, mask, position_mask, place_record)
        N2_time += time.time() - time0

        if alpha > 0:
            hpwl_info_for_each_net = update_info(
                node_name, placedb, grid_size, chosen_loc_x, chosen_loc_y, net_ls, hpwl_info_for_each_net
            )
        width, height = placedb.node_info[node_name].width, placedb.node_info[node_name].height
        new_place_record[node_name] = Record(width, height, chosen_loc_x, chosen_loc_y, grid_size)
    time_end = time.time()

    hpwl = cal_hpwl(new_place_record, placedb)
    # print("time: {}\nN2_time: {}\nhpwl: {}\nshuffle or not: {}".format(time_end - time_start, N2_time, hpwl, shuffle))
    print("hpwl:", hpwl)
    print("time:", time_end - time_start)
    print("N2_time:", N2_time)
    print("shuffle or not: ", shuffle)
    print("\n")
    return new_place_record, hpwl


def write_final_placement(best_placed_macro: PlaceRecord, dir):
    csv_file2 = open(dir, "a+")
    csv_writer2 = csv.writer(csv_file2)
    csv_writer2.writerow([time.time()])
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


def draw_macro_placement(place_record: PlaceRecord, file_path, placedb: PlaceDB, m2m_flow: M2MFlow, correct=None):
    fig = plt.figure()
    ax = fig.add_axes([0, 0, 1, 1], frameon=True, aspect=1.0)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    ax.margins(x=0, y=0)
    for node_name in place_record:
        width, height = place_record[node_name].width, place_record[node_name].height
        x, y = place_record[node_name].bottom_left_x, place_record[node_name].bottom_left_y
        node_id = placedb.node_info[node_name].id
        is_correct = False
        if correct is not None and correct[node_id]:
            is_correct = True
        ax.add_patch(
            patches.Rectangle(
                (x / placedb.max_width, y / placedb.max_height),  # (x,y)
                float(width / placedb.max_width),  # width
                float(height / placedb.max_height),
                linewidth=0.1,
                edgecolor="k",
                alpha=0.9,
                facecolor="tab:blue" if is_correct else "tab:green",
            )
        )
        cx = (x + width / 2) / placedb.max_width
        cy = (y + height / 2) / placedb.max_height

        ax.annotate(
            placedb.node_info[node_name].id,
            (x / placedb.max_width, y / placedb.max_height),
            (cx, cy),
            color="k",
            weight="bold",
            fontsize=6,
            ha="center",
            va="center",
        )
    for node_name1 in m2m_flow:
        for node_name2 in m2m_flow[node_name1]:
            ax.plot(
                [place_record[node_name1].center_x / placedb.max_width, place_record[node_name2].center_x / placedb.max_width],
                [place_record[node_name1].center_y / placedb.max_height, place_record[node_name2].center_y / placedb.max_height],
                color="blue",
                linewidth=np.log(m2m_flow[node_name1][node_name2] + 1),
            )

    # print("x_max = {}, y_max ={}".format(x_max, y_max))
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    plt.savefig(file_path, dpi=600, bbox_inches="tight")
    plt.close()


def read_placement(placedb: PlaceDB, grid_size, file_path) -> PlaceRecord:  # 将所有macro随机放置
    place_record: PlaceRecord = {}
    f = open(file_path, encoding="utf8")
    # 将 f 移动到最后一个记录的位置
    pos = 0
    l = f.readline()
    while l != "":
        if is_float(l):
            pos = f.tell()
        l = f.readline()
    f.seek(pos)

    l = f.readline()
    while l != "" and l != "\n":
        node_id, bottom_left_x, bottom_left_y = l.split(",")
        bottom_left_x, bottom_left_y = int(bottom_left_x), int(bottom_left_y)
        chosen_loc_x, chosen_loc_y = int(bottom_left_x / grid_size), int(bottom_left_y / grid_size)
        place_record[node_id] = Record(
            placedb.node_info[node_id].width, placedb.node_info[node_id].height, chosen_loc_x, chosen_loc_y, grid_size
        )
        l = f.readline()
    return place_record


def draw_macros(placedb: PlaceDB, pl_file, grid_size, m2m_flow: M2MFlow, pic_path):
    place_record = read_placement(placedb, grid_size, pl_file)
    draw_macro_placement(place_record, pic_path, placedb, m2m_flow)


def draw_detailed_placement(node_file: str, pl_file: str, pic_file: str, max_width: int, max_height: int, grid_size: int):
    node_dict: Dict[str, Node] = {}
    with open(node_file, "r", encoding="utf8") as f:
        cnt = 0
        for l in f:
            if l.startswith("\t") or l.startswith(" "):
                l = l.strip().split()
                node_name, width, height = l[:3]
                node = Node(cnt, node_name, 0, 0, int(width), int(height), grid_size)
                if l[-1] == "terminal":
                    node.is_fixed = True
                    cnt += 1
                node_dict[node_name] = node
    with open(pl_file, "r", encoding="utf8") as f:
        for l in f:
            if l.startswith("o"):
                l = l.strip().split()
                node_name, bottom_left_x, bottom_left_y = l[:3]
                node_dict[node_name].bottom_left_x = int(bottom_left_x)
                node_dict[node_name].bottom_left_y = int(bottom_left_y)

    fig = plt.figure()
    ax = fig.add_axes([0, 0, 1, 1], frameon=True, aspect=1.0)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    # for node_name, node in node_dict.items():
    node_x_list, node_y_list = [], []
    for node in node_dict.values():
        # print(node.name)
        if node.is_fixed:
            ax.add_patch(
                patches.Rectangle(
                    (node.bottom_left_x / max_width, node.bottom_left_y / max_height),  # (x,y)
                    float(node.width / max_width),  # width
                    float(node.height / max_height),
                    linewidth=0.1,
                    edgecolor="k",
                    alpha=0.9,
                    facecolor="tab:green",
                )
            )
            cx = (node.bottom_left_x + node.width / 2) / max_width
            cy = (node.bottom_left_y + node.height / 2) / max_height
            ax.annotate(
                node.id,
                (node.bottom_left_x / max_width, node.bottom_left_y / max_height),
                (cx, cy),
                color="k",
                weight="bold",
                fontsize=6,
                ha="center",
                va="center",
            )
        else:
            node_x_list.append(node.bottom_left_x / max_width)
            node_y_list.append(node.bottom_left_y / max_height)
    ax.scatter(node_x_list, node_y_list, 0.15, "dodgerblue", edgecolors="none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.savefig(pic_file, dpi=600, bbox_inches="tight")
    plt.close(fig)
