from abc import ABC, abstractmethod
import operator
from Utilities import helper


def get_truth(input, relate, compare_against):
    # compare 2 values based n the operator sign provided
    ops = {'>': operator.gt,
           '<': operator.lt,
           '>=': operator.ge,
           '<=': operator.le,
           '==': operator.eq}
    return ops[relate](input, compare_against)


class Signal(ABC):
    """
    abstract class for Trading signal generations
    Checks required characteristics and provides whether signal is breached 
    """

    @abstractmethod
    def __init__(self, name, field, operator, isComparisonRelative, threshold=  None, comparisonField = None):
        """
        name        --> signal Name
        operator    --> >, >=, <, <=, ==
        isComparisonRelative --> boolean
        threshold --> value to be checked. Not applicable if isComparisonRelative is True
        comparisonField --> field to be compared against. Not applicable if isComparisonRelative is False

        """

        self.name   = name
        self.field  = field
        self.operator = operator
        self.isComparisonRelative = isComparisonRelative
        self.threshold = threshold
        self.comparisonField = comparisonField


    @abstractmethod
    def check(self, currentvalue, relativeFieldValue = None):

        if self.isComparisonRelative:
            if relativeFieldValue is not None:
                blnCheck = get_truth(input=currentvalue, relate=self.operator, compare_against=relativeFieldValue)
            else:
                # no value provided for comparison
                blnCheck = False
        else:
            blnCheck = get_truth(input=currentvalue, relate=self.operator, compare_against=self.threshold)

        return blnCheck


class AssetSignal(Signal):
    """
    abstract class for Trading signal generations based on individual assets 
    Checks individual assets' required characteristics and provides whether that asset's signal is breached 
    """

    def __init__(self, name, field, operator, isComparisonRelative, threshold=  None, comparisonField = None):
        super().__init__(name, field, operator, isComparisonRelative, threshold=  threshold, comparisonField = comparisonField)


    def check(self, currentvalue, relativeFieldValue = None):
        blnCheck =  super().check(currentvalue=currentvalue, relativeFieldValue=relativeFieldValue)
        return blnCheck




class PortfolioSignal(Signal):
    """
    abstract class for Trading signal generations based on entire Portfolio
    Checks Portfolio level required characteristics and provides whether the signal is breached. 
    """

    def __init__(self, name, field, operator, isComparisonRelative, threshold=  None, comparisonField = None):
        super().__init__(name, field, operator, isComparisonRelative, threshold=  threshold, comparisonField = comparisonField)


    def check(self, currentvalue, relativeFieldValue = None):
        blnCheck =  super().check(currentvalue=currentvalue, relativeFieldValue=relativeFieldValue)
        return blnCheck


class MarketSignal(Signal):
    """
    abstract class for Trading signal generations based on Market and conditions    
    """

    def __init__(self, name, field, operator, isComparisonRelative, threshold=  None, comparisonField = None, assetstoConsider = "ALL"):
        super().__init__(name, field, operator, isComparisonRelative, threshold=  threshold, comparisonField = comparisonField)
        self.assetstoConsider = assetstoConsider
        

    def check(self, currentvalue, relativeFieldValue = None):
        blnCheck =  super().check(currentvalue=currentvalue, relativeFieldValue=relativeFieldValue)
        return blnCheck



