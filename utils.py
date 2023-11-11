import csv
import math
import time
from typing import Dict, List, Tuple

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import distance

from common import my_inf
from place_db import Node, PlaceDB


class Record:
    def __init__(
        self,
        name: str,
        _width: int,
        _height: int,
        grid_x: int,
        grid_y: int,
        bottom_left_x: int,
        bottom_left_y: int,
        grid_size: int,
    ) -> None:
        self.name = name
        self.width: int = _width
        self.height: int = _height
        self.grid_x: int = grid_x
        self.grid_y: int = grid_y
        self.bottom_left_x: int = bottom_left_x
        self.bottom_left_y: int = bottom_left_y
        self.scaled_width: int = math.ceil(
            (_width + bottom_left_x - grid_size * grid_x) / grid_size
        )
        self.scaled_height: int = math.ceil(
            (_height + bottom_left_y - grid_size * grid_y) / grid_size
        )
        self.center_x: float = bottom_left_x + 0.5 * _width
        self.center_y: float = bottom_left_y + 0.5 * _height

    def refresh(self, grid_size: int):
        self.scaled_width: int = math.ceil(
            (self.width + self.bottom_left_x - grid_size * self.grid_x) / grid_size
        )
        self.scaled_height: int = math.ceil(
            (self.height + self.bottom_left_y - grid_size * self.grid_y) / grid_size
        )
        self.center_x: float = self.bottom_left_x + 0.5 * self.width
        self.center_y: float = self.bottom_left_y + 0.5 * self.height


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


def random_guiding(
    node_name_list: List[str], placedb: PlaceDB, grid_size: int
) -> PlaceRecord:  # 将所有macro随机放置
    place_record: PlaceRecord = {}
    for node_name in node_name_list:
        width = placedb.node_info[node_name].width
        height = placedb.node_info[node_name].height
        if placedb.node_info[node_name].is_port:
            loc_x = placedb.node_info[node_name].bottom_left_x // grid_size
            loc_y = placedb.node_info[node_name].bottom_left_y // grid_size
            bottom_left_x = placedb.node_info[node_name].bottom_left_x
            bottom_left_y = placedb.node_info[node_name].bottom_left_y
        else:
            loc_x = np.random.randint(0, grid_size)
            loc_y = np.random.randint(0, grid_size)
            bottom_left_x = loc_x * grid_size
            bottom_left_y = loc_y * grid_size
        place_record[node_name] = Record(
            node_name,
            width,
            height,
            loc_x,
            loc_y,
            bottom_left_x,
            bottom_left_y,
            grid_size,
        )
    return place_record


def rank_macros_area(placedb: PlaceDB) -> List[str]:
    # 将macro按照固定顺序（net面积总和）从大到小排列，输出排序后的macro序列。
    for net_name in placedb.net_info:
        sum_area = 0
        for node_name in placedb.net_info[net_name]["nodes"].keys():
            if not placedb.node_info[node_name].is_port:
                sum_area += placedb.node_info[node_name].area
        placedb.net_info[net_name]["area"] = sum_area

    rank_area = {node_name: 0 for node_name in placedb.macro_name}
    for net_name in placedb.net_info:
        for node_name in placedb.net_info[net_name]["nodes"].keys():
            if not placedb.node_info[node_name].is_port:
                rank_area[node_name] += placedb.net_info[net_name][
                    "area"
                ]  # 自己的面积被算了 #net 次？

    node_name_ls = sorted(placedb.port_name) + sorted(
        placedb.macro_name, key=lambda x: (rank_area[x], x), reverse=True
    )
    return node_name_ls


