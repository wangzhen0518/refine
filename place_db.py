import argparse
import math
import os
import numpy as np

from typing import Dict, Tuple

normal_set = {"adaptec1", "adaptec2", "bigblue1"}
delete_set = {"adaptec3", "adaptec4", "bigblue3", "bigblue4"}


class Node:
    def __init__(
        self,
        _id: int = 0,
        _name: str = "",
        _bottom_left_x: int = 0,
        _bottom_left_y: int = 0,
        _width: int = 0,
        _height: int = 0,
        grid_size: int = 0,
    ):
        self.id: int = _id
        self.name: str = _name
        self.bottom_left_x: int = _bottom_left_x
        self.bottom_left_y: int = _bottom_left_y
        self.width: int = _width
        self.height: int = _height
        self.area: int = _width * _height
        self.scaled_width: int = math.ceil(_width / grid_size)
        self.scaled_height: int = math.ceil(_height / grid_size)
        self.area_sum: int = 0
        self.is_fixed = False
        self.is_port = False

    def set_size(self, _width: int, _height: int, grid_size: int):
        self.width, self.height = _width, _height
        self.scaled_width: int = math.ceil(_width / grid_size)
        self.scaled_height: int = math.ceil(_height / grid_size)

    def resize_grid(self, grid_size: int):
        self.scaled_width: int = math.ceil(self.width / grid_size)
        self.scaled_height: int = math.ceil(self.height / grid_size)


class Port:
    def __init__(self) -> None:
        pass


def read_node_file(fopen, grid_size):
    node_info: Dict[str, Node] = {}
    node_cnt = 0
    cell_area = 0
    for line in fopen.readlines():
        line = line.strip()
        if line.startswith("o"):
            line = line.split()
            node_name = line[0]
            width = int(line[1])
            height = int(line[2])
            if line[-1] == "terminal":
                node_info[node_name] = Node(
                    node_cnt, node_name, 0, 0, width, height, grid_size
                )
                node_cnt += 1
            else:
                cell_area += width * height
    print("len node_info", len(node_info))
    return node_info, cell_area


def read_net_file(fopen, node_info):
    net_info = {}
    net_name = None
    net_cnt = 0
    pin_cnt = 0
    for line in fopen.readlines():
        if (
            not line.startswith("\t")
            and not line.startswith("  ")
            and not line.startswith("NetDegree")
        ):
            continue
        line = line.strip().split()
        if line[0] == "NetDegree":
            net_name = line[-1]
        else:
            node_name = line[0]
            node_direct = line[1]
            if node_name in node_info:  # 只留 macro
                pin_cnt += 1
                if net_name not in net_info:
                    net_info[net_name] = {}
                    net_info[net_name]["nodes"] = {}
                    net_info[net_name]["ports"] = {}
                if (
                    not node_name.startswith("p")
                    and node_name not in net_info[net_name]["nodes"]
                ):
                    x_offset = float(line[-2])
                    y_offset = float(line[-1])
                    net_info[net_name]["nodes"][node_name] = {
                        "direct": node_direct,
                        "x_offset": x_offset,
                        "y_offset": y_offset,
                    }
                elif (
                    node_name.startswith("p")
                    and node_name in net_info[net_name]["ports"]
                ):
                    x_offset = float(line[-2])
                    y_offset = float(line[-1])
                    net_info[net_name]["ports"][node_name] = {
                        "direct": node_direct,
                        "x_offset": x_offset,
                        "y_offset": y_offset,
                    }
    for net_name in list(net_info.keys()):
        if len(net_info[net_name]["nodes"]) <= 1:
            net_info.pop(net_name)
    for net_name in net_info:
        net_info[net_name]["id"] = net_cnt
        net_cnt += 1
    print("adjust net size = {}".format(len(net_info)))
    return net_info, pin_cnt


def read_pl_file(fopen, node_info: Dict[str, Node]):
    max_height = 0
    max_width = 0
    min_height = 999999
    min_width = 999999
    for line in fopen.readlines():
        if line.startswith("o"):
            line = line.strip().split()
            node_name = line[0]
            bottom_left_x = int(line[1])
            bottom_left_y = int(line[2])
            if node_name in node_info:
                node_info[node_name].bottom_left_x = bottom_left_x
                node_info[node_name].bottom_left_y = bottom_left_y
                max_height = max(
                    max_height,
                    node_info[node_name].width + node_info[node_name].bottom_left_x,
                )
                max_width = max(
                    max_width,
                    node_info[node_name].height + node_info[node_name].bottom_left_y,
                )
                min_height = min(min_height, node_info[node_name].bottom_left_x)
                min_width = min(min_width, node_info[node_name].bottom_left_y)
    return max(max_height, max_width), max(max_height, max_width), min_height, min_width


