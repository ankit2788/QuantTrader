import numpy as np
import pandas as pd

import datetime
from scipy.stats import norm



ANNUALPERIOD = 252
ACTUALDAYS_YEAR = 365


def getDaysInPeriod(from_date, to_date):

    assert(isinstance(from_date, datetime.date))
    assert(isinstance(to_date, datetime.date))

    delta = to_date - from_date

    return delta.days



def DailyRetunstoAnnualized(dailyret):
    return (1 + dailyret)**ANNUALPERIOD - 1

def AnnualReturnstoDaily(annualizedReturns):
    return (1 + annualizedReturns)**(1/ANNUALPERIOD) - 1



def Returns(data, cumulativePeriod = False, rollingWindow = None, priceCol = None):

    ret = None

    if priceCol is None:
        raise Exception("Price Column not provided")

    if cumulativePeriod:

        ret     = data[priceCol]/ data[priceCol].iloc[0] - 1
        cumRet  = data[priceCol].iloc[-1]/ data[priceCol].iloc[0] - 1

        from_date   = list(data["Date"])[0]
        to_date     = list(data["Date"])[-1]

        periodDays  = getDaysInPeriod(from_date, to_date)

        if periodDays/ACTUALDAYS_YEAR > 1:
            years = np.round(periodDays/ ACTUALDAYS_YEAR, 2)
            return (1 + cumRet)**(1/years) - 1

        else:
            return cumRet


    else:

        if rollingWindow is None:
            ret = data[priceCol]/data[priceCol].shift(1) - 1

        else:

            data["Returns"] = Returns(data, rollingWindow=None, priceCol = priceCol)
            ret = data["Returns"].rolling(rollingWindow).mean()

    return ret



def var_historic(ret, confidenceLevel = 0.95):
    ret = ret.sort_values(by = "Returns", ascending = True, inplace = True)
    var = - np.percentile(ret, (1 - confidenceLevel)* 100)

    return var

def var_gaussian(ret, confidenceLevel = 0.95):
    ret = np.array(ret)
    z = norm.ppf(1 - confidenceLevel, np.mean(ret), np.std(ret))
    
    return -z
    

