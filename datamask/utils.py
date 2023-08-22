import time
import numpy as np
import math
import csv
import random

from scipy.spatial import distance

my_inf = int(1e8)


def random_guiding(node_id_ls, placedb, grid_num, grid_size):  # 将所有macro随机放置
    placed_macros = {}
    N2_time = 0
    placed_macros = {}

    for node_id in node_id_ls:
        x = placedb.node_info[node_id]["x"]
        y = placedb.node_info[node_id]["y"]
        scaled_x = math.ceil(x / grid_size)
        scaled_y = math.ceil(y / grid_size)
        placedb.node_info[node_id]["scaled_x"] = scaled_x
        placedb.node_info[node_id]["scaled_y"] = scaled_y

        position_mask = np.ones((grid_num, grid_num))

        # loc_x_ls = np.where(position_mask == 1)[0]
        # loc_y_ls = np.where(position_mask == 1)[1]
        loc_x_ls, loc_y_ls = np.where(position_mask == 1)
        placed_macros[node_id] = {}

        time0 = time.time()

        # print(np.where(wire_mask == min_ele)[0][0],np.where(wire_mask == min_ele)[1][0])
        idx = random.choice(range(len(loc_x_ls)))

        chosen_loc_x = loc_x_ls[idx]
        chosen_loc_y = loc_y_ls[idx]

        N2_time += time.time() - time0

        center_loc_x = grid_size * chosen_loc_x + 0.5 * x
        center_loc_y = grid_size * chosen_loc_y + 0.5 * y

        placed_macros[node_id] = {
            # 原先的位置
            "scaled_x": scaled_x,
            "scaled_y": scaled_y,
            "x": x,
            "y": y,
            # 随机选择后的位置
            "loc_x": chosen_loc_x,
            "loc_y": chosen_loc_y,
            "center_loc_x": center_loc_x,
            "center_loc_y": center_loc_y,
            "bottom_left_x": chosen_loc_x * grid_size,
            "bottom_left_y": chosen_loc_y * grid_size,
        }
    return placed_macros


def rank_macros(placedb):  # 将macro按照固定顺序（net面积总和）从大到小排列，输出排序后的macro序列。
    node_id_ls = list(placedb.node_info.keys()).copy()
    for node_id in node_id_ls:
        placedb.node_info[node_id]["area"] = placedb.node_info[node_id]["x"] * placedb.node_info[node_id]["y"]

    net_id_ls = list(placedb.net_info.keys()).copy()
    for net_id in net_id_ls:
        sum = 0
        # print(placedb.net_info[net_id]["nodes"])
        for node_id in placedb.net_info[net_id]["nodes"].keys():
            sum += placedb.node_info[node_id]["area"]
        placedb.net_info[net_id]["area"] = sum
        # print(placedb.net_info[net_id]["area"])

    for node_id in node_id_ls:
        placedb.node_info[node_id]["area_sum"] = 0
        for net_id in net_id_ls:
            if node_id in placedb.net_info[net_id]["nodes"].keys():
                placedb.node_info[node_id]["area_sum"] += placedb.net_info[net_id]["area"]  # 自己的面积被算了 #net 次？

    for node_id in node_id_ls:
        placedb.node_info[node_id]["area_sum"] = 0
    for net_id in net_id_ls:
        for node_id in placedb.net_info[net_id]["nodes"].keys():
            placedb.node_info[node_id]["area_sum"] += placedb.net_info[net_id]["area"]

    node_id_ls.sort(key=lambda x: placedb.node_info[x]["area_sum"], reverse=True)
    return node_id_ls


def cal_hpwl(placed_macros, placedb):
    hpwl = 0
    net_hpwl = {}
    for net_id in placedb.net_info.keys():
        for node_id in placedb.net_info[net_id]["nodes"]:
            if node_id not in placed_macros.keys():
                continue
            pin_x = (
                placed_macros[node_id]["center_loc_x"]
                + placedb.net_info[net_id]["nodes"][node_id]["x_offset"]
            )
            pin_y = (
                placed_macros[node_id]["center_loc_y"]
                + placedb.net_info[net_id]["nodes"][node_id]["y_offset"]
            )
            if net_id not in net_hpwl.keys():
                net_hpwl[net_id] = {}
                net_hpwl[net_id] = {"x_max": pin_x, "x_min": pin_x, "y_max": pin_y, "y_min": pin_y}
            else:
                if net_hpwl[net_id]["x_max"] < pin_x:
                    net_hpwl[net_id]["x_max"] = pin_x
                elif net_hpwl[net_id]["x_min"] > pin_x:
                    net_hpwl[net_id]["x_min"] = pin_x
                if net_hpwl[net_id]["y_max"] < pin_y:
                    net_hpwl[net_id]["y_max"] = pin_y
                elif net_hpwl[net_id]["y_min"] > pin_y:
                    net_hpwl[net_id]["y_min"] = pin_y
    for net_id in net_hpwl.keys():
        hpwl += (
            net_hpwl[net_id]["x_max"]
            - net_hpwl[net_id]["x_min"]
            + net_hpwl[net_id]["y_max"]
            - net_hpwl[net_id]["y_min"]
        )
    return hpwl