def rank_macros_mixed_port(
    placedb: PlaceDB, m2m_flow: M2MFlow, alpha=0.8, beta=0.2
) -> List[str]:
    # 将macro按照固定顺序（net面积总和）从大到小排列，输出排序后的macro序列。
    for net_name in placedb.net_info:
        sum = 0
        for node_name in placedb.net_info[net_name]["nodes"].keys():
            sum += placedb.node_info[node_name].area
        placedb.net_info[net_name]["area"] = sum

    rank_area = {node_name: 0 for node_name in placedb.macro_name}
    if alpha > 0:
        # for net_name in placedb.net_info:
        #     for node_name in placedb.net_info[net_name]["nodes"].keys():
        #         if node_name in rank_area:
        #             # 自己的面积被算了 #net 次？
        #             rank_area[node_name] += placedb.net_info[net_name]["area"]
        rank_area = {
            node_name: placedb.node_info[node_name].area
            for node_name in placedb.macro_name
        }
        nomalize_list = np.array(list(rank_area.values()))
        aver = np.average(nomalize_list)
        std = np.std(nomalize_list)
        for node in rank_area:
            rank_area[node] = (rank_area[node] - aver) / std

    rank_dataflow = {node_name: 0 for node_name in placedb.macro_name}
    if beta > 0:
        for node_name1 in m2m_flow:
            for node_name2 in m2m_flow[node_name1]:
                if node_name1 in rank_dataflow and node_name2 in placedb.node_info:
                    rank_dataflow[node_name1] += m2m_flow[node_name1][node_name2]
        nomalize_list = np.array(list(rank_dataflow.values()))
        aver = np.average(nomalize_list)
        std = np.std(nomalize_list)
        for node in rank_dataflow:
            rank_dataflow[node] = (rank_dataflow[node] - aver) / std

    alpha, beta = alpha / (alpha + beta), beta / (alpha + beta)

    node_name_ls = sorted(
        placedb.macro_name,
        key=lambda x: (alpha * rank_area[x] + beta * rank_dataflow[x], x),
        reverse=True,
    )
    node_name_ls = sorted(placedb.port_name) + node_name_ls
    return node_name_ls


