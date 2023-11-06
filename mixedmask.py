import argparse
import csv
import os
import random
import time
from typing import Tuple

import numpy as np

from common import my_inf, grid_setting
from place_db import PlaceDB
from utils import (
    M2MFlow,
    PlaceRecord,
    Record,
    cal_dataflow,
    cal_hpwl,
    cal_regularity,
    draw_macros,
    get_m2m_flow,
    mixed_placer,
    rank_macros_mixed_port,
    write_final_placement,
    write_pl_for_detailed,
)

rank_alpha, rank_beta = 0.8, 0.2
evaluate_alpha, evaluate_beta, evaluate_gamma = 0.2, 0.8, 0
mask_alpha, mask_beta, mask_gamma = 0.2, 0.8, 0


def set_seed(seed: int):
    np.random.seed(seed)
    random.seed(seed)


def db2record(placedb: PlaceDB, grid_size: int) -> PlaceRecord:
    place_record: PlaceRecord = {}
    for node_name in placedb.node_info:
        chosen_loc_x = int(placedb.node_info[node_name].bottom_left_x / grid_size)
        chosen_loc_y = int(placedb.node_info[node_name].bottom_left_y / grid_size)
        place_record[node_name] = Record(
            node_name,
            placedb.node_info[node_name].width,
            placedb.node_info[node_name].height,
            chosen_loc_x,
            chosen_loc_y,
            placedb.node_info[node_name].bottom_left_x,
            placedb.node_info[node_name].bottom_left_y,
            grid_size,
        )
    return place_record


def pl2record(pl_file, placedb: PlaceDB, grid_size: int) -> PlaceRecord:
    place_record: PlaceRecord = {}
    with open(pl_file, "r", encoding="utf8") as f:
        for line in f:
            if line.startswith("o"):
                line = line.strip().split()
                node_name = line[0]
                bottom_left_x = int(line[1])
                bottom_left_y = int(line[2])

                if node_name in placedb.node_info:
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
    return place_record


def swap(node1: Record, node2: Record, grid_size: int):
    node1.bottom_left_x, node2.bottom_left_x = node2.bottom_left_x, node1.bottom_left_x
    node1.bottom_left_y, node2.bottom_left_y = node2.bottom_left_y, node1.bottom_left_y

    node1.grid_x, node2.grid_x = node2.grid_x, node1.grid_x
    node1.grid_y, node2.grid_y = node2.grid_y, node1.grid_y

    node1.refresh(grid_size)
    node2.refresh(grid_size)


class Disturbance:
    def __init__(self, placedb: PlaceDB) -> None:
        self.candidates = sorted(placedb.macro_name)
        m2m_file = os.path.join("benchmarks", placedb.benchmark, "macro2macro.csv")
        m2m_flow = get_m2m_flow(m2m_file)
        self.priority = np.log(
            [sum(m2m_flow[node_name].values()) for node_name in self.candidates]
        )
        # self.priority = np.log(
        #     np.array(
        #         [placedb.node_info[node_name].area for node_name in self.candidates]
        #     )
        # )
        self.priority /= np.sum(self.priority)
        self.action_record = None

    def disturbance(self, place_record: PlaceRecord, grid_size: int):
        node_name1, node_name2 = np.random.choice(
            self.candidates, 2, replace=False, p=self.priority
        )
        print(node_name1, node_name2)
        swap(place_record[node_name1], place_record[node_name2], grid_size)
        self.action_record = (node_name1, node_name2)
        return (node_name1, node_name2)

    def recover(self, place_record: PlaceRecord, grid_size: int):
        node_name1, node_name2 = self.action_record
        swap(place_record[node_name1], place_record[node_name2], grid_size)


class EvalRecord:
    def __init__(self, value, hpwl, dataflow, regularity) -> None:
        self.value = value
        self.hpwl = hpwl
        self.dataflow = dataflow
        self.regularity = regularity

    def __str__(self) -> str:
        return f"{self.value}, {self.hpwl}, {self.dataflow}, {self.regularity}"

    def __lt__(self, other) -> bool:
        return self.value < other.value

    def show(self):
        print(self.__dict__)


class RunningMeanStd:
    def __init__(self, epsilon: float = 1e-8) -> None:
        self.cnt = 0
        self.epsilon = epsilon
        self.mean = 0
        self.var = 1
        self.std = 1
        self.last_x = 0

    def update(self, x: float):
        self.cnt += 1
        if self.cnt == 1:
            self.mean = x
            self.S = 0
        else:
            old_mean = self.mean
            self.mean += (x - self.mean) / self.cnt
            self.S += (x - old_mean) * (x - self.mean)
        self.var = self.S / self.cnt
        self.std = np.sqrt(self.var)
        self.last_x = x

    def normalized_value(self):
        return (self.last_x - self.mean) / (self.std + self.epsilon)


