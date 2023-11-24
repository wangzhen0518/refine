#pragma once

#include <cassert>
#include <iomanip>
#include <iostream>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "Net.h"
#include "Node.h"
#include "Pin.h"
#include "PlaceDB.h"

#define RED "\e[1;31m"
#define YELLOW "\e[1;33m"
#define BLUE "\e[1;34m"
#define BLACK_BACK "\e[1;40m"   // 黑色背景
#define RED_BACK "\e[1;41m"     // 红色背景
#define GREEN_BACK "\e[1;42m"   // 绿色背景
#define YELLOW_BACK "\e[1;43m"  // 棕色背景
#define BLUE_BACK "\e[1;44m"    // 蓝色背景
#define ARED_BACK "\e[1;45m"    // 品红背景
#define ABLUE_BACK "\e[1;46m"   // 孔雀蓝背景
#define WHITE_BACK "\e[1;47m"   // 白色背景
#define COLOR_END "\e[0m"

// using namespace DreamPlace;

// TODO! dNode 采用 const& 还是复制？
// 目前采用 const&，因为 dPathNode 中使用了指针用于判断路径节点类型，如果 dNode
// 采用复制，那么指针就会失效

class dPlaceDB : public DreamPlace::PlaceDB {
  public:
    /// add node to m_vNode and m_mNodeName2Index
    /// \param n denotes name
    /// \return index in m_vNode and successful flag
    std::pair<index_type, bool> addNode(std::string const& n) {
        return DreamPlace::PlaceDB::addNode(n);
    }

    /// add node to m_vMacro and m_mMacroName2Index
    /// \param n denotes name
    /// \return index in m_vMacro and successful flag
    std::pair<index_type, bool> addMacro(std::string const& n) {
        return DreamPlace::PlaceDB::addMacro(n);
    }

    /// add net to m_vNet and m_mNetName2Index
    /// \param n denotes name
    /// \return index in m_vNet and successful flag
    std::pair<index_type, bool> addNet(std::string const& n) {
        return DreamPlace::PlaceDB::addNet(n);
    }

    /// add pin to m_vPin, node and net
    /// \param pinName denotes name of corresponding macro pin
    /// \param net and \param node are corresponding net and node
    void addPin(std::string const& macroPinName,
                DreamPlace::Net& net,
                DreamPlace::Node& node,
                std::string instName = "") {
        return DreamPlace::PlaceDB::addPin(macroPinName, net, node, instName);
    }
    void addPin(index_type macroPinId,
                DreamPlace::Net& net,
                DreamPlace::Node& node,
                std::string pinName) {
        return DreamPlace::PlaceDB::addPin(macroPinId, net, node, pinName);
    }

    /// lower level helper to addPin()
    DreamPlace::Pin& createPin(DreamPlace::Net& net,
                               DreamPlace::Node& node,
                               DreamPlace::SignalDirect const& direct,
                               DreamPlace::Point<coordinate_type> const& offset,
                               index_type macroPinId,
                               std::string pinName = "") {
        return DreamPlace::PlaceDB::createPin(net, node, direct, offset, macroPinId, pinName);
    }

    /// add region to m_vRegion
    /// \param r region name
    /// \return index in m_vRegion and successful flag
    std::pair<index_type, bool> addRegion(std::string const& r) {
        return DreamPlace::PlaceDB::addRegion(r);
    }

    /// collect nodes for groups and summarize the statistics for fence region
    void processGroups() { return DreamPlace::PlaceDB::processGroups(); }

    void setFixedNode(std::vector<index_type> fixedNodeIndex) {
        m_vFixedNodeIndex = fixedNodeIndex;
        m_numFixed = m_vFixedNodeIndex.size();
    }

    // bool read(int argc, char** argv) { return this->userParam().read(argc, argv); }
};

class dDataflowCaler;
struct dPathNode;

enum class dNodeType { Macro, Register, IOPin, Other };

