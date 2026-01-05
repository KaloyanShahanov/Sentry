from dataclasses import dataclass
import requests
from logger_setup import setup_logger

logger = setup_logger("fetchers")

BITFINEX_BASE = "https://api-pub.bitfinex.com/v2"
KRAKEN_BASE = "https://api.kraken.com/0/public"

DEFAULT_FEES = {
    "Bitfinex": 0.0001,  # percent
    "Kraken": 0.0001,    # percent
}

@dataclass
class Quote:
    exchange: str
    pair: str            # "ETH/EUR"
    amount_base: float
    price_quote: float   # EUR per 1 ETH
    fee_percent: float

def _split_pair(pair: str) -> tuple[str, str]:
    base, quote = pair.upper().replace("-", "/").split("/")
    return base, quote

def fetch_bitfinex_last_price(pair: str) -> float:
    base, quote = _split_pair(pair)

    symbols_to_try = [
        f"t{base}:{quote}",  # tETH:EUR
        f"t{base}{quote}",   # tETHEUR
    ]

    last_error = None
    for symbol in symbols_to_try:
        url = f"{BITFINEX_BASE}/ticker/{symbol}"

        for attempt in range(3):
            try:
                r = requests.get(url, timeout=10)
                if r.status_code >= 500:
                    logger.warning(f"Bitfinex server error {r.status_code} (attempt {attempt+1}/3) for {symbol}")
                    last_error = RuntimeError(r.text)
                    continue

                r.raise_for_status()
                data = r.json()
                price = float(data[6])  # LAST_PRICE
                logger.info(f"Fetched Bitfinex price for {pair} ({symbol}): {price}")
                return price

            except Exception as e:
                last_error = e
                logger.warning(f"Bitfinex fetch failed (attempt {attempt+1}/3) for {pair} ({symbol}): {e}")

    logger.exception(f"Bitfinex ticker failed for {pair}.")
    raise RuntimeError(f"Bitfinex ticker failed for {pair}. Last error: {last_error}")

def fetch_kraken_last_price(pair: str) -> float:
    base, quote = _split_pair(pair)

    candidates = [
        f"{base}{quote}",     # ETHEUR
        f"X{base}Z{quote}",   # XETHZEUR
    ]

    last_error = None
    for kr_pair in candidates:
        url = f"{KRAKEN_BASE}/Ticker"
        try:
            r = requests.get(url, params={"pair": kr_pair}, timeout=10)
            r.raise_for_status()
            payload = r.json()

            if payload.get("error"):
                last_error = RuntimeError(str(payload["error"]))
                logger.warning(f"Kraken returned error for {kr_pair}: {payload['error']}")
                continue

            result = payload["result"]
            first_key = next(iter(result.keys()))
            price = float(result[first_key]["c"][0])
            logger.info(f"Fetched Kraken price for {pair} ({kr_pair}): {price}")
            return price

        except Exception as e:
            last_error = e
            logger.warning(f"Kraken fetch failed for {pair} ({kr_pair}): {e}")

    logger.exception(f"Kraken ticker failed for {pair}.")
    raise RuntimeError(f"Kraken ticker failed for {pair}. Last error: {last_error}")

def fetch_quotes(pair: str, amount_base: float) -> tuple[Quote, Quote]:
    logger.info(f"Fetching quotes for pair={pair}, amount={amount_base}")

    bitfinex_price = fetch_bitfinex_last_price(pair)
    kraken_price = fetch_kraken_last_price(pair)

    buy = Quote("Bitfinex", pair, amount_base, bitfinex_price, DEFAULT_FEES["Bitfinex"])
    sell = Quote("Kraken", pair, amount_base, kraken_price, DEFAULT_FEES["Kraken"])

    logger.info(f"Quotes ready: Bitfinex={bitfinex_price}, Kraken={kraken_price} for {pair}")
    return buy, sell
