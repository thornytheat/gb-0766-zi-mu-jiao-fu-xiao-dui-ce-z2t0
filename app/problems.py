class Rejection(Exception):
    def __init__(self, code, text, status=422):
        super().__init__(text)
        self.code = code
        self.status = status
