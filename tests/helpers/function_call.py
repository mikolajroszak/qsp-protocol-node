####################################################################################################
#                                                                                                  #
# (c) 2018, 2019 Quantstamp, Inc. This content and its use are governed by the license terms at    #
# <https://s3.amazonaws.com/qsp-protocol-license/V2_LICENSE.txt>                                   #
#                                                                                                  #
####################################################################################################


class FunctionCall:

    def __init__(self, function_name, params, return_value):
        self.params = params
        self.function_name = function_name
        self.return_value = return_value

    def __str__(self):
        return self.function_name

    def __repr__(self):
        return self.function_name
