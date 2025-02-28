import requests
import websockets
import asyncio
import json
import sqlite3
import time
import datetime
import logging
from typing import List

"""
TODO: Fetch minute based options data filtered for volume and close price greater than 0.
TODO: Store the fetched data in a SQLite database.
TODO: Make sure to update option symbol database when (define best condition).
"""

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

# Global dictionary to store the latest underlying prices
underlying_prices = {}
# Global variable to store options metadata (unique symbols)
global_options_metadata = []
# Global dictionary to store the persistent latest options messages
latest_options_messages = {}

def fetch_options_metadata_binance():
    """
    Fetch Binance options metadata and return a list of symbols filtered by BTC and ETH.

    The Binance API returns a JSON object containing multiple attributes per option, including:
    - `symbol`: The option's symbol (e.g., "ETH-250301-2200-C")
    - `side`: "CALL" or "PUT"
    - `strikePrice`: The strike price for the option
    - `underlying`: The base asset (e.g., "ETHUSDT" or "BTCUSDT")
    - `expiryDate`: Expiration date in milliseconds
    - `priceScale`, `quantityScale`: Precision for price and quantity
    - `makerFeeRate`, `takerFeeRate`: Trading fees

    This function extracts **only the symbols** for BTC and ETH options.

    :return: List of option symbols for BTC and ETH
    :raises ValueError: If no options are found or if connection error occurs.
    """
    try:
        response = requests.get('https://eapi.binance.com/eapi/v1/exchangeInfo')
        response.raise_for_status()
        metadata = response.json()
        options_symbols = metadata.get("optionSymbols", [])
        if not options_symbols:
            raise ValueError('No options symbols found')
        return [opt["symbol"] for opt in options_symbols if opt["underlying"].replace("USDT", "") in ("BTC", "ETH")]
    except requests.exceptions.RequestException as e:
        raise ValueError(f'Error fetching Binance options metadata: {e}')

