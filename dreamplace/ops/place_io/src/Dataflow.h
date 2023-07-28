#pragma once

#include <cassert>

#include "Macro.h"
#include "Net.h"
#include "Node.h"
#include "Pin.h"
#include "PlaceDB.h"

DREAMPLACE_BEGIN_NAMESPACE

// TODO! dNode 采用 const& 还是复制？

class dDataflowCaler;
struct dPathNode;

class dNode {
  private:
    Node const& _node;
    PlaceDB const& _db;
    bool _isMacro;

  public:
    dNode(Node const& _node, PlaceDB const& _db) : _node(_node), _db(_db), _isMacro(false) {}
    ~dNode() {}
    unsigned int id() const { return _node.id(); }
    bool is_Macro() const { return _isMacro; }
    void setMacro(bool _isMacro) { this->_isMacro = _isMacro; }
    bool operator<(dNode const& rhs) const { return this->id() < rhs.id(); }

    std::vector<dPathNode> getNeighbors(dDataflowCaler const& cdf) const;
};

class dPathNode {
  private:
    dNode const* _startNode;
    dNode const* _endNode;
    Net const* _net;
    Pin const* _startPin;
    Pin const* _endPin;

  public:
    dPathNode(dNode const* _startNode,
              dNode const* _endNode,
              Net const* _net,
              Pin const* _startPin,
              Pin const* _endPin)
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
    bool is_end() const {
        // 路径终止点，只有 _startNode 存储了路径起始点 dNode
        return _startNode != nullptr && _endNode == nullptr;
    }
    Net const* net() const {  // TODO! 修改警告方式
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
    PlaceDB const& _db;
    std::vector<dNode> _dNodeList;
    std::vector<dPath> _allMacro2MacroPath;
    dDataflow _dMacro2MacroFlow;
    unsigned int _depthMax;
    unsigned int _numMacro;

  public:
    dDataflowCaler(PlaceDB const& _db, unsigned int depth) : _db(_db), _depthMax(depth) {}
    ~dDataflowCaler() {}
    dNode const& node(unsigned int id) const { return _dNodeList.at(id); }
    unsigned int getNumMacro() const { return _numMacro; }
    dDataflow const& getdMacro2MacroFlow() const { return _dMacro2MacroFlow; }
    dDataflow getdMacro2MacroFlow() { return _dMacro2MacroFlow; }

    // void trans();    // TODO! 将 dDataflow 转换为 dMacroMatrix
    void dNodeInit();
    void computeMacro2MacroPath();
    void computeMacro2MacroDataflow();
    void compute();  // TODO! 修改返回值类型

  private:
    std::vector<dPath> DFS(std::vector<dPathNode>& s);  // TODO! 存储 dNode 还是 dNode const& ?
};

DREAMPLACE_END_NAMESPACE