class Evaluator:
    def __init__(
        self, alpha: float = 0.6, beta: float = 0.3, gamma: float = 0.1
    ) -> None:
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

        self.hpwl = RunningMeanStd()
        self.dataflow = RunningMeanStd()
        self.regularity = RunningMeanStd()

    def update(self, hpwl: float, dataflow: float, regulatrity_aver: float):
        self.hpwl.update(hpwl)
        self.dataflow.update(dataflow)
        self.regularity.update(regulatrity_aver)

    def evaluate(self, place_record: PlaceRecord, placedb: PlaceDB, m2m_flow: M2MFlow):
        hpwl = cal_hpwl(place_record, placedb) if self.alpha > 0 else 0
        dataflow = cal_dataflow(place_record, placedb, m2m_flow) if self.beta > 0 else 0
        regularity = cal_regularity(place_record, placedb) if self.gamma > 0 else 0
        self.update(hpwl, dataflow, regularity)

        value = (
            self.alpha * self.hpwl.normalized_value()
            + self.beta * self.dataflow.normalized_value()
            + self.gamma * self.regularity.normalized_value()
        )
        return EvalRecord(value, hpwl, dataflow, regularity)


def evaluate(
    place_record: PlaceRecord,
    placedb: PlaceDB,
    m2m_flow: M2MFlow,
    alpha: float = 0.5,
    beta: float = 0.3,
    gamma: float = 0.2,
) -> EvalRecord:
    # 计算 hpwl
    # 计算 datamask value
    # 计算规整度
    hpwl = cal_hpwl(place_record, placedb) if alpha > 0 else 0
    dataflow = cal_dataflow(place_record, placedb, m2m_flow) if beta > 0 else 0
    regularity = cal_regularity(place_record, placedb) if gamma > 0 else 0
    return EvalRecord(
        alpha * hpwl + beta * dataflow + gamma * regularity,
        hpwl,
        dataflow,
        regularity,
    )


def refine_EA(
    iter_rounds,
    placedb,
    curve_file,
    placement_file,
    grid_num,
    grid_size,
    m2m_flow,
    pl_file,
) -> Tuple[PlaceRecord, EvalRecord]:
    # benchmark = "adaptec1"
    # result_dir = os.path.join("results_macro_refine-EA_bbo", benchmark)
    # pic_file = os.path.join(result_dir, f"{benchmark}.png")

    curve_fp = open(curve_file, "a+")
    curve_writer = csv.writer(curve_fp)
    node_id_ls = rank_macros_mixed_port(placedb, m2m_flow, rank_alpha, rank_beta)

    evaluator = Evaluator(evaluate_alpha, evaluate_beta, evaluate_gamma)
    disturbancer = Disturbance(placedb)

    place_record = pl2record(pl_file, placedb, grid_size)
    eval_record = evaluator.evaluate(place_record, placedb, m2m_flow)
    eval_record.show()
    curve_writer.writerow(
        [
            eval_record.value,
            eval_record.hpwl,
            eval_record.dataflow,
            eval_record.regularity,
            time.time(),
        ]
    )
    write_final_placement(place_record, my_inf, placement_file)
    # draw_macros(placedb, placement_file, grid_size, m2m_flow, pic_file)

    # 第一轮调整，判断是否有可行解
    # print("first round")
    # place_record, is_legal = mixed_placer(
    #     node_id_ls,
    #     placedb,
    #     grid_num,
    #     grid_size,
    #     place_record,
    #     m2m_flow,
    #     mask_alpha,
    #     mask_beta,
    #     mask_gamma,
    # )
    # if not is_legal:
    #     print("no legal solution")
    #     write_final_placement(place_record, my_inf, placement_file)
    #     draw_macros(placedb, placement_file, grid_size, m2m_flow, pic_file)
    #     return place_record, eval_record
    # eval_record = evaluator.evaluate(place_record, placedb, m2m_flow)
    # eval_record.show()
    # curve_writer.writerow(
    #     [
    #         eval_record.value,
    #         eval_record.hpwl,
    #         eval_record.dataflow,
    #         eval_record.regularity,
    #         time.time(),
    #     ]
    # )

    # EA 迭代
    best_placed_record, best_eval = place_record, eval_record
    for i in range(iter_rounds):
        print(i)
        disturbancer.disturbance(place_record, grid_size)
        place_record_new, is_legal = mixed_placer(
            node_id_ls,
            placedb,
            grid_num,
            grid_size,
            place_record,
            m2m_flow,
            mask_alpha,
            mask_beta,
            mask_gamma,
        )
        if is_legal:
            eval_record = evaluator.evaluate(place_record_new, placedb, m2m_flow)
            eval_record.show()
            curve_writer.writerow(
                [
                    eval_record.value,
                    eval_record.hpwl,
                    eval_record.dataflow,
                    eval_record.regularity,
                    time.time(),
                ]
            )
            curve_fp.flush()
        if is_legal and eval_record < best_eval:
            best_eval = eval_record
            best_placed_record = place_record = place_record_new
            write_final_placement(best_placed_record, best_eval.hpwl, placement_file)
            # draw_macros(placedb, placement_file, grid_size, m2m_flow, pic_file)
        else:
            print("Recover\n")
            disturbancer.recover(place_record, grid_size)
    curve_writer.writerow(
        [
            best_eval.value,
            best_eval.hpwl,
            best_eval.dataflow,
            best_eval.regularity,
            time.time(),
        ]
    )
    curve_writer.writerow([])
    curve_fp.flush()
    write_final_placement(best_placed_record, best_eval.hpwl, placement_file)
    return best_placed_record, best_eval


