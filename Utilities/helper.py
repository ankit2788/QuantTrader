import operator



def get_truth(input, relate, compare_against):
    # compare 2 values based n the operator sign provided
    ops = {'>': operator.gt,
           '<': operator.lt,
           '>=': operator.ge,
           '<=': operator.le,
           '==': operator.eq}
    return ops[relate](input, compare_against)



def isfloat(num):
    try:
        float(num)
        return True
    except ValueError:
        return False

def isnumeric(num):
    try:
        int(num)
        return True
    except ValueError:
        return False


class ConfigHelper():       
       @staticmethod
       def getList(strConfig):
              listItems = strConfig.split(",")

              # remove None or blank items from list
              newList = []
              for item in listItems:
                     if item == "" or item.upper() == "NONE":
                            pass
                     else:
                            if isfloat(item):
                                   newList.append(float(item))
                            else:
                                   newList.append(item)
              
              return newList


       @staticmethod
       def getFloat(strConfig):

              if isfloat(strConfig):
                     return float(strConfig)
              else:
                     return None