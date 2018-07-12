class FunctionCall:

    def __init__(self, function_name, params, return_value):
        self.params = params
        self.function_name = function_name
        self.return_value = return_value

    def __str__(self):
        return self.function_name

    def __repr__(self):
        return self.function_name
