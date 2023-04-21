'''
A Strategy that triggers
- a buy when the buy_weighted sum of indicators turns from negative to positive
- a sell when the sell_weighted sum of indicators turns from negative to positive

Questions for lab facilitator:
- Is 720, 1 day data points all that is required to evolve strategy?
- Why is price between 0.26-1.24 as opposed to around $30,000 USD?
'''

import pandas as pd
from matplotlib import pyplot as plt
import ta

class Strategy():

  # callables that take close as first parameter and return a pandas Series
  INDICATORS = [
    ta.trend.sma_indicator,
    ta.trend.ema_indicator,
    # ... simply add more indicators
  ]

  NUM_INDICATORS = len(INDICATORS)

  def __init__(
      self,
      ohlcv: pd.DataFrame,
      params: list[dict],
      buy_weights: list[float],
      sell_weights: list[float]
    ) -> None:
    '''
    Parameters
    ----------
      ohlcv : pandas.DataFrame
        A DataFrame containing ohlcv candle data.

      params : list[dict]
        A list of dicts, where each dict contains the keyword arguments to pass to the corresponding indicator.

      buy_weights : list[float]
        A list of weights to be applied to each indicator in the buy sum.

      sell_weights : list[float]
        A list of weights to be applied to each indicator in the sell sum.
    '''

    self.ohlcv = ohlcv
    self.close = self.ohlcv.iloc[:, 4] # 5th column is close price

    self.params = params
    self.buy_weights = buy_weights
    self.sell_weights = sell_weights

    self.set_indicators()

  def set_indicators(self):
    '''
    Reset the indicators with current params
    '''
    self.indicators = [Strategy.INDICATORS[i](self.close, **self.params[i]) for i in range(Strategy.NUM_INDICATORS)]

  def buy_sum(self, t: int) -> float:
    '''
    Return buy_weighted sum of indicators at time period t

    Parameters
    ----------
    t : int
      The time period to assess. Assumed to be within [1, len(self.close)]
    '''

    return sum([self.buy_weights[i] * self.indicators[i][t] for i in range(Strategy.NUM_INDICATORS)])

  def sell_sum(self, t: int) -> float:
    '''
    Return sell_weighted sum of indicators at time period t

    Parameters
    ----------
    t : int
      The time period to assess. Assumed to be within [1, len(self.close)]
    '''

    return sum([self.sell_weights[i] * self.indicators[i][t] for i in range(Strategy.NUM_INDICATORS)])

  def buy_trigger(self, t: int) -> bool:
    '''
    Return True if should buy at time period t, else False.

    Parameters
    ----------
    t : int
      The time period to assess. Assumed to be within [1, len(self.close)]
    '''

    return self.buy_sum(t) > 0 and self.buy_sum(t-1) <= 0
  
  def sell_trigger(self, t: int) -> bool:
    '''
    Return True if should sell at time period t, else False.

    Parameters
    ----------
    t : int
      The time period to assess. Assumed to be within [1, len(self.close)]
    '''

    return self.sell_sum(t) > 0 and self.sell_sum(t-1) <= 0

  def evaluate(self, verbose: bool = False) -> float:
    '''
    Return the fitness of the Strategy, which is defined as the USD remaining after starting with $1 USD, buying and selling at each trigger in the timeframe, and selling in the last time period.
    '''

    usd = 1
    bitcoin = 0

    for t in range(1, len(self.close)):

      if self.buy_trigger(t):
        bitcoin += usd / self.close[t]
        if verbose: print(f'Bought {bitcoin:4.2f} bitcoin for {usd:4.2f} USD at time {t:3d}, price {self.close[t]:4.2f}')
        usd = 0

      elif bitcoin and self.sell_trigger(t): # must buy before selling
        usd += bitcoin * self.close[t]
        if verbose: print(f'Sold   {bitcoin:4.2f} bitcoin for {usd:4.2f} USD at time {t:3d}, price {self.close[t]:4.2f}')
        bitcoin = 0

    # if haven't sold, sell in last time period
    if bitcoin:
      usd += bitcoin * self.close.iloc[-1]
      if verbose: print(f'Sold   {bitcoin:4.2f} bitcoin for {usd:4.2f} USD at time {t:3d}, price {self.close.iloc[-1]:4.2f}')

    return usd
  
  def graph(self) -> None:
    '''
    Graph the close prices, the Strategy's indicators, and the buy and sell points. Block until figure is closed.
    '''
    
    plt.plot(self.close, label='Close price')
    for i in range(Strategy.NUM_INDICATORS): plt.plot(self.indicators[i], label=Strategy.INDICATORS[i].__name__)

    bought, sold = 0, 0

    for t in range(1, len(self.close)):

        if self.buy_trigger(t):
            plt.plot((t), (self.close[t]), 'o', color='red', label='Buy' if not bought else '')
            bought += 1

        elif bought and self.sell_trigger(t): # must buy before selling
            plt.plot((t), (self.close[t]), 'o', color='green', label='Sell' if not sold else '')
            sold += 1

    # if haven't sold, sell in last time period
    if bought > sold:
      plt.plot((len(self.close)-1), (self.close.iloc[-1]), 'o', color='green', label='Sell' if not sold else '')

    plt.legend()
    plt.show(block=True)

if __name__ == '__main__':
  import ccxt

  MARKET = 'BIT/USD'
  TIMEFRAME = '1d'

  kraken = ccxt.kraken()
  ohlcv = pd.DataFrame(kraken.fetch_ohlcv(MARKET, TIMEFRAME))

  # --- imitate simple strategy ---
  params = [
    {'window': 20}, # SMA
    {'window': 10}, # EMA
  ]
  buy_weights = [-1, 1]
  sell_weights = [1, -1]
  # -------------------------------

  strat = Strategy(ohlcv, params, buy_weights, sell_weights) # simple strategy
  
  fitness = strat.evaluate(verbose=True)
  print(f'\nFinal balance {fitness:.2f} USD')
  
  strat.graph()


