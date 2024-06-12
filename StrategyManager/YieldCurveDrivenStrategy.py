import pandas as pd
from importlib import reload
import numpy as np

import StrategyManager
# from StrategyManager import Strategy
from Utilities import ExceptionManager, loggingManager
from PolicyManager import YieldCurvePolicy

reload(YieldCurvePolicy)
reload(StrategyManager)



Logger = loggingManager.logger.getLogger("Strategy - YieldCurveDriven")



class YieldCurveRegimeDrivenStrategy(StrategyManager.Strategy):

    def __init__(self, configFile):

        """
        Inputs:
            configFile: strategy config file path
        
        """

        self.name = __class__.__name__
        super().__init__(configFile=configFile)


        Logger.info("Strategy Initialized and required Data loaded")
        Logger.info("------------------------")
        



    def run(self, startDate, endDate):
        super().run(startDate = startDate, endDate = endDate)
        


    def updateAction_as_per_policy(self, action):
        """
        method to update the action generated 
        converted action will account for % of asset weight in the portfolio
        """

        # if action is sell, then sell everything
        # if action is buy, based on available Cash --> update action

        revisedAction       = {}
        availableCash_pct   = self.PortfolioManager.PortfolioLevelInfo.Cash_Pct
        availableCash_pct_perAsset = availableCash_pct/len(self.listAssets)
        revisedAction = {asset: availableCash_pct_perAsset if action[asset] == 1 else action[asset] for asset in action.keys()}
        

        return revisedAction


    def convertActiontoTrade(self, action, currentPrice, action_condition):

        # create orderInfo from actions
        orders = {}

        _availableCash = self.PortfolioManager.PortfolioLevelInfo.Cash * (1 - self.minCashRequired)

        for index, asset in enumerate(self.listAssets):
            

            _thisAction = action[asset]
            _price      = currentPrice[asset]
            _thisObj    = getattr(self.PortfolioManager.AssetLevelInfo, asset)
            _holding    = getattr(_thisObj, "Holding")
            _value      = getattr(_thisObj, "Value")


            if _thisAction < 0:
                # selling  completely
                quantity    = -1 * _holding
                price       = _price

                orders[asset] = {"Quantity": quantity, "Price": price}

                Logger.info(f'{asset} exiting. Conditions met: {action_condition[asset]}')
            
            elif _thisAction > 0:
                # buying based on available Cash
                purchase_notional   = _availableCash * _thisAction
                quantity            = np.floor(purchase_notional/ _price)
                if quantity > 0:
                    orders[asset] = {"Quantity": quantity, "Price": _price}
                    Logger.info(f'{asset} Entering. Conditions met: {action_condition[asset]}')

        
        return orders


    def computePerformance(self):
        return super().computePerformance()

    def plot_performance(self):
        return super().plot_performance()

