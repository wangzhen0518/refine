#include <cassert>
#include <cmath>

#include "Dataflow.h"

DREAMPLACE_BEGIN_NAMESPACE

bool is_inPath(std::vector<dPathNode> const& nodeList, dNode const& node) {
    for (dPathNode const& n : nodeList) {
        if (n.endNode()->id() == node.id()) {
            return true;
        }
    }
    return false;
}

std::vector<dPathNode> dNode::getNeighbors(dDataflowCaler const& cdf) const {
    std::vector<dPathNode> neighbors;
    for (auto nodePinId : _node.pins()) {
        Pin const& nodePin = _db.pin(nodePinId);
        Net const& net = _db.net(nodePin.netId());
        for (auto netPinId : net.pins()) {
            Pin const& netPin = _db.pin(netPinId);
            dNode const& neighborNode = cdf.node(netPin.nodeId());
            if (neighborNode.id() != _node.id()) {
                dPathNode pn = dPathNode(this, &neighborNode, &net, &nodePin, &netPin);
                neighbors.push_back(pn);
            }
        }
    }
    return neighbors;
}

void dDataflowCaler::dNodeInit() {
    for (auto const& node : _db.nodes()) {
        _dNodeList.push_back(dNode(node, _db));
    }
    for (auto fixedId : _db.fixedNodeIndices()) {
        _dNodeList.at(fixedId).setMacro(true);
    }
    _numMacro = _db.numFixed();
}

void dDataflowCaler::compute() {
    // 初始化所有 dNode，关键在于初始化 _isMacro
    if (_dNodeList.empty()) {
        dNodeInit();
    }
    computeMacro2MacroPath();
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
    assert(!_dNodeList.empty());
    for (dNode const& node : _dNodeList) {
        if (node.is_Macro()) {
            std::vector<dPathNode> s;
            dPathNode startNode(nullptr, &node, nullptr, nullptr, nullptr);
            s.push_back(startNode);
            std::vector<dPath> nodePaths = DFS(s);
            _allMacro2MacroPath.insert(_allMacro2MacroPath.end(), nodePaths.begin(), nodePaths.end());
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

std::vector<dPath> dDataflowCaler::DFS(std::vector<dPathNode>& s) {
    std::vector<dPath> dPathList;
    if (!s.empty() && s.size() < _depthMax + 1) {
        // size=1 时，只有路径起始的 macro，所以不应该发生 s.empty() 的情况
        dPathNode n = s.back();
        dNode const& boundary = *n.endNode();
        for (dPathNode neighborNode : boundary.getNeighbors(*this)) {
            dNode const& next = *neighborNode.endNode();
            if (is_inPath(s, next)) {
                continue;  // 跳过该 node
            } else if (next.is_Macro()) {
                dPath newPath(s);
                newPath.add(neighborNode);
                dPathList.push_back(newPath);
            } else {
                s.push_back(neighborNode);
                std::vector<dPath> nodePaths = DFS(s);
                dPathList.insert(dPathList.end(), nodePaths.begin(), nodePaths.end());
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
        _dMacro2MacroFlow.at(start.id()).at(end.id()) += powf64(0.5, k);
    }
}

DREAMPLACE_END_NAMESPACE