def rank_macros_mixed(
    placedb: PlaceDB, m2m_flow: M2MFlow, alpha=0.8, beta=0.2
) -> List[str]:
    # 将macro按照固定顺序（net面积总和）从大到小排列，输出排序后的macro序列。
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
                    rank_area[node_name] += placedb.net_info[net_name][
                        "area"
                    ]  # 自己的面积被算了 #net 次？
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

    alpha, beta = alpha / (alpha + beta), beta / (alpha + beta)  # TODO

    node_name_ls = sorted(
        placedb.node_info,
        key=lambda x: alpha * rank_area[x] + beta * rank_dataflow[x],
        reverse=True,
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


def get_m2m_flow(m2m_flow_file, threshold=1e-2) -> M2MFlow:
    df = pd.read_csv(m2m_flow_file, index_col=0)
    m2m_flow = {}
    for mi in df.index:
        m2m_flow[mi] = {}
    x, y = np.where(df >= threshold)
    for id1, id2 in zip(x, y):
        m1_name = df.columns[id1]
        m2_name = df.columns[id2]
        df12 = max(df.iloc[id1, id2], df.iloc[id2, id1])
        m2m_flow[m1_name][m2_name] = m2m_flow[m2_name][m1_name] = df12
    return m2m_flow


def cal_dataflow(place_record: PlaceRecord, placedb: PlaceDB, m2m_flow: M2MFlow):
    dataflow_total = 0
    for node_name1 in placedb.macro_name:
        for node_name2 in m2m_flow[node_name1]:
            if node_name2 in place_record:
                dataflow_total += (
                    abs(
                        place_record[node_name1].center_x
                        - place_record[node_name2].center_x
                    )
                    + abs(
                        place_record[node_name1].center_y
                        - place_record[node_name2].center_y
                    )
                ) * m2m_flow[node_name1][node_name2]
    return dataflow_total


def cal_regularity(place_record: PlaceRecord, placedb: PlaceDB):
    regularity = 0
    for node_name in placedb.macro_name:
        left_x = place_record[node_name].bottom_left_x
        right_x = place_record[node_name].bottom_left_x + place_record[node_name].width
        bottom_y = place_record[node_name].bottom_left_y
        top_y = place_record[node_name].bottom_left_y + place_record[node_name].height
        regularity += placedb.node_info[node_name].area * cal_pos_regularity(
            left_x, right_x, bottom_y, top_y, node_name, placedb
        )
    return regularity


def cal_pos_regularity(left_x, right_x, bottom_y, top_y, node_name, placedb: PlaceDB):
    center_x = left_x + 0.5 * placedb.node_info[node_name].width
    center_y = bottom_y + 0.5 * placedb.node_info[node_name].height
    dist = distance.euclidean(
        (center_x, center_y), (placedb.center_x, placedb.center_y)
    )
    if dist > placedb.r:
        regu = min(
            abs(left_x - placedb.left_boundary),
            abs(placedb.right_boundary - right_x),
            abs(bottom_y - placedb.bottom_boundary),
            abs(placedb.top_boundary - top_y),
        )
    else:
        regu = placedb.L2 / (dist + 1e-5)
    return regu


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
        # 在 m2m_flow 中的点，可能是被删除的 port，所以需要标记是否有效
        if node_name2 in place_record:
            pos_x2, pos_y2 = (
                place_record[node_name2].center_x,
                place_record[node_name2].center_y,
            )
            for col in range(grid_num):
                # 改为使用曼哈顿距离，减少对 row 的遍历，降低计算量
                row = col
                pos_x = row * grid_size + 0.5 * placedb.node_info[node_name1].width
                pos_y = col * grid_size + 0.5 * placedb.node_info[node_name1].height
                data_mask[row, :] += df_func(
                    abs(pos_x2 - pos_x), m2m_flow[node_name1][node_name2]
                )
                data_mask[:, col] += df_func(
                    abs(pos_y2 - pos_y), m2m_flow[node_name1][node_name2]
                )

    return data_mask


def draw_position_mask(position_mask: np.ndarray):
    from PIL import Image

    table = [0] + [1] * 255
    pic = Image.fromarray(np.flip(position_mask, 0), mode="L").point(table, "1")
    pic.save("position_mask.png")
    pic.close()


def cal_positionmask(
    node_name1: str, placedb: PlaceDB, place_record: PlaceRecord, grid_num
):
    scaled_width = placedb.node_info[node_name1].scaled_width
    scaled_height = placedb.node_info[node_name1].scaled_height

    position_mask = np.zeros((grid_num, grid_num), dtype=bool)
    position_mask[: grid_num - scaled_width, : grid_num - scaled_height] = True
    # draw_position_mask(position_mask)

    for node_name2 in place_record.keys():
        bottom_left_x = max(0, place_record[node_name2].grid_x - scaled_width + 1)
        bottom_left_y = max(0, place_record[node_name2].grid_y - scaled_height + 1)
        top_right_x = min(
            grid_num - 1,
            place_record[node_name2].grid_x + place_record[node_name2].scaled_width,
        )
        top_right_y = min(
            grid_num - 1,
            place_record[node_name2].grid_y + place_record[node_name2].scaled_height,
        )

        position_mask[bottom_left_x:top_right_x, bottom_left_y:top_right_y] = False
        # draw_position_mask(position_mask)
    return position_mask


def chose_position(
    node_name,
    value_mask: np.ndarray,
    position_mask: np.ndarray,
    place_record: PlaceRecord,
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


#! 实现 data-based 贪心策略
def datamask_placer(
    node_id_ls,
    placedb: PlaceDB,
    grid_num,
    grid_size,
    place_record: PlaceRecord,
    m2m_flow,
):
    shuffle = 0
    new_place_record: PlaceRecord = {}

    time_start = time.time()
    N2_time = 0
    for cnt, node_name in enumerate(node_id_ls):
        # print(cnt, node_id)
        if placedb.node_info[node_name].is_port:
            chosen_loc_x = placedb.node_info[node_name].bottom_left_x // grid_size
            chosen_loc_y = placedb.node_info[node_name].bottom_left_y // grid_size
            bottom_left_x = placedb.node_info[node_name].bottom_left_x
            bottom_left_y = placedb.node_info[node_name].bottom_left_y
        else:
            #! 这部分为什么不直接用 place_record 里的结果？line 294-300
            position_mask = cal_positionmask(
                node_name, placedb, new_place_record, grid_num
            )
            if not np.any(position_mask == 1):
                print("no_legal_place")
                print("\n")
                return {}, my_inf

            # TODO !
            time0 = time.time()
            data_mask = cal_datamask(
                node_name,
                placedb,
                grid_num,
                grid_size,
                new_place_record,
                place_record,
                m2m_flow,
            )
            data_mask = normalize(data_mask)
            chosen_loc_x, chosen_loc_y = chose_position(
                node_name, data_mask, position_mask, place_record
            )
            bottom_left_x = grid_size * chosen_loc_x
            bottom_left_y = grid_size * chosen_loc_y
            N2_time += time.time() - time0

        width, height = (
            placedb.node_info[node_name].width,
            placedb.node_info[node_name].height,
        )
        new_place_record[node_name] = Record(
            node_name,
            width,
            height,
            chosen_loc_x,
            chosen_loc_y,
            bottom_left_x,
            bottom_left_y,
            grid_size,
        )
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


def cal_wiremask(
    node_id, placedb: PlaceDB, grid_num, grid_size, net_ls, hpwl_info_for_each_net
):
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
    bottom_left_x,
    bottom_left_y,
    net_ls,
    hpwl_info_for_each_net,
):
    center_loc_x = bottom_left_x + 0.5 * placedb.node_info[node_name].width
    center_loc_y = bottom_left_y + 0.5 * placedb.node_info[node_name].height
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
    node_name_ls: List[str],
    placedb: PlaceDB,
    grid_num,
    grid_size,
    place_record: PlaceRecord,
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
            new_place_record[node_name] = place_record[node_name]
            bottom_left_x = placedb.node_info[node_name].bottom_left_x
            bottom_left_y = placedb.node_info[node_name].bottom_left_y
        else:
            #! 这部分为什么不直接用 place_record 里的结果？line 294-300
            position_mask = cal_positionmask(
                node_name, placedb, new_place_record, grid_num
            )
            if not np.any(position_mask == 1):
                print("no_legal_place\n\n")
                return {}, my_inf

            time0 = time.time()
            wire_mask = cal_wiremask(
                node_name, placedb, grid_num, grid_size, net_ls, hpwl_info_for_each_net
            )
            chosen_loc_x, chosen_loc_y = chose_position(
                node_name, wire_mask, position_mask, place_record
            )
            bottom_left_x = grid_size * chosen_loc_x
            bottom_left_y = grid_size * chosen_loc_y
            new_place_record[node_name] = Record(
                node_name,
                placedb.node_info[node_name].width,
                placedb.node_info[node_name].height,
                chosen_loc_x,
                chosen_loc_y,
                bottom_left_x,
                bottom_left_y,
                grid_size,
            )
            N2_time += time.time() - time0
        hpwl_info_for_each_net = update_info(
            node_name,
            placedb,
            bottom_left_x,
            bottom_left_y,
            net_ls,
            hpwl_info_for_each_net,
        )
    time_end = time.time()

    hpwl = cal_hpwl(new_place_record, placedb)
    # print("time: {}\nN2_time: {}\nhpwl: {}\nshuffle or not: {}".format(time_end - time_start, N2_time, hpwl, shuffle))
    print("time:", time_end - time_start)
    print("N2_time:", N2_time)
    print("hpwl:", hpwl)
    print("shuffle or not: ", shuffle)
    print("\n")
    return new_place_record, hpwl


def cal_regularity_mask(
    node_name1: str, placedb: PlaceDB, grid_num: int, grid_size: int
):
    regu_mask = np.zeros((grid_num, grid_num))
    for row in range(grid_num):
        left_x = row * grid_size
        right_x = row * grid_size + placedb.node_info[node_name1].width
        for col in range(grid_num):
            bottom_y = col * grid_size
            top_y = col * grid_size + placedb.node_info[node_name1].height
            regu_mask[row, col] = cal_pos_regularity(
                left_x, right_x, bottom_y, top_y, node_name1, placedb
            )
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
    new_place_record: PlaceRecord = {}
    hpwl_info_for_each_net = {}
    total_regu_mask = {}

    for node_name in node_name_ls:
        if alpha > 0:
            net_ls = {}
            for net_id in placedb.net_info.keys():
                if node_name in placedb.net_info[net_id]["nodes"].keys():
                    net_ls[net_id] = placedb.net_info[net_id]
        if placedb.node_info[node_name].is_port:
            new_place_record[node_name] = place_record[node_name]
            bottom_left_x = placedb.node_info[node_name].bottom_left_x
            bottom_left_y = placedb.node_info[node_name].bottom_left_y
        else:
            # print(node_name, end=", ")
            position_mask = cal_positionmask(
                node_name, placedb, new_place_record, grid_num
            )
            if not np.any(position_mask):
                print(f"\n{node_name}\tno_legal_place")
                # for node in new_place_record.values():
                #     print(node.name, node.scaled_width, node.scaled_height)
                return new_place_record, False

            if alpha > 0:
                wiremask = cal_wiremask(
                    node_name,
                    placedb,
                    grid_num,
                    grid_size,
                    net_ls,
                    hpwl_info_for_each_net,
                )
                wiremask = normalize(wiremask)
            else:
                wiremask = np.zeros((grid_num, grid_num))
            if beta > 0:
                datamask = cal_datamask(
                    node_name,
                    placedb,
                    grid_num,
                    grid_size,
                    new_place_record,
                    place_record,
                    m2m_flow,
                )
                datamask = normalize(datamask)
            else:
                datamask = np.zeros((grid_num, grid_num))
            if gamma > 0:
                if node_name not in total_regu_mask:
                    total_regu_mask[node_name] = normalize(
                        cal_regularity_mask(node_name, placedb, grid_num, grid_size)
                    )
                regu_mask = total_regu_mask[node_name]
            else:
                regu_mask = np.zeros((grid_num, grid_num))
            mask = alpha * wiremask + beta * datamask + gamma * regu_mask
            chosen_loc_x, chosen_loc_y = chose_position(
                node_name, mask, position_mask, place_record
            )
            bottom_left_x = grid_size * chosen_loc_x
            bottom_left_y = grid_size * chosen_loc_y
            new_place_record[node_name] = Record(
                node_name,
                placedb.node_info[node_name].width,
                placedb.node_info[node_name].height,
                chosen_loc_x,
                chosen_loc_y,
                bottom_left_x,
                bottom_left_y,
                grid_size,
            )
        if alpha > 0:
            hpwl_info_for_each_net = update_info(
                node_name,
                placedb,
                bottom_left_x,
                bottom_left_y,
                net_ls,
                hpwl_info_for_each_net,
            )

    return new_place_record, True


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


def draw_regularity(ax, placedb: PlaceDB):
    if placedb.center_core:
        ax.add_patch(
            patches.Circle(
                (0.5, 0.5),
                placedb.r / placedb.max_width,
                linewidth=1,
                edgecolor="orange",
                fill=False,
            )
        )
    if placedb.virtual_boundary:
        ax.add_patch(
            patches.Rectangle(
                (
                    placedb.left_boundary / placedb.max_width,
                    placedb.bottom_boundary / placedb.max_height,
                ),
                (placedb.boundary_length) / placedb.max_width,
                (placedb.boundary_length) / placedb.max_height,
                linewidth=1,
                edgecolor="red",
                fill=False,
            )
        )


def draw_macro_placement(
    place_record: PlaceRecord,
    file_path,
    placedb: PlaceDB,
    m2m_flow: M2MFlow = None,
    draw_id: bool = True,
):
    fig = plt.figure()
    ax = fig.add_axes([0, 0, 1, 1], frameon=True, aspect=1.0)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    ax.margins(x=0, y=0)

    for node_name in place_record:
        width, height = place_record[node_name].width, place_record[node_name].height
        x, y = (
            place_record[node_name].bottom_left_x,
            place_record[node_name].bottom_left_y,
        )
        if not placedb.node_info[node_name].is_port:  # macro 用绿色
            color = "tab:green"
        else:  # port 用蓝色
            color = "cyan"
        ax.add_patch(
            patches.Rectangle(
                (x / placedb.max_width, y / placedb.max_height),  # (x,y)
                float(width / placedb.max_width),  # width
                float(height / placedb.max_height),
                linewidth=0.1,
                edgecolor="k",
                alpha=0.9,
                facecolor=color,
            )
        )
        cx = (x + width / 2) / placedb.max_width
        cy = (y + height / 2) / placedb.max_height
        if (not placedb.node_info[node_name].is_port) and draw_id:
            ax.annotate(
                placedb.node_info[node_name].name,
                (x / placedb.max_width, y / placedb.max_height),
                (cx, cy),
                color="k",
                weight="bold",
                fontsize=6,
                ha="center",
                va="center",
            )
    if m2m_flow:
        m2m_flow_draw_record = set()
        for node_name1 in m2m_flow:
            if node_name1 in place_record:
                for node_name2 in m2m_flow[node_name1]:
                    if node_name2 in place_record:
                        if ((node_name1, node_name2) not in m2m_flow_draw_record) and (
                            (node_name2, node_name1) not in m2m_flow_draw_record
                        ):
                            ax.plot(
                                [
                                    place_record[node_name1].center_x
                                    / placedb.max_width,
                                    place_record[node_name2].center_x
                                    / placedb.max_width,
                                ],
                                [
                                    place_record[node_name1].center_y
                                    / placedb.max_height,
                                    place_record[node_name2].center_y
                                    / placedb.max_height,
                                ],
                                color="blue",
                                linewidth=np.log2(m2m_flow[node_name1][node_name2] + 1),
                            )
                            m2m_flow_draw_record.add((node_name1, node_name2))

    draw_regularity(ax, placedb)

    # print("x_max = {}, y_max ={}".format(x_max, y_max))
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    plt.savefig(file_path, dpi=600, bbox_inches="tight")
    plt.close()


def read_placement(
    placedb: PlaceDB, grid_size, file_path
) -> PlaceRecord:  # 将所有macro随机放置
    place_record: PlaceRecord = {}
    f = open(file_path, encoding="utf8")
    # 将 f 移动到最后一个记录的位置
    pos = 0
    line = f.readline()
    while line != "":
        line = line.strip().split(",")
        if is_float(line[0]):
            pos = f.tell()
        line = f.readline()
    f.seek(pos)

    line = f.readline()
    while line != "" and line != "\n":
        node_name, bottom_left_x, bottom_left_y = line.split(",")
        bottom_left_x, bottom_left_y = int(bottom_left_x), int(bottom_left_y)
        chosen_loc_x = bottom_left_x // grid_size
        chosen_loc_y = bottom_left_y // grid_size
        place_record[node_name] = Record(
            node_name,
            placedb.node_info[node_name].width,
            placedb.node_info[node_name].height,
            chosen_loc_x,
            chosen_loc_y,
            bottom_left_x,
            bottom_left_y,
            grid_size,
        )
        line = f.readline()
    return place_record


def draw_macros(placedb: PlaceDB, pl_file, grid_size, m2m_flow: M2MFlow, pic_path):
    place_record = read_placement(placedb, grid_size, pl_file)
    draw_macro_placement(place_record, pic_path, placedb, m2m_flow)


def draw_detailed_placement(
    node_file: str,
    pl_file: str,
    pic_file: str,
    max_width: int,
    max_height: int,
    grid_size: int,
    placedb: PlaceDB,
    draw_id: bool = True,
):
    node_dict: Dict[str, Node] = {}

    with open(pl_file, "r", encoding="utf8") as f:
        cnt = 0
        for line in f:
            if line.startswith("o"):
                cnt += 1
                line = line.strip().split()
                node_name, bottom_left_x, bottom_left_y = line[:3]
                node_dict[node_name] = Node(
                    cnt,
                    node_name,
                    int(bottom_left_x),
                    int(bottom_left_y),
                    0,
                    0,
                    grid_size,
                )
    with open(node_file, "r", encoding="utf8") as f:
        for line in f:
            if line.startswith("\t") or line.startswith(" "):
                line = line.strip().split()
                node_name, width, height = line[:3]
                if node_name in node_dict:
                    node_dict[node_name].set_size(int(width), int(height), grid_size)
                    if line[-1] == "terminal":
                        node_dict[node_name].is_fixed = True
    fig = plt.figure()
    ax = fig.add_axes([0, 0, 1, 1], frameon=True, aspect=1.0)
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)

    node_x_list, node_y_list = [], []
    for node in node_dict.values():
        # print(node.name)
        if node.is_fixed:
            if not (
                node.name in placedb.port_to_delete
                or placedb.node_info[node.name].is_port
            ):  # macro 用绿色
                color = "tab:green"
            else:  # port 用蓝色
                color = "cyan"
            ax.add_patch(
                patches.Rectangle(
                    (
                        node.bottom_left_x / max_width,
                        node.bottom_left_y / max_height,
                    ),  # (x,y)
                    float(node.width / max_width),  # width
                    float(node.height / max_height),
                    linewidth=0.1,
                    edgecolor="k",
                    alpha=0.9,
                    facecolor=color,
                )
            )
            cx = (node.bottom_left_x + node.width / 2) / max_width
            cy = (node.bottom_left_y + node.height / 2) / max_height
            if (
                not (  # 如果是 port 就不标 name
                    node.name in placedb.port_to_delete
                    or placedb.node_info[node.name].is_port
                )
                and draw_id
            ):
                ax.annotate(
                    node.name,
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

    draw_regularity(ax, placedb)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.savefig(pic_file, dpi=600, bbox_inches="tight")
    plt.close(fig)


def write_pl_for_detailed(place_record: PlaceRecord, pl_file: str):
    with open(pl_file, "w", encoding="utf8") as f:
        f.write("UCLA pl 1.0\n\n")
        for node, record in place_record.items():
            f.write(
                f"{node}\t{record.bottom_left_x}\t{record.bottom_left_y} : N /FIXED\n"
            )
        f.flush()


def write_pl_for_refine(place_record: PlaceRecord, placedb: PlaceDB, pl_file: str):
    with open(pl_file, "w", encoding="utf8") as f:
        f.write("UCLA pl 1.0\n\n")
        for node, record in place_record.items():
            f.write(f"{node}\t{record.bottom_left_x}\t{record.bottom_left_y} : N")
            if placedb.node_info[node].is_port:
                f.write(" /FIXED")
            f.write("\n")
