import os
import numpy as np
import matplotlib.pyplot as plt

from scipy.spatial import distance

from common import grid_setting, benchmark_list
from place_db import PlaceDB
from utils import (
    M2MFlow,
    PlaceRecord,
    Record,
    draw_detailed_placement,
    draw_macro_placement,
    get_m2m_flow,
    read_placement,
)

refine_center_scaled_factor = 0.8
refine_virtual_boundary_scaled_factor = 1.2


def cal_dataflow(placedb: PlaceDB, place_record: PlaceRecord, m2m_flow: M2MFlow):
    dataflow_total = 0
    for node_name1 in placedb.node_info:
        for node_name2 in m2m_flow[node_name1]:
            dataflow_total += (
                distance.euclidean(
                    (
                        place_record[node_name1].center_x,
                        place_record[node_name1].center_y,
                    ),
                    (
                        place_record[node_name2].center_x,
                        place_record[node_name2].center_y,
                    ),
                )
                * m2m_flow[node_name1][node_name2]
            )
    return dataflow_total


def db2record(placedb: PlaceDB, grid_size: int) -> PlaceRecord:
    place_record: PlaceRecord = {}
    for node_name in placedb.node_info:
        chosen_loc_x = placedb.node_info[node_name].bottom_left_x // grid_size
        chosen_loc_y = placedb.node_info[node_name].bottom_left_y // grid_size
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


def read_pl_file(placedb: PlaceDB, pl_file: str):
    with open(pl_file, encoding="utf8") as f:
        for line in f:
            if line.startswith("o"):
                line = line.strip().split()
                node_name = line[0]
                bottom_left_x, bottom_left_y = int(line[1]), int(line[2])
                if node_name in placedb.node_info:
                    placedb.node_info[node_name].bottom_left_x = bottom_left_x
                    placedb.node_info[node_name].bottom_left_y = bottom_left_y
    return placedb


def draw_wiremask(benchmark: str):
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    m2m_file = "benchmarks/{}/macro2macro.csv".format(benchmark)
    m2m_flow = get_m2m_flow(m2m_file)
    pl_file = "result/EA_swap_only/placement/{}_seed_2027_wiremask_hot.csv".format(
        benchmark
    )
    place_record = read_placement(placedb, grid_size, pl_file)
    pic_file = "result/EA_swap_only/pic/{}_seed_2027_wiremask_hot.png".format(benchmark)
    draw_macro_placement(place_record, pic_file, placedb, m2m_flow)


def draw_datamask(benchmark):
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    m2m_file = "benchmarks/{}/macro2macro.csv".format(benchmark)
    m2m_flow = get_m2m_flow(m2m_file)
    pl_file = "result/EA_swap_only/placement/{}_seed_2027_datamask_hot.csv".format(
        benchmark
    )
    place_record = read_placement(placedb, grid_size, pl_file)
    pic_file = "result/EA_swap_only/pic/{}_seed_2027_datamask_hot.png".format(benchmark)
    draw_macro_placement(place_record, pic_file, placedb, m2m_flow)


def draw_mixedmask(benchmark):
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    m2m_file = "benchmarks/{}/macro2macro.csv".format(benchmark)
    m2m_flow = get_m2m_flow(m2m_file)
    pl_file = (
        "result/EA_swap_only/placement/{}_seed_2027_mixedmask_iter_regu.csv".format(
            benchmark
        )
    )
    place_record = read_placement(placedb, grid_size, pl_file)
    pic_file = "result/EA_swap_only/pic/{}_seed_2027_mixedmask_iter_regu.png".format(
        benchmark
    )
    draw_macro_placement(place_record, pic_file, placedb, m2m_flow)


def draw_detailed(benchmark):
    print(benchmark)
    # suffix = "wiremask_iter"
    # suffix = "wiremask"
    # suffix = "origin"
    # suffix = "mixedmask_iter_port"
    # suffix = "mixedmask_iter_regu_port_random"
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    node_file = f"benchmarks/{benchmark}/{benchmark}.nodes"
    pl_file = f"./results/{benchmark}_dreamplace_origin/{benchmark}.gp.pl"
    pic_file = f"./results/{benchmark}_dreamplace_origin/detailed_placement.png"
    draw_detailed_placement(
        node_file, pl_file, pic_file, placedb.max_width, placedb.max_height, grid_size
    )


def draw_origin(benchmark: str):
    print(f"draw_origin {benchmark}")
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    # m2m_file = "benchmarks/{}/macro2macro.csv".format(benchmark)
    # m2m_flow = get_m2m_flow(m2m_file)
    m2m_flow = None

    # pl_file = os.path.join("benchmarks", benchmark, f"{benchmark}.pl")
    pic_file = os.path.join("benchmarks", benchmark, f"{benchmark}.png")
    # read_pl_file(placedb, pl_file)
    origin_record = db2record(placedb, grid_size)
    draw_macro_placement(origin_record, pic_file, placedb, m2m_flow)


