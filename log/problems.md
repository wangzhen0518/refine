# 问题

1. PlaceDB 中的 m_vMacro 并不是实际的 macro，至少在 ispd2005 数据集上，m_vMacro 是全部元件的数组。
2. PlaceDB 中并没有在 m_vNode 或 m_vNodeProperty 中记录 Node 是否是 Fixed, 单独有一个数组 m_vFixedNodeIndex 记录了所有 Fixed Node 的 index。

# 解决

1. 需要自行构建 Macro 的数组和 Node 的数组及数据结构。
2. Pin 中的 m_direct 记录了 Pin 是 Input/Output，后续如果需要构建有向图可以利用。

# TODO

1. 自定义 Node 数据结构 dNode, 与 Node 进行区分
2. 生成 Macro 和 Node 的数组
3. 编写 FindNeighbor 函数，实现 node-pin-net-pin-node 过程，获取当前 node 的所有邻居
4. 实现 DFS 和计算数据流的入口 computeDataflow
