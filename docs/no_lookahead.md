# 无未来函数

- 09:25 候选管线会物理删除 Signal Day 日线。
- 所有滚动基线先 `shift(1)`，当前观测不进入自身基线。
- 分钟 t 触发，订单的 `earliest_fill_at` 是 t+1。
- Broker 拒绝 entry_date 当日卖出。
- 研究标签位于 `research/labels.py`，策略模块不导入它。
- 板块成员按 `effective_from/effective_to` 查询。

