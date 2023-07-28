#include <iostream>
#include <vector>

#include "Dataflow.h"
#include "PlaceDB.h"

DREAMPLACE_BEGIN_NAMESPACE
bool readBookshelf(PlaceDB& db) {
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
DREAMPLACE_END_NAMESPACE

bool adder_32bit(){
    
}

int main() {
    int argc = 5;
    char* argv[] = {"DREAMPlace", "--bookshelf_aux_input",
                    "benchmarks/ispd2005/adaptec1/adaptec1.aux", "--sort_nets_by_degree", "0"};

    DREAMPLACE_NAMESPACE::PlaceDB db;
    db.userParam().read(argc, argv);

    bool flag;
    flag = DREAMPLACE_NAMESPACE::readBookshelf(db);

    db.adjustParams();

    int x = 10;
    printf("Hello World %d\n", x);

    return 0;
}