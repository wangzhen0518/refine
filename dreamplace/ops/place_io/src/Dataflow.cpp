#include <spdlog/spdlog.h>
#include <cassert>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <unordered_set>

#include "Dataflow.h"
#include "Net.h"
#include "Node.h"
#include "Pin.h"

std::vector<dPathNode> dNode::getNeighbors(dDataflowCaler const& cdf) const {
    std::vector<dPathNode> neighbors;
    for (auto nodePinId : _pinIdList) {
        DreamPlace::Pin const& nodePin = _db.pin(nodePinId);
        if (nodePin.direct().value() == DreamPlace::SignalDirectEnum::OUTPUT) {
            DreamPlace::Net const& net = _db.net(nodePin.netId());
            for (auto netPinId : net.pins()) {
                DreamPlace::Pin const& netPin = _db.pin(netPinId);
                if (netPin.direct().value() == DreamPlace::SignalDirectEnum::INPUT) {
                    dNode const& neighborNode = cdf.node(netPin.nodeId());
                    if (neighborNode.node_id() != _node_id) {
                        dPathNode pn = dPathNode(this, &neighborNode, &net, &nodePin, &netPin);
                        neighbors.push_back(pn);
                    }
                }
            }
        }
    }
    return neighbors;
}

void dPath::printPath() const {
    const unsigned int width = 2;
    for (dPathNode const& n : _dPathNodeList) {
        if (n.is_start()) {
            n.endNode()->print_node();
        } else {
            std::cout << ":";
            std::cout << YELLOW << "Pin(" << std::setw(width) << n.startPin()->id() << ")"
                      << COLOR_END;
            std::cout << "--";
            std::cout << BLUE << "Net(" << std::setw(width) << n.net()->id() << ")" << COLOR_END;
            std::cout << "--";
            std::cout << YELLOW << "Pin(" << std::setw(width) << n.endPin()->id() << ")"
                      << COLOR_END;
            std::cout << ":";
            n.endNode()->print_node();
        }
    }
}

void dDataflowCaler::dNodeInit() {
    spdlog::info("start dNodeInit");

    for (unsigned int i = 0; i < _db.nodes().size(); ++i) {
        _dNodeList.push_back(dNode(_db.node(i), _db.nodeProperty(i).name(), _db));
    }

    _numRegister = _numMacro = _numIOPin = 0;
    if (_db.macros().size() >= _db.nodes().size()) {  // TODO ispd2005 不完善
        for (unsigned int i = 0; i < _db.fixedNodeIndices().size(); ++i) {
            unsigned int fixedId = _db.fixedNodeIndices().at(i);
            _dNodeList.at(fixedId).setMacro(i);
        }
        _numRegister = _db.numMovable();
        _numMacro = _db.numFixed();
    } else {
        for (unsigned int i = 0; i < _dNodeList.size(); ++i) {
            _dNodeList[i].setNodeId(i);
            switch (_dNodeList[i].type()) {
                case dNodeType::Register:
                    _numRegister++;
                    break;
                case dNodeType::Macro: {
                    _dNodeList[i].setMacroId(_numMacro);
                    _numMacro++;
                } break;
                case dNodeType::IOPin:
                    _numIOPin++;
                    break;
            }
        }
    }
}

void dDataflowCaler::compute() {
    // 初始化所有 dNode，关键在于初始化 _isMacro
    if (_dNodeList.empty()) {
        dNodeInit();
    }
    spdlog::info("macro num: {}", _numMacro);

    spdlog::info("start computeMacro2MacroPath");
    computeMacro2MacroPath();

    spdlog::info("start computeMacro2MacroDataflow");
    computeMacro2MacroDataflow();
}

// 根据 DFS 计算出所有 macro2macro 只经过 register 和 cell 的路径
void dDataflowCaler::computeMacro2MacroPath() {
    unsigned int cnt = 0;
    assert(!_dNodeList.empty());
    for (dNode const& node : _dNodeList) {
        if (node.is_Macro()) {
            dStack s(node);
            std::vector<dPath> nodePaths = DFS(s);
            _allMacro2MacroPath.insert(_allMacro2MacroPath.end(), nodePaths.begin(),
                                       nodePaths.end());
            spdlog::info("{}: macro {} has {} paths, total {} paths", cnt++, node.node_id(),
                         nodePaths.size(), _allMacro2MacroPath.size());
        }
    }
}