class dNode {
  private:
    std::string _name;
    dNodeType _type;
    std::vector<unsigned int> _pinIdList;
    // _xxx_id_ori 根据初始化决定
    // _xxx_id 在全部 dNode 初始化结束后，再遍历dDataflowCaler中的_dNodeList进行修改
    unsigned int _node_id;
    unsigned int _macro_id;      // dDataflowCaler 中的 macro id
    unsigned int _macro_id_ori;  // PlaceDB 中的 macro id
    DreamPlace::Node const* _node;
    DreamPlace::Macro const* _macro;
    dPlaceDB const& _db;

  public:
    dNode(DreamPlace::Node const& node, std::string const& name, dPlaceDB const& db) : _db(db) {
        _node = &node;
        _name = name;
        _node_id = _db.nodeName2Index().at(name);
        _pinIdList = node.pins();
        if (_db.macros().size() >= _db.nodes().size()) {  // ispd2005
            _type = dNodeType::Register;
            _macro = nullptr;
            _macro_id = _macro_id_ori = 0;
        } else {
            _macro_id = _macro_id_ori = _db.nodeProperty(*_node).macroId();
            _macro = &_db.macro(_macro_id_ori);
            if (_macro->className().find("BLOCK") != std::string::npos) {
                _type = dNodeType::Macro;
            } else if (_macro->className().find("IOPin") != std::string::npos) {
                _type = dNodeType::IOPin;
            } else {  // 是 cell
                _type = dNodeType::Other;
                for (unsigned int p_id : _node->pins()) {
                    DreamPlace::Pin const& p = _db.pin(p_id);
                    if (p.name().find("clk") != std::string::npos) {
                        _type = dNodeType::Register;
                        break;
                    }
                }
            }
        }
    }
    dNode(DreamPlace::Macro const& macro, dPlaceDB const& db) : _db(db) {
        assert("Abandoned");

        _name = macro.name();
        _macro = &macro;
        _macro_id = _macro_id_ori = _db.macroName2Index().at(_name);
        if (_name.find("IOPin") != std::string::npos) {
            _type = dNodeType::IOPin;
        } else {
            _type = dNodeType::Macro;
        }
        if (_db.nodeName2Index().count(_name) > 0) {  // macro 存在对应的 node
            _node_id = _db.nodeName2Index().at(_name);
            _node = &_db.node(_node_id);
            _pinIdList = _node->pins();
        } else {
            _node_id = 0;
            _node = nullptr;
            _pinIdList.clear();  // TODO 如何处理macro 的 pin
        }
    }

    std::string const& name() const { return _name; }
    // std::string name() const { return _name; }

    /**
     * @brief 获取 dNode 在 db.m_vNode 中的索引
     * @return unsigned int
     */
    unsigned int node_id() const { return _node_id; }

    /**
     * @brief 获取 macro 在 db.m_vMacro 中的索引
     * @return unsigned int
     */
    unsigned int macro_id_ori() const {
        assert(_type == dNodeType::Macro || _type == dNodeType::IOPin);
        return _macro_id_ori;
    }

    /**
     * @brief 获取 macro 在 dDataflowCaler 中的索引
     * @return unsigned int
     */
    unsigned int macro_id() const {
        assert(_type == dNodeType::Macro || _type == dNodeType::IOPin);
        return _macro_id;
    }

