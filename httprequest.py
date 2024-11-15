class HttpRequest:

    def __init__(self):
        
        self.method: str = None
        self.path: str = None
        self.version: str = None
        self.headers: dict = {}
        self.raw_body: bytearray = None
        self.body: bytearray = None

        return