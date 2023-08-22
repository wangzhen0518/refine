#include <spdlog/spdlog.h>
#include <cassert>
#include <cmath>
#include <csv2/writer.hpp>
#include <iomanip>
#include <iostream>
#include <unordered_set>

#include "Dataflow.h"
#include "Net.h"
#include "Node.h"
#include "Pin.h"
#include "PlaceDB.h"

#define RED "\e[1;31m"
#define YELLOW "\e[1;33m"
#define BLUE "\e[1;34m"
#define COLOR_END "\e[0m"

// 0 不在路径中
// 1 路径中有重复 node
// 2 路径中有重复 net
// 3 路径中有重复 pin
unsigned int is_inPath(std::unordered_set<unsigned int> const& node_set,
                       std::unordered_set<unsigned int> const& net_set,
                       std::unordered_set<unsigned int> const& pin_set,
                       dPathNode const& node) {
    if (node_set.find(node.endNode()->id()) != node_set.end()) {
        return 1;
    } else if (net_set.find(node.net()->id()) != net_set.end()) {
        return 2;
    } else if (pin_set.find(node.startPin()->id()) != pin_set.end() ||
               pin_set.find(node.endPin()->id()) != pin_set.end()) {
        return 3;
    } else
        return 0;
}

std::vector<dPathNode> dNode::getNeighbors(dDataflowCaler const& cdf) const {
    std::vector<dPathNode> neighbors;
    for (auto nodePinId : _node.pins()) {
        DreamPlace::Pin const& nodePin = _db.pin(nodePinId);
        if (nodePin.direct().value() == DreamPlace::SignalDirectEnum::OUTPUT) {
            DreamPlace::Net const& net = _db.net(nodePin.netId());
            for (auto netPinId : net.pins()) {
                DreamPlace::Pin const& netPin = _db.pin(netPinId);
                if (netPin.direct().value() == DreamPlace::SignalDirectEnum::INPUT) {
                    dNode const& neighborNode = cdf.node(netPin.nodeId());
                    if (neighborNode.id() != _node.id()) {
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
            std::cout << RED << "Node(" << std::setw(width) << n.endNode()->id() << ")"
                      << COLOR_END;
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
            std::cout << RED << "Node(" << std::setw(width) << n.endNode()->id() << ")"
                      << COLOR_END;
        }
    }
}

void dDataflowCaler::dNodeInit() {
    for (auto const& node : _db.nodes()) {
        _dNodeList.push_back(dNode(node, _db));
    }
    for (unsigned int i = 0; i < _db.fixedNodeIndices().size(); ++i) {
        unsigned int fixedId = _db.fixedNodeIndices().at(i);
        _dNodeList.at(fixedId).setMacro(true, i);
    }
    _numMacro = _db.numFixed();
}

void dDataflowCaler::compute() {
    // 初始化所有 dNode，关键在于初始化 _isMacro
    if (_dNodeList.empty()) {
        spdlog::info("start dNodeInit");
        dNodeInit();
    }
    spdlog::info("macro num: {}", _numMacro);
    spdlog::info("start computeMacro2MacroPath");
    computeMacro2MacroPath();
    spdlog::info("start computeMacro2MacroDataflow");
    computeMacro2MacroDataflow();
}

// dDataflow computeDataflowFunc(std::vector<Node> const& m_vNode,
//                               std::vector<NodeProperty> const& m_vNodeProperty,
//                               std::vector<Net> const& m_vNet,
//                               std::vector<NetProperty> const& m_vNetProperty,
//                               std::vector<Pin> const& m_vPin,
//                               std::vector<Macro> const& m_vMacro) {
//     for (auto const& m1 : m_vMacro) {
//     std::vector<Node const&> s;
//     for (auto const& mp : m1.macroPins()) {
//         auto const& n1 = m_vNode.at(m_vPin.at(mp.id()).nodeId());
//     }
// }
// 遍历所有macro
// 访问该 macro 的所有邻居
// 如果是 macro 则创建新 path
// 如果是 node 则入栈
//
// while 栈非空
// n = s.back()
// for n 的所有邻居
// if macro 则创建新 path
// if 达到 path 长度上限, 新 node 退栈
// if is_inPath(s, n) 则跳过该 node
// else s.push_back(n)
//
// 几个终止条件
// 1. 访问到 macro, 创建新 path, 访问该 node 的下一个邻居
// 2. 达到 path 长度上限, 新 node 退栈
// 3. 访问到已经访问过的 node, 跳过该 node
// }

// 根据 DFS 计算出所有 macro2macro 只经过 cell 的路径
void dDataflowCaler::computeMacro2MacroPath() {
    unsigned int cnt = 0;
    assert(!_dNodeList.empty());
    for (dNode const& node : _dNodeList) {
        if (node.is_Macro()) {
            std::vector<dPathNode> s;
            std::unordered_set<unsigned int> node_set;
            std::unordered_set<unsigned int> net_set;
            std::unordered_set<unsigned int> pin_set;
            dPathNode startNode(nullptr, &node, nullptr, nullptr, nullptr);
            s.push_back(startNode);
            node_set.insert(node.id());
            std::vector<dPath> nodePaths = DFS(s, node_set, net_set, pin_set);
            _allMacro2MacroPath.insert(_allMacro2MacroPath.end(), nodePaths.begin(),
                                       nodePaths.end());
            spdlog::info("{}: macro {} has {} paths, total {} paths", cnt++, node.id(),
                         nodePaths.size(), _allMacro2MacroPath.size());
        }
    }
}

// bool DFS(...){
// if (!s.empty()) {
// n = s.back()
// for n 的所有邻居
// if macro 则创建新 path
// if 达到 path 长度上限, 新 node 退栈
// if is_inPath(s, n) 则跳过该 node
// else s.push_back(n); DFS(...);
// }
// }

std::vector<dPath> dDataflowCaler::DFS(std::vector<dPathNode>& s,
                                       std::unordered_set<unsigned int>& node_set,
                                       std::unordered_set<unsigned int>& net_set,
                                       std::unordered_set<unsigned int>& pin_set) {
    std::vector<dPath> dPathList;
    if (!s.empty() && s.size() < _depthMax + 1) {
    // if (!s.empty()) {
        // size=1 时，只有路径起始的 macro，所以不应该发生 s.empty() 的情况
        dPathNode n = s.back();
        dNode const& boundary = *n.endNode();
        for (dPathNode neighborNode : boundary.getNeighbors(*this)) {
            if (is_inPath(node_set, net_set, pin_set, neighborNode) != 0) {
                continue;  // 跳过该 node
            } else if (neighborNode.endNode()->is_Macro()) {
                dPath newPath(s);
                newPath.add(neighborNode);
                dPathList.push_back(newPath);
            } else {
                s.push_back(neighborNode);
                node_set.insert(neighborNode.endNode()->id());
                net_set.insert(neighborNode.net()->id());
                pin_set.insert(neighborNode.startPin()->id());
                pin_set.insert(neighborNode.endPin()->id());

                std::vector<dPath> nodePaths = DFS(s, node_set, net_set, pin_set);
                dPathList.insert(dPathList.end(), nodePaths.begin(), nodePaths.end());

                dPathNode endNode = s.back();
                node_set.erase(neighborNode.endNode()->id());
                net_set.erase(neighborNode.net()->id());
                pin_set.erase(neighborNode.startPin()->id());
                pin_set.erase(neighborNode.endPin()->id());
                s.pop_back();
            }
        }
    }
    return dPathList;
}

void dDataflowCaler::computeMacro2MacroDataflow() {
    // 初始化 _dMacro2MacroFlow
    _dMacro2MacroFlow.resize(_numMacro);
    for (auto& line : _dMacro2MacroFlow) {
        line.resize(_numMacro, 0);
    }
    // 遍历所有 macro2macro path
    for (auto const& p : _allMacro2MacroPath) {
        unsigned int k = p.length() - 2;  // 此处路径长度不计算两端的 macro
        assert(k >= 0);
        dNode const& start = p.startNode();
        dNode const& end = p.endNode();
        _dMacro2MacroFlow.at(start.macro_id()).at(end.macro_id()) += powf64(0.5, k);
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
        }
        std::cout << std::endl;
    }
}

void dDataflowCaler::printMacro2MacroPath() const {
    unsigned width = 3;
    unsigned i = 0;
    for (auto const& p : _allMacro2MacroPath) {
        std::cout << "Path" << std::setw(width) << i++ << ": ";
        p.printPath();
        unsigned int k = p.length() - 2;  // 此处路径长度不计算两端的 macro
        double weight = powf64(0.5, k);
        std::cout << "    " << std::setw(width) << weight << std::endl;
    }
}

void dDataflowCaler::writeMacro2MacroFlow(std::string const& filename) const {
    std::ofstream fw(filename);
    for (auto const& line : _dMacro2MacroFlow) {
        for (unsigned int i = 0; i < line.size() - 1; ++i) {
            fw << line.at(i) << ",";
        }
        fw << line.back() << std::endl;
    }
    fw.close();
}
