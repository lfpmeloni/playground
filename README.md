# playground

Small projects that exist because I wanted to find out what would happen. Some
of them work.

## What's in here

- **[commitzilla](commitzilla/)** — paints a Japanese dragon onto my contribution
  graph, one day at a time, for a year. A cron job does the painting and a nightly
  Claude routine checks the colours came out right. Peak effort in service of
  absolutely no one.

- **[crypto_options_data](crypto_options_data/)** — opens a pile of Binance
  websockets, watches every BTC and ETH option at once, and drops a snapshot into
  SQLite every minute. Mostly an excuse to learn `asyncio` the hard way.

- **[google_fit](google_fit/)** — asks Google how much I walked this week and
  draws it in matplotlib. The chart is usually more motivating than the number.

- **[langchain](langchain/)** — one afternoon of poking a ReAct agent with a
  calculator and a search tool to see where the loop falls apart. It falls apart.

## Running any of it

Each folder is independent — no shared install, no root command. `cd` into one
and read its own README (where it has one).

```bash
git clone https://github.com/lfpmeloni/playground.git
```
