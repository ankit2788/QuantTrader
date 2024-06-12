from PolicyManager import Policy
from Utilities import loggingManager, ExceptionManager
from importlib import reload
import numpy as np

import configparser
from configparser import ExtendedInterpolation



Logger = loggingManager.logger.getLogger("YieldCurvePolicy")

                            

class YieldCurveRegimePolicy(Policy):

    def __init__(self, name = None, configFile = None ):

        if name is None:
            name = __class__.__name__

        super().__init__(name = name, configFile=configFile)


    def checkAssetLevelSignals(self, assetList,  currentAssetLevelInfo):
        # currentAssetLevelInfo = self.__convertFeaturesDict(providedFeaturesSet=currentAssetLevelInfo, assetLevel=True)
        return super().checkAssetLevelSignals(assetList = assetList, currentAssetLevelInfo = currentAssetLevelInfo)

    def checkPortfolioLevelSignals(self, currentPortfolioInfo):
        # currentPortfolioInfo = self.__convertFeaturesDict(providedFeaturesSet=currentPortfolioInfo, assetLevel=False)
        return super().checkPortfolioLevelSignals(currentPortfolioInfo)

    def checkMarketLevelSignals(self, currentMarketInfo):
        # currentMarketInfo = self.__convertFeaturesDict(providedFeaturesSet=currentMarketInfo, assetLevel=False)
        return super().checkMarketLevelSignals(currentMarketInfo)


    def checkPerAssetEntryExitPolicy(self, assetName, policyName):
        return super().checkPerAssetEntryExitPolicy(assetName, policyName)


    def checkEntryExitPolicy(self, currentAssetLevelInfo, currentPortfolioInfo, currentMarketInfo):
        listAssets = self.listAllAssets
        return super().checkEntryExitPolicy(listAssets, currentAssetLevelInfo, currentPortfolioInfo, currentMarketInfo)


    def getAction(self, assetLevelState, portfolioLevelState, marketLevelState):
        """
        based on current portfolio, and varying conditions --> perform action

        Inputs:
            assetLevelState: 
                dictionary of items at individual asset level
                Eg: {"A": {"runningPerformance": -0.34, "runningDays": 21, "currentPosition": 10},
                    "B": {"runningPerformance": 0.05, "runningDays": 21, "currentPosition": 210},   
                }

            portfolioLevelState: dictionary of items at portfolio level
                Eg: {
                    "running_cashPct": 0.05
                    }
            marketLevelState: 
                dictionary of items for which we will compare our entry/ exit criteria
                Eg: {
                        "regime_next2M": "RiskOn", 
                        "probRiskOn_nextMonth": "0.4", 
                }

        Output: 
            list of holdings to be bought/ sold for each asset


        Trading Strategy:
        1. On 1st day, Enter into the position based on the conditions met  (action for that asset should be 1)
        2. On subsequent days, 
            2.1. check for any of the exit criterias being met.
                2.1.1 if met, exit the position (action for that asset should be -1)
                2.2.2 if not met, no action
            2.2. check for Entry  criteria:
                2.2.1. add more position on existing. 
                2.2.2 add new Positions if new entry criteria met.
            
            
        """

        # convert currentPortfolioState into dictionary of features. Each feature contains list of values for each asset
        # assetLevelValues = self.__convertFeaturesDict(providedFeaturesSet=assetLevelState, assetLevel=True)
        # portLevelValues = self.__convertFeaturesDict(providedFeaturesSet=portfolioLevelState, assetLevel=False)
        # marketLevelValues = self.__convertFeaturesDict(providedFeaturesSet=marketLevelState, assetLevel=False)


        # based on current values, get applicable signals
        # AssetWiseSignalOutcome  = self.checkAssetLevelSignals(currentAssetLevelInfo=assetLevelState)
        # PortfolioSignalOutcome  = self.checkPortfolioLevelSignals(currentPortfolioInfo=portfolioLevelState)
        # MarketSignalOutcome     = self.checkMarketLevelSignals(currentMarketInfo=marketLevelState)



        # based on signals, validate any of the entry or exit policy is holding true
        policyCheck = self.checkEntryExitPolicy(currentAssetLevelInfo=assetLevelState, 
                                                currentPortfolioInfo=portfolioLevelState, 
                                                currentMarketInfo=marketLevelState)

                                                


        # combine the entry and exit criterias to get the final action
        action      = {asset: 0 for asset in self.listAllAssets}
        conditions  = {asset: [] for asset in self.listAllAssets}

        for asset in policyCheck.keys():
            for policy in policyCheck[asset]:
                if "EXIT" in policy and policyCheck[asset][policy]:
                    action[asset] = -1
                    conditions[asset].append(policy)
                
                if "ENTRY" in policy and policyCheck[asset][policy]:
                    action[asset] = 1
                    conditions[asset].append(policy)

        return action, conditions






    def __convertFeaturesDict(self, providedFeaturesSet, assetLevel = True):
        if providedFeaturesSet is not None:

            if assetLevel:
                features = []
                for asset in providedFeaturesSet.keys():
                    features = features + list(providedFeaturesSet[asset].keys())
                    
                

                newStateFeatures = {feature: [] for feature in set(features)}

                for feat in newStateFeatures.keys():
                    for asset in self.listAllAssets:

                        if asset not in providedFeaturesSet.keys():
                            newStateFeatures[feat].append(0)
                        else:

                            value = providedFeaturesSet[asset].get(feat, 0)
                            newStateFeatures[feat].append(value)

            else:
                newStateFeatures = providedFeaturesSet
            
            valuesList = []
            for feat in newStateFeatures.keys():
                _this = {"field": feat, "value": newStateFeatures[feat]}
                valuesList.append(_this)      

            return valuesList

        else:
            return None              
        
  




                    

                    


                        

                