class Risk():

    def __init__(self):
        pass


    @staticmethod
    def Volatility(data, rollingWindow = None, returnCol = None):

        if returnCol is None:
            raise Exception("Returns Column not provided")
            
        vol = None
        if rollingWindow is None:
            vol = data[returnCol].std() * np.sqrt(ANNUALPERIOD)
        else:
            vol = data[returnCol].rolling(rollingWindow).std() * np.sqrt(ANNUALPERIOD)


        return vol


    @staticmethod
    def VaR(data, distribution = "HIST", confidenceLevel = 0.95, returnCol = None):

        if returnCol is None:
            raise Exception("Returns Column not provided")

        var = None

        ret = pd.DataFrame()
        ret["Returns"] = data[returnCol].dropna()

        if distribution == "HIST":
            var = var_historic(ret, confidenceLevel = confidenceLevel)

        elif distribution == "NORM":
            var = var_gaussian(ret, confidenceLevel = confidenceLevel)


        return var


    @staticmethod
    def CVaR(data, distribution = "HIST", confidenceLevel = 0.95, returnCol = None):
        if returnCol is None:
            raise Exception("Returns Column not provided")

        cvar = None

        ret = pd.DataFrame()
        ret["Returns"] = data[returnCol].dropna()

        if distribution == "HIST":
            is_beyond = ret <= -var_historic(ret, confidenceLevel=confidenceLevel)


        elif distribution == "NORM":
            is_beyond = ret <= -var_gaussian(ret, confidenceLevel=confidenceLevel)

        ret = np.array(ret)
        cvar = -np.mean(ret[is_beyond])

        return cvar


    @staticmethod
    def Drawdown(data, priceCol = None):
        if priceCol is None:
            raise Exception("Price Column not provided")

        rollingMax  = data[priceCol].cummax()
        daily_DD    = data[priceCol]/ rollingMax -  1.0

        return daily_DD

    @staticmethod
    def MaxDrawdown(data, priceCol = None):
        if priceCol is None:
            raise Exception("Price Column not provided")

        daily_DD    = Risk().Drawdown(data, priceCol=priceCol)
        maxDD       = min(daily_DD)

        return maxDD
    



    @staticmethod
    def Beta(data, benchmarkData, rollingWindow = None, returnCol = None):
        if returnCol is None:
            raise Exception("Returns Column not provided")

        columns_merge = ["Date"] + [returnCol]

        mergedData = data[columns_merge].merge(benchmarkData[columns_merge], on = "Date", how = "left")
        mergedData.rename(columns = {f'{returnCol}_x': returnCol, f'{returnCol}_y': f'{returnCol}_BM'}, inplace = True)
        mergedData.dropna(inplace = True)

        if rollingWindow is None:
            covarMatrix = np.cov(mergedData[returnCol], mergedData[f'{returnCol}_BM'])
            beta        = covarMatrix[0][1]/ covarMatrix[1][1]

        else:
            jointCovar = mergedData[returnCol].rolling(rollingWindow).cov(mergedData[f'{returnCol}_BM'])

            # benchmark variance
            bmVaR = mergedData[f'{returnCol}_BM'].rolling(rollingWindow).cov()

            beta = np.divide(jointCovar, bmVaR)

        return beta




    @staticmethod
    def Correlation(data, benchmarkData, rollingWindow = None, returnCol = None):
        if returnCol is None:
            raise Exception("Returns Column not provided")

        columns_merge = ["Date"] + [returnCol]

        mergedData = data[columns_merge].merge(benchmarkData[columns_merge], on = "Date", how = "left")
        mergedData.rename(columns = {f'{returnCol}_x': returnCol, f'{returnCol}_y': f'{returnCol}_BM'}, inplace = True)
        mergedData.dropna(inplace = True)

        if rollingWindow is None:
            covarMatrix = np.cov(mergedData[returnCol], mergedData[f'{returnCol}_BM'])
            corr        = covarMatrix[0][1]/ (np.sqrt(covarMatrix[1][1]) * np.sqrt(covarMatrix[0][0]))

        else:
            jointCovar = mergedData[returnCol].rolling(rollingWindow).cov(mergedData[f'{returnCol}_BM'])

            # portoflio & benchmark volatility
            portVol = mergedData[f'{returnCol}'].rolling(rollingWindow).std()
            bmVol   = mergedData[f'{returnCol}_BM'].rolling(rollingWindow).std()

            _denominator = np.multiply(portVol, bmVol)
            corr = np.divide(jointCovar, _denominator)

        return corr



    @staticmethod
    def TrackingError(data, benchmarkData,  returnCol = None):
        if returnCol is None:
            raise Exception("Returns Column not provided")

        columns_merge = ["Date"] + [returnCol]

        mergedData = data[columns_merge].merge(benchmarkData[columns_merge], on = "Date", how = "left")
        mergedData.rename(columns = {f'{returnCol}_x': returnCol, f'{returnCol}_y': f'{returnCol}_BM'}, inplace = True)
        mergedData.dropna(inplace = True)

        diff            = mergedData[f'{returnCol}'] - mergedData[f'{returnCol}_BM']
        trackingerror   = np.std(diff) * np.sqrt(ANNUALPERIOD)


        return trackingerror



    

