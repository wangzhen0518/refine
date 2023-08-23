#include <spdlog/spdlog.h>
#include <algorithm>
#include <cassert>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "Dataflow.h"
#include "Net.h"
#include "Node.h"
#include "Pin.h"
#include "PlaceDB.h"

#include "mytest.h"

#define RED "\e[1;31m"
#define YELLOW "\e[1;33m"
#define BLUE "\e[1;34m"
#define COLOR_END "\e[0m"

bool readBookshelf(DreamPlace::PlaceDB& db) {
    using namespace DreamPlace;
    // read bookshelf
    std::string const& bookshelfAuxInput = db.userParam().bookshelfAuxInput;
    if (!bookshelfAuxInput.empty()) {
        std::string const& filename = bookshelfAuxInput;
        dreamplacePrint(kINFO, "reading %s\n", filename.c_str());
        bool flag = BookshelfParser::read(db, filename);
        if (!flag) {
            dreamplacePrint(kERROR, "Bookshelf file parsing failed: %s\n", filename.c_str());
            return false;
        }
    } else
        dreamplacePrint(kWARN, "no Bookshelf file specified\n");
    // read additional .pl file
    std::string const& bookshelfPlInput = db.userParam().bookshelfPlInput;
    if (!bookshelfPlInput.empty()) {
        std::string const& filename = bookshelfPlInput;
        dreamplacePrint(kINFO, "reading %s\n", filename.c_str());
        bool flag = BookshelfParser::readPl(db, filename);
        if (!flag) {
            dreamplacePrint(kERROR, "Bookshelf additional .pl file parsing failed: %s\n",
                            filename.c_str());
            return false;
        }
    } else
        dreamplacePrint(kWARN, "no additional Bookshelf .pl file specified\n");
    return true;
}

bool readVerilog(DreamPlace::PlaceDB& db) {
    using namespace DreamPlace;
    // read verilog
    std::string const& verilogInput = db.userParam().verilogInput;
    if (!verilogInput.empty()) {
        std::string const& filename = verilogInput;
        dreamplacePrint(kINFO, "reading %s\n", filename.c_str());
        bool flag = VerilogParser::read(db, filename);
        if (!flag) {
            dreamplacePrint(kERROR, "Verilog file parsing failed: %s\n", filename.c_str());
            return false;
        }
    } else
        dreamplacePrint(kWARN, "no Verilog file specified\n");

    return true;
}

bool readLef(DreamPlace::PlaceDB& db) {
    using namespace DreamPlace;
    // read lef
    std::vector<std::string> const& vLefInput = db.userParam().vLefInput;
    for (std::vector<std::string>::const_iterator it = vLefInput.begin(), ite = vLefInput.end();
         it != ite; ++it) {
        std::string const& filename = *it;
        dreamplacePrint(kINFO, "reading %s\n", filename.c_str());
        bool flag = LefParser::read(db, filename);
        if (!flag) {
            dreamplacePrint(kERROR, "LEF file parsing failed: %s\n", filename.c_str());
            return false;
        }
    }
    return true;
}

void prereadDef(DreamPlace::PlaceDB& db, std::string const& filename) {
    using namespace DreamPlace;

    std::ifstream inFile(filename.c_str());
    if (!inFile.good())
        return;

    // need to extract following information
    unsigned numRows = 0;
    unsigned numNodes = 0;
    unsigned numIOPin = 0;
    unsigned numNets = 0;
    unsigned numBlockages = 0;

    std::string line;
    std::string token;
    while (!inFile.eof()) {
        std::getline(inFile, line);
        if (line.compare(0, 3, "ROW") == 0)  // a line starts with keyword "ROW"
            ++numRows;
        else if (line.compare(0, 10, "COMPONENTS") == 0) {
            std::istringstream iss(line);
            iss >> token >> numNodes >> token;
        } else if (line.compare(0, 4, "PINS") == 0) {
            std::istringstream iss(line);
            iss >> token >> numIOPin >> token;
        } else if (line.compare(0, 4, "NETS") == 0) {
            std::istringstream iss(line);
            iss >> token >> numNets >> token;
        } else if (line.compare(0, 9, "BLOCKAGES") == 0) {
            std::istringstream iss(line);
            iss >> token >> numBlockages >> token;
        }
    }

    dreamplacePrint(kINFO, "detect %u rows, %u components, %u IO pins, %u nets, %u blockages\n",
                    numRows, numNodes, numIOPin, numNets, numBlockages);
    db.prepare(numRows, numNodes, numIOPin, numNets, numBlockages);

    inFile.close();
}

