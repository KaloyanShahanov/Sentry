from fetchers import fetch_quotes, Quote
from alerts import send_discord_alert
from logger_setup import setup_logger

logger = setup_logger("sentry")

def percent_diff(buy_price: float, sell_price: float) -> float:
    return ((sell_price - buy_price) / buy_price) * 100.0

def fee_amount(eur_amount: float, fee_percent: float) -> float:
    return eur_amount * (fee_percent / 100.0)

def compute_arbitrage(buy: Quote, sell: Quote) -> dict:
    if buy.pair != sell.pair:
        raise ValueError("Pairs must match.")
    if buy.amount_base != sell.amount_base:
        raise ValueError("Amounts must match.")

    buy_gross = buy.price_quote * buy.amount_base
    sell_gross = sell.price_quote * sell.amount_base

    buy_fee = fee_amount(buy_gross, buy.fee_percent)
    sell_fee = fee_amount(sell_gross, sell.fee_percent)

    buy_total_cost = buy_gross + buy_fee
    sell_total_received = sell_gross - sell_fee

    profit_eur = sell_total_received - buy_total_cost
    profit_percent_net = (profit_eur / buy_total_cost) * 100.0

    gross_spread_eur = sell.price_quote - buy.price_quote
    gross_spread_percent = percent_diff(buy.price_quote, sell.price_quote)

    return {
        "pair": buy.pair,
        "amount_base": buy.amount_base,
        "buy_exchange": buy.exchange,
        "buy_price": buy.price_quote,
        "buy_fee_percent": buy.fee_percent,
        "buy_fee_eur": buy_fee,
        "buy_total_cost": buy_total_cost,
        "sell_exchange": sell.exchange,
        "sell_price": sell.price_quote,
        "sell_fee_percent": sell.fee_percent,
        "sell_fee_eur": sell_fee,
        "sell_total_received": sell_total_received,
        "gross_spread_eur": gross_spread_eur,
        "gross_spread_percent": gross_spread_percent,
        "profit_eur": profit_eur,
        "profit_percent_net": profit_percent_net,
    }

def should_alert(result: dict, gross_threshold_percent: float = 0.5, require_net_profit: bool = True) -> bool:
    if result["gross_spread_percent"] < gross_threshold_percent:
        return False
    if require_net_profit and result["profit_eur"] <= 0:
        return False
    return True

def format_discord_message(r: dict) -> str:
    profit_status = "NEGATIVE PROFIT" if r["profit_eur"] < 0 else "POSITIVE PROFIT"

    return (
        f"**Sentry Test Alert**\n"
        f"**Status:** {profit_status}\n"
        f"**Pair:** {r['pair']} | **Amount:** {r['amount_base']}\n\n"

        f"**{r['buy_exchange']} (paid / buy)**\n"
        f"- Price: EUR {r['buy_price']:.2f}\n"
        f"- Fee: {r['buy_fee_percent']:.4f}% = EUR {r['buy_fee_eur']:.2f}\n"
        f"- Total cost: EUR {r['buy_total_cost']:.2f}\n\n"

        f"**{r['sell_exchange']} (received / sell)**\n"
        f"- Price: EUR {r['sell_price']:.2f}\n"
        f"- Fee: {r['sell_fee_percent']:.4f}% = EUR {r['sell_fee_eur']:.2f}\n"
        f"- Total received: EUR {r['sell_total_received']:.2f}\n\n"

        f"**Gross spread:** EUR {r['gross_spread_eur']:.2f} "
        f"({r['gross_spread_percent']:.3f}%)\n"

        f"**Net result:** EUR {r['profit_eur']:.2f} "
        f"({r['profit_percent_net']:.3f}%)\n"
    )


def run_once(pair: str = "ETH/EUR", amount_base: float = 1.0, gross_threshold_percent: float = 0.02):
    logger.info(f"Starting Sentry run for pair={pair}, amount={amount_base}, threshold={gross_threshold_percent}%")

    try:
        buy_quote, sell_quote = fetch_quotes(pair, amount_base)
        result = compute_arbitrage(buy_quote, sell_quote)

        logger.info(
            f"Computed: pair={pair} gross={result['gross_spread_percent']:.3f}% "
            f"net={result['profit_percent_net']:.3f}% profit= EUR {result['profit_eur']:.2f}"
        )

        if should_alert(result, gross_threshold_percent=gross_threshold_percent, require_net_profit=True):
            logger.info(f"ALERT triggered for {pair}: gross={result['gross_spread_percent']:.3f}%")
            send_discord_alert(format_discord_message(result))
        else:
            logger.info(f"No alert for {pair} (below threshold or not profitable).")

    except Exception:
        logger.exception("Sentry run failed with exception.")

if __name__ == "__main__":
    run_once()
