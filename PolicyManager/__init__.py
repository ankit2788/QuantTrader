from abc import ABC, abstractmethod
import numpy as np

from importlib import reload
import configparser
from configparser import ExtendedInterpolation
import re
import SignalManager
from Utilities import loggingManager, ExceptionManager, helper


reload(SignalManager)



Logger = loggingManager.logger.getLogger("Policies")





    


class Dummy():
    def __init__(self):
        pass



class Policy(ABC):

    @abstractmethod
    def __init__(self, name, configFile):

        self.name           = name
        self.configparser   = configparser.ConfigParser(interpolation = ExtendedInterpolation())
        self.configparser.read(configFile)

        # get list of all assets
        self.listAllAssets  = helper.ConfigHelper.getList(self.configparser.get(section="StrategyConfig", option="Assets"))


        self.registerRequiredSignals()
        self.EntryPolicies  = self.registerEntryExitPolicies(entry = True)
        self.ExitPolicies   = self.registerEntryExitPolicies(entry = False)

        self.AllPolicies = {**self.ExitPolicies, **self.EntryPolicies} 
        

    
    def registerRequiredSignals(self):

        # get all Signal based Sections
        signalSections = [section for section in self.configparser.sections() if "Signal" in section]

        self.Signals = Dummy()
        for section in signalSections:
            sectionName = section.split("_")[1]

            setattr(self.Signals, sectionName, Dummy())

            # under each Sub section, get all the required Signals registered
            allSignals = self.configparser.options(section)
            for signalName in allSignals:

                # register individual signal by creating a SignalManager object
                signalConfigString = self.configparser.get(section, signalName)

                # extract signal Condition details
                parameters  = signalConfigString.split(",")
                _field      = parameters[0]
                _operator   = parameters[1]
                _isRelative = parameters[2]
                _isRelative = True if _isRelative.lower() == "true" else False

                _threshold  = parameters[3]
                _threshold  = None if _threshold.upper() == "NONE" else _threshold
                    
                if helper.isfloat(_threshold):
                    _threshold = float(_threshold)

                _comparisonField    = parameters[4]
                _comparisonField    = None if _comparisonField.upper() == "NONE" else _comparisonField


                # create Signal Object
                if sectionName.upper() == "ASSET":
                    objSignal = SignalManager.AssetSignal(name = signalName, field=_field, operator=_operator, 
                                            isComparisonRelative=_isRelative, threshold=_threshold, comparisonField=_comparisonField)
                elif sectionName.upper() == "PORTFOLIO":
                    objSignal = SignalManager.PortfolioSignal(name = signalName, field=_field, operator=_operator, 
                                                            isComparisonRelative=_isRelative, threshold=_threshold, comparisonField=_comparisonField)

                elif sectionName.upper() == "MARKET":     
                    assetstoConsider    = parameters[5:]

                    objSignal = SignalManager.MarketSignal(name = signalName, field=_field, operator=_operator, 
                                                            isComparisonRelative=_isRelative, threshold=_threshold, comparisonField=_comparisonField, \
                                                            assetstoConsider=assetstoConsider)

            
                setattr(getattr(self.Signals, sectionName),signalName,objSignal)

    
    def registerEntryExitPolicies(self, entry = True):
        if "TradePolicyConfig" not in self.configparser.sections():
            Logger.error("TradePolicyConfig --> Not available in Config File")
            raise Exception("TradePolicyConfig --> Not available in Config File")


        options                 = self.configparser.items("TradePolicyConfig")
        entry_exit_option       = "ENTRY" if entry else "EXIT"
        entryPoints             = self.configparser.get("TradePolicyConfig", entry_exit_option)
        entryPoints             = entryPoints.split(",")

        criterias = {}        
        for criteria in entryPoints:

            # config for each criteria needs to be read
            criterias[criteria] = {}

            _thisCriteriaOptions = self.configparser.options(section = criteria) 

            for option in _thisCriteriaOptions:
                # option --> either asset, portfolio or market
                # each option under this criteria  (either asset, portfolio or market) needs to be read

                criterias[criteria][option] = {}

                configString = self.configparser.get(section=criteria, option=option)
                conditions = self.__extractConditions(strConfig=configString, typeCondition=option)
                

                criterias[criteria][option] = conditions

        

        return criterias 


    def __extractConditions(self, strConfig, typeCondition):
        # orConditions = []
        andConditions = []
        
        res = re.findall(r'\(.*?\)', strConfig)
        for item in res:
            orConditions = []

            sub1 = "("
            sub2 = ")"
            
            s=str(re.escape(sub1))        
            e=str(re.escape(sub2))
            
            res1=re.findall(s+"(.*)"+e,item)[0]
            if "|" in res1:
                _allORConditions = res1.split("|")
                for _cond in _allORConditions:

                    # get signal object from the signals list

                    _thisObj = self.__fetchSignalObject(signalName=_cond, typeCondition=typeCondition)
                    if _thisObj is not None:
                        orConditions.append((_thisObj.name, _thisObj))
            else:
                _thisObj = self.__fetchSignalObject(signalName=res1, typeCondition=typeCondition)
                if _thisObj is not None:
                    orConditions.append((_thisObj.name, _thisObj))

            andConditions.append(orConditions)

        return andConditions            





    def __fetchSignalObject(self, signalName, typeCondition) :

        # parse the config for this signal 
        if typeCondition.upper() == "ASSET":
            objSignalType = getattr(self.Signals, "Asset")
        elif typeCondition.upper() == "PORTFOLIO":
            objSignalType = getattr(self.Signals, "Portfolio")
        elif typeCondition.upper() == "MARKET":
            objSignalType = getattr(self.Signals, "Market")

        # get object
        if hasattr(objSignalType, signalName.lower()):
            return getattr(objSignalType, signalName.lower())
        else:
            Logger.warning(f"{signalName} not available in Signal Type: {typeCondition}")
            return None
        
    
    @abstractmethod
    def checkAssetLevelSignals(self, assetList, currentAssetLevelInfo):
        """
        all asset signals to be checked against all assets
        """

        assetSignals        = getattr(self.Signals, "Asset")
        listassetSignals    = [signal for signal in dir(assetSignals) if "__" not in signal]
        
        signalChecks = {}
        for asset in assetList:
            signalChecks[asset] = {}
    
            for signalName in listassetSignals:
                
                objSignal = getattr(assetSignals, signalName)

                blnCheck = False
                if asset in currentAssetLevelInfo.keys():
                    thisAsset_currentValue = currentAssetLevelInfo[asset]
                    fieldName           = objSignal.field
                    thisassetfieldValue = thisAsset_currentValue[fieldName]
                    blnCheck            = objSignal.check(currentvalue = thisassetfieldValue)
                
                signalChecks[asset][signalName] = blnCheck
    
        return signalChecks


    @abstractmethod
    def checkPortfolioLevelSignals(self, currentPortfolioInfo):
        """
        all portfolio signals to be checked against portfolio level information
        """
        portfolioSignals    = getattr(self.Signals, "Portfolio")
        listportSignals     = [signal for signal in dir(portfolioSignals) if "__" not in signal]

        signalChecks = {}
        for signalName in listportSignals:

            objSignal = getattr(portfolioSignals, signalName)

            fieldName           = objSignal.field

            blnCheck = False
            if fieldName in currentPortfolioInfo.keys():
                thisfieldValue      = currentPortfolioInfo[fieldName]
                blnCheck            = objSignal.check(currentvalue = thisfieldValue)

            signalChecks[signalName] = blnCheck

        return signalChecks


    @abstractmethod
    def checkMarketLevelSignals(self, currentMarketInfo):
        """
        all market signals to be checked against provided market information
        """
        marketSignals       = getattr(self.Signals, "Market")
        listmarketSignals   = [signal for signal in dir(marketSignals) if "__" not in signal]
        signalChecks = {}
        for signalName in listmarketSignals:

            objSignal = getattr(marketSignals, signalName)

            fieldName           = objSignal.field

            blnCheck = False
            if fieldName in currentMarketInfo.keys():
                thisfieldValue      = currentMarketInfo[fieldName]
                blnCheck            = objSignal.check(currentvalue = thisfieldValue)

            signalChecks[signalName] = blnCheck

        return signalChecks


    @abstractmethod
    def checkEntryExitPolicy(self, listAssets, currentAssetLevelInfo, currentPortfolioInfo, currentMarketInfo):
        # checks all the policies for all assets based on current level information
        # Inputs:
        #   listAssets --> list of all assets
        #   currentAssetLevelInfo --> current asset level data (dict of dicts)
        #   currentPortfolioInfo --> current portfolio level data (dict)
        #   currentMarketInfo --> current market level data (dict)


        # run Signal checks
        assetSignalCheck    = self.checkAssetLevelSignals(assetList=listAssets, currentAssetLevelInfo=currentAssetLevelInfo)
        portSignalCheck     = self.checkPortfolioLevelSignals(currentPortfolioInfo=currentPortfolioInfo)
        marketSignalCheck   = self.checkMarketLevelSignals(currentMarketInfo=currentMarketInfo)


        self.assetSignalCheck   = assetSignalCheck
        self.portSignalCheck    = portSignalCheck
        self.marketSignalCheck  = marketSignalCheck

        # print(self.assetSignalCheck, self.portSignalCheck, self.marketSignalCheck)

        policyCheck = {}
        for asset in listAssets:
            policyCheck[asset] = {}

            # Check for Entry level policies
            for policy in self.AllPolicies:
                policyCheck[asset][policy] = self.checkPerAssetEntryExitPolicy(assetName=asset, policyName=policy)

        # self.assetSignalCheck   = None
        # self.portSignalCheck    = None
        # self.marketSignalCheck  = None

       
        return policyCheck


    
    @abstractmethod
    def checkPerAssetEntryExitPolicy(self, assetName, policyName):
        # checks whether the entry or exit policy holds true for each asset 
        # Inputs:
        #   assetName --> asset name to be checked
        #   policyName --> name of the entry or exit policy

        if self.assetSignalCheck is None or self.portSignalCheck is None or self.marketSignalCheck is None:
            Logger.error("Signal Checks not done. Run checkAssetLevelSignals/checkPortfolioLevelSignals/checkMarketLevelSignals")
            raise Exception("Signal Checks not done. Run checkAssetLevelSignals/checkPortfolioLevelSignals/checkMarketLevelSignals")


        _thisPolicy = self.AllPolicies[policyName]

        individualCheck = []
        for option in _thisPolicy.keys():
            _check = self.checkPerAssetEntryExitPolicy_perCondition(assetName=assetName, policyName=policyName, typeCondition=option)
            individualCheck.append(_check)

        # take the AND of all conditions
        final = True
        for item in individualCheck:
            final = final and  item

        return final


    def checkPerAssetEntryExitPolicy_perCondition(self, assetName, policyName, typeCondition):
        # checks whether the entry or exit policy holds true for each asset for a particular type (either asset level, portfolio level or market level)
        # Inputs:
        #   assetName --> asset name to be checked
        #   policyName --> name of the entry or exit policy
        #   typeCondition --> either asset, portfolio or market

        _thisPolicy = self.AllPolicies[policyName]

        outerConditionsCheck = []
        for condition_outer in _thisPolicy[typeCondition]:

            innerConditions = []
            innerConditionsCheck = []
            for condition_inner in condition_outer:
                # get the signal name 
                signalName = condition_inner[0]

                # get signal type
                if isinstance(condition_inner[1], SignalManager.AssetSignal):
                    # asset  based signal           
                    check = self.assetSignalCheck[assetName][signalName]
                elif isinstance(condition_inner[1], SignalManager.PortfolioSignal):
                    check = self.portSignalCheck[signalName]                    
                elif isinstance(condition_inner[1], SignalManager.MarketSignal):
                    # check if the asset needs to be considered if market signal matches
                    
                    check = False
                    if assetName in condition_inner[1].assetstoConsider:
                        check = self.marketSignalCheck[signalName]
                    

                innerConditionsCheck.append(check)


            # take the OR of all inner conditions
            final_inner = False
            for item in innerConditionsCheck:
                # print(final_inner, item)
                final_inner = final_inner or  item
                # print(final_inner)

            outerConditionsCheck.append(final_inner)
            # print(outerConditionsCheck)

        # take the and product of all outer conditions
        final = True
        for item in outerConditionsCheck:
            final = final and  item

        return final

    @abstractmethod
    def getAction(self, currentPortfolioState, currentConditionalCheck, **args):
        pass