def refine_iter(
    iter_rounds,
    placedb,
    curve_file,
    placement_file,
    grid_num,
    grid_size,
    m2m_flow,
    pl_file,
) -> Tuple[PlaceRecord, EvalRecord]:
    curve_fp = open(curve_file, "a+")
    curve_writer = csv.writer(curve_fp)
    node_id_ls = rank_macros_mixed_port(placedb, m2m_flow, rank_alpha, rank_beta)

    evaluator = Evaluator(evaluate_alpha, evaluate_beta, evaluate_gamma)

    place_record = pl2record(pl_file, placedb, grid_size)
    eval_record = evaluator.evaluate(place_record, placedb, m2m_flow)
    print("origin hpwl: ", eval_record.hpwl)
    curve_writer.writerow(
        [
            eval_record.value,
            eval_record.hpwl,
            eval_record.dataflow,
            eval_record.regularity,
            time.time(),
        ]
    )

    is_legal = True
    for i in range(iter_rounds):
        print(i)
        place_record_new, is_legal = mixed_placer(
            node_id_ls,
            placedb,
            grid_num,
            grid_size,
            place_record,
            m2m_flow,
            mask_alpha,
            mask_beta,
            mask_gamma,
        )
        if not is_legal:
            print("illegal")
            break
        eval_record = evaluator.evaluate(place_record, placedb, m2m_flow)
        eval_record.show()
        curve_writer.writerow(
            [
                eval_record.value,
                eval_record.hpwl,
                eval_record.dataflow,
                eval_record.regularity,
                time.time(),
            ]
        )
        place_record = place_record_new
    write_final_placement(place_record, eval_record.hpwl, placement_file)
    return place_record, eval_record


def main():
    parser = argparse.ArgumentParser(description="argparse testing")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--seed", default=2027)
    parser.add_argument("--iter_rounds", default=10)
    parser.add_argument("--front", default="bbo")
    args = parser.parse_args()
    benchmark = args.dataset
    iter_rounds = int(args.iter_rounds)
    seed = int(args.seed)
    front = args.front

    set_seed(seed)

    grid_num = grid_setting[benchmark]["grid_num"]
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    print("#port", placedb.port_cnt)
    print("#macro", len(placedb.macro_name))

    if front == "bbo":
        init_macro_pl_file = os.path.join(
            "results_macro_front_bbo", benchmark, f"{benchmark}.gp.pl"
        )
        result_dir = os.path.join("results_macro_refine-EA_bbo", benchmark)
    elif front == "dreamplace-mixed":
        init_macro_pl_file = os.path.join(
            "results_detailed_front_dreamplace-mixed", benchmark, f"{benchmark}.gp.pl"
        )
        result_dir = os.path.join("results_macro_refine-EA_dreamplace-mixed", benchmark)
    else:
        raise NotImplementedError

    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    m2m_flow_file = "benchmarks/{}/macro2macro.csv".format(benchmark)
    m2m_flow = get_m2m_flow(m2m_flow_file)

    curve_file = os.path.join(result_dir, "curve.csv")
    placement_file = os.path.join(result_dir, "placement.csv")
    pl_file = os.path.join(result_dir, f"{benchmark}.gp.pl")

    best_placed_macro, _ = refine_EA(
        iter_rounds,
        placedb,
        curve_file,
        placement_file,
        grid_num,
        grid_size,
        m2m_flow,
        init_macro_pl_file,
    )
    write_pl_for_detailed(best_placed_macro, pl_file)

    pic_file = os.path.join(result_dir, f"{benchmark}.png")
    draw_macros(placedb, placement_file, grid_size, m2m_flow, pic_file)


if __name__ == "__main__":
    main()
