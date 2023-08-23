## July 26 Wed, 2023

00:14

1. 在 DreamPlace 中添加一个模块`mytest.cpp`，运行该模块即可得到解析文件后的 PlaceDB，跳过 python 的接口部分，方便后续调试。通过对该模块进行调试即可读取 PlaceDB 运行时的信息，从而理解 PlaceDB 数据结构，用于编写计算数据流的代码。
2. 过程中解决了各种库和头文件的链接问题，修改了原有的 CMakeList.txt，用于生成新添加模块的可执行文件。
3. 目前新加模块已经可以正常运行，并通过断点调试读出 PlaceDB 的运行时信息。

## July 28 Fri, 2023

00:06

1. 构建自己的数据结构，命名中均以`d`开头，表示 dataflow 的含义。
2. 构建`dNode`，包含`isMacro`用于判断是 cell 还是 macro。
3. 构建`dPathNode`，用于记录路径上的节点信息，包含一条边的起始节点、终止节点、起始引脚、终止引脚、所使用的 net。
4. 构建`dPath`，记录路径。
5. 构建`dDataflowCaler`，代表计算数据流的功能，`dNodeInit`从 PlaceDB 中初始化所有`dNode`，`DFS`根据深度优先遍历，计算从一个宏出发，到其他宏的路径，`computeMacro2MacroPath`是计算路径的入口，`computeMacro2MacroDataflow`根据计算出的路径，统计 macro 两两之间的数据流的值，`compute`是计算数据流的总入口，将以上函数进行了组合。

## August 22 Tue, 2023

23:22

TODO:

1. ispd 2005 和 ispd 2015 判断节点是否是 macro 的方式不同，需要修改。
2. 是否可以根据 node 名称中是否存在 reg 判断 node 是否是寄存器？ 待确认
3. m_vNode 中是否包含 m_vMacro 中的点
4. m_vMacro 的引脚如何处理
