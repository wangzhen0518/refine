##
# @file   Placer.py
# @author Yibo Lin
# @date   Apr 2018
# @brief  Main file to run the entire placement flow.
#

import logging
import os
import sys
import time
from typing import Tuple
import argparse

import matplotlib
import numpy as np

# for consistency between python2 and python3
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)
import NonLinearPlace  # noqa: E402
import Params  # noqa: E402
import PlaceDB  # noqa: E402
import Timer  # noqa: E402

import dreamplace.configure as configure  # noqa: E402

matplotlib.use("Agg")


def is_float(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def read_maskplace(placedb: PlaceDB.PlaceDB, csv_file):
    place_record = {}
    with open(csv_file, encoding="utf8") as f:
        pos = 0
        line = f.readline()
        while line != "":
            if is_float(line):
                pos = f.tell()
            line = f.readline()
        f.seek(pos)

        line = f.readline()
        while line != "" and line != "\n":
            line = line.strip().split(",")
            macro, x, y = line[0], int(line[1]), int(line[2])
            place_record[macro] = [x, y]
            line = f.readline()

    for macro, (x, y) in place_record.items():
        idx = placedb.node_name2id_map[macro]
        placedb.node_x[idx] = x
        placedb.node_y[idx] = y
        # placedb.rawdb
    return placedb


def read_pl_file(
    placedb: PlaceDB.PlaceDB, pl_file: str, shift_factor: Tuple[float, float]
):
    with open(pl_file, encoding="utf8") as f:
        for line in f:
            if line.startswith("o"):
                line = line.strip().split()
                node_name = line[0]
                bottom_left_x, bottom_left_y = int(line[1]), int(line[2])
                idx = placedb.node_name2id_map[node_name]
                placedb.node_x[idx] = bottom_left_x - shift_factor[0]
                placedb.node_y[idx] = bottom_left_y - shift_factor[1]
    return placedb


def read_dreamplace_pl_file(
    placedb: PlaceDB.PlaceDB, pl_file: str, shift_factor: Tuple[float, float]
):
    with open(pl_file, encoding="utf8") as f:
        for line in f:
            if line.startswith("o"):
                line = line.strip().split()
                node_name = line[0]
                bottom_left_x, bottom_left_y = int(line[1]), int(line[2])
                if node_name in placedb.fixed_node_name:
                    idx = placedb.node_name2id_map[node_name]
                    placedb.node_x[idx] = bottom_left_x - shift_factor[0]
                    placedb.node_y[idx] = bottom_left_y - shift_factor[1]
    return placedb


def place(params):
    """
    @brief Top API to run the entire placement flow.
    @param params parameters
    """

    assert (not params.gpu) or configure.compile_configurations[
        "CUDA_FOUND"
    ] == "TRUE", "CANNOT enable GPU without CUDA compiled"

    np.random.seed(params.random_seed)
    # read database
    tt = time.time()
    placedb = PlaceDB.PlaceDB()
    placedb(params)

    if params.type == "front" and params.method == "dreamplace-mixed":
        pl_file = f"./results_macro_front_dreamplace-mixed/{params.design_name()}/{params.design_name()}.gp.pl"
        read_dreamplace_pl_file(placedb, pl_file, params.shift_factor)
    else:
        if params.type == "front":
            if params.method == "bbo":
                pl_file = f"./results_macro_front_bbo/{params.design_name()}/{params.design_name()}.gp.pl"
            elif params.method == "dreamplace-macro":
                pl_file = f"./results_macro_front_dreamplace-macro/{params.design_name()}/{params.design_name()}.gp.pl"
        elif params.type == "refine":
            if params.method == "bbo":
                pl_file = f"./results_macro_refine-EA_bbo/{params.design_name()}/{params.design_name()}.gp.pl"
            elif params.method == "dreamplace-mixed":
                pl_file = f"./results_macro_refine-EA_dreamplace-mixed/{params.design_name()}/{params.design_name()}.gp.pl"
            elif params.method == "dreamplace-macro":
                pl_file = f"./results_macro_refine-EA_dreamplace-macro/{params.design_name()}/{params.design_name()}.gp.pl"
            else:
                raise NotImplementedError
        else:
            raise NotImplementedError
        read_pl_file(placedb, pl_file, params.shift_factor)

    logging.info("reading database takes %.2f seconds" % (time.time() - tt))

    # Read timing constraints provided in the benchmarks into out timing analysis
    # engine and then pass the timer into the placement core.
    timer = None
    if params.timing_opt_flag:
        tt = time.time()
        timer = Timer.Timer()
        timer(params, placedb)
        # This must be done to explicitly execute the parser builders.
        # The parsers in OpenTimer are all in lazy mode.
        timer.update_timing()
        logging.info("reading timer takes %.2f seconds" % (time.time() - tt))

        # Dump example here. Some dump functions are defined.
        # Check instance methods defined in Timer.py for debugging.
        # timer.dump_pin_cap("pin_caps.txt")
        # timer.dump_graph("timing_graph.txt")

    # solve placement
    tt = time.time()
    placer = NonLinearPlace.NonLinearPlace(params, placedb, timer)
    logging.info(
        "non-linear placement initialization takes %.2f seconds" % (time.time() - tt)
    )
    metrics = placer(params, placedb)
    logging.info("non-linear placement takes %.2f seconds" % (time.time() - tt))

    # write placement solution
    path = "%s/%s" % (params.result_dir, params.design_name())
    if not os.path.exists(path):
        os.system("mkdir -p %s" % (path))
    gp_out_file = os.path.join(
        path, "%s.gp.%s" % (params.design_name(), params.solution_file_suffix())
    )
    placedb.write(params, gp_out_file)

    # call external detailed placement
    # TODO: support more external placers, currently only support
    # 1. NTUplace3/NTUplace4h with Bookshelf format
    # 2. NTUplace_4dr with LEF/DEF format
    if params.detailed_place_engine and os.path.exists(params.detailed_place_engine):
        logging.info(
            "Use external detailed placement engine %s" % (params.detailed_place_engine)
        )
        if params.solution_file_suffix() == "pl" and any(
            dp_engine in params.detailed_place_engine
            for dp_engine in ["ntuplace3", "ntuplace4h"]
        ):
            dp_out_file = gp_out_file.replace(".gp.pl", "")
            # add target density constraint if provided
            target_density_cmd = ""
            if params.target_density < 1.0 and not params.routability_opt_flag:
                target_density_cmd = " -util %f" % (params.target_density)
            cmd = "%s -aux %s -loadpl %s %s -out %s -noglobal %s" % (
                params.detailed_place_engine,
                params.aux_input,
                gp_out_file,
                target_density_cmd,
                dp_out_file,
                params.detailed_place_command,
            )
            logging.info("%s" % (cmd))
            tt = time.time()
            os.system(cmd)
            logging.info(
                "External detailed placement takes %.2f seconds" % (time.time() - tt)
            )

            if params.plot_flag:
                # read solution and evaluate
                placedb.read_pl(params, dp_out_file + ".ntup.pl")
                iteration = len(metrics)
                pos = placer.init_pos
                pos[0 : placedb.num_physical_nodes] = placedb.node_x
                pos[
                    placedb.num_nodes : placedb.num_nodes + placedb.num_physical_nodes
                ] = placedb.node_y
                hpwl, density_overflow, max_density = placer.validate(
                    placedb, pos, iteration
                )
                logging.info(
                    "iteration %4d, HPWL %.3E, overflow %.3E, max density %.3E"
                    % (iteration, hpwl, density_overflow, max_density)
                )
                placer.plot(params, placedb, iteration, pos)
        elif "ntuplace_4dr" in params.detailed_place_engine:
            dp_out_file = gp_out_file.replace(".gp.def", "")
            cmd = "%s" % (params.detailed_place_engine)
            for lef in params.lef_input:
                if "tech.lef" in lef:
                    cmd += " -tech_lef %s" % (lef)
                else:
                    cmd += " -cell_lef %s" % (lef)
                benchmark_dir = os.path.dirname(lef)
            cmd += " -floorplan_def %s" % (gp_out_file)
            if params.verilog_input:
                cmd += " -verilog %s" % (params.verilog_input)
            cmd += " -out ntuplace_4dr_out"
            cmd += " -placement_constraints %s/placement.constraints" % (
                # os.path.dirname(params.verilog_input))
                benchmark_dir
            )
            cmd += " -noglobal %s ; " % (params.detailed_place_command)
            # cmd += " %s ; " % (params.detailed_place_command) ## test whole flow
            cmd += "mv ntuplace_4dr_out.fence.plt %s.fence.plt ; " % (dp_out_file)
            cmd += "mv ntuplace_4dr_out.init.plt %s.init.plt ; " % (dp_out_file)
            cmd += "mv ntuplace_4dr_out %s.ntup.def ; " % (dp_out_file)
            cmd += "mv ntuplace_4dr_out.ntup.overflow.plt %s.ntup.overflow.plt ; " % (
                dp_out_file
            )
            cmd += "mv ntuplace_4dr_out.ntup.plt %s.ntup.plt ; " % (dp_out_file)
            if os.path.exists("%s/dat" % (os.path.dirname(dp_out_file))):
                cmd += "rm -r %s/dat ; " % (os.path.dirname(dp_out_file))
            cmd += "mv dat %s/ ; " % (os.path.dirname(dp_out_file))
            logging.info("%s" % (cmd))
            tt = time.time()
            os.system(cmd)
            logging.info(
                "External detailed placement takes %.2f seconds" % (time.time() - tt)
            )
        else:
            logging.warning(
                "External detailed placement only supports NTUplace3/NTUplace4dr API"
            )
    elif params.detailed_place_engine:
        logging.warning(
            "External detailed placement engine %s or aux file NOT found"
            % (params.detailed_place_engine)
        )

    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True)
    parser.add_argument("--method", required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    """
    @brief main function to invoke the entire placement flow.
    """
    logging.root.name = "DREAMPlace"
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)-7s] %(name)s - %(message)s",
        stream=sys.stdout,
    )
    params = Params.Params()
    params.printWelcome()
    params.type = args.type
    params.method = args.method
    # if len(sys.argv) == 1 or "-h" in sys.argv[1:] or "--help" in sys.argv[1:]:
    #     params.printHelp()
    #     exit()
    # elif len(sys.argv) != 2:
    #     logging.error("One input parameters in json format in required")
    #     params.printHelp()
    #     exit()

    # load parameters
    # params.load(sys.argv[1])
    params.load(args.config)
    logging.info("parameters = %s" % (params))
    # control numpy multithreading
    os.environ["OMP_NUM_THREADS"] = "%d" % (params.num_threads)

    # run placement
    tt = time.time()
    place(params)
    logging.info("placement takes %.3f seconds" % (time.time() - tt))