def chunk_list(lst, n):
    """
    Split a list into chunks of size `n`.

    :param lst: List to be split
    :param n: Maximum chunk size
    :return: Generator yielding n-sized chunks
    """
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def create_snapshot_table():
    """
    Create a SQLite table to store option snapshots if it doesn't exit.
    The table contains the following columns:
    - `snapshot_index`: Unique snapshot identifier
    - `timestamp`: Snapshot timestamp
    - `symbol`: Option symbol (e.g., "ETH-250301-2200-C")
    - `underlying`: Underlying asset (e.g., "BTC" or "ETH")
    - `expiration`: Expiration date
    - `strike`: Strike price
    - `side`: Option side ("CALL" or "PUT")
    - `underlying_price`: Current price of the underlying asset
    - raw trade data (`o`, `h`, `l`, `c`, `V`, `A`, `n`, `bo`, `ao`, `bq`, `aq`, `d`, `t`, `g`, `v`, `vo`, `mp`)
    """
    conn = sqlite3.connect('binance_options.db')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS option_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_index INTEGER,
            timestamp TEXT,
            symbol TEXT,
            underlying TEXT,
            expiration TEXT,
            strike INTEGER,
            side TEXT,
            underlying_price TEXT,
            o TEXT,
            h TEXT,
            l TEXT,
            c TEXT,
            V TEXT,
            A TEXT,
            n INTEGER,
            bo TEXT,
            ao TEXT,
            bq TEXT,
            aq TEXT,
            delta TEXT,
            theta TEXT,
            gama TEXT,
            vega TEXT,
            vo TEXT,
            mp TEXT
        )
    """)
    conn.commit()
    conn.close()

def read_snapshot_index() -> int:
    """
    Read the latest snapshot index from the SQLite database.

    :return: Latest snapshot index
    """
    conn = sqlite3.connect('binance_options.db')
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(snapshot_index) FROM option_snapshots")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] is not None else 0

async def subscribe_options_group(symbols_chunk: List[str]):
    """
    Subscribe to Binance WebSocket for a group of options symbols.
    Instead of collecting messages for a fixed duration, this connection remains open,
    continously updating the global dictionary 'latest_options_messages'.
    
    Example WebSocket message:
    {
      "stream": "ETH-250314-2900-C@ticker",
      "data": {
        "e": "24hrTicker",          // Event type
        "E": 1740600596083,         // Event time (Unix timestamp in milliseconds)
        "T": 1740600596000,         // Transaction time (Unix timestamp in milliseconds)
        "s": "ETH-250314-2900-C",   // Option symbol
        "o": "27.4",                // Opening price over the last 24 hours
        "h": "28.6",                // Highest price over the last 24 hours
        "l": "10.4",                // Lowest price over the last 24 hours
        "c": "10.4",                // Last price
        "V": "30.86",               // Trading volume in contracts over the last 24 hours
        "A": "682.27",              // Trade amount in quote asset over the last 24 hours
        "P": "-0.6204",             // Price change percent over the last 24 hours
        "p": "-17",                 // Price change over the last 24 hours
        "Q": "0.4",                 // Quantity of the last completed trade in contracts
        "F": "10",                  // First trade ID in the last 24 hours
        "L": "19",                  // Last trade ID in the last 24 hours
        "n": 10,                    // Number of trades over the last 24 hours
        "bo": "10.6",               // Best bid price
        "ao": "10.8",               // Best ask price
        "bq": "150",                // Best bid quantity
        "aq": "31",                 // Best ask quantity
        "b": "0.72217524",          // Buy implied volatility
        "a": "0.72518587",          // Sell implied volatility
        "d": "0.07344626",          // Delta
        "t": "-1.54495251",         // Theta
        "g": "0.0004054",           // Gamma
        "v": "0.66151029",          // Vega
        "vo": "0.72236903",         // Implied volatility
        "mp": "10.6",               // Mark price
        "hl": "437.7",              // Buy maximum price
        "ll": "0.2",                // Sell minimum price
        "eep": "0",                 // Estimated strike price (provided half an hour before exercise)
        "r": "0.065"                // Interest rate
      }
    }

    :param symbols_chunk: A list of up to 200 option symbols to subscribe to.
    :raises Exception: If WebSocket connection fails or is closed.
    """
    global latest_options_messages
    streams = "/".join([f"{symbol}@ticker" for symbol in symbols_chunk])
    ws_url = f"wss://nbstream.binance.com/eoptions/stream?streams={streams}"
    while True:
        try:
            async with websockets.connect(ws_url) as ws:
                logging.info(f"Connected to Binance WebSocket for chunk: {symbols_chunk[0]} ... {symbols_chunk[-1]} (total {len(symbols_chunk)})")
                while True:
                    message = await ws.recv()
                    data = json.loads(message)
                    ticker_data = data.get("data", {})
                    symbol = ticker_data.get("s", "")
                    if symbol:
                        # Update the persistent dictionary with the latest message for this symbol
                        latest_options_messages[symbol] = ticker_data
        except Exception as e:
            logging.error(f"Option WebSocket Error for chunk {symbols_chunk}: {e}. Reconnecting in 1 minute...")
            await asyncio.sleep(60)  # Sleep for 1 minute and re-try

async def subscribe_options_binance(option_symbols: List[str]):
    """
    Subscribe to all Binance options by breaking them into chunks of 200 symbols (Binance limit). 
    It runs multiple WebSocket connections in parallel for each chunk which will update the dictionary.

    :param option_symbols: List of all available Binance option symbols.
    """
    symbol_chunks = list(chunk_list(option_symbols, 200))
    logging.info(f"Subscribing to {len(symbol_chunks)} chunks of options ...")
    tasks = [asyncio.create_task(subscribe_options_group(chunk)) for chunk in symbol_chunks]
    await asyncio.gather(*tasks)

async def subscribe_underlying_binance():
    """
    Subscribe to Binance WebSocket for BTC & ETH prices and update the global 'underlying_prices' dictionary.
    The connection is maintained until an error occurs, in which case it will reconnect after 1 minute.

    This function listens to the Binance **trade stream** (`btcusdt@trade`, `ethusdt@trade`).

    Example WebSocket message:
    {
      "stream": "btcusdt@trade",
      "data": {
        "e": "trade",
        "E": 1739800154263,
        "s": "BTCUSDT",
        "p": "43521.67",
        "q": "0.001",
        "T": 1739800154260
      }
    }

    :raises Exception: If WebSocket connection fails.
    """
    global underlying_prices
    underlyings = ["BTC", "ETH"]
    streams = "/".join([f"{underlying.lower()}usdt@trade" for underlying in underlyings])
    ws_url = f"wss://stream.binance.com:9443/stream?streams={streams}"
    while True:
        try:
            async with websockets.connect(ws_url) as ws:
                logging.info(f"Connected to Binance WebSocket: {ws_url}")
                while True:
                    message = await ws.recv()
                    data = json.loads(message)
                    trade_info = data.get("data", {})
                    asset = trade_info.get("s") 
                    price = trade_info.get("p")
                    if asset and price:
                        underlying_prices[asset] = price
        except websockets.exceptions.ConnectionClosed as e:
            logging.error(f"WebSocket connection closed: {e}, reconnecting in 1 minute...")
            await asyncio.sleep(60)  # Sleep for 1 minute and re-try
        except Exception as e:
            logging.error(f"Underlying WebSocket Error: {e}, reconnecting in 1 minute...")
            await asyncio.sleep(60)  # Sleep for 1 minute and re-try

async def take_snapshot():
    """
    Every 1 minute, collect a snapshot from the persistent global dictionary `latest_options_messages`.
    Filter to store only options that have volume (V) > 0 and last close price (c) > 0.
    Expired options (past their 8:00 UTC experation) are not stored.
    The snapshot is then stored in the SQLite database.

    For each snapshot:
    - Print the total number of messages collected, how many were saved and how many dropped.
    - Parse the option symbol into its components (underlying, expiration, strike, side).
    - Store the snapshot in the SQLite database.
    - The snapshot index is incremented.
    """
    create_snapshot_table()
    snapshot_index = read_snapshot_index()
    current_time = datetime.datetime.now(datetime.timezone.utc)
    valid_messages = {}
    for symbol, data in latest_options_messages.items():
        parts = symbol.split("-")
        if len(parts) != 4:
            continue
        try:
            # Parse expiration date and set expiration time to 08:00 UTC
            expiration_date = datetime.datetime.strptime(parts[1], "%y%m%d").replace(tzinfo=datetime.timezone.utc)
            expiration_date = expiration_date.replace(hour=8, minute=0, second=0, microsecond=0)
        except Exception:
            continue
        if current_time < expiration_date:
            valid_messages[symbol] = data
    total_messages = len(valid_messages)
    latest_filtered = {}
    for symbol, data in valid_messages.items():
        try:
            volume = float(data.get("V", 0))
            close_price = float(data.get("c", 0))
        except ValueError:
            continue
        if volume > 0 and close_price > 0:
            latest_filtered[symbol] = data
    num_saved = len(latest_filtered)
    num_dropped = total_messages - num_saved
    logging.info(f"Snapshot {snapshot_index+1}: Collected {total_messages} messages. Saved {num_saved}, dropped {num_dropped}.")
    conn = sqlite3.connect('binance_options.db')
    cursor = conn.cursor()
    for symbol, data in latest_filtered.items():
        parts = symbol.split("-")
        if len(parts) != 4:
            continue
        underlying, expiration, strike, side = parts
        underlying_price = underlying_prices.get(f"{underlying}USDT", "")
        row = (
            snapshot_index + 1,
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
            symbol,
            underlying,
            expiration,
            int(strike),
            side,
            underlying_price,
            data.get("o", ""),
            data.get("h", ""),
            data.get("l", ""),
            data.get("c", ""),
            data.get("V", ""),
            data.get("A", ""),
            data.get("n", ""),
            data.get("bo", ""),
            data.get("ao", ""),
            data.get("bq", ""),
            data.get("aq", ""),
            data.get("d", ""),
            data.get("t", ""),
            data.get("g", ""),
            data.get("v", ""),
            data.get("vo", ""),
            data.get("mp", ""),
        )
        cursor.execute("""
            INSERT INTO option_snapshots (
                snapshot_index, timestamp, symbol, underlying, expiration, strike, side, underlying_price,
                o, h, l, c, V, A, n, bo, ao, bq, aq, delta, theta, gama, vega, vo, mp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, row)
    conn.commit()
    conn.close()
    logging.info(f"Snapshot {snapshot_index+1}: Saved {num_saved} records to the database.")

