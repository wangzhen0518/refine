#ifndef DREAMPLACE_DATAFLOW_TMP_H
#define DREAMPLACE_DATAFLOW_TMP_H

#include <vector>
#include <unordered_set>

#include "Macro.h"
#include "Pin.h"
#include "Net.h"
#include "PlaceDB.h"

DREAMPLACE_BEGIN_NAMESPACE

class Dataflow {
  private:
    std::vector<std::unordered_set<std::pair<Macro const&, double>>> m_vMacroFlow;
};

class Path {
  public:
    Path(Macro const& macroStart, Macro const& macroEnd, std::vector<Node const&> const& path)
        : m_macroStart(macroStart), m_macroEnd(macroEnd), m_path(path) {}
    Macro const& macroStart() const { return m_macroStart; }
    Macro const& macroEnd() const { return m_macroEnd; }
    std::vector<Node const&> const& path() const { return m_path; }

  private:
    Macro const& m_macroStart;
    Macro const& m_macroEnd;
    std::vector<Node const&> m_path;
};

DREAMPLACE_END_NAMESPACE

#endif