bool readDef(DreamPlace::PlaceDB& db) {
    using namespace DreamPlace;
    // read def
    std::string const& defInput = db.userParam().defInput;
    if (!defInput.empty()) {
        std::string const& filename = defInput;
        dreamplacePrint(kINFO, "reading %s\n", filename.c_str());
        // a pre-reading phase to grep number of components, nets, and pins
        prereadDef(db, filename);
        bool flag = DefParser::read(db, filename);
        if (!flag) {
            dreamplacePrint(kERROR, "DEF file parsing failed: %s\n", filename.c_str());
            return false;
        }
    } else
        dreamplacePrint(kWARN, "no DEF file specified\n");

    return true;
}

dPlaceDB genPlaceDB(int argc, const char* argv[]) {
    using namespace DreamPlace;

    char** arg_list = new char*[argc];
    for (unsigned int i = 0; i < argc; ++i) {
        arg_list[i] = new char[strlen(argv[i]) + 1];
        strcpy(arg_list[i], argv[i]);
    }

    dPlaceDB db;
    db.userParam().read(argc, arg_list);

    // order for reading files
    // 1. lef files
    // 2. def files
    bool flag;

    // read lef
    flag = readLef(db);
    dreamplaceAssertMsg(flag, "failed to read input LEF files");

    // read def
    flag = readDef(db);
    dreamplaceAssertMsg(flag, "failed to read input DEF files");

    // if netlist is not set by DEF, read verilog
    if (db.nets().empty()) {
        // read verilog
        flag = readVerilog(db);
        dreamplaceAssertMsg(flag, "failed to read input Verilog files");
    }

    // read bookshelf
    flag = readBookshelf(db);
    dreamplaceAssertMsg(flag, "failed to read input Bookshelf files");

    // adjust input parameters
    db.adjustParams();
    std::for_each(std::reverse_iterator<char**>(arg_list), std::reverse_iterator<char**>(arg_list),
                  [](char* str) { delete[] str; });
    delete[] arg_list;
    return db;
}

void judge(dDataflow const& df1, dDataflow const& df2) {
    assert(df1.size() == df2.size());
    for (unsigned int i = 0; i < df1.size(); ++i) {
        assert(df1[i].size() == df2[i].size());
        for (unsigned int j = 0; j < df1[i].size(); ++j) {
            assert(abs(df1[i][j] - df2[i][j]) < 1e-6);
        }
    }
}

void adder_32bit() {
    int argc = 5;
    const char* argv[] = {
        "DREAMPlace",
        "--bookshelf_aux_input",
        "benchmarks/simple/adder32/adder32.aux",
        "--sort_nets_by_degree",
        "0",
    };

    dPlaceDB db = genPlaceDB(argc, argv);

    dDataflowCaler cdf(db, 4);
    cdf.compute();
    cdf.printMacro2MacroPath();
    cdf.printMacro2MacroFlow();

    dDataflow df = {
        {0, 1, 0, 1},
        {0, 0, 0, 1},
        {2, 2, 0, 0},
        {0, 0, 0, 0},
    };
    judge(df, cdf.getdMacro2MacroFlow());
}

void add_sub_32bit() {
    int argc = 5;
    const char* argv[] = {
        "DREAMPlace",
        "--bookshelf_aux_input",
        "benchmarks/simple/add_sub32/add_sub32.aux",
        "--sort_nets_by_degree",
        "0",
    };

    dPlaceDB db = genPlaceDB(argc, argv);

    dDataflowCaler cdf(db, 4);
    cdf.compute();
    cdf.printMacro2MacroPath();
    cdf.printMacro2MacroFlow();

    dDataflow df = {
        {0, 0, 1, 0},
        {2, 0, 0, 3},
        {0, 0, 0, 0},
        {1, 0, 1, 0},
    };
    judge(df, cdf.getdMacro2MacroFlow());
}