async def snapshot_main():
    """
    Take a snapshot every 1 minute from the persistent global dictionary `latest_options_messages`.
    """
    while True:
        await take_snapshot()
        await asyncio.sleep(60)

async def refresh_options_metadata():
    """
    Refresh the options metadata every day at 08:01 UTC.
    Upon refresh, update 'global_optons_metadata' and remove expired 
    or outdated symbols from the presistent dictionary 'latest_options_messages'.
    """
    global global_options_metadata, latest_options_messages
    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        target = now.replace(hour=8, minute=1, second=0, microsecond=0)
        if now > target:
            target += datetime.timedelta(days=1)
        sleep_seconds = (target - now).total_seconds()
        await asyncio.sleep(sleep_seconds)
        try:
            new_metadata = fetch_options_metadata_binance()
            global_options_metadata = new_metadata
            logging.info(f"Refreshed options metadata: {len(new_metadata)} symbols.")
            valid_symbols = set(new_metadata)
            keys_to_remove = []
            current_time = datetime.datetime.now(datetime.timezone.utc)
            for symbol in list(latest_options_messages.keys()):
                if symbol not in valid_symbols:
                    keys_to_remove.append(symbol)
                    continue
                parts = symbol.split("-")
                if len(parts) != 4:
                    keys_to_remove.append(symbol)
                    continue
                try:
                    expiration_date = datetime.datetime.strptime(parts[1], "%y%m%d").replace(tzinfo=datetime.timezone.utc)
                    expiration_date = expiration_date.replace(hour=8, minute=0, second=0, microsecond=0)
                except Exception:
                    keys_to_remove.append(symbol)
                    continue
                if current_time > expiration_date:
                    keys_to_remove.append(symbol)
            for key in keys_to_remove:
                del latest_options_messages[key]
        except Exception as e:
            logging.error(f"Error refreshing options metadata: {e}")

async def main():
    # Fetch and store only the symbols in the global variable
    global global_options_metadata
    global_options_metadata = fetch_options_metadata_binance()
    logging.info(f"Fetched {len(global_options_metadata)} options symbols from Binance.")
    # Create tasks for (1) underlying subscription (2) options subscription (3) snapshot collection (4) metadata refresh
    await asyncio.gather(
        subscribe_underlying_binance(),
        subscribe_options_binance(global_options_metadata),
        snapshot_main(),
        refresh_options_metadata()
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Program terminated by user. Shutting down.")

