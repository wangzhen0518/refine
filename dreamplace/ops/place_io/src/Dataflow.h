#pragma once

#include <cassert>
#include <unordered_set>

#include "Net.h"
#include "Node.h"
#include "Pin.h"
#include "PlaceDB.h"

// using namespace DreamPlace;

// TODO! dNode 采用 const& 还是复制？
// 目前采用 const&，因为 dPathNode 中使用了指针用于判断路径节点类型，如果 dNode
// 采用复制，那么指针就会失效

class dDataflowCaler;
struct dPathNode;

class dNode {
  private:
    DreamPlace::Node const& _node;
    DreamPlace::PlaceDB const& _db;
    bool _is_Macro;
    bool _is_Register;  // TODO! 待初始化
    unsigned int _macro_id;

  public:
    dNode(DreamPlace::Node const& _node, DreamPlace::PlaceDB const& _db)
        : _node(_node), _db(_db), _is_Macro(false), _is_Register(true) {}
    ~dNode() {}
    unsigned int id() const { return _node.id(); }
    unsigned int macro_id() const {
        assert(_is_Macro);
        return _macro_id;
    }
    bool is_Macro() const { return _is_Macro; }
    bool is_Register() const { return _is_Register; }
    void setMacro(bool _is_Macro, unsigned int _id) {
        this->_is_Macro = _is_Macro;
        if (_is_Macro) {
            this->_macro_id = _id;
            this->_is_Register = false;
        }
    }
    void setRegister(bool _is_Register) { this->_is_Register = _is_Register; }
    bool operator<(dNode const& rhs) const { return this->id() < rhs.id(); }

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
        for (unsigned int i = 1; i < this->_dPathNodeList.size() - 1; i++) {
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
    unsigned int length() const { return _dPathNodeList.size(); }
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
        _node_set.insert(node.id());
    }
    dStack() : _depth(0) {}
    dStack(dNode const& node) { this->init(node); }
    ~dStack() {}
    void push(dPathNode n) {
        _stack.push_back(n);
        _node_set.insert(n.endNode()->id());
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
        _node_set.erase(n.endNode()->id());
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
    unsigned int is_inPath(dPathNode const& node) {
        // 0 不在路径中
        // 1 路径中有重复 node
        // 2 路径中有重复 net
        // 3 路径中有重复 pin
        if (_node_set.find(node.endNode()->id()) != _node_set.end()) {
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
class dDataflowCaler {
  private:
    DreamPlace::PlaceDB const& _db;
    std::vector<dNode> _dNodeList;
    std::vector<dPath> _allMacro2MacroPath;
    dDataflow _dMacro2MacroFlow;
    unsigned int _depthMax;
    unsigned int _numMacro;

  public:
    dDataflowCaler(DreamPlace::PlaceDB const& _db, unsigned int depth)
        : _db(_db), _depthMax(depth) {}
    ~dDataflowCaler() {}
    dNode const& node(unsigned int id) const { return _dNodeList.at(id); }
    unsigned int getNumMacro() const { return _numMacro; }
    dDataflow const& getdMacro2MacroFlow() const { return _dMacro2MacroFlow; }
    dDataflow getdMacro2MacroFlow() { return _dMacro2MacroFlow; }

  public:
    void dNodeInit();
    void computeMacro2MacroPath();
    void computeMacro2MacroDataflow();
    void compute();  // TODO! 修改返回值类型
    void printMacro2MacroFlow() const;
    void printMacro2MacroPath() const;
    void writeMacro2MacroFlow(std::string const& filename) const;

  private:
    std::vector<dPath> DFS(dStack& s);  // TODO! 存储 dNode 还是 dNode const& ?
};