def cal_datamask(node_id, placedb, grid_num, grid_size, placed_macros, m2m_flow):
    id_cnt1 = placedb.node_info[node_id]["id"]
    data_mask = np.zeros((grid_num, grid_num))
    for col in range(grid_num):
        pos_x = col * grid_size + 0.5 * placedb.node_info[node_id]["x"]
        for row in range(grid_num):
            pos_y = row * grid_size + 0.5 * placedb.node_info[node_id]["y"]
            for node_id2 in placed_macros:
                id_cnt2 = placedb.node_info[node_id2]["id"]
                data_mask[col, row] += m2m_flow[id_cnt1][id_cnt2] * distance.euclidean(
                    (pos_x, pos_y),
                    (placed_macros[node_id2]["center_loc_x"], placed_macros[node_id2]["center_loc_y"]),
                )
    return data_mask


def chose_position(node_id, mask, place_record):
    min_ele = np.min(mask)
    chosen_loc_x, chosen_loc_y = np.where(mask == min_ele)
    distance_ls = []
    for xi, yi in zip(chosen_loc_x, chosen_loc_y):
        distance_ls.append(
            distance.euclidean((xi, yi), (place_record[node_id]["loc_x"], place_record[node_id]["loc_y"]))
        )
    idx = np.argmin(distance_ls)
    chosen_loc_x = chosen_loc_x[idx]
    chosen_loc_y = chosen_loc_y[idx]
    return chosen_loc_x, chosen_loc_y


#! 实现 data-based 贪心策略
def datamask_placer(node_id_ls, placedb, grid_num, grid_size, place_record, m2m_flow):
    shuffle = 0
    placed_macros = {}

    time_start = time.time()
    N2_time = 0
    for node_id in node_id_ls:
        #! 这部分为什么不直接用 place_record里的结果？line 294-300
        x = placedb.node_info[node_id]["x"]
        y = placedb.node_info[node_id]["y"]
        scaled_x = math.ceil(x / grid_size)
        scaled_y = math.ceil(y / grid_size)
        placedb.node_info[node_id]["scaled_x"] = scaled_x
        placedb.node_info[node_id]["scaled_y"] = scaled_y

        position_mask = np.ones((grid_num, grid_num)) * my_inf
        position_mask[
            : grid_num - scaled_x, : grid_num - scaled_y
        ] = 1  #! 这么做的原因？为什么是 grid_num - scaled_x, 而不是 scaled_x

        for key1 in placed_macros.keys():
            bottom_left_x = max(0, placed_macros[key1]["loc_x"] - scaled_x + 1)
            bottom_left_y = max(0, placed_macros[key1]["loc_y"] - scaled_y + 1)
            top_right_x = min(grid_num - 1, placed_macros[key1]["loc_x"] + placed_macros[key1]["scaled_x"])
            top_right_y = min(grid_num - 1, placed_macros[key1]["loc_y"] + placed_macros[key1]["scaled_y"])

            position_mask[bottom_left_x:top_right_x, bottom_left_y:top_right_y] = my_inf

        if not np.any(position_mask == 1):
            print("no_legal_place")
            return [], my_inf

        # TODO !
        time0 = time.time()
        data_mask = cal_datamask(node_id, placedb, grid_num, grid_size, placed_macros, m2m_flow)
        data_mask = np.multiply(data_mask, position_mask)
        chosen_loc_x, chosen_loc_y = chose_position(node_id, data_mask, place_record)
        N2_time += time.time() - time0

        placed_macros[node_id] = {
            # 原先的位置
            "scaled_x": scaled_x,
            "scaled_y": scaled_y,
            "x": x,
            "y": y,
            # 随机选择后的位置
            "loc_x": chosen_loc_x,
            "loc_y": chosen_loc_y,
            "center_loc_x": grid_size * chosen_loc_x + 0.5 * x,
            "center_loc_y": grid_size * chosen_loc_y + 0.5 * y,
            "bottom_left_x": grid_size * chosen_loc_x + 452,  #! 452 从哪来的
            "bottom_left_y": grid_size * chosen_loc_y + 452,
        }
    time_end = time.time()

    hpwl = cal_hpwl(placed_macros, placedb)
    # print("time: {}\nN2_time: {}\nhpwl: {}\nshuffle or not: {}".format(time_end - time_start, N2_time, hpwl, shuffle))
    print("time:", time_end - time_start)
    print("N2_time:", N2_time)
    print("hpwl:", hpwl)
    print("shuffle or not: ", shuffle)
    return placed_macros, hpwl