class Ratios():
    def __init__(self):
        pass

    @staticmethod
    def Sharpe(data, riskfreerate = 0.0, rollingWindow = None, priceCol = None, returnCol = None):


        if returnCol is None:
            raise Exception("Returns Column not provided")


        dailyRiskFreeRatee = AnnualReturnstoDaily(riskfreerate)
        if rollingWindow is None:
            if priceCol is None:
                raise Exception("Price Column not provided")


            annualizedReturn    = Returns(data= data, cumulativePeriod=True, rollingWindow=None, priceCol=priceCol)
            excessReturn        = annualizedReturn - dailyRiskFreeRatee

            annualized_vol      = data[returnCol].dropna().std() * np.sqrt(ANNUALPERIOD)
            sharpe              = excessReturn/ annualized_vol if annualized_vol > 0 else np.nan


        else:

            rollingData         = data[returnCol].dropna().rolling(rollingWindow)
            annualizedReturn    = rollingData.apply(lambda x: np.prod(x + 1)**(ANNUALPERIOD/rollingWindow) - 1)
            excessReturn        = annualizedReturn - dailyRiskFreeRatee

            annualized_vol      = rollingData.std() * np.sqrt(ANNUALPERIOD)
            sharpe              = excessReturn/ annualized_vol

        return sharpe


    @staticmethod
    def Information(data, benchmarkData, rollingWindow = None, priceCol = None, returnCol = None):


        if returnCol is None:
            raise Exception("Returns Column not provided")

        columns_merge = ["Date"] + [returnCol]

        mergedData = data[columns_merge].merge(benchmarkData[columns_merge], on = "Date", how = "left")
        mergedData.rename(columns = {f'{returnCol}_x': returnCol, f'{returnCol}_y': f'{returnCol}_BM'}, inplace = True)
        mergedData.dropna(inplace = True)

        if rollingWindow is None:
            if priceCol is None:
                raise Exception("Price Column not provided")

            annualizedRet       = Returns(data, cumulativePeriod=True, rollingWindow=None, priceCol=priceCol)
            annualizedRet_BM    = Returns(benchmarkData, cumulativePeriod=True, rollingWindow=None, priceCol=priceCol)

            diff                = mergedData[returnCol] - mergedData[f'{returnCol}_BM']
            ann_outperformance  = annualizedRet - annualizedRet_BM
            ratio               = ann_outperformance/ (diff.std() * np.sqrt(ANNUALPERIOD))


        else:
            dataRet             = mergedData[returnCol].rolling(rollingWindow)
            dataRetBM           = mergedData[f'{returnCol}_BM'].rolling(rollingWindow)
            ann_outperformance  = dataRet.apply(lambda x: np.prod(1+x)**(ANNUALPERIOD/rollingWindow)) - dataRetBM.apply(lambda x: np.prod(1+x)**(ANNUALPERIOD/rollingWindow))

            diff                = (mergedData[returnCol] - mergedData[f'{returnCol}_BM']).rolling(rollingWindow)
            ratio               = ann_outperformance/ (diff.std() * np.sqrt(ANNUALPERIOD))


        return ratio


    @staticmethod
    def Sortino(data, riskfreerate = 0.0, rollingWindow = None, priceCol = None, returnCol = None):
        if returnCol is None:
            raise Exception("Returns Column not provided")

        dailyRiskFreeRatee  = AnnualReturnstoDaily(riskfreerate)
        fnDownsideRisk      = lambda x: np.std([min(0, item) for item in x])

        sortino             = None
        excessReturn        = data[returnCol].dropna() - dailyRiskFreeRatee


        if rollingWindow is None:
            if priceCol is None:
                raise Exception("Price Column not provided")

            retData             = data[returnCol].dropna()
            downsideRisk        = fnDownsideRisk(retData - dailyRiskFreeRatee)
            annualized_return   = Returns(data, cumulativePeriod=True, rollingWindow=None, priceCol=priceCol)

            sortino             = (annualized_return - dailyRiskFreeRatee)/ (downsideRisk* np.sqrt(ANNUALPERIOD)) if downsideRisk > 0 else np.nan
            if sortino == np.inf:
                sortino = np.nan

        else:
            retData             = data[returnCol].dropna().rolling(rollingWindow)
            downsideRisk        = retData.apply(lambda x: fnDownsideRisk(x - dailyRiskFreeRatee))
            annualized_return   = retData.apply(lambda x: np.prod(1+x)**(ANNUALPERIOD/rollingWindow))

            sortino             = (annualized_return - dailyRiskFreeRatee)/ (downsideRisk* np.sqrt(ANNUALPERIOD))
            sortino.replace([np.inf, -np.inf], np.nan, inplace = True)


        return sortino




    @staticmethod
    def Calmar(data, riskfreerate = 0.0, rollingWindow = None, priceCol = None, returnCol = None):
        if returnCol is None:
            raise Exception("Returns Column not provided")


        dailyRiskFreeRatee  = AnnualReturnstoDaily(riskfreerate)
        excessReturn        = data[returnCol].dropna() - dailyRiskFreeRatee

        if rollingWindow is None:
            if priceCol is None:
                raise Exception("Price Column not provided")

            annualized_return   = Returns(data, cumulativePeriod=True, rollingWindow=None, priceCol=priceCol)
            maxDD               = Risk().MaxDrawdown(data=data, priceCol=priceCol)

            calmar              = (annualized_return - dailyRiskFreeRatee)/ np.absolute(maxDD)

        else:
            retData             = data[returnCol].dropna().rolling(rollingWindow)
            annualized_return   = retData.apply(lambda x: np.prod(1+x)**(ANNUALPERIOD/rollingWindow))

            cumRets             = ((excessReturn + 1).cumprod()).rolling(rollingWindow)
            maxDD               = cumRets.apply(lambda x: np.absolute(min((x/ x.cummax() - 1.0).cummin()) ))

            calmar              = (annualized_return - dailyRiskFreeRatee)/ maxDD

        return calmar


            

