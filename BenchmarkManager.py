import pandas as pd
import os 
import numpy as np
from importlib import reload

from Utilities import loggingManager
from PortfolioUtilsManager import Datadownloader
from pandas.tseries.offsets import *


Logger = loggingManager.logger.getLogger("Benchmark")


class CompositeBenchmark():

    def __init__(self, benchmarkDetails):
        """
        benchmarkDetails: dictionary of below items:
        {"assets": [], "weights": [], pricePath: None}

        """



        
        self.component_IDs = benchmarkDetails["assets"]
        self.component_weights = benchmarkDetails["weights"]

        if np.sum(self.component_weights) != 1.0:
            raise Exception(f"Benchmark weights is not summing to 1. Current Total weight: {np.sum(self.component_weights)}")


        self.pricePath = benchmarkDetails["pricepath"]
        self.__loadPriceData(priceInfo = {"listAssets": benchmarkDetails["assets"], "pricePath": benchmarkDetails["pricepath"]})





    def __loadPriceData(self, priceInfo = {"listAssets": None, "pricePath": None}):
        __PriceDownloader = Datadownloader(listAssets=self.component_IDs, path = priceInfo["pricePath"])
        __PriceDownloader.loadData(priceCol = "Close")
        _PriceData = __PriceDownloader.allData_df
        self.PriceData = _PriceData.to_dict(orient = "series")



    def loadBenchmarkData(self, startDate, endDate = None):
        # loads the benchmark individual assets' data and construct the benchmark value

        allIndexData = pd.DataFrame()
        dateRange = pd.Series(pd.date_range(start = startDate, end = endDate, freq = BDay())).dt.date
        dateRange = pd.DataFrame(dateRange, columns = ["Date"])


        for index in self.component_IDs:

            _thisIndexData = self.PriceData[index]

            _thisIndexData = pd.DataFrame(_thisIndexData).reset_index(inplace = False, drop = False)
            _thisIndexData["Date"] = pd.to_datetime(_thisIndexData["Date"]).dt.date
            _thisIndexData = _thisIndexData.sort_values(by = "Date", ascending = True)


            _thisIndexData = dateRange.merge(_thisIndexData, how = "left", left_on="Date", right_on="Date")
            _thisIndexData.fillna(method = "ffill", inplace = True)
            _thisIndexData.set_index("Date", inplace = True)

            allIndexData = allIndexData.merge(_thisIndexData[[index]], how = "outer", left_index=True, right_index=True)
            allIndexData.rename(columns = {index: f'Price_{index}'}, inplace = True)


        allIndexData.reset_index(inplace = True)

        # create composite benchmark value
        benchmarkValue = self.constructBenchmark(startDate=startDate, individualPrices=allIndexData)
        self.benchmarkData = benchmarkValue

        return benchmarkValue



    def constructBenchmark(self, startDate, individualPrices):

        initialNotional = 100000000     # 100 Million

        # get component prices for 1st day
        _initialBenchmarkPrice = individualPrices[individualPrices["Date"] == startDate]
        if len(_initialBenchmarkPrice) != 1:
            Logger.error(f'Index price not available for Date: {startDate}')
            raise Exception(f'Index price not available for Date: {startDate}')

        _initialBenchmarkPrice = list(_initialBenchmarkPrice.iloc[0].values[1:])
        _initialBenchmarkPrice = np.round(np.array(_initialBenchmarkPrice),4)

        # compute holdings required to be bought for each asset
        _initialHoldings = np.divide(initialNotional * (np.array(self.component_weights)/sum(self.component_weights)), _initialBenchmarkPrice)
        _initialHoldings = np.nan_to_num(_initialHoldings, posinf = 0, neginf = 0)

        self.initialBenchmarkHoldings = _initialHoldings.copy()
        initialCash = initialNotional - np.sum(self.initialBenchmarkHoldings * _initialBenchmarkPrice)
        initialCash = np.round(initialCash, 4)


        # fetch prices for each asset, and compute daily benchmark value
        individualPrices = individualPrices.set_index("Date")

        _shape = individualPrices.shape
        _initialBenchmarkHolding = np.broadcast_to(self.initialBenchmarkHoldings, (_shape))
        benchmarkValue = _initialBenchmarkHolding * individualPrices

        dict_newnames = {}
        for col in benchmarkValue.columns:
            indexID = col.split("_")[1]
            dict_newnames[f'Price_{indexID}'] = f'Value_{indexID}'

        benchmarkValue = benchmarkValue.rename(columns = dict_newnames)
        benchmarkValue["Cash"] = initialCash
        benchmarkValue["TotalValue"] = benchmarkValue.sum(axis = 1)

        # normalize the price from 100
        benchmarkValue["Price"] = np.round(benchmarkValue["TotalValue"] * 100 / initialNotional, 4)

        # combine all data points
        benchmarkInfo = individualPrices
        for index, asset in enumerate(self.component_IDs):
            benchmarkInfo[f'Holdings_{asset}'] = self.initialBenchmarkHoldings[index]

        benchmarkInfo = benchmarkInfo.merge(benchmarkValue, how = "outer", left_index = True, right_index = True)

        return benchmarkInfo







            



        




