import numpy as np
import pandas as pd
import os
from datetime import datetime

from Utilities import loggingManager, ExceptionManager


Logger = loggingManager.logger.getLogger("Portfolio Utilities")

class Dummy():
    def __init__(self):
        pass


class Datadownloader():

    def __init__(self, listAssets, path):

        self.assets = listAssets
        self.filepath = path

        # get the start date and end date from available data
        _allStartDates = []
        _allEndDates = []
        for asset in self.assets:


            datapath = os.path.join(path, f'{asset}.csv')
            if not os.path.exists(datapath):
                Logger.error(f'{asset} data not available in {datapath}')

            _thisData = pd.read_csv(os.path.join(path, f'{asset}.csv'))
            _thisData["Date"] = pd.to_datetime(_thisData["Date"]).dt.date
            _thisData = _thisData.sort_values("Date", ascending=True)
            _thisStartDate = _thisData["Date"].iloc[0]
            _thisEndDate = _thisData["Date"].iloc[-1]

            _allStartDates.append(_thisStartDate)
            _allEndDates.append(_thisEndDate)

        self.startDate = min(_allStartDates)
        self.endDate = max(_allEndDates)



    def loadData(self, priceCol = "Close"):

        requiredPriceCol = priceCol
        data_close = pd.DataFrame()

        dateRange = pd.Series(pd.bdate_range(start = self.startDate, end = self.endDate, freq = "D")).dt.date
        dateRange = pd.DataFrame(dateRange, columns = ["Date"])

        for asset in self.assets:
            _thisData = pd.read_csv(os.path.join(self.filepath, f'{asset}.csv'))
            _thisData["Date"] = pd.to_datetime(_thisData["Date"]).dt.date
            _thisData = _thisData.sort_values("Date", ascending=True)
            # _thisData.set_index("Date", drop = True, inplace = True)
            # print(_thisData.columns)


            if requiredPriceCol not in _thisData.columns:
                Logger.error(f"Price Column not available for {asset}")
                raise ExceptionManager.MissingColumnException("Close")

            _thisData = dateRange.merge(_thisData[["Date", requiredPriceCol]], how = "left", left_on = "Date", right_on = "Date")
            _thisData.set_index("Date", drop = True, inplace = True)

            # fillNa
            _thisData = _thisData.fillna(method = "ffill")
            _thisData = _thisData.fillna(-1)   # in case no price available for older dates --> -1

            data_close = data_close.merge(_thisData[[requiredPriceCol]], how = "outer", left_index=True, right_index=True)

            data_close.rename(columns = {requiredPriceCol: f'{asset}'}, inplace = True)



        
        self.allData_df = data_close
        self.allData_dict = data_close.to_dict(orient = "index")



class MacroMarketDataLoader():

    def __init__(self, listMarketInfoFiles, path):

        self.marketFactors = listMarketInfoFiles
        self.filepath = path


        # get the start date and end date from available data
        _allStartDates = []
        _allEndDates = []
        for factor in self.marketFactors:

            datapath = os.path.join(path, f'{factor}.csv')
            if not os.path.exists(datapath):
                Logger.error(f'{factor} data not available in {datapath}')

            _thisData = pd.read_csv(os.path.join(path, f'{factor}.csv'))
            _thisData["Date"] = pd.to_datetime(_thisData["Date"]).dt.date
            _thisData = _thisData.sort_values("Date", ascending=True)
            _thisStartDate = _thisData["Date"].iloc[0]
            _thisEndDate = _thisData["Date"].iloc[-1]

            _allStartDates.append(_thisStartDate)
            _allEndDates.append(_thisEndDate)

        self.startDate = min(_allStartDates)
        self.endDate = max(_allEndDates)        


    def loadData(self):

        data_close = pd.DataFrame()

        dateRange = pd.Series(pd.bdate_range(start = self.startDate, end = self.endDate, freq = "D")).dt.date
        dateRange = pd.DataFrame(dateRange, columns = ["Date"])

        for factor in self.marketFactors:
            _thisData = pd.read_csv(os.path.join(self.filepath, f'{factor}.csv'))
            _thisData["Date"] = pd.to_datetime(_thisData["Date"]).dt.date
            _thisData = _thisData.sort_values("Date", ascending=True)
            # _thisData.set_index("Date", drop = True, inplace = True)


            _thisData = dateRange.merge(_thisData, how = "left", left_on = "Date", right_on = "Date")
            _thisData.set_index("Date", drop = True, inplace = True)

            # fillNa
            _thisData = _thisData.fillna(method = "ffill")
            _thisData = _thisData.fillna("NA")   # in case no price available for older dates --> -1

            data_close = data_close.merge(_thisData, how = "outer", left_index=True, right_index=True)

        
        self.allData_df = data_close
        self.allData_dict = data_close.to_dict(orient = "index")




