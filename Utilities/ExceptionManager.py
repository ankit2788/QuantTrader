class MissingColumnException(Exception):

    def __init__(self, columnName):

        self.message = f'{columnName} not available'
        super().__init__(self.message)

    def __str__(self):
        return f'{self.message}'



class MissingArgumentException(Exception):

    def __init__(self, argumentName):

        self.message = f'{argumentName} not available'
        super().__init__(self.message)

    def __str__(self):
        return f'{self.message}'


class IncorrectObjectTypeException(Exception):

    def __init__(self, requiredObjectType):

        self.message = f'Object required of type {requiredObjectType}'
        super().__init__(self.message)

    def __str__(self):
        return f'{self.message}'
