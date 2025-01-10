
class InvalidClientInput(Exception):
    def __init__(self, err_msg="input provided by client is invalid"):
        super().__init__(err_msg)
