import os

from common import shift_factor


def shift_pl(benchmark: str):
    node_record = dict()
    file_name = os.path.join("front_dreamplace-mixed_results", benchmark, f"{benchmark}.gp.pl")
    with open(file_name, "r", encoding="utf8") as fread:
        for l in fread:
            l = l.strip()
            if l.startswith("o"):
                is_fixed = l.endswith("/FIXED")
                l = l.split()
                node_name, bottom_left_x, bottom_left_y = l[0], int(l[1]), int(l[2])
                bottom_left_x += shift_factor[benchmark][0]
                bottom_left_y += shift_factor[benchmark][1]
                node_record[node_name] = [bottom_left_x, bottom_left_y, is_fixed]
    with open(file_name, "w", encoding="utf8") as fwrite:
        fwrite.write("UCLA pl 1.0\n\n")
        for node_name, (bottom_left_x, bottom_left_y, is_fixed) in node_record.items():
            fwrite.write(
                f"{node_name}\t{bottom_left_x}\t{bottom_left_y}\t: N"
                + ("/FIXED" if is_fixed else "")
                + "\n"
            )


if __name__ == "__main__":
    # benchmark = "adaptec1"
    blist = [
        # "adaptec1",
        "adaptec2",
        "adaptec3",
        "adaptec4",
        "bigblue1",
        "bigblue2",
        "bigblue3",
        "bigblue4",
    ]
    for b in blist:
        shift_pl(b)
