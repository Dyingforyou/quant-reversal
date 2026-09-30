"""A-share symbol conversions used by external provider adapters."""


def plain_symbol(value: str) -> str:
    return str(value).split(".", 1)[0].zfill(6)


def tushare_symbol(value: str) -> str:
    symbol = plain_symbol(value)
    suffix = "SH" if symbol.startswith(("5", "6", "9")) else "BJ" if symbol.startswith(("4", "8")) else "SZ"
    return f"{symbol}.{suffix}"
