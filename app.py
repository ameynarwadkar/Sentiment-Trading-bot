from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies import Strategy
from lumibot.traders import Trader
from datetime import datetime
from alpaca_trade_api import REST
from timedelta import Timedelta
from finbert_utils import estimate_sentiment
import numpy as np
import time

API_KEY = "API_KEY"
API_SECRET = "API_SECRET"
BASE_URL = "https://paper-api.alpaca.markets/v2"

ALPACA_CREDS = {
    "API_KEY": API_KEY,
    "API_SECRET": API_SECRET,
    "PAPER": True
}

class MLTrader(Strategy): 
    def initialize(self, symbol:str="SPY", cash_at_risk:float=.5): 
        self.symbol = symbol
        self.sleeptime = "24H" 
        self.last_trade = None 
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)

    def position_sizing(self): 
        cash = self.get_cash() 
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price,0)
        return cash, last_price, quantity

    def get_dates(self): 
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')

    def get_sentiment(self): 
        today, three_days_prior = self.get_dates()
        news = self.api.get_news(symbol=self.symbol, 
                                 start=three_days_prior, 
                                 end=today) 
        news = [ev.__dict__["_raw"]["headline"] for ev in news]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment 

    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing() 
        probability, sentiment = self.get_sentiment()
        volatility = self.calculate_volatility()

        if cash > last_price: 
            if sentiment == "positive" and probability > .5 and volatility > 0:
                target_price = self.calculate_target_price(last_price, volatility, "buy")
                stop_loss_price = self.calculate_stop_loss_price(last_price, volatility, "buy")
                
                if self.last_trade == "sell": 
                    self.sell_all() 
                order = self.create_order(
                    self.symbol, 
                    quantity, 
                    "buy", 
                    #type="limit", 
                    limit_price=target_price, 
                    stop_loss_price=stop_loss_price
                )
                self.submit_order(order) 
                self.last_trade = "buy"
            elif sentiment == "negative" and probability > .5 and volatility > 0:
                target_price = self.calculate_target_price(last_price, volatility, "sell")
                stop_loss_price = self.calculate_stop_loss_price(last_price, volatility, "sell")
                
                if self.last_trade == "buy": 
                    self.sell_all() 
                order = self.create_order(
                    self.symbol, 
                    quantity, 
                    "sell", 
                    #type="limit", 
                    limit_price=target_price, 
                    stop_loss_price=stop_loss_price
                )
                self.submit_order(order) 
                self.last_trade = "sell"
                
    def calculate_target_price(self, current_price, volatility, action):
        if action == "buy":
            return current_price * (1 + 0.2 * volatility)
        elif action == "sell":
            return current_price * (1 - 0.2 * volatility)

    def calculate_stop_loss_price(self, current_price, volatility, action):
        if action == "buy":
            return current_price * (1 - 0.05 * volatility)
        elif action == "sell":
            return current_price * (1 + 0.05 * volatility)

    def calculate_volatility(self):
        return np.random.uniform(0.01, 0.1)



if __name__ == '__main__':
    trade = False #Change this to True to make a live trade on alpaca
    if trade:    
        broker = Alpaca(ALPACA_CREDS) 
        strategy = MLTrader(name='mlstrat', broker=broker, 
                    parameters={"symbol":"SPY", 
                                "cash_at_risk":.5})
        trader = Trader()
        trader.add_strategy(strategy)
        while True:    
            trader.run_all()
            time.sleep(5*60)
    else:
        start_date = datetime(2021,1,1)
        end_date = datetime(2023,12,31) 
        MLTrader.backtest(
        YahooDataBacktesting, 
        start_date,
        end_date, 
        parameters={"symbol":"SPY", "cash_at_risk":.5}
        )
