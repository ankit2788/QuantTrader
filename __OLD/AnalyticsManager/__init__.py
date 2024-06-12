from abc import ABC, abstractclassmethod
import numpy as np

import Utilities.Constants as Constants
import Utilities.ExceptionManager as ExceptionManager



class RiskStats():

    def __init__(self):
        pass

    @staticmethod
    def Volatility(data, rollingWindow = None):

        vol = None

        if "returns" in data.columns:

            if rollingWindow is None:
                vol = data["returns"].std() * np.sqrt(Constants.ANNUAL_PERIOD)

            else:
                vol = data["returns"].rolling(rollingWindow).std() * np.sqrt(Constants.ANNUAL_PERIOD)

        else:
            ExceptionManager.MissingColumnException(columnName="returns")


    @staticmethod
    def dailyDrawdown(data):

        rollingMax = data["Value"].cummax()
        daily_DD = data["Value"]/rollingMax - 1.0

        return daily_DD


    @staticmethod
    def MaxDrawdown(data):

        dailyDD = RiskStats.dailyDrawdown(data)

        maxDD = min(dailyDD)
        #TODO: get the duration as well for max drawdown
        return maxDD





    

