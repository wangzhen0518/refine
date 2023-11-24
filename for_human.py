import os
from common import grid_setting, benchmark_list
from place_db import PlaceDB, Pin, Net
from utils import draw_macro_placement, get_m2m_flow
from draw_placement import db2record
from typing import Dict


def write_nodes_cell(
    src_file: str, dst_file: str, placedb: PlaceDB, is_fixed: bool = False
):
    # is_fixed 表示是否固定 macro
    fwrite = open(dst_file, "w", encoding="utf8")
    fwrite.write(
        """\
UCLA nodes 1.0
# Created	:	Jan  6 2005
# User   	:	Gi-Joon Nam & Mehmet Yildiz at IBM Austin Research({gnam, mcan}@us.ibm.com)\n
"""
    )
    with open(src_file, "r", encoding="utf8") as fread:
        for line in fread:
            line = line.strip()
            if line.startswith("NumNodes"):
                num_nodes = int(line.split()[-1])
                fwrite.write(f"NumNodes : {num_nodes - len(placedb.port_to_delete)}\n")
            elif line.startswith("NumTerminals"):
                if is_fixed:  # is_fixed 表示是否固定 macro
                    fwrite.write(f"NumTerminals : {placedb.node_cnt}\n")
                else:
                    fwrite.write(f"NumTerminals : {placedb.port_cnt}\n")
            elif line.startswith("o") and not line.endswith("terminal"):
                line = line.split()
                node_name, width, height = line[0], int(line[1]), int(line[2])
                fwrite.write(f"\t{node_name}\t{width}\t{height}\n")
    fwrite.close()


def write_pl_cell(src_file: str, dst_file: str):
    fwrite = open(dst_file, "w", encoding="utf8")
    fwrite.write("UCLA pl 1.0\n\n")
    with open(src_file, "r", encoding="utf8") as fread:
        for line in fread:
            line = line.strip()
            if line.startswith("o") and not line.endswith("/FIXED"):
                line = line.split()
                node_name, bottom_left_x, bottom_left_y = (
                    line[0],
                    int(line[1]),
                    int(line[2]),
                )
                fwrite.write(f"{node_name}\t{bottom_left_x}\t{bottom_left_y}\t: N\n")
    fwrite.close()


def write_nets_cell(src_file: str, dst_file: str, placedb: PlaceDB):
    net_info: Dict[str, Net] = dict()
    num_nets = 0
    num_pins = 0
    with open(src_file, "r", encoding="utf8") as fread:
        for line in fread:
            line = line.strip()
            if line.startswith("NumNets"):
                num_nets = int(line.split()[-1])
            elif line.startswith("NumPins"):
                num_pins = int(line.split()[-1])
            elif line.startswith("NetDegree"):
                net_name = line.split()[-1]
                net_info[net_name] = dict()
            elif line.startswith("o"):
                line = line.split()
                node_name = line[0]
                direc = line[1]
                pos_x, pos_y = float(line[-1]), float(line[-2])
                if node_name in placedb.port_to_delete:
                    num_pins -= 1
                else:
                    if node_name not in net_info[net_name]:
                        net_info[net_name][node_name] = []
                    net_info[net_name][node_name].append(Pin(direc, pos_x, pos_y))
    for net_name in list(net_info):
        have_in = False
        have_out = False
        for node_name in net_info[net_name]:
            for pin in net_info[net_name][node_name]:
                if pin.direct == "I":
                    have_in = True
                elif pin.direct == "O":
                    have_out = True
        if (len(net_info[net_name]) == 0) or not (have_in and have_out):
            net_pin_num = sum(
                [len(net_info[net_name][node_name]) for node_name in net_info[net_name]]
            )
            num_pins -= net_pin_num
            net_info.pop(net_name)
            num_nets -= 1

    with open(dst_file, "w", encoding="utf8") as fwrite:
        fwrite.write(
            """\
UCLA nets 1.0
# Created	:	Dec 27 2004
# User   	:	Gi-Joon Nam & Mehmet Yildiz at IBM Austin Research({gnam, mcan}@us.ibm.com)
"""
        )
        fwrite.write("\n")
        fwrite.write(
            f"""\
NumNets : {num_nets}
NumPins : {num_pins}
"""
        )
        for net_name in net_info:
            net_pin_num = sum(
                [len(net_info[net_name][node_name]) for node_name in net_info[net_name]]
            )
            fwrite.write(f"NetDegree : {net_pin_num} {net_name}\n")
            for node_name in net_info[net_name]:
                for pin in net_info[net_name][node_name]:
                    fwrite.write(
                        f"\t{node_name} {pin.direct} : {pin.x_offset:.6f} {pin.y_offset:.6f}\n"
                    )


def for_human_preprocessing(benchmark: str):
    print(benchmark)
    grid_size = grid_setting[benchmark]["grid_size"]
    placedb = PlaceDB(benchmark, grid_size)

    origin_benchmark_dir = os.path.join("benchmarks", benchmark)
    benchmarks_for_human_dir = os.path.join("benchmarks_for_human", benchmark)
    os.system(f"mkdir -p {benchmarks_for_human_dir}")
    # 处理 .nodes, .nets, .pl 文件
    nodes_file = os.path.join(benchmarks_for_human_dir, f"{benchmark}.nodes")
    pl_file = os.path.join(benchmarks_for_human_dir, f"{benchmark}.pl")
    nets_file = os.path.join(benchmarks_for_human_dir, f"{benchmark}.nets")
    write_nodes_cell(
        os.path.join(origin_benchmark_dir, f"{benchmark}.nodes"),
        nodes_file,
        placedb,
        True,
    )
    write_pl_cell(os.path.join(origin_benchmark_dir, f"{benchmark}.pl"), pl_file)
    placedb.write_nodes_pure_pam(nodes_file)
    placedb.write_pl_pure_pam(pl_file)
    write_nets_cell(
        os.path.join(origin_benchmark_dir, f"{benchmark}.nets"), nets_file, placedb
    )

    # 处理 .aux, .scl, .wts 文件
    origin_benchmark_dir = os.path.join("benchmarks", benchmark)
    os.system(
        f"cp -f {origin_benchmark_dir}/{benchmark}.aux {benchmarks_for_human_dir}"
    )
    os.system(
        f"cp -f {origin_benchmark_dir}/{benchmark}.scl {benchmarks_for_human_dir}"
    )
    os.system(
        f"cp -f {origin_benchmark_dir}/{benchmark}.wts {benchmarks_for_human_dir}"
    )

    # 生成布局对应的图片
    m2m_csv_file = os.path.join("benchmarks", benchmark, "macro2macro.csv")
    m2m_flow = get_m2m_flow(m2m_csv_file)
    place_record = db2record(placedb, grid_size)
    pic_file = os.path.join(benchmarks_for_human_dir, f"{benchmark}_dataflow_id.png")
    draw_macro_placement(place_record, pic_file, placedb, m2m_flow, True)

    pic_file = os.path.join(benchmarks_for_human_dir, f"{benchmark}_nodataflow_id.png")
    draw_macro_placement(place_record, pic_file, placedb, None, True)

    pic_file = os.path.join(benchmarks_for_human_dir, f"{benchmark}_dataflow_noid.png")
    draw_macro_placement(place_record, pic_file, placedb, m2m_flow, False)

    pic_file = os.path.join(
        benchmarks_for_human_dir, f"{benchmark}_nodataflow_noid.png"
    )
    draw_macro_placement(place_record, pic_file, placedb, None, False)


if __name__ == "__main__":
    for b in benchmark_list:
        for_human_preprocessing(b)