class PlaceDB:
    def __init__(self, benchmark="adaptec1", grid_size=1, boundary_radio: float = 0.1):
        self.benchmark = benchmark
        self.grid_size = grid_size
        assert os.path.exists(os.path.join("benchmarks", benchmark))
        node_file = open(
            os.path.join("benchmarks", benchmark, benchmark + ".nodes"), "r"
        )
        self.node_info, self.cell_area = read_node_file(node_file, grid_size)
        self.node_cnt = len(self.node_info)
        node_file.close()

        net_file = open(os.path.join("benchmarks", benchmark, benchmark + ".nets"), "r")
        self.net_info, self.pin_cnt = read_net_file(net_file, self.node_info)
        self.net_cnt = len(self.net_info)
        net_file.close()

        pl_file = open(os.path.join("benchmarks", benchmark, benchmark + ".pl"), "r")
        self.max_height, self.max_width, self.min_height, self.min_width = read_pl_file(
            pl_file, self.node_info
        )
        pl_file.close()

        self.aver_area = (
            sum([ni.area for ni in self.node_info.values()]) / self.node_cnt
        )

        self.center_core = False
        self.virtual_boundary = False

        # if grid_size == 1:
        #     min_width = min([ni.width for ni in self.node_info.values()])
        #     min_height = min([ni.height for ni in self.node_info.values()])
        #     self.grid_size = max(min_width, min_height)
        #     print(f"grid size: {self.grid_size}")
        #     self.grid_size = min(self.grid_size, 50)
        #     print(f"real grid size: {self.grid_size}")
        #     length = min(self.max_height, self.max_width)
        #     upper = math.ceil(length / self.grid_size)
        #     lower = math.floor(length / self.grid_size)
        #     #!TODO 确定 grid_num 大小
        #     if (upper * self.grid_size - length) < (length - lower * self.grid_size):
        #         self.grid_num = upper
        #     else:
        #         self.grid_num = lower

        self.preprocess(boundary_radio)

        # if grid_size == 1:
        #     for ni in self.node_info.values():
        #         ni.resize_grid(self.grid_size)

    def node_list(self):
        return list(self.node_info.values())

    def preprocess(self, boundary_radio=0.1):
        # 如果节点的面积小于平均面积，则认为是 port
        # 如果节点的位置不在边界上，则删除节点
        # 处理 macro, port 区分
        self.macro_name = set()
        self.port_name = set()
        self.port_cnt = 0
        self.port_to_delete = set()
        for ni in list(self.node_info.values()):
            if self.is_port(ni.name):
                if self.benchmark in normal_set:
                    if self.is_boundary(ni.name, boundary_radio):
                        self.port_name.add(ni.name)
                        self.port_cnt += 1
                    else:
                        self.port_to_delete.add(ni.name)
                        self.node_info.pop(ni.name)
                        self.node_cnt -= 1
                elif self.benchmark in delete_set:
                    self.port_to_delete.add(ni.name)
                    self.node_info.pop(ni.name)
                    self.node_cnt -= 1
            else:
                self.macro_name.add(ni.name)
        # 删除 net 所连接的被删除的 port
        for net_name in list(self.net_info):
            for node_name in list(self.net_info[net_name]["nodes"]):
                if node_name in self.port_to_delete:
                    self.net_info[net_name]["nodes"].pop(node_name)
                    self.pin_cnt -= 1
                    if len(self.net_info[net_name]) == 0:
                        self.net_info.pop(net_name)
                        self.net_cnt -= 1
        return self.port_to_delete

    def is_port(self, node_name):
        if self.node_info[node_name].area < self.aver_area:
            self.node_info[node_name].is_port = True
            return True
        else:
            return False

    def is_boundary(self, node_name, boundary_radio=0.1):
        node_left = self.node_info[node_name].bottom_left_x
        node_right = node_left + self.node_info[node_name].width
        node_bottom = self.node_info[node_name].bottom_left_y
        node_top = node_bottom + self.node_info[node_name].height

        boundary_left = boundary_radio * self.max_width
        boundary_right = (1 - boundary_radio) * self.max_width
        boundary_bottom = boundary_radio * self.max_height
        boundary_top = (1 - boundary_radio) * self.max_height

        if (
            node_left > boundary_left
            and node_right < boundary_right
            and node_bottom > boundary_bottom
            and node_top < boundary_top
        ):
            return False
        else:
            return True

    def write_nodes_pure(self, file: str):
        with open(file, "a", encoding="utf8") as f:
            for node in self.node_list():
                f.write(f"\t{node.name}\t{node.width}\t{node.height}")
                if node.is_port:
                    f.write("\tterminal")
                f.write("\n")

    def write_nodes_pure_fixed(self, file: str):
        with open(file, "a", encoding="utf8") as f:
            for node in self.node_list():
                f.write(f"\t{node.name}\t{node.width}\t{node.height}\tterminal\n")

    def write_nodes_pure_pam(self, file: str):
        """区分macro和port，结尾不写terminal，而是macro/port"""
        with open(file, "a", encoding="utf8") as f:
            for node in self.node_list():
                f.write(f"\t{node.name}\t{node.width}\t{node.height}")
                if node.is_port:
                    f.write("\tport")
                else:
                    f.write("\tmacro")
                f.write("\n")

    def write_nodes(self, file: str):
        with open(file, "w", encoding="utf8") as f:
            f.write(
                """\
UCLA nodes 1.0
# Created	:	Jan  6 2005
# User   	:	Gi-Joon Nam & Mehmet Yildiz at IBM Austin Research({gnam, mcan}@us.ibm.com)\n
"""
            )
            f.write(
                f"""\
NumNodes : 		{self.node_cnt}
NumTerminals : 		{self.port_cnt}
"""
            )
        self.write_nodes_pure(file)

    def write_pl_pure(self, file: str):
        with open(file, "a", encoding="utf8") as f:
            for node in self.node_list():
                f.write(f"{node.name}\t{node.bottom_left_x}\t{node.bottom_left_y}\t: N")
                if node.is_port:
                    f.write(" /FIXED")
                f.write("\n")

    def write_pl_pure_fixed(self, file: str):
        with open(file, "a", encoding="utf8") as f:
            for node in self.node_list():
                f.write(
                    f"{node.name}\t{node.bottom_left_x}\t{node.bottom_left_y}\t: N /FIXED\n"
                )

    def write_pl_pure_pam(self, file: str):
        """区分macro和port，结尾不写FIXED，而是macro/port"""
        with open(file, "a", encoding="utf8") as f:
            for node in self.node_list():
                f.write(f"{node.name}\t{node.bottom_left_x}\t{node.bottom_left_y}\t: N")
                if node.is_port:
                    f.write("\tport")
                else:
                    f.write("\tmacro")
                f.write("\n")

    def write_pl(self, file: str):
        with open(file, "w", encoding="utf8") as f:
            f.write("UCLA pl 1.0\n\n")
        self.write_pl_pure(file)

    def write_nets_pure(self, file: str):
        with open(file, "a", encoding="utf8") as f:
            for net in self.net_info:
                f.write(f"NetDegree : {len(self.net_info[net]['nodes'])} {net}\n")
                for node in self.net_info[net]["nodes"]:
                    f.write(
                        f"\t{node} {self.net_info[net]['nodes'][node]['direct']} : {self.net_info[net]['nodes'][node]['x_offset']:.6f} {self.net_info[net]['nodes'][node]['y_offset']:.6f}\n"
                    )
                for port in self.net_info[net]["ports"]:
                    f.write(
                        f"\t{port} {self.net_info[net]['nodes'][port]['direct']} : {self.net_info[net]['ports'][port]['x_offset']:.6f} {self.net_info[net]['ports'][port]['y_offset']:.6f}\n"
                    )

    def write_nets(self, file: str):
        with open(file, "w", encoding="utf8") as f:
            f.write(
                """\
UCLA nets 1.0
# Created	:	Dec 27 2004
# User   	:	Gi-Joon Nam & Mehmet Yildiz at IBM Austin Research({gnam, mcan}@us.ibm.com)
"""
            )
            f.write("\n")
            f.write(
                f"""\
NumNets : {self.net_cnt}
NumPins : {self.pin_cnt}
"""
            )
            f.write("\n")
        self.write_nets_pure(file)

    def deal_center_core(self, scale_factor=1.25):
        self.center_core = True
        self.r = np.sqrt(scale_factor * self.cell_area / np.pi)
        self.center_x = self.max_width / 2
        self.center_y = self.max_height / 2
        self.L2 = (self.center_x - self.r) * self.r
        # self.L2 = self.center_x * self.center_x

    def deal_virtual_boundary(self, scale_factor=1.25):
        self.virtual_boundary = True
        self.macro_area = np.sum([self.node_info[ni].area for ni in self.macro_name])
        # self.port_area = np.sum([self.node_info[ni].area for ni in self.port_name])
        total_area = self.cell_area + self.macro_area  # + self.port_area
        self.boundary_length = np.sqrt(total_area * scale_factor)
        self.left_boundary = max(0, self.center_x - self.boundary_length / 2)
        self.right_boundary = min(
            self.max_width, self.center_x + self.boundary_length / 2
        )
        self.bottom_boundary = max(0, self.center_y - self.boundary_length / 2)
        self.top_boundary = min(
            self.max_height, self.center_y + self.boundary_length / 2
        )


if __name__ == "__main__":
    from common import grid_setting

    parser = argparse.ArgumentParser(description="argparse testing")
    parser.add_argument("--dataset", required=True)
    args = parser.parse_args()
    dataset = args.dataset
    grid_size = grid_setting[dataset]["grid_size"]
    placedb = PlaceDB(dataset, grid_size)
    print(placedb.node_info)