def cal_wiremask(node_id, placedb, grid_num, grid_size, hpwl_info_for_each_net):
    wire_mask = np.ones((grid_num, grid_num)) * 0.1
    net_ls = placedb.net_info
    for net_id in net_ls.keys():
        if net_id in hpwl_info_for_each_net.keys():
            x_offset = net_ls[net_id]["nodes"][node_id]["x_offset"] + 0.5 * placedb.node_info[node_id]["x"]
            y_offset = net_ls[net_id]["nodes"][node_id]["y_offset"] + 0.5 * placedb.node_info[node_id]["y"]
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


def update_info(node_id, placedb, grid_size, chosen_loc_x, chosen_loc_y, hpwl_info_for_each_net):
    center_loc_x = grid_size * chosen_loc_x + 0.5 * placedb.node_info[node_id]["x"]
    center_loc_y = grid_size * chosen_loc_y + 0.5 * placedb.node_info[node_id]["y"]
    for net_id in placedb.net_info.keys():
        x_offset = placedb.net_info[net_id]["nodes"][node_id]["x_offset"]
        y_offset = placedb.net_info[net_id]["nodes"][node_id]["y_offset"]
        if net_id not in hpwl_info_for_each_net.keys():
            hpwl_info_for_each_net[net_id] = {}
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
def wiremask_placer(node_id_ls, placedb, grid_num, grid_size, place_record, m2m_flow=None):
    shuffle = 0
    placed_macros = {}
    hpwl_info_for_each_net = {}

    time_start = time.time()
    N2_time = 0
    for node_id in node_id_ls:
        #! 这部分为什么不直接用 place_record里的结果？line 294-300
        x = placedb.node_info[node_id]["x"]
        y = placedb.node_info[node_id]["y"]
        scaled_x = math.ceil(x / grid_size)
        scaled_y = math.ceil(y / grid_size)
        placedb.node_info[node_id]["scaled_x"] = scaled_x
        placedb.node_info[node_id]["scaled_y"] = scaled_y

        position_mask = np.ones((grid_num, grid_num)) * my_inf
        position_mask[
            : grid_num - scaled_x, : grid_num - scaled_y
        ] = 1  #! 这么做的原因？为什么是 grid_num - scaled_x, 而不是 scaled_x

        for key1 in placed_macros.keys():
            bottom_left_x = max(0, placed_macros[key1]["loc_x"] - scaled_x + 1)
            bottom_left_y = max(0, placed_macros[key1]["loc_y"] - scaled_y + 1)
            top_right_x = min(grid_num - 1, placed_macros[key1]["loc_x"] + placed_macros[key1]["scaled_x"])
            top_right_y = min(grid_num - 1, placed_macros[key1]["loc_y"] + placed_macros[key1]["scaled_y"])
            position_mask[bottom_left_x:top_right_x, bottom_left_y:top_right_y] = my_inf

        if not np.any(position_mask == 1):
            print("no_legal_place")
            return [], my_inf

        time0 = time.time()
        wire_mask = cal_wiremask(node_id, placedb, grid_num, grid_size, hpwl_info_for_each_net)
        wire_mask = np.multiply(wire_mask, position_mask)
        chosen_loc_x, chosen_loc_y = chose_position(node_id, wire_mask, place_record)
        N2_time += time.time() - time0

        hpwl_info_for_each_net = update_info(
            node_id, placedb, grid_size, chosen_loc_x, chosen_loc_y, hpwl_info_for_each_net
        )
        placed_macros[node_id] = {
            # 原先的位置
            "scaled_x": scaled_x,
            "scaled_y": scaled_y,
            "x": x,
            "y": y,
            # 随机选择后的位置
            "loc_x": chosen_loc_x,
            "loc_y": chosen_loc_y,
            "center_loc_x": grid_size * chosen_loc_x + 0.5 * x,
            "center_loc_y": grid_size * chosen_loc_y + 0.5 * y,
            "bottom_left_x": grid_size * chosen_loc_x + 452,  #! 452 从哪来的
            "bottom_left_y": grid_size * chosen_loc_y + 452,
        }
    time_end = time.time()

    hpwl = cal_hpwl(placed_macros, placedb)
    # print("time: {}\nN2_time: {}\nhpwl: {}\nshuffle or not: {}".format(time_end - time_start, N2_time, hpwl, shuffle))
    print("time:", time_end - time_start)
    print("N2_time:", N2_time)
    print("hpwl:", hpwl)
    print("shuffle or not: ", shuffle)
    return placed_macros, hpwl