def draw_macro_front_dreamplace_mixed(benchmark):
    print(f"draw_macro_front_dreamplace_mixed {benchmark}")
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    m2m_file = "benchmarks/{}/macro2macro.csv".format(benchmark)
    m2m_flow = get_m2m_flow(m2m_file)
    pl_file = os.path.join(
        "results_macro_front_dreamplace-mixed", benchmark, f"{benchmark}.gp.pl"
    )
    read_pl_file(placedb, pl_file)
    front_bbo_record = db2record(placedb, grid_size)
    pic_file = os.path.join(
        "results_macro_front_dreamplace-mixed",
        benchmark,
        f"{benchmark}_macro.png",
    )
    draw_macro_placement(front_bbo_record, pic_file, placedb, m2m_flow)


def draw_macro_refine_dreamplace_mixed(benchmark):
    print(f"draw_macro_refine_dreamplace_mixed {benchmark}")
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    placedb.deal_center_core(scale_factor=refine_center_scaled_factor)
    placedb.deal_virtual_boundary(scale_factor=refine_virtual_boundary_scaled_factor)
    m2m_file = "benchmarks/{}/macro2macro.csv".format(benchmark)
    m2m_flow = get_m2m_flow(m2m_file)
    pl_file = os.path.join(
        # "results_v8_grid_search_820",
        "results_macro_refine-EA_dreamplace-mixed",
        benchmark,
        f"{benchmark}.gp.pl",
    )
    read_pl_file(placedb, pl_file)
    front_bbo_record = db2record(placedb, grid_size)
    pic_file = os.path.join(
        # "results_v8_grid_search_820",
        "results_macro_refine-EA_dreamplace-mixed",
        benchmark,
        f"{benchmark}_macro.png",
    )
    draw_macro_placement(front_bbo_record, pic_file, placedb, m2m_flow)


def draw_detailed_front_dreamplace_mixed(benchmark):
    print(f"draw_detailed_front_dreamplace_mixed {benchmark}")
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    node_file = f"benchmarks/{benchmark}/{benchmark}.nodes"
    pl_file = os.path.join(
        "results_detailed_front_dreamplace-mixed", benchmark, f"{benchmark}.gp.pl"
    )
    pic_file = os.path.join(
        "results_detailed_front_dreamplace-mixed", benchmark, f"{benchmark}.png"
    )
    draw_detailed_placement(
        node_file,
        pl_file,
        pic_file,
        placedb.max_width,
        placedb.max_height,
        grid_size,
        placedb,
    )


def draw_detailed_refine_dreamplace_mixed(benchmark):
    print(f"draw_detailed_refine_dreamplace-mixed {benchmark}")
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    placedb.deal_center_core(scale_factor=refine_center_scaled_factor)
    placedb.deal_virtual_boundary(scale_factor=refine_virtual_boundary_scaled_factor)
    node_file = f"benchmarks/{benchmark}/{benchmark}.nodes"
    pl_file = os.path.join(
        # "results_v8_grid_search_820",
        "results_detailed_refine-EA_dreamplace-mixed",
        # "results",
        benchmark,
        f"{benchmark}.gp.pl",
    )
    pic_file = os.path.join(
        # "results_v8_grid_search_820",
        "results_detailed_refine-EA_dreamplace-mixed",
        # "results",
        benchmark,
        f"{benchmark}.png",
    )
    # pl_file = os.path.join("results", benchmark, f"{benchmark}.gp.pl")
    # pic_file = os.path.join("results", benchmark, f"{benchmark}_id_noportid.png")
    draw_detailed_placement(
        node_file,
        pl_file,
        pic_file,
        placedb.max_width,
        placedb.max_height,
        grid_size,
        placedb,
    )


def draw_macro_front_bbo(benchmark):
    print(f"draw_macro_front_bbo {benchmark}")
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    m2m_file = "benchmarks/{}/macro2macro.csv".format(benchmark)
    m2m_flow = get_m2m_flow(m2m_file)
    pl_file = os.path.join("results_macro_front_bbo", benchmark, f"{benchmark}.gp.pl")
    read_pl_file(placedb, pl_file)
    front_bbo_record = db2record(placedb, grid_size)
    pic_file = os.path.join(
        "results_macro_front_bbo", benchmark, f"{benchmark}_macro.png"
    )
    draw_macro_placement(front_bbo_record, pic_file, placedb, m2m_flow)


