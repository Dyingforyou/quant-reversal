# 策略定义

核心结构升级为“2板以上首次断板反包母策略”。Research 模式默认保存2～10板首次断板样本，不因高度提前丢弃；Signal Day 先识别高度和市场地位，再路由至 `LowHeightReversal`（2～3板）、`MidHeightReversal`（4～5板）或 `HighLeaderReversal`（6板以上）。三组权重均为待验证假设，不预设高板更好或低板更安全。

模型路由发生在研究入池之后：`BoardHeight Detection → Strategy Router → Low/Mid/High Reversal Model → 后续评分`。低位模型保留较高 MA5 权重，中位模型降低 MA5 权重，高标模型仅将 MA5 作为辅助，并提高高度地位、换手和市场情绪权重。

日线可可靠计算周期、高度、断板质量、成交额和换手代理。首次/最后封板时间、炸板次数、封板持续时长、封单金额等盘口字段，在未接入相应历史数据源时必须为 `NO_DATA`，不得用日线反推或填充模拟值。