    void setMacro(unsigned int _id) {
        _type = dNodeType::Macro;
        _macro_id = _id;
        _macro = &_db.macro(_id);
    }
    void setMacroId(unsigned int _id) { _macro_id = _id; }
    void setNodeId(unsigned int _id) { _node_id = _id; }
    bool is_Macro() const { return _type == dNodeType::Macro; }
    bool is_Register() const { return _type == dNodeType::Register; }
    bool is_IOPin() const { return _type == dNodeType::IOPin; }
    dNodeType type() const { return _type; }
    void print_node(unsigned int width = 2) const {
        switch (_type) {
            case dNodeType::Macro:
                std::cout << GREEN_BACK << RED << "Macro(" << std::setw(width) << this->macro_id()
                          << ")" << COLOR_END;
                break;
            case dNodeType::IOPin:
                std::cout << ABLUE_BACK << RED << "IOPin(" << std::setw(width) << this->macro_id()
                          << ")" << COLOR_END;
                break;
            case dNodeType::Register:
                std::cout << WHITE_BACK << RED << "Register(" << std::setw(width) << this->node_id()
                          << ")" << COLOR_END;
                break;
            case dNodeType::Other:
            default:
                std::cout << RED << "Node(" << std::setw(width) << this->node_id() << ")"
                          << COLOR_END;
                break;
        }
    }

    // bool operator<(dNode const& rhs) const { return this->id() < rhs.id(); }

  public:
    std::vector<dPathNode> getNeighbors(dDataflowCaler const& cdf) const;
};

class dPathNode {
  private:
    dNode const* _startNode;
    dNode const* _endNode;
    DreamPlace::Net const* _net;
    DreamPlace::Pin const* _startPin;
    DreamPlace::Pin const* _endPin;

  public:
    dPathNode(dNode const* _startNode,
              dNode const* _endNode,
              DreamPlace::Net const* _net,
              DreamPlace::Pin const* _startPin,
              DreamPlace::Pin const* _endPin)
        : _startNode(_startNode),
          _endNode(_endNode),
          _net(_net),
          _startPin(_startPin),
          _endPin(_endPin) {}
    ~dPathNode() {}
    bool is_start() const {
        // 路径起始点，只有 _endNode 存储了路径起始点 dNode
        return _startNode == nullptr && _endNode != nullptr;
    }
    bool is_end() const {  //! 无效，终止点没有单独存储
        // 路径终止点，只有 _startNode 存储了路径起始点 dNode
        return _startNode != nullptr && _endNode == nullptr;
    }
    DreamPlace::Net const* net() const {  // TODO! 修改警告方式
        assert(_net != nullptr);
        return _net;
    }
    dNode const* startNode() const {
        assert(_startNode != nullptr);
        return _startNode;
    }
    dNode const* endNode() const {
        assert(_endNode != nullptr);
        return _endNode;
    }
    DreamPlace::Pin const* startPin() const {
        assert(_startPin != nullptr);
        return _startPin;
    }
    DreamPlace::Pin const* endPin() const {
        assert(_endPin != nullptr);
        return _endPin;
    }
};

class dPath {
  private:
    std::vector<dPathNode> _dPathNodeList;  // TODO! 存储 dNode 还是 dNode const& ?
    unsigned int _depth;
    std::vector<unsigned int> _register_idx;

  public:
    dPath(std::vector<dPathNode> _dPathNodeList) {
        this->_dPathNodeList = _dPathNodeList;
        this->_depth = 0;
        for (unsigned int i = 0; i < this->_dPathNodeList.size(); i++) {
            if (this->_dPathNodeList[i].endNode()->is_Register()) {
                _depth++;
                _register_idx.push_back(i);
            }
        }
    }
    ~dPath() {}
    void add(dPathNode n) {
        if (n.endNode()->is_Register()) {
            _depth++;
            _register_idx.push_back(_dPathNodeList.size());
        }
        _dPathNodeList.push_back(n);
    }
    std::vector<dPathNode> const& get() const { return _dPathNodeList; }
    unsigned int length() const {
        return _depth + 2;  // +2 是考虑到两端的 macro
    }
    dNode const& startNode() const {
        assert(!_dPathNodeList.empty());
        return *_dPathNodeList.front().endNode();
    }
    dNode const& endNode() const {
        assert(!_dPathNodeList.empty());
        return *_dPathNodeList.back().endNode();
    }

  public:
    void printPath() const;
};

class dStack {
  private:
    std::vector<dPathNode> _stack;
    std::unordered_set<unsigned int> _node_set;
    std::unordered_set<unsigned int> _net_set;
    std::unordered_set<unsigned int> _pin_set;
    unsigned int _depth;

