class InvalidClientInput(Exception):
    def __init__(self, err_msg="input provided by client is invalid"):
        super().__init__(err_msg)


class UnsupportedColor(Exception):
    def __init__(self, err_msg="The color you chose inst supported"):
        super().__init__(err_msg)


class InvalidRequestFormat(Exception):
    def __init__(self, err_msg="The request packet format is invalid"):
        super().__init__(err_msg)


class InvalidOfferFormat(Exception):
    def __init__(self, err_msg="The offer packet format is invalid"):
        super().__init__(err_msg)