def draw_macro_refine_bbo(benchmark):
    print(f"draw_macro_refine_bbo {benchmark}")
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    placedb.deal_center_core(scale_factor=refine_center_scaled_factor)
    placedb.deal_virtual_boundary(scale_factor=refine_virtual_boundary_scaled_factor)
    m2m_file = "benchmarks/{}/macro2macro.csv".format(benchmark)
    m2m_flow = get_m2m_flow(m2m_file)
    pl_file = os.path.join(
        "results_macro_refine-EA_bbo", benchmark, f"{benchmark}.gp.pl"
    )
    read_pl_file(placedb, pl_file)
    front_bbo_record = db2record(placedb, grid_size)
    pic_file = os.path.join(
        "results_macro_refine-EA_bbo", benchmark, f"{benchmark}_macro.png"
    )
    draw_macro_placement(front_bbo_record, pic_file, placedb, m2m_flow)


def draw_detailed_front_bbo(benchmark):
    print(f"draw_detailed_bbo {benchmark}")
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    node_file = f"benchmarks/{benchmark}/{benchmark}.nodes"
    # pl_file = os.path.join("refine_dreamplace_detailed_results", benchmark, f"{benchmark}.gp.pl")
    # pic_file = os.path.join("refine_dreamplace_detailed_results", benchmark, f"{benchmark}_id_noportid.png")
    pl_file = os.path.join(
        "results_detailed_front_bbo", benchmark, f"{benchmark}.gp.pl"
    )
    pic_file = os.path.join("results_detailed_front_bbo", benchmark, f"{benchmark}.png")
    draw_detailed_placement(
        node_file,
        pl_file,
        pic_file,
        placedb.max_width,
        placedb.max_height,
        grid_size,
        placedb,
    )


def draw_detailed_refine_bbo(benchmark):
    print(f"draw_detailed_refine_bbo {benchmark}")
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    node_file = f"benchmarks/{benchmark}/{benchmark}.nodes"
    placedb.deal_center_core(scale_factor=refine_center_scaled_factor)
    placedb.deal_virtual_boundary(scale_factor=refine_virtual_boundary_scaled_factor)
    pl_file = os.path.join(
        "results_detailed_refine-EA_bbo", benchmark, f"{benchmark}.gp.pl"
    )
    pic_file = os.path.join(
        "results_detailed_refine-EA_bbo", benchmark, f"{benchmark}.png"
    )
    draw_detailed_placement(
        node_file,
        pl_file,
        pic_file,
        placedb.max_width,
        placedb.max_height,
        grid_size,
        placedb,
    )


def draw_macro_front_dreamplace_macro(benchmark):
    print(f"draw_macro_front_dreamplace_macro {benchmark}")
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    m2m_file = "benchmarks/{}/macro2macro.csv".format(benchmark)
    m2m_flow = get_m2m_flow(m2m_file)
    pl_file = os.path.join(
        "results_macro_front_dreamplace-macro", benchmark, f"{benchmark}.gp.pl"
    )
    read_pl_file(placedb, pl_file)
    front_bbo_record = db2record(placedb, grid_size)
    pic_file = os.path.join(
        "results_macro_front_dreamplace-macro",
        benchmark,
        f"{benchmark}_macro.png",
    )
    draw_macro_placement(front_bbo_record, pic_file, placedb, m2m_flow)


def draw_macro_refine_dreamplace_macro(benchmark):
    print(f"draw_macro_refine_dreamplace_macro {benchmark}")
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    placedb.deal_center_core(scale_factor=refine_center_scaled_factor)
    placedb.deal_virtual_boundary(scale_factor=refine_virtual_boundary_scaled_factor)
    m2m_file = "benchmarks/{}/macro2macro.csv".format(benchmark)
    m2m_flow = get_m2m_flow(m2m_file)
    pl_file = os.path.join(
        # "results_v8_grid_search_820",
        "results_macro_refine-EA_dreamplace-macro",
        benchmark,
        f"{benchmark}.gp.pl",
    )
    read_pl_file(placedb, pl_file)
    front_bbo_record = db2record(placedb, grid_size)
    pic_file = os.path.join(
        # "results_v8_grid_search_820",
        "results_macro_refine-EA_dreamplace-macro",
        benchmark,
        f"{benchmark}_macro.png",
    )
    draw_macro_placement(front_bbo_record, pic_file, placedb, m2m_flow)


def draw_detailed_front_dreamplace_macro(benchmark):
    print(f"draw_detailed_front_dreamplace_macro {benchmark}")
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    node_file = f"benchmarks/{benchmark}/{benchmark}.nodes"
    pl_file = os.path.join(
        "results_detailed_front_dreamplace-macro", benchmark, f"{benchmark}.gp.pl"
    )
    pic_file = os.path.join(
        "results_detailed_front_dreamplace-macro", benchmark, f"{benchmark}.png"
    )
    draw_detailed_placement(
        node_file,
        pl_file,
        pic_file,
        placedb.max_width,
        placedb.max_height,
        grid_size,
        placedb,
    )