  public:
    void init(dNode const& node) {
        _stack.clear();
        _node_set.clear();
        _net_set.clear();
        _pin_set.clear();
        _depth = 0;
        dPathNode startNode(nullptr, &node, nullptr, nullptr, nullptr);
        _stack.push_back(startNode);
        _node_set.insert(node.node_id());
    }
    dStack() : _depth(0) {}
    dStack(dNode const& node) { this->init(node); }
    ~dStack() {}
    void push(dPathNode n) {
        _stack.push_back(n);
        _node_set.insert(n.endNode()->node_id());
        assert(n.net() != nullptr);
        assert(n.startPin() != nullptr);
        assert(n.endPin() != nullptr);
        _net_set.insert(n.net()->id());
        _pin_set.insert(n.startPin()->id());
        _pin_set.insert(n.endPin()->id());

        if (n.endNode()->is_Register()) {
            _depth++;
        }
    }
    void pop() {
        dPathNode n = _stack.back();
        _stack.pop_back();
        _node_set.erase(n.endNode()->node_id());
        assert(n.net() != nullptr);
        assert(n.startPin() != nullptr);
        assert(n.endPin() != nullptr);
        _net_set.erase(n.net()->id());
        _pin_set.erase(n.startPin()->id());
        _pin_set.erase(n.endPin()->id());

        if (n.endNode()->is_Register()) {
            _depth--;
        }
    }
    bool empty() const { return _stack.empty(); }
    unsigned int depth() const { return _depth; }
    std::vector<dPathNode> const& getPath() const { return _stack; }
    dPathNode const& back() const {
        assert(!_stack.empty());
        return _stack.back();
    }
    /**
     * @brief 判断 node 是否在路径中
     * @param node
     * @return 0 不在路径中，1 路径中有重复 node，2 路径中有重复 net，3 路径中有重复 pin
     */
    unsigned int is_inPath(dPathNode const& node) {
        if (_node_set.find(node.endNode()->node_id()) != _node_set.end()) {
            return 1;
        } else if (_net_set.find(node.net()->id()) != _net_set.end()) {
            return 2;
        } else if (_pin_set.find(node.startPin()->id()) != _pin_set.end() ||
                   _pin_set.find(node.endPin()->id()) != _pin_set.end()) {
            return 3;
        } else
            return 0;
    }
};

typedef std::vector<std::vector<double>> dDataflow;
// typedef std::unordered_map<std::string, std::unordered_map<std::string, double>> dDataflow;
class dDataflowCaler {
  private:
    dPlaceDB const& _db;
    std::vector<dNode> _dNodeList;
    std::vector<dPath> _allMacro2MacroPath;
    dDataflow _dMacro2MacroFlow;
    unsigned int _depthMax;
    unsigned int _numMacro;
    unsigned int _numRegister;
    unsigned int _numIOPin;

  public:
    void dNodeInit();
    void computeMacro2MacroPath();
    void computeMacro2MacroDataflow();
    void compute();  // TODO! 修改返回值类型
    void printMacro2MacroFlow() const;
    void printMacro2MacroPath() const;
    void writeMacro2MacroFlow(std::string const& filename) const;

  public:
    dDataflowCaler(dPlaceDB const& _db, unsigned int depth) : _db(_db), _depthMax(depth) {
        dNodeInit();
    }
    ~dDataflowCaler() {}
    dNode const& node(unsigned int id) const { return _dNodeList.at(id); }
    unsigned int getNumMacro() const { return _numMacro; }
    dDataflow const& getdMacro2MacroFlow() const { return _dMacro2MacroFlow; }
    dDataflow getdMacro2MacroFlow() { return _dMacro2MacroFlow; }

  private:
    std::vector<dPath> DFS(dStack& s);  // TODO! 存储 dNode 还是 dNode const& ?
};
