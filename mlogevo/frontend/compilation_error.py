

class CompilationError(BaseException):
    def __init__(self, **kwargs):
        # reason / coord required
        self.error_info = kwargs
        super().__init__(kwargs)
    pass
