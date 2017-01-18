from ... import matchers, utils


@matchers.matcher()
class Any:
    """
    filter any raw text
    """
    type = 'text.Any'

    def __init__(self):
        pass

    def validate(self, message):
        return utils.safe_get(message, 'data', 'text', 'raw')


@matchers.matcher()
class Equal:
    """
    filter equal raw text (case sensitive)
    """
    type = 'text.Equal'

    def __init__(self, test_string):
        self.test_string = test_string

    def validate(self, message):
        return self.test_string == utils.safe_get(message, 'data', 'text', 'raw')

    def serialize(self):
        return self.test_string

    def deserialize(self, state):
        self.test_string = state

    @staticmethod
    def can_handle(data):
        return utils.is_string(data)

    @staticmethod
    def handle(data):
        return Match(data)


@matchers.matcher()
class EqualCaseIgnore:
    """
    filter equal raw text (case in-sensitive)
    """
    type = 'text.EqualCaseIgnore'

    def __init__(self, test_string):
        self.test_string = test_string.lower()

    def validate(self, message):
        return self.test_string == utils.safe_get(message, 'data', 'text', 'raw', default='').lower()

    def serialize(self):
        return self.test_string

    def deserialize(self, state):
        self.test_string = state

    @staticmethod
    def can_handle(data):
        return utils.is_string(data)

    @staticmethod
    def handle(data):
        return Match(data)


@matchers.matcher()
class Match:
    type = 'text.Match'

    def __init__(self, test_string):
        self.test_string = test_string

    def validate(self, message):
        return self.test_string == utils.safe_get(message, 'data', 'text', 'raw')

    def serialize(self):
        return self.test_string

    def deserialize(self, state):
        self.test_string = state

    @staticmethod
    def can_handle(data):
        return utils.is_string(data)

    @staticmethod
    def handle(data):
        return Match(data)