std::vector<dPath> dDataflowCaler::DFS(dStack& s) {
    std::vector<dPath> dPathList;
    if (!s.empty() && s.depth() < _depthMax) {
        // if (!s.empty()) {
        // size=1 时，只有路径起始的 macro，所以不应该发生 s.empty() 的情况
        dPathNode const& n = s.back();
        dNode const& boundary = *n.endNode();
        for (dPathNode neighborNode : boundary.getNeighbors(*this)) {
            // if (is_inPath(node_set, net_set, pin_set, neighborNode) != 0) {
            if (s.is_inPath(neighborNode) != 0 || neighborNode.endNode()->is_IOPin()) {
                continue;  // 跳过该 node
            } else if (neighborNode.endNode()->is_Macro()) {
                dPath newPath(s.getPath());
                newPath.add(neighborNode);
                dPathList.push_back(newPath);
            } else {
                s.push(neighborNode);
                std::vector<dPath> nodePaths = DFS(s);
                dPathList.insert(dPathList.end(), nodePaths.begin(), nodePaths.end());
                s.pop();
            }
        }
    }
    return dPathList;
}

void dDataflowCaler::computeMacro2MacroDataflow() {
    // 初始化 _dMacro2MacroFlow
    _dMacro2MacroFlow.resize(_numMacro);
    for (std::vector<double>& line : _dMacro2MacroFlow) {
        line.resize(_numMacro, 0);
    }
    // for (auto const& node1 : _dNodeList) {
    //     for (auto const& node2 : _dNodeList) {
    //         _dMacro2MacroFlow[node1.name()][node2.name()] = 0.0;
    //     }
    // }
    // 遍历所有 macro2macro path
    for (dPath const& p : _allMacro2MacroPath) {
        unsigned int k = p.length() - 2;  // 此处路径长度不计算两端的 macro
        assert(k >= 0);
        dNode const& start = p.startNode();
        dNode const& end = p.endNode();
        _dMacro2MacroFlow.at(start.macro_id()).at(end.macro_id()) += powf64(0.5, k);
        // _dMacro2MacroFlow[start.name()][end.name()] += powf64(0.5, k);
    }
}

void dDataflowCaler::printMacro2MacroFlow() const {
    const unsigned int width = 10;
    std::cout << std::setw(width) << " ";
    for (unsigned i = 0; i < _numMacro; ++i) {
        std::cout << std::setw(width) << _db.fixedNodeIndices().at(i);
    }
    std::cout << std::endl;
    for (unsigned i = 0; i < _numMacro; ++i) {
        std::cout << std::setw(width) << _db.fixedNodeIndices().at(i);
        for (unsigned j = 0; j < _numMacro; ++j) {
            std::cout << std::setw(width) << _dMacro2MacroFlow.at(i).at(j);
            // std::string node_name1 = _dNodeList.at(i).name();
            // std::string node_name2 = _dNodeList.at(j).name();
            // std::cout << std::setw(width) << _dMacro2MacroFlow[node_name1][node_name2];
        }
        std::cout << std::endl;
    }
}

void dDataflowCaler::printMacro2MacroPath() const {
    unsigned width = 3;
    unsigned i = 0;
    for (dPath const& p : _allMacro2MacroPath) {
        std::cout << "Path" << std::setw(width) << i++ << ": ";
        p.printPath();
        unsigned int k = p.length() - 2;  // 此处路径长度不计算两端的 macro
        double weight = powf64(0.5, k);
        std::cout << "    " << std::setw(width) << weight << std::endl;
    }
}

void dDataflowCaler::writeMacro2MacroFlow(std::string const& filename) const {
    std::ofstream fw(filename);
    for (auto const& node : _dNodeList) {
        if (node.is_Macro())
            fw << "," << node.name();
    }
    fw << std::endl;
    // for (auto const& node1 : _dNodeList) {
    //     fw << node1.name();
    //     for (auto const& node2 : _dNodeList) {
    //         fw << "," << _dMacro2MacroFlow[node1.name()][node2.name()];
    //     }
    //     fw << std::endl;
    // }
    int mi = 0;
    for (auto const& line : _dMacro2MacroFlow) {
        while (!_dNodeList[mi].is_Macro())  // 找到 line 对应的 macro
            ++mi;
        fw << _dNodeList[mi].name();
        for (double df : line) {
            fw << "," << df;
        }
        fw << std::endl;
        ++mi;
    }
    fw.close();
}
