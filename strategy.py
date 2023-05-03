"""
A Strategy that triggers a:
- Buy when the buy_weighted sum of indicators turns from negative to positive, and
- Sell when the sell_weighted sum of indicators turns from negative to positive.

Ideas:
- Could have separate indicators with separate params for buy and sell triggers.
"""

import types
from typing import Callable, Any
import pandas as pd
from matplotlib import pyplot as plt
import numpy as np
import json
from ta.trend import sma_indicator, ema_indicator
from ta.volatility import bollinger_lband, bollinger_hband
import uuid

from globals import *
from dnf import ChromosomeHandler


class Strategy:
    def __init__(
        self,
        candles: pd.DataFrame,
        chromosome: dict[str, Any],
        market="BTC/AUD",
    ) -> None:
        """
        Init a Strategy with randomised indicator params.

        Parameters
        ----------
          candles : pandas.DataFrame
            A DataFrame containing ohlcv data.
        """

        self.candles = candles
        self.close = self.candles.iloc[:, 4]  # 5th column is close price

        self.base, self.quote = market.split("/")  # currencies

        self.id = uuid.uuid4()
        self.close_prices = []

        # Chromosome = 5 window sizes + 2 window deviations + 6 constants
        self.chromosome = chromosome
        self.set_chromosome(self.chromosome)

        self.portfolio = self.evaluate()  # evaluate fitness once on init
        self.fitness = None

    def set_chromosome(self, chromosome: dict[str, int | float]):
        """Given a chromosome, set all indicators."""
        self.n_indicators = len(chromosome["indicators"])
        self.indicators = []
        # For each indicator, provide respective params and generate DataFrame features
        for i in range(self.n_indicators):
            self.indicators.append(
                chromosome["indicators"][i][1](**chromosome["params"][i])
            )
        self.buy_trigger = types.MethodType(chromosome["function"], self)
        self.sell_trigger = types.MethodType(chromosome["function"], self)


    def evaluate(self, graph: bool = False) -> float:
        """
        Return the fitness of the Strategy, which is defined as the quote currency remaining after:
        - starting with 1 unit of quote currency,
        - buying and selling at each trigger in the timeframe, and
        - selling in the last time period.

        Parameters
        ----------
          graph : bool
            Also plot the close price, indicators, and buy and sell points and block execution
        """

        if graph:
            plt.plot(self.close, label="Close price")
            for i in range(self.n_indicators):
                plt.plot(
                    [
                        self.sma1,
                        self.sma2,
                        self.ema,
                        self.bollinger_lband,
                        self.bollinger_hband,
                    ][i],
                    label=["SMA1", "SMA2", "EMA", "Bollinger Lband", "Bollinger Hband"][
                        i
                    ],
                )

        quote = 100  # AUD
        base = 0  # BTC
        bought, sold = 0, 0
        self.close_prices = [quote]

        for t in range(1, len(self.close)):
            if bought == sold and self.buy_trigger(t):
                base = (quote * 0.98) / self.close[t]
                self.close_prices.append(quote)

                if graph:
                    print(
                        f"Bought {base:.2E} {self.base} for {quote:.2f} {self.quote} at time {t:3d}, price {self.close[t]:.2f}"
                    )
                    plt.plot(
                        (t),
                        (self.close[t]),
                        "o",
                        color="red",
                        label="Buy" if not bought else "",
                    )
                quote = 0
                bought += 1

            elif bought > sold and self.sell_trigger(t):  # must buy before selling
                # NOTE: 2% is applied TO the bitcoin!
                quote = (base * 0.98) * self.close[t]
                self.close_prices.append(quote)

                if graph:
                    print(
                        f"Sold   {base:.2E} {self.base} for {quote:.2f} {self.quote} at time {t:3d}, price {self.close[t]:.2f}"
                    )
                    plt.plot(
                        (t),
                        (self.close[t]),
                        "o",
                        color="chartreuse",
                        label="Sell" if not sold else "",
                    )
                base = 0
                sold += 1
                # What is the point of this else statement?
            else:
                temp = quote + base * self.close[t]
                self.close_prices.append(temp)

        # if haven't sold, sell in last time period
        if base:
            quote = (base * 0.98) * self.close.iloc[-1]
            self.close_prices.append(quote)
            if graph:
                print(
                    f"Sold   {base:.2E} {self.base} for {quote:.2f} {self.quote} at time {t:3d}, price {self.close.iloc[-1]:.2f}"
                )
                plt.plot(
                    (len(self.close) - 1),
                    (self.close.iloc[-1]),
                    "o",
                    color="chartreuse",
                    label="Sell" if not sold else "",
                )

        if graph:
            plt.legend()
            plt.show(block=True)

        self.portfolio = quote
        return quote

    def to_json(self) -> dict:
        """
        Return a dict of the minimum data needed to represent this strategy, as well as the fitness.
        """

        return {
            "window_sizes": self.chromosome["window_sizes"].tolist(),
            "window_devs": self.chromosome["window_devs"].tolist(),
            "constants": self.chromosome["constants"].tolist(),
            "fitness": self.fitness,
            "portfolio": self.portfolio,
        }

    @classmethod
    def from_json(
        self, candles: pd.DataFrame, filename: str, n: int = 1
    ) -> list["Strategy"]:
        """
        Return a list of n Strategy objects from json file data.
        """

        with open(filename, "r") as f:
            data = json.load(f)
            strategies = []
            for i in range(len(data)):
                data[i]["window_sizes"] = np.array(data[i]["window_sizes"])
                data[i]["window_devs"] = np.array(data[i]["window_devs"])
                data[i]["constants"] = np.array(data[i]["constants"])
                strategies.append(Strategy(candles, data[i]))

            return strategies

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.to_json()}>"

    @staticmethod
    def gen_random_chromosome(n_window: int, n_constant: int, n_window_dev: int):
        return {
            "window_sizes": np.random.randint(1, INT_OFFSET, size=n_window),
            "window_devs": np.round(
                np.random.uniform(1, FLOAT_OFFSET, size=n_window_dev), DECIMAL_PLACES
            ),
            "constants": np.round(
                np.random.uniform(0, CONST_MAX, size=n_constant), DECIMAL_PLACES
            ),
        }


if __name__ == "__main__":
    """
    Testing
    """

    from candle import get_candles

    candles = get_candles()


    best_fitness = 0
    # Randomly generate strategies and write the best to a file
    while True:
        handler = ChromosomeHandler(candles)
        c1 = handler.generate_chromosome()
        s = Strategy(candles, c1)
        s.buy_trigger(2)
        s.sell_trigger(3)