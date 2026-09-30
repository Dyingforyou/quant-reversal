#!/usr/bin/env bash
set -euo pipefail

project_dir="/home/admin/quant-reversal"
target_date="2026-08-18"
phase="${1:?需要阶段：prepare、auction、minute 或 archive}"
data_dir="$project_dir/data/normalized"
log_file="$data_dir/live_${target_date//-/}.log"

mkdir -p "$data_dir"
cd "$project_dir"
set -a
source "$project_dir/.env"
set +a

run() {
    "$project_dir/.venv/bin/quant-reversal" "$@" >>"$log_file" 2>&1
}

case "$phase" in
    prepare)
        [[ "$(date +%F)" == "2026-08-17" ]] || exit 0
        exec 9>"$data_dir/prepare.lock"
        flock -n 9 || exit 0
        run data prepare-pool --date "$target_date" --output "$data_dir"
        ;;
    auction)
        [[ "$(date +%F)" == "$target_date" ]] || exit 0
        exec 9>"$data_dir/live.lock"
        flock -n 9 || exit 0
        run data collect-auction --date "$target_date" --output "$data_dir"
        run data publish-dashboard --date "$target_date" --output "$data_dir" --public /var/www/html/quant-reversal/data
        ;;
    minute)
        [[ "$(date +%F)" == "$target_date" ]] || exit 0
        exec 9>"$data_dir/live.lock"
        flock -n 9 || exit 0
        run data collect-live-minute --date "$target_date" --output "$data_dir"
        run data publish-dashboard --date "$target_date" --output "$data_dir" --public /var/www/html/quant-reversal/data
        ;;
    archive)
        [[ "$(date +%F)" == "$target_date" ]] || exit 0
        exec 9>"$data_dir/live.lock"
        flock -n 9 || exit 0
        if ! run data collect-live-minute --date "$target_date" --output "$data_dir"; then
            echo "收盘分钟补齐失败，保留错误日志并继续验证已落库的真实日线" >>"$log_file"
        fi
        run data publish-dashboard --date "$target_date" --output "$data_dir" --public /var/www/html/quant-reversal/data
        "$project_dir/.venv/bin/python" "$project_dir/scripts/purge_synthetic_after_real.py" >>"$log_file" 2>&1
        cd "$project_dir/frontend"
        npm run build >>"$log_file" 2>&1
        cp -a "$project_dir/frontend/dist/." /var/www/html/quant-reversal/
        ;;
    *)
        echo "未知阶段：$phase" >&2
        exit 2
        ;;
esac