def computeAnnualPerformance(strategydata, riskfreerate = 0.0, priceCol = None, returnsCol = None,  **portfolio):

    data = strategydata

    if "Date" not in data.columns:
        data = data.reset_index(drop = False)
        data = data.rename(columns = {"index": "Date"})


    data["Year"] = pd.to_datetime(data["Date"]).dt.year

    allPortfolios = portfolio
    allPortfolios["strategy"] = data

    unique_year = data.Year.unique()

    performance = {"Returns (%)": {}, \
                   "Volatility (%)": {}, \
                   "Sharpe": {}}

    
    for port, portData in allPortfolios.items():

        tempData = portData.copy()
        tempData["Year"] = pd.to_datetime(tempData["Date"]).dt.year

        performance["Returns (%)"][port] = {}
        performance["Volatility (%)"][port] = {}
        performance["Sharpe"][port] = {}

        for year in unique_year:

            temp        = tempData[tempData.Year == year]
            prevYear    = tempData[tempData.Year == year - 1].tail(1)
            temp        = pd.concat([prevYear, temp])

            # compute stats
            temp["Returns"] = Returns(data = temp, cumulativePeriod=False, rollingWindow=None, priceCol=priceCol)

            periodReturns   = Returns(data = temp, cumulativePeriod=True, rollingWindow=None, priceCol=priceCol)
            sharpe          = Ratios.Sharpe(data = temp, riskfreerate=riskfreerate, rollingWindow=None, priceCol=priceCol, returnCol=returnsCol)
            vol             = Risk.Volatility(data = temp, rollingWindow=None, returnCol= returnsCol)

            performance["Returns (%)"][port][year]      = periodReturns
            performance["Volatility (%)"][port][year]   = vol
            performance["Sharpe"][port][year]           = sharpe

        
    combinedPerformance = {}

    for outer, innerDict in performance.items():

        for inner, values in innerDict.items():
            combinedPerformance[(outer, inner)] = values

    # multiindex dataframe
    df_performance = pd.DataFrame(combinedPerformance)

    return df_performance



def computeMonthlyPerformance(strategydata, riskfreerate = 0.0, priceCol = None, returnCol = None, **portfolio):

    data = strategydata

    if "Date" not in data.columns:
        data = data.reset_index(drop = False)
        data = data.rename(columns = {"index": "Date"})


    data["Year"] = pd.to_datetime(data["Date"]).dt.year
    data["Month"] = pd.to_datetime(data["Date"]).dt.month

    data["Month-Year"] = data.apply(lambda row: str(row["Year"]) + "-" + str(row["Month"]), axis = 1)

    allPortfolios = portfolio
    allPortfolios["strategy"] = data

    unique_month = data["Month-Year"].unique()


    performance = {"Returns (%)": {}, \
                   "Volatility (%)": {}, \
                   "Sharpe": {}}

    
    for port, portData in allPortfolios.items():

        tempData = portData.copy()
        tempData["Year"] = pd.to_datetime(tempData["Date"]).dt.year
        tempData["Month"] = pd.to_datetime(tempData["Date"]).dt.month

        tempData["Month-Year"] = tempData.apply(lambda row: str(row["Year"]) + "-" + str(row["Month"]), axis = 1)


        performance["Returns (%)"][port] = {}
        performance["Volatility (%)"][port] = {}
        performance["Sharpe"][port] = {}

        for period in unique_month:

            temp        = tempData[tempData["Month-Year"] == period]

            # get previous month
            current_month   = int(period.split("-")[1])
            current_year    = int(period.split("-")[0])

            if current_month == 1:
                previous_month  = 12
                previous_year   = current_year - 1
                previous        = str(previous_year) + "-" + str(previous_month)
            else:
                previous_month  = current_month - 1
                previous_year   = current_year
                previous        = str(previous_year) + "-" + str(previous_month)


            prevYear    = tempData[tempData.Year == previous].tail(1)
            temp        = pd.concat([prevYear, temp])

            # compute stats
            temp["Returns"] = Returns(data = temp, cumulativePeriod=False, rollingWindow=None, priceCol=priceCol)

            periodReturns   = Returns(data = temp, cumulativePeriod=True, rollingWindow=None, priceCol=priceCol)
            sharpe          = Ratios.Sharpe(data = temp, riskfreerate=riskfreerate, rollingWindow=None, priceCol=priceCol, returnCol=returnCol)
            vol             = Risk.Volatility(data = temp, rollingWindow=None, returnCol= returnCol)

            performance["Returns (%)"][port][period]      = periodReturns
            performance["Volatility (%)"][port][period]   = vol
            performance["Sharpe"][port][period]           = sharpe

        
    combinedPerformance = {}

    for outer, innerDict in performance.items():

        for inner, values in innerDict.items():
            combinedPerformance[(outer, inner)] = values

    # multiindex dataframe
    df_performance = pd.DataFrame(combinedPerformance)

    return df_performance




















        






            







