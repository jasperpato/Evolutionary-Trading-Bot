from strategy import Strategy
import random


class RandomStrategy(Strategy):
  def __init__(self, candles, prob=0.05):  # buy or sell roughly once every 20 days
    self.prob = prob
    super(RandomStrategy, self).__init__(candles)

  def buy_trigger(self, t):
    return random.random() < self.prob

  def sell_trigger(self, t):
    return self.buy_trigger(t)


if __name__ == '__main__':
  from candle import get_candles_split, get_candles
  _, candles = get_candles_split()
  # print(max(RandomStrategy(candles).portfolio for _ in range(1000)))
  r = RandomStrategy(candles)
  r.evaluate(graph=True, fname='graphs/random.png',
             title='Random strategy, test data')
