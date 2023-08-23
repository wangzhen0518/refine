#pragma once

#include <vector>

#include "Net.h"
#include "Node.h"
#include "Pin.h"
#include "PlaceDB.h"

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