void decode() {
    int argc = 11;
    const char* argv[] = {"DREAMPlace",
                          "--lef_input",
                          "benchmarks/ispd2015/mgc_fft_1/tech.lef",
                          "--lef_input",
                          "benchmarks/ispd2015/mgc_fft_1/cells.lef",
                          "--def_input",
                          "benchmarks/ispd2015/mgc_fft_1/floorplan.def",
                          "--verilog_input",
                          "benchmarks/ispd2015/mgc_fft_1/design.v",
                          "--sort_nets_by_degree",
                          "0"};

    dPlaceDB db = genPlaceDB(argc, argv);

    dDataflowCaler cdf(db, 4);
    cdf.compute();
}

char* strcat_n(const char* s1, const char* s2) {
    char* result = new char[strlen(s1) + strlen(s2) + 1];
    if (!result) {
        printf("malloc error\n");
        exit(1);
    }
    std::strcpy(result, s1);
    std::strcat(result, s2);
    return result;
}

void ispd2005(const char* benchmark, int depth) {
    int argc = 5;
    std::stringstream dir_stream;
    dir_stream << "benchmarks/ispd2005/" << benchmark;

    std::stringstream aux_stream;
    aux_stream << dir_stream.str() << "/" << benchmark << ".aux";
    std::string aux_file = aux_stream.str();
    const char* argv[] = {"DREAMPlace", "--bookshelf_aux_input", aux_file.c_str(),
                          "--sort_nets_by_degree", "0"};

    dPlaceDB db = genPlaceDB(argc, argv);

    spdlog::info("start calculate dataflow\n");
    dDataflowCaler cdf(db, depth);
    cdf.compute();
    spdlog::info("end calculate dataflow\n");

    std::stringstream csv_stream;
    csv_stream << dir_stream.str() << "/macro2macro_d" << depth << ".csv";
    spdlog::info("write macro2macro dataflow");
    cdf.writeMacro2MacroFlow(csv_stream.str());
}

void ispd2015(const char* benchmark, unsigned int depth) {
    int argc = 11;
    std::stringstream dir_stream;
    dir_stream << "benchmarks/ispd2015/" << benchmark;

    std::stringstream tech_stream;
    std::stringstream cells_stream;
    std::stringstream floorplan_stream;
    std::stringstream design_stream;
    tech_stream << dir_stream.str() << "/tech.lef";
    cells_stream << dir_stream.str() << "/cells.lef";
    floorplan_stream << dir_stream.str() << "/floorplan.def";
    design_stream << dir_stream.str() << "/design.v";
    
    std::string tech_file = tech_stream.str();
    std::string cells_file = cells_stream.str();
    std::string floorplan_file = floorplan_stream.str();
    std::string design_file = design_stream.str();

    const char* argv[] = {"DREAMPlace",
                          "--lef_input",
                          tech_file.c_str(),
                          "--lef_input",
                          cells_file.c_str(),
                          "--def_input",
                          floorplan_file.c_str(),
                          "--verilog_input",
                          design_file.c_str(),
                          "--sort_nets_by_degree",
                          "0"};

    dPlaceDB db = genPlaceDB(argc, argv);

    spdlog::info("start calculate dataflow\n");
    dDataflowCaler cdf(db, depth);
    cdf.compute();
    spdlog::info("end calculate dataflow\n");

    std::stringstream csv_stream;
    csv_stream << dir_stream.str() << "/macro2macro_d" << depth << ".csv";
    spdlog::info("write macro2macro dataflow");
    cdf.writeMacro2MacroFlow(csv_stream.str());
}

int main(int argc, char* argv[]) {
    // adder_32bit();
    // add_sub_32bit();

    assert(argc >= 2);
    const char* benchmark = argv[1];
    int depth = 3;
    if (argc == 3) {
        depth = atoi(argv[2]);
    }
    // ispd2005(benchmark, depth);
    ispd2015(benchmark, depth);
    // decode();

    int x = 10;
    printf("Hello World %d\n", x);

    return 0;
}