from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from datetime import datetime
from importlib import reload, import_module
from dateutil import relativedelta
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

import PortfolioUtilsManager
import PerformanceManager
import BenchmarkManager
import configparser
from configparser import ExtendedInterpolation
import SignalManager

reload(PortfolioUtilsManager)
reload(PerformanceManager)
reload(SignalManager)
reload(BenchmarkManager)


from PortfolioUtilsManager import PortfolioManager, Datadownloader, MacroMarketDataLoader
from Utilities import loggingManager, helper

warnings.filterwarnings("ignore")

Logger = loggingManager.logger.getLogger("StrategyManager")





class Dummy():
    def __init_(self):
        pass

class Strategy(ABC):

    def __init__(self, configFile = None):

        """
        configFile --> config file path
        policy --> object of type: PolicyManager.Policy
        """

        self.configFile = configFile
        self.configparser = configparser.ConfigParser(interpolation=ExtendedInterpolation())
        self.configparser.read(self.configFile)

        self.name = None



        self.__readConfig()

        # load the required Data
        self.Benchmark = BenchmarkManager.CompositeBenchmark(benchmarkDetails=self.benchmarkDetails)


        # load the price and macro market info data
        self.__loadPriceData()
        self.__loadMacroMarketData()

        self.initialCapital = 1000000

        # create the Strategy policy
        self.__createPolicyManagerobject(configFile)


        # setup the Portfolio and Holdings Manager
        self.PortfolioManager = PortfolioManager(listAssets=self.listAssets, initialCash=self.initialCapital, transaction_cost=self.transaction_cost)





    def __readConfig(self):
        # reads the Strategy master config

        section = "StrategyConfig" 

        options = self.configparser.options(section = section)

        self.listAssets         = helper.ConfigHelper.getList(self.configparser.get(section=section, option="Assets"))
        self.listMarketInfoFiles= helper.ConfigHelper.getList(self.configparser.get(section=section, option="MarketInfoFiles"))

        self.minCashRequired    = helper.ConfigHelper.getFloat(self.configparser.get(section=section, option="minCashRequired"))
        self.transaction_cost   = helper.ConfigHelper.getFloat(self.configparser.get(section=section, option="transaction_cost"))

        self.initialCapital     = helper.ConfigHelper.getFloat(self.configparser.get(section=section, option="initialCapital"))




        # get all paths
        self.paths = {}
        for _opt in options:
            if "path" in _opt:
                self.paths[_opt] =  self.configparser.get(section=section, option=_opt)

        # get benchmark Details
        self.benchmarkDetails = self.__getBenchmarkConfig()


    def __createPolicyManagerobject(self, configFile):
        # get the Policy Information and import the policy module
        policyOptions = self.configparser.options("TradePolicyConfig")
        if "policy" not in policyOptions:
            Logger.error("Policy not provided in config file")
            raise Exception("Policy not provided in config file")

        policy = self.configparser.get("TradePolicyConfig", "Policy")

        # import the policy object
        myModule = import_module(f"PolicyManager.{policy.split('.')[0]}")
        try:
            myPolicy = getattr(myModule,policy.split('.')[1])
            self.PolicyManager = myPolicy(configFile = configFile)
        except:
            _temp = policy.split('.')[1]
            raise Exception(f'{_temp} NOT available as part of any Policy')
        

        




    def __getBenchmarkConfig(self):
        # get Benchmark config
        if "BenchmarkConfig" not in self.configparser.sections():
            print("BenchmarkConfig --> Not available in Config File")
            return None

        benchmarkConfig = {item: None for item in self.configparser.options("BenchmarkConfig")}
        for item in benchmarkConfig.keys():
            _thisItemConfig = self.configparser.get("BenchmarkConfig", item)

            if item == "pricepath":
                benchmarkConfig[item] = _thisItemConfig
            else:
                benchmarkConfig[item] = helper.ConfigHelper.getList(_thisItemConfig)

        return benchmarkConfig        


    # Data Loaders
    def __loadPriceData(self, ):
        listAssets  = self.listAssets
        pricePath   = self.paths.get("assetdatapath", None)
        if pricePath is None:
            Logger.error("Asset Price Path not provided in Config file.")
            raise Exception("Asset Price Path not provided in Config file.")

        __PriceDownloader = Datadownloader(listAssets=listAssets, path = pricePath)
        __PriceDownloader.loadData()
        self.PriceData = __PriceDownloader.allData_dict


    def __loadMacroMarketData(self):
        listMarketInfoFiles     = self.listMarketInfoFiles
        marketDataPath          = self.paths.get("marketdatapath", None)
        if marketDataPath is None:
            Logger.error("marketDataPath not provided in Config file.")
            raise Exception("marketDataPath not provided in Config file.")

        __MacroDataInfo = MacroMarketDataLoader(listMarketInfoFiles= listMarketInfoFiles, \
                                                   path = marketDataPath)
        __MacroDataInfo.loadData()
        self.MacroData = __MacroDataInfo.allData_dict





    @abstractmethod
    def run(self, startDate, endDate):
        """
        runs the defined strategy based on the provided policy
        Inputs:
            startDate, endDate: 
                type: string of format: YYYYMMDD
            
            macroMarketInfo: {"listMarketInfoFiles": None, "path": None}
                contains the macro market features to be used to govern the trading strategy
        """

        # load data for the date period

        done = False
        self.currentDate = datetime.strptime(startDate, "%Y%m%d").date()

        # load the benchmark Data
        self.BenchmarkData = self.Benchmark.loadBenchmarkData(startDate= self.currentDate, endDate = datetime.strptime(endDate, "%Y%m%d").date())

        # # load the market info if provided
        # if len(macroMarketInfo.keys()) > 0:
        #     self.__loadMacroMarketData(macroMarketInfo=macroMarketInfo)

        while not done:



            if self.currentDate >= datetime.strptime(endDate, "%Y%m%d").date():
                done = True

            # get current values (using properties of this class)
            currentAssetLevelState  = self.currentAssetLevelState
            currentPortfolioState   = self.currentPortfolioLevelState
            currentMarketState      = self.currentMarketConditions
            currentPrice            = self.getTodayPrice

            # get action based on the current portfolio state and market conditions
            action, conditionsMet = self.PolicyManager.getAction(assetLevelState = currentAssetLevelState, \
                                                  portfolioLevelState = currentPortfolioState, \
                                                  marketLevelState = currentMarketState)


            # update the action as needed by the policy
            # print(self.currentDate, action)
            action = self.updateAction_as_per_policy(action)

            # Log how we are entering/ exiting 
            
            # create orderInfo from actions
            orders = self.convertActiontoTrade(action=action, currentPrice=currentPrice, action_condition = conditionsMet)
            # if len(orders) > 0:
            #     Logger.info(f'Date: {self.currentDate}, Action: {action}  Order: {orders}')


            # perform Trade based on the suggested action
            self.PortfolioManager.update(date = self.currentDate, newTrade=orders, currentPrice=currentPrice)

            # update the current date
            self.currentDate = self.currentDate + relativedelta.relativedelta(days=1)



        Logger.info(f"Strategy Run completed")

    
    @property
    def currentAssetLevelState(self):
        currentAssetState = {}

        for asset in self.listAssets:
            _thisAssetObject    = getattr(self.PortfolioManager.AssetLevelInfo, asset)
            currentPosition     = getattr(_thisAssetObject, "Value")
            runningDays         = getattr(_thisAssetObject, "DaysHolding")
            runningPerformance  = getattr(_thisAssetObject, "RunningPerformance")
            daysSinceLastTrade  = getattr(_thisAssetObject, "DaysSinceLastTrade") 

            currentAssetState[asset] = {"currentPosition": currentPosition, \
                                            "runningDays": runningDays, \
                                            "runningPerformance": runningPerformance, \
                                            "DaysSinceLastTrade": daysSinceLastTrade}

        return currentAssetState


    @property
    def currentPortfolioLevelState(self):
        currentPortfolioState = {}

        cash            = self.PortfolioManager.PortfolioLevelInfo.Cash
        cash_pct        = self.PortfolioManager.PortfolioLevelInfo.Cash_Pct

        currentPortfolioState = {"runningCash": cash, \
                                 "runningCash_pct": cash_pct}

        return currentPortfolioState


    @property
    def currentMarketConditions(self):

        if self.currentDate not in self.MacroData.keys():
            Logger.info(f"Market doesnt have any value for Date: {self.currentDate}")
            marketState = None
        else:
            marketState = self.MacroData[self.currentDate]

        return marketState




    @property
    def getTodayPrice(self):

        # convert date from string format to datetime format
        # currentDate = datetime.strptime(self.currentDate, "%Y%m%d").date()
        if self.currentDate not in self.PriceData.keys():
            Logger.info(f"No Price available for Date: {self.currentDate}")
            priceInfo = None
        else:
            priceInfo = self.PriceData[self.currentDate]

        return priceInfo



    @abstractmethod
    def updateAction_as_per_policy(self, action):
        """
        method to update the action generated 
        converted action will account for % of asset weight in the portfolio
        """
        return action


    @abstractmethod
    def convertActiontoTrade(self, action, currentPrice, action_condition):
        """
        converts action into executable orders
        """

        

        # create orderInfo from actions
        orders = {}
        for index, asset in enumerate(self.listAssets):

            _thisAction = action[asset]
            price = currentPrice[asset]

            # get current holdings
            _thisAssetObject    = getattr(self.PortfolioManager.AssetLevelInfo, asset)
            currentHolding      = getattr(_thisAssetObject, "Holding")
            currentPosition     = getattr(_thisAssetObject, "Value")
            availableCash       = getattr(self.PortfolioManager.PortfolioLevelInfo, "Cash")

            if _thisAction == 0:
                pass


            # convert the action in Holdings to be sold/ bought
            elif _thisAction < 0:

                if _thisAction == -1:
                    # sold everything for this stock
                    quantity = currentHolding * -1
                else:
                    value_to_trade = currentPosition * _thisAction
                    quantity = np.floor(np.divide(value_to_trade, price)) * -1

                orders[asset] = {"Quantity": quantity, "Price": price}


            elif _thisAction > 0:

                if currentHolding > 0:
                    # buy holding worth the same Notional
                    value_to_trade = currentPosition * _thisAction
                    quantity = np.floor(np.divide(value_to_trade, price)) 

                else:
                    # entering a fresh position
                    # divide the current cash equally into all assets
                    availableCash_asset = availableCash/ len(self.listAssets)
                    value_to_trade = availableCash_asset * _thisAction
                    quantity = np.floor(np.divide(value_to_trade, price)) 

                orders[asset] = {"Quantity": quantity, "Price": price}


        
        return orders




    @property
    def portfolioHistory(self):
        _portfolioHistory    = self.PortfolioManager.DailyPortfolioDetails
        _portfolioHistory["Date"]    = pd.to_datetime(_portfolioHistory["Date"]).dt.date
        _portfolioHistory["Price"]   = _portfolioHistory["PortfolioValue"] * 100 / self.PortfolioManager.initialCash

        # compute daily return
        _portfolioHistory["Returns"]  = PerformanceManager.Returns(data = _portfolioHistory, cumulativePeriod=False, \
                                                                 rollingWindow=None, priceCol="PortfolioValue")

        return _portfolioHistory


    @property
    def benchmarkHistory(self):
        temp = self.BenchmarkData.reset_index(inplace = False, drop = False)
        __bmHistory = temp[["Date", "Price"]]
        
        # compute daily return
        __bmHistory["Returns"]  = PerformanceManager.Returns(data = __bmHistory, cumulativePeriod=False, \
                                                                 rollingWindow=None, priceCol="Price")

        return  __bmHistory                                                             



    @property
    def dailyAllData(self):
        # should include:
        # 1. Daily Portfolio level information (% holdings of Cash)
        # 2. Daily Asset level information 
        # 3. Daily Market level Information

        # Portfolio and asset level information
        data = pd.DataFrame()
        portHistory     = self.portfolioHistory.copy()
        assetHistory    = self.PortfolioManager.DailyAssetHoldings.copy()
        runningPerf     = self.PortfolioManager.DailyRunningPerformance.copy()
        holdingPeriod   = self.PortfolioManager.DailyHoldingPeriod.copy()
        daysLastTrade   = self.PortfolioManager.DailyDaysSinceLastTrade.copy()

        # merge the information
        data = pd.DataFrame()
        data["Date"] = portHistory["Date"]
        data = data.merge(portHistory[["Date", "Price", "Returns", "Drawdown"]], how = "inner", left_on="Date", right_on="Date")
        
        cols = ["Date"] + [item for item in assetHistory.columns if "weight" in item]
        data = data.merge(assetHistory[cols], how = "inner", left_on="Date", right_on="Date")

        renameCols = {item: f"Perf_{item.split('_')[0]}" for item in runningPerf.columns if "Data" in item }
        runningPerf.rename(columns = renameCols, inplace = True)
        data = data.merge(runningPerf, how = "inner", left_on="Date", right_on="Date")

        renameCols = {item: f"HoldingPeriod_{item.split('_')[0]}" for item in holdingPeriod.columns if "Data" in item }
        holdingPeriod.rename(columns = renameCols, inplace = True)
        data = data.merge(holdingPeriod, how = "inner", left_on="Date", right_on="Date")

        renameCols = {item: f"LastTradeDays_{item.split('_')[0]}" for item in daysLastTrade.columns if "Data" in item }
        daysLastTrade.rename(columns = renameCols, inplace = True)
        data = data.merge(daysLastTrade, how = "inner", left_on="Date", right_on="Date")




        # market level information
        macroData       = pd.DataFrame.from_dict(self.MacroData, orient="index")
        macroData.reset_index(inplace = True)
        macroData.rename(columns = {"index": "Date"}, inplace = True)

        data = data.merge(macroData, how = "inner", left_on="Date", right_on="Date")

        return data


                








        


    @abstractmethod
    def computePerformance(self):
        
        portfolioHistory = self.portfolioHistory
        bmHistory = self.benchmarkHistory

        cumulativePerformance = {"Stgy": {}, "Benchmark": {}}



        # 1. compute cumulativePerformance
        periodReturn    = PerformanceManager.Returns(data = portfolioHistory, cumulativePeriod=True, \
                                                         rollingWindow=None, priceCol="PortfolioValue")

        annualizedVol   = PerformanceManager.Risk.Volatility(data = portfolioHistory, rollingWindow=None, returnCol="Returns")

        # var             = PerformanceManager.Risk.VaR(data = portfolioHistory, distribution="HIST", confidenceLevel=0.95, returnCol="Return")
        # cvar            = PerformanceManager.Risk.CVaR(data = portfolioHistory, distribution="HIST", confidenceLevel=0.95, returnCol="Return")
        maxDD           = PerformanceManager.Risk.MaxDrawdown(data = portfolioHistory, priceCol="PortfolioValue")

        sharpe          = PerformanceManager.Ratios.Sharpe(data = portfolioHistory, riskfreerate=0.0, rollingWindow= None, priceCol="PortfolioValue", returnCol="Returns")
        sortino         = PerformanceManager.Ratios.Sortino(data = portfolioHistory, riskfreerate=0.0, rollingWindow= None, priceCol="PortfolioValue", returnCol="Returns")


        beta            = PerformanceManager.Risk.Beta(data = portfolioHistory, benchmarkData=bmHistory, rollingWindow=None, returnCol = "Returns") 
        trackingerror   = PerformanceManager.Risk.TrackingError(data = portfolioHistory, benchmarkData=bmHistory, returnCol = "Returns") 
        informationRatio = PerformanceManager.Ratios.Information(data = portfolioHistory, benchmarkData=bmHistory, priceCol = "Price", returnCol = "Returns")

        cumulativePerformance["Stgy"]["Returns"]    = np.round(periodReturn,4)
        cumulativePerformance["Stgy"]["Volatility"] = np.round(annualizedVol,4)
        cumulativePerformance["Stgy"]["Max Drawdown"] = np.round(maxDD,4)
        # cumulativePerformance["95% CVaR"]   = np.round(cvar,4)
        cumulativePerformance["Stgy"]["Sharpe Ratio"] = np.round(sharpe,4)
        cumulativePerformance["Stgy"]["Sortino Ratio"] = np.round(sortino,4)

        cumulativePerformance["Stgy"]["Beta"] = np.round(beta, 4)
        cumulativePerformance["Stgy"]["Tracking Error"] = np.round(trackingerror, 4)
        cumulativePerformance["Stgy"]["Information Ratio"] = np.round(informationRatio, 4)


        # -- get cumulative Info for benchmark
        periodReturn    = PerformanceManager.Returns(data = bmHistory, cumulativePeriod=True, \
                                                         rollingWindow=None, priceCol="Price")

        annualizedVol   = PerformanceManager.Risk.Volatility(data = bmHistory, rollingWindow=None, returnCol="Returns")

        # var             = PerformanceManager.Risk.VaR(data = portfolioHistory, distribution="HIST", confidenceLevel=0.95, returnCol="Return")
        # cvar            = PerformanceManager.Risk.CVaR(data = portfolioHistory, distribution="HIST", confidenceLevel=0.95, returnCol="Return")
        maxDD           = PerformanceManager.Risk.MaxDrawdown(data = bmHistory, priceCol="Price")

        sharpe          = PerformanceManager.Ratios.Sharpe(data = bmHistory, riskfreerate=0.0, rollingWindow= None, priceCol="Price", returnCol="Returns")
        sortino         = PerformanceManager.Ratios.Sortino(data = bmHistory, riskfreerate=0.0, rollingWindow= None, priceCol="Price", returnCol="Returns")

        beta            = PerformanceManager.Risk.Beta(data = bmHistory, benchmarkData=bmHistory, rollingWindow=None, returnCol = "Returns") 
        trackingerror   = PerformanceManager.Risk.TrackingError(data = bmHistory, benchmarkData=bmHistory, returnCol = "Returns") 
        informationRatio = PerformanceManager.Ratios.Information(data = bmHistory, benchmarkData=bmHistory, priceCol = "Price", returnCol = "Returns")


        cumulativePerformance["Benchmark"]["Returns"]    = np.round(periodReturn,4)
        cumulativePerformance["Benchmark"]["Volatility"] = np.round(annualizedVol,4)
        cumulativePerformance["Benchmark"]["Max Drawdown"] = np.round(maxDD,4)
        # cumulativePerformance["95% CVaR"]   = np.round(cvar,4)
        cumulativePerformance["Benchmark"]["Sharpe Ratio"] = np.round(sharpe,4)
        cumulativePerformance["Benchmark"]["Sortino Ratio"] = np.round(sortino,4)

        cumulativePerformance["Benchmark"]["Beta"] = np.round(beta, 4)
        cumulativePerformance["Benchmark"]["Tracking Error"] = np.round(trackingerror, 4)
        cumulativePerformance["Benchmark"]["Information Ratio"] = np.round(informationRatio, 4)

        cumulativePerformance = pd.DataFrame.from_dict(cumulativePerformance, orient="index").T


        # 2. compute Trailing Metrics


        # 3. compute Annual Performance
        annualPerformance = PerformanceManager.computeAnnualPerformance(strategydata=portfolioHistory, riskfreerate=0.0, priceCol="Price", returnsCol="Returns", benchmark = bmHistory)

        # 4. Monthly Performance
        monthlyPerformance = PerformanceManager.computeMonthlyPerformance(strategydata=portfolioHistory, riskfreerate=0.0, priceCol="Price", returnCol="Returns", benchmark = bmHistory)

        return cumulativePerformance, annualPerformance, monthlyPerformance


    @abstractmethod
    def plot_performance(self):

        cumPerformance, annPerformance, monPerformance = self.computePerformance()

        # 4 plots to be added:
        fig, ax = plt.subplots(4,1, figsize = (15,20))

        portfolioHistory = self.portfolioHistory
        bmHistory = self.benchmarkHistory

        # 1. Cumulative Portfolio performance
        ax[0].plot(portfolioHistory["Date"], portfolioHistory["Price"], label = "Strategy", color = "green", lw = 2)
        ax[0].plot(bmHistory["Date"], bmHistory["Price"], label = "Benchmark", color = "red", lw = 2)
        ax[0].set_xlabel("Date")
        ax[0].set_ylabel("Cumulative Performance")
        ax[0].set_title("Performance")
        ax[0].legend()


        # 2. Rolling Drawdown
        portfolioHistory["Drawdown"] = PerformanceManager.Risk.Drawdown(data = portfolioHistory, priceCol="Price")
        bmHistory["Drawdown"] = PerformanceManager.Risk.Drawdown(data = bmHistory, priceCol="Price")

        ax[1].fill_between(portfolioHistory["Date"], portfolioHistory["Drawdown"], 0, color = "red", alpha = 0.4, label = "Strategy")
        ax[1].fill_between(bmHistory["Date"], bmHistory["Drawdown"], 0, color = "red", alpha = 0.2, label = "Benchmark")
        ax[1].set_xlabel("Date")
        ax[1].set_ylabel("Max Drawdown")
        ax[1].set_title("Max Drawdown")
        ax[1].legend()


        # 3. Monthly performance heatmap
        monthly = monPerformance["Returns (%)"]
        monthly.reset_index(inplace = True)
        monthly["Year"]     = monthly["index"].apply(lambda x: int(x.split("-")[0]))
        monthly["Month"]    = monthly["index"].apply(lambda x: int(x.split("-")[1]))

        heatmapData = {}
        for year in monthly["Year"].unique():
            _tempData = monthly[monthly["Year"] == year][["Month", "strategy"]].set_index("Month", inplace = False)
            heatmapData[year] = _tempData.T.values[0]

        monthlyReturns = pd.DataFrame.from_dict(heatmapData, orient = "index")
        monthlyReturns.columns = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        monthlyReturns = monthlyReturns * 100
        monthlyReturns = monthlyReturns.T


        sns.heatmap(data = monthlyReturns, annot = True, cmap = "RdYlGn", ax = ax[2], vmin = -5, vmax = 5)
        ax[2].set_title("Monthly Performance")

        # 4. Annual Performance
        annual = annPerformance["Returns (%)"]
        annual.reset_index(inplace = True)
        annual.rename(columns = {"index": "Year"}, inplace = True)

        labels = list(annual["Year"].unique())

        x = np.arange(len(labels))  # the label locations
        width = 0.35  # the width of the bars

        rects1 = ax[3].bar(x - width/2, annual["strategy"], width, label='Strategy')
        rects2 = ax[3].bar(x + width/2, annual["benchmark"], width, label='Benchmark')

        # Add some text for labels, title and custom x-axis tick labels, etc.
        ax[3].set_ylabel('Annual Performance')
        ax[3].set_xticks(x)
        ax[3].set_xticklabels(labels)
        ax[3].legend()
















        