def mix_placer(node_id_ls, placedb, grid_num, grid_size, place_record, m2m_flow, alpha=0.5, beta=0.5):
    shuffle = 0
    placed_macros = {}
    hpwl_info_for_each_net = {}

    time_start = time.time()
    N2_time = 0
    for node_id in node_id_ls:
        #! 这部分为什么不直接用 place_record里的结果？line 294-300
        x = placedb.node_info[node_id]["x"]
        y = placedb.node_info[node_id]["y"]
        scaled_x = math.ceil(x / grid_size)
        scaled_y = math.ceil(y / grid_size)
        placedb.node_info[node_id]["scaled_x"] = scaled_x
        placedb.node_info[node_id]["scaled_y"] = scaled_y

        position_mask = np.ones((grid_num, grid_num)) * my_inf
        position_mask[
            : grid_num - scaled_x, : grid_num - scaled_y
        ] = 1  #! 这么做的原因？为什么是 grid_num - scaled_x, 而不是 scaled_x

        for key1 in placed_macros.keys():
            bottom_left_x = max(0, placed_macros[key1]["loc_x"] - scaled_x + 1)
            bottom_left_y = max(0, placed_macros[key1]["loc_y"] - scaled_y + 1)
            top_right_x = min(grid_num - 1, placed_macros[key1]["loc_x"] + placed_macros[key1]["scaled_x"])
            top_right_y = min(grid_num - 1, placed_macros[key1]["loc_y"] + placed_macros[key1]["scaled_y"])
            position_mask[bottom_left_x:top_right_x, bottom_left_y:top_right_y] = my_inf

        if not np.any(position_mask == 1):
            print("no_legal_place")
            return [], my_inf

        time0 = time.time()
        data_mask = cal_datamask(node_id, placedb, grid_num, grid_size, placed_macros, m2m_flow)
        wire_mask = cal_wiremask(node_id, placedb, grid_num, grid_size, hpwl_info_for_each_net)
        mask = np.multiply((alpha * data_mask + beta * wire_mask) / (alpha + beta), position_mask)
        chosen_loc_x, chosen_loc_y = chose_position(node_id, mask, place_record)
        N2_time += time.time() - time0

        hpwl_info_for_each_net = update_info(
            node_id, placedb, grid_size, chosen_loc_x, chosen_loc_y, hpwl_info_for_each_net
        )
        placed_macros[node_id] = {
            # 原先的位置
            "scaled_x": scaled_x,
            "scaled_y": scaled_y,
            "x": x,
            "y": y,
            # 随机选择后的位置
            "loc_x": chosen_loc_x,
            "loc_y": chosen_loc_y,
            "center_loc_x": grid_size * chosen_loc_x + 0.5 * x,
            "center_loc_y": grid_size * chosen_loc_y + 0.5 * y,
            "bottom_left_x": grid_size * chosen_loc_x + 452,  #! 452 从哪来的
            "bottom_left_y": grid_size * chosen_loc_y + 452,
        }
    time_end = time.time()

    hpwl = cal_hpwl(placed_macros, placedb)
    # print("time: {}\nN2_time: {}\nhpwl: {}\nshuffle or not: {}".format(time_end - time_start, N2_time, hpwl, shuffle))
    print("time:", time_end - time_start)
    print("N2_time:", N2_time)
    print("hpwl:", hpwl)
    print("shuffle or not: ", shuffle)
    return placed_macros, hpwl


def write_final_placement(best_placed_macro, dir):
    csv_file2 = open(dir, "a+")
    csv_writer2 = csv.writer(csv_file2)
    csv_writer2.writerow([time.time()])
    for node_id in list(best_placed_macro.keys()):
        csv_writer2.writerow(
            [
                node_id,
                best_placed_macro[node_id]["bottom_left_x"],
                best_placed_macro[node_id]["bottom_left_y"],
            ]
        )
    csv_writer2.writerow([])
    csv_file2.close()


def get_m2m_flow(m2m_flow_file):
    m2m_flow = []
    with open(m2m_flow_file, "r", encoding="utf8") as fp:
        for line in fp:
            m2m_flow.append([float(df) for df in line.strip().split(",")])
    m2m_flow = np.array(m2m_flow)
    return m2m_flow
