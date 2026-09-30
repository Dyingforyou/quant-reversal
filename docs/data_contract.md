# 数据契约

## 高度母策略特征

研究池默认保存所有2～10板首次断板样本。核心字段包括 `board_count`、`height_group`、`height_rank`、`is_market_highest`、`same_height_count`、`prev_market_highest_board`、`sub_strategy`、`cycle_start_date`、`cycle_board_high`、`break_count_in_cycle` 和 `is_first_break`。

断板与筹码字段包括 `break_quality`、`break_max_drawdown`、`break_close_position`、`tail_support`、`turnover_rate`、`amount`、`amount_ratio20_mean`、`break_amount_ratio20`、`is_historical_record_amount`、`one_price_boards_in_cycle`、`turnover_boards_in_cycle` 和 `board_type`。

市场情绪字段包括 `market_highest_board`、`market_advancement_rate`、`high_stock_next_day_premium`、`market_bust_rate`、`market_limit_down_count`、`market_board_stock_avg_return` 和 `previous_leader_today_return`。

`first_limit_time`、`last_limit_time`、`limit_break_count`、`sealed_duration_minutes`、`sealed_order_amount`、`sealed_order_to_float_cap` 和 `tail_support` 需要历史分钟、逐笔或盘口数据。来源缺失时值必须为空并标记 `NO_DATA`，禁止伪造。

`data_dir` 下使用 `daily_bars.parquet`、`auction.parquet`、`minute_bars.parquet`、`sector_membership.parquet`、`trading_calendar.parquet`。字段定义以项目规格书第 5 节为准。`limit_up_price` 与 `limit_down_price` 必须由标准化层提供，策略不猜测板块涨跌幅。