def draw_detailed_refine_dreamplace_macro(benchmark):
    print(f"draw_detailed_refine_dreamplace-macro {benchmark}")
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)
    placedb.deal_center_core(scale_factor=refine_center_scaled_factor)
    placedb.deal_virtual_boundary(scale_factor=refine_virtual_boundary_scaled_factor)
    node_file = f"benchmarks/{benchmark}/{benchmark}.nodes"
    pl_file = os.path.join(
        # "results_v8_grid_search_820",
        "results_detailed_refine-EA_dreamplace-macro",
        # "results",
        benchmark,
        f"{benchmark}.gp.pl",
    )
    pic_file = os.path.join(
        # "results_v8_grid_search_820",
        "results_detailed_refine-EA_dreamplace-macro",
        # "results",
        benchmark,
        f"{benchmark}.png",
    )
    # pl_file = os.path.join("results", benchmark, f"{benchmark}.gp.pl")
    # pic_file = os.path.join("results", benchmark, f"{benchmark}_id_noportid.png")
    draw_detailed_placement(
        node_file,
        pl_file,
        pic_file,
        placedb.max_width,
        placedb.max_height,
        grid_size,
        placedb,
    )


def draw_area_dataflow(benchmark):
    grid_size = grid_setting[benchmark]["grid_size"]
    m2m_file = "benchmarks/{}/macro2macro.csv".format(benchmark)
    m2m_flow = get_m2m_flow(m2m_file)
    placedb = PlaceDB(benchmark, grid_size)
    cnt = len(placedb.macro_name)
    macro_list = sorted(placedb.macro_name)
    area_list = np.array([placedb.node_info[ni].area for ni in macro_list])
    df_list = np.array([sum(m2m_flow[ni].values()) for ni in macro_list])
    # idx_list = np.argsort(-area_list)  # 按面积降序排序
    idx_list = np.argsort(area_list)  # 按面积升序排序
    area_list = np.array([np.log(area_list[i]) for i in idx_list])  #! 其他实现方式？
    df_list = np.array([df_list[i] for i in idx_list])  #! 其他实现方式？

    # fig, ax = plt.subplots()
    # ax.plot(range(cnt), area_list, c="orange", label="area")
    # ax.legend()
    # ax2 = ax.twinx()
    # ax2.plot(range(cnt), df_list, c="blue", label="dataflow")
    # ax2.legend()
    # fig.savefig(f"{benchmark}_area_dataflow.png")
    # plt.close(fig)

    fig, ax = plt.subplots()
    ax.plot(area_list, df_list)
    ax.set_xlabel("area")
    ax.set_ylabel("dataflow")
    fig.savefig(f"{benchmark}_area_dataflow.png")
    plt.close(fig)


if __name__ == "__main__":
    # assert len(sys.argv) >= 2
    # benchmark = sys.argv[1]
    # draw_detailed(benchmark)

    # draw_origin(benchmark)
    # draw_datamask(benchmark)
    # draw_wiremask(benchmark)
    # draw_mixedmask(benchmark)

    # blist = [
    #     "adaptec1",
    #     "adaptec2",
    #     "adaptec3",
    #     "adaptec4",
    #     "bigblue1",
    #     "bigblue3",
    #     # "bigblue4",
    # ]
    blist = [
        "superblue2",
        "superblue3",
        "superblue6",
        "superblue7",
        "superblue9",
        "superblue11",
        "superblue12",
        "superblue14",
        "superblue16",
        "superblue18",
        "superblue19",
    ]
    # for b in benchmark_list:
    #     # draw_origin(b)
    #     # draw_macro_front_dreamplace_macro(b)
    #     # draw_detailed_front_dreamplace_macro(b)
    #     #     draw_detailed_front_dreamplace_mixed(b)
    #     #     draw_macro_front_dreamplace_mixed(b)

    #     # draw_macro_refine_dreamplace_mixed(b)
    #     # draw_detailed_refine_dreamplace_mixed(b)

    #     draw_macro_refine_dreamplace_macro(b)
    #     draw_detailed_refine_dreamplace_macro(b)

    #     #     draw_macro_front_bbo(b)
    #     #     draw_detailed_front_bbo(b)

    #     draw_macro_refine_bbo(b)
    #     draw_detailed_refine_bbo(b)

    # draw_area_dataflow(b)

    # draw_detailed_front_bbo("bigblue4")
    # draw_detailed_front_dreamplace_mixed("adaptec2")
    # draw_detailed_refine_dreamplace_mixed("bigblue3")

    draw_detailed_refine_dreamplace_macro("bigblue1")
