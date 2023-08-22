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
    bool _isMacro;
    bool _isRegister;  // TODO! 待初始化
    unsigned int _macro_id;

  public:
    dNode(DreamPlace::Node const& _node, DreamPlace::PlaceDB const& _db)
        : _node(_node), _db(_db), _isMacro(false) {}
    ~dNode() {}
    unsigned int id() const { return _node.id(); }
    unsigned int macro_id() const {
        assert(_isMacro);
        return _macro_id;
    }
    bool is_Macro() const { return _isMacro; }
    bool is_Register() const { return _isRegister; }
    void setMacro(bool _isMacro, unsigned int _id) {
        this->_isMacro = _isMacro;
        if (_isMacro) {
            this->_macro_id = _id;
        }
    }
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

  public:
    dPath(std::vector<dPathNode> _dPathNodeList) : _dPathNodeList(_dPathNodeList) {}
    ~dPath() {}
    void add(dPathNode n) { _dPathNodeList.push_back(n); }
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

typedef std::vector<std::vector<double>> dDataflow;

// class dDataflow {
//   private:
//     std::vector<std::set<std::pair<dNode const&, double>>> dMacroFlow;

//   public:
//     dDataflow(/* args */);
//     ~dDataflow();
// };

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
    // void trans();    // TODO! 将 dDataflow 转换为 dMacroMatrix
    void dNodeInit();
    void computeMacro2MacroPath();
    void computeMacro2MacroDataflow();
    void compute();  // TODO! 修改返回值类型
    void printMacro2MacroFlow() const;
    void printMacro2MacroPath() const;
    void writeMacro2MacroFlow(std::string const& filename) const;

  private:
    std::vector<dPath> DFS(
        std::vector<dPathNode>& s,
        std::unordered_set<unsigned int>& node_set,
        std::unordered_set<unsigned int>& net_set,
        std::unordered_set<unsigned int>& pin_set);  // TODO! 存储 dNode 还是 dNode const& ?
};

