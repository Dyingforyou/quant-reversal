#!/usr/bin/env bash
set -euo pipefail

project_dir="/home/admin/quant-reversal"
data_dir="$project_dir/data/normalized"
public_dir="/var/www/html/quant-reversal/data"
phase="${1:?需要阶段：prepare、auction、opening、minute、manage 或 archive}"
today="$(date +%F)"
log_file="$data_dir/live_${today//-/}.log"

mkdir -p "$data_dir" "$public_dir"
cd "$project_dir"
set -a
source "$project_dir/.env"
set +a
# Public quote endpoints are more reliable when they bypass the host's optional proxy.
export NO_PROXY="${NO_PROXY:-},.eastmoney.com,.gtimg.cn,.sina.com.cn"
export no_proxy="$NO_PROXY"

run() { "$project_dir/.venv/bin/quant-reversal" "$@" >>"$log_file" 2>&1; }
pool_date() { [[ -f "$data_dir/current_pool_date.txt" ]] && tr -d '[:space:]' <"$data_dir/current_pool_date.txt"; }
require_today_pool() {
    local target
    target="$(pool_date)"
    [[ "$target" == "$today" ]] || { echo "$(date -Is) 今日股票池未就绪，记录日期=$target" >>"$log_file"; exit 1; }
}
publish() { run data publish-dashboard --date "$today" --output "$data_dir" --public "$public_dir"; }

exec 9>"$data_dir/${phase}.lock"
flock -n 9 || exit 0
# Serialize Parquet upserts/publication across phases. Opening capture has its
# own immutable dataset and must not miss 09:35 behind a minute request.
if [[ "$phase" != "opening" ]]; then
    exec 8>"$data_dir/runtime.lock"
    flock -w 45 8 || exit 0
fi
if ! "$project_dir/.venv/bin/quant-reversal" data is-trading-day --date "$today" --output "$data_dir"; then
    echo "$(date -Is) 交易日历未确认开市，跳过 $phase" >>"$log_file"
    exit 0
fi
paper() { run paper run --date "$today" --config configs/real.yaml; }

case "$phase" in
    prepare)
        run data collect-reference --date "$today" --output "$data_dir" || echo "$(date -Is) 参考数据暂缺，将在竞价阶段重试" >>"$log_file"
        run data prepare-next-pool --date "$today" --output "$data_dir"
        target="$(pool_date)"
        run data publish-dashboard --date "$target" --output "$data_dir" --public "$public_dir"
        ;;
    auction)
        require_today_pool
        run data collect-reference --date "$today" --output "$data_dir" || echo "$(date -Is) 参考数据失败，模拟账户将显示阻断原因" >>"$log_file"
        if ! run data collect-market-auction --date "$today" --output "$data_dir"; then
            echo "$(date -Is) 全市场竞价基线采集失败，继续采集候选股竞价" >>"$log_file"
        fi
        run data collect-auction --date "$today" --output "$data_dir"
        paper
        publish
        ;;
    minute)
        require_today_pool
        run data collect-live-minute --date "$today" --output "$data_dir"
        paper
        publish
        ;;
    opening)
        run data collect-opening --date "$today" --output "$data_dir"
        ;;
    manage)
        if "$project_dir/.venv/bin/python" -c 'from pathlib import Path; from quant_reversal.paper import positions; import sys; sys.exit(0 if positions(Path("data/normalized")) else 1)'; then
            run data collect-live-minute --date "$today" --output "$data_dir"
            paper
            publish
        fi
        ;;
    archive)
        require_today_pool
        run data collect-live-minute --date "$today" --output "$data_dir" || true
        paper
        publish
        "$project_dir/.venv/bin/python" "$project_dir/scripts/purge_synthetic_after_real.py" >>"$log_file" 2>&1
        ;;
    *) echo "未知阶段：$phase" >&2; exit 2 ;;
esac