class PortfolioManager():

    def __init__(self, listAssets, initialCash, transaction_cost = 0):

        self.listAssets = listAssets
        self.transaction_cost = transaction_cost

        self.initialCash = initialCash

        self.PortfolioLevelInfo = Dummy()
        self.PortfolioLevelInfo.Value = initialCash
        self.PortfolioLevelInfo.Cash = initialCash
        self.PortfolioLevelInfo.Cash_Pct = 1.0
        self.PortfolioLevelInfo.Cost = 0

        self.AssetLevelInfo = Dummy()
        for asset in self.listAssets:
            
            setattr(self.AssetLevelInfo, asset, Dummy())
            _thisAssetObject = getattr(self.AssetLevelInfo, asset)


            setattr(_thisAssetObject, "Holding", 0)
            setattr(_thisAssetObject, "Value", 0)
            setattr(_thisAssetObject, "Pct_Holding", 0)
            setattr(_thisAssetObject, "CurrentPrice", 0)
            setattr(_thisAssetObject, "AvgPurchasePrice", 0)
            setattr(_thisAssetObject, "LastTradeDate", None)   #when was the last purchase made
            setattr(_thisAssetObject, "DaysSinceLastTrade", 0)   #when was the last purchase made

            # note down the performance related Info
            setattr(_thisAssetObject, "DaysHolding", 0)
            setattr(_thisAssetObject, "RunningPerformance", 0)


        self.Trades = pd.DataFrame(columns = ["Date", "Asset", "Quantity", "Price", "Cost"])

        # store daily level Information
        col_port = ["Date", "Cash"] + self.listAssets + ["Cost", "PortfolioValue"]
        col_runningPerform = ["Date"] + self.listAssets

        col_assetHoldings = ["Date", "Cash_weight"]
        for asset in self.listAssets:
            col_assetHoldings.append(asset)
            col_assetHoldings.append(f'{asset}_weight')
        
        self.DailyPortfolioDetails = pd.DataFrame(columns=col_port)        
        self.DailyAssetHoldings = pd.DataFrame(columns=col_assetHoldings)

        self.DailyRunningPerformance = pd.DataFrame(columns=col_runningPerform)
        self.DailyHoldingPeriod = pd.DataFrame(columns=col_runningPerform)
        self.DailyDaysSinceLastTrade = pd.DataFrame(columns=col_runningPerform)

        


    def update(self, date, newTrade, currentPrice):
        """
        Inputs:
            date: current date in string (YYYYMMDD) format
            newTrade: dictionary of different assets'trades
                Eg: {
                        "A": {"Quantity": 100, "Price": 20}, 
                        "B": {"Quantity": -50, "Price": 120}
                    }

            currentPrice: dictionary of current price of each asset
        """


        # check for Traded Notional on this day (including Cost)
        totaltradedNotional = 0
        totaltransactionCost = 0


        # 1. check for available Cash
        self.__checkCashPostTrades(trades = newTrade)


        # execute the order and update the relevant information as needed
        for asset in newTrade.keys():            
            self.executeSingleOrder(date = date, assetName=asset, orderDetail=newTrade[asset])
        
        # 2. once all orders executed, update all asset level and portfolio level info
        currentCash = getattr(self.PortfolioLevelInfo, "Cash")
        portValue = currentCash
        for asset in self.listAssets:

            # update the Position level Information
            _thisAssetNotional = self.__updateDailyAssetLevelInfo(date = date, assetName=asset, currentPrice=currentPrice)
            portValue += _thisAssetNotional

        setattr(self.PortfolioLevelInfo, "Value", portValue)


        # 3. Update asset pct holdings and compute running performances
        self.__updatePerformance_HoldingsInfo()

        # store all info on a daily basis
        self.__computePortfolioSummary(date = date)





    def __checkCashPostTrades(self, trades):

        totaltradedNotional = 0
        totaltransactionCost = 0
        for asset in trades.keys():
            _thisNotional = trades[asset]["Quantity"] * trades[asset]["Price"]
            totaltradedNotional += _thisNotional
            totaltransactionCost += abs(_thisNotional) * self.transaction_cost


        requiredCash = totaltradedNotional + totaltransactionCost
        availableCash = self.PortfolioLevelInfo.Cash
        
        if requiredCash > availableCash:
            Logger.error(f"Portfolio doesnt have enough Cash. Current Cash: {availableCash}. Required: {requiredCash}")
            raise Exception(f"Portfolio doesnt have enough Cash. Current Cash: {availableCash}. Required: {requiredCash}")
            




    def executeSingleOrder(self, date, assetName, orderDetail):
        """        
        assetName: name of asset to be traded
        orderDetail: {"Quantity": 100, "Price": 100 }
        """

        quantity = orderDetail["Quantity"]
        price = orderDetail["Price"]

        # get the current values for this asset
        _thisAssetObject = getattr(self.AssetLevelInfo, assetName)


        previousHolding = getattr(_thisAssetObject, "Holding")
        previousNotional = getattr(_thisAssetObject, "Value")
        lastavgPurchasePruce = getattr(_thisAssetObject, "AvgPurchasePrice")

        availableCash = getattr(self.PortfolioLevelInfo, "Cash")


        # update Information with the transaction

        # 1. Holdings
        newHoldings = previousHolding + quantity
        transactedValue = quantity* price
        transactionCost = np.round(np.abs(transactedValue)*self.transaction_cost, 2)

        if newHoldings < 0:
            raise Exception(f"Holdings cannot be negative. {assetName} -- Previous: {previousHolding} OrderSize: {quantity}")

        Logger.info(f"Date: {date}  ---- Order {assetName}: {quantity} @ {price} Executed")

        setattr(_thisAssetObject, "Holding", newHoldings)



        # 2. Average Purchase Price
        __averagePreviousPurchaseNotional = lastavgPurchasePruce * previousHolding
        __thisTradeNotional = transactedValue
        __averageNewPurchaseNotional = __averagePreviousPurchaseNotional + __thisTradeNotional
        
        newAvgPurchasePrice = np.round(__averageNewPurchaseNotional/ newHoldings, 2) if newHoldings > 0 else 0.00
        setattr(_thisAssetObject, "AvgPurchasePrice", newAvgPurchasePrice)
        
        # 3. Portfolio Available Cash
        availableCash -= (__thisTradeNotional + transactionCost)
        setattr(self.PortfolioLevelInfo, "Cash", availableCash)

        # 4. Total Cost
        setattr(self.PortfolioLevelInfo, "Cost", transactionCost + getattr(self.PortfolioLevelInfo, "Cost"))

        # 5. Last Trade how many days ago
        setattr(_thisAssetObject, "LastTradeDate", date)


        # update the Trade table
        _thisTrade = [date, assetName, quantity,price, transactionCost]
        self.Trades.loc[len(self.Trades)] = _thisTrade


    def __updateDailyAssetLevelInfo(self, date, assetName, currentPrice):
        """
        Updates the position on daliy basis of each asset based on current Holding and latest price
        """


        _thisAssetObject = getattr(self.AssetLevelInfo, assetName)

        _assetPrice   = currentPrice[assetName]
        _assetHolding = getattr(_thisAssetObject, "Holding")
        _LastTradedate = getattr(_thisAssetObject, "LastTradeDate")

        _newNotional = np.round(_assetHolding * _assetPrice,2)
        setattr(_thisAssetObject, "Value", _newNotional)
        setattr(_thisAssetObject, "CurrentPrice", _assetPrice)

        if _LastTradedate is not None:
            DaysSinceLastTrade = (date - _LastTradedate).days
        else:
            DaysSinceLastTrade =  0 
        # print(assetName, date, _LastTradedate, DaysSinceLastTrade )
        setattr(_thisAssetObject, "DaysSinceLastTrade", DaysSinceLastTrade)

        return _newNotional


    def __updatePerformance_HoldingsInfo(self):
        # method to compute the running Performance and holdings periods
        # any more running Information can be added here


        currentCash = getattr(self.PortfolioLevelInfo, "Cash")
        portValue = getattr(self.PortfolioLevelInfo, "Value")
        
        cash_pct = currentCash/ portValue
        setattr(self.PortfolioLevelInfo, "Cash_Pct", cash_pct)


        for asset in self.listAssets:

            # 1. update the percent Holdings 
            _thisAssetObject = getattr(self.AssetLevelInfo, asset)
            _assetValue = getattr(_thisAssetObject, "Value")
            
            _pctHolding = _assetValue/ portValue
            setattr(_thisAssetObject, "Pct_Holding", _pctHolding)



            # 2. update holding period
            _currentHolding = getattr(_thisAssetObject, "Holding")
            _previousHoldingPeriod = getattr(_thisAssetObject, "DaysHolding")

            _newHoldingPeriod = 0 if _currentHolding == 0 else _previousHoldingPeriod + 1

            setattr(_thisAssetObject, "DaysHolding" , _newHoldingPeriod)
            

            # 3. compute running Performance
            _currentPrice = getattr(_thisAssetObject, "CurrentPrice")
            _avgPurchasePrice = getattr(_thisAssetObject, "AvgPurchasePrice")

            _runningPerformance = 0 if _currentHolding == 0 else (_currentPrice - _avgPurchasePrice)/ _avgPurchasePrice

            setattr(_thisAssetObject, "RunningPerformance" , _runningPerformance)



    def __computePortfolioSummary(self, date):

        # 1. add the latest info 
        _currentCash = getattr(self.PortfolioLevelInfo, "Cash")
        _currentCash_pct = getattr(self.PortfolioLevelInfo, "Cash_Pct")
        _cost        = getattr(self.PortfolioLevelInfo, "Cost")
        _portValue   = getattr(self.PortfolioLevelInfo, "Value")
 
        _assetValues = []
        _Holdings = []
        _performances = []
        _holdingPeriods = []
        _lastTrade = []

        for asset in self.listAssets:

            _thisAssetObject    = getattr(self.AssetLevelInfo, asset)

            _assetValue         = getattr(_thisAssetObject, "Value")
            _holding_absolute   = getattr(_thisAssetObject, "Holding")
            _holding_percent    = getattr(_thisAssetObject, "Pct_Holding")

            _runningPerformance = getattr(_thisAssetObject, "RunningPerformance")
            _holdingPeriod      = getattr(_thisAssetObject, "DaysHolding")

            _DaysSinceLastTrade = getattr(_thisAssetObject, "DaysSinceLastTrade")


            _assetValues.append(_assetValue)
            _Holdings.append(_holding_absolute)
            _Holdings.append(_holding_percent)

            _performances.append(_runningPerformance)
            _holdingPeriods.append(_holdingPeriod)
            _lastTrade.append(_DaysSinceLastTrade)




        # update Portfolio
        _currentInfo = [date, _currentCash] + _assetValues + [_cost, _portValue]
        self.DailyPortfolioDetails.loc[len(self.DailyPortfolioDetails)] = _currentInfo

        # update Asset Holdings
        _currentInfo = [date, _currentCash_pct] + _Holdings
        self.DailyAssetHoldings.loc[len(self.DailyAssetHoldings)] = _currentInfo

        # update Running Performance
        _currentInfo = [date] + _performances
        self.DailyRunningPerformance.loc[len(self.DailyRunningPerformance)] = _currentInfo

        # update holding period
        _currentInfo = [date] + _holdingPeriods
        self.DailyHoldingPeriod.loc[len(self.DailyHoldingPeriod)] = _currentInfo


        # update last trade how many days
        _currentInfo = [date] + _lastTrade
        self.DailyDaysSinceLastTrade.loc[len(self.DailyDaysSinceLastTrade)] = _currentInfo

