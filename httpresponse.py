class HttpResponse:

    def __init__(self):
        
        self.version: str = None
        self.status_code: int = None
        self.status: str = None
        self.headers: dict = {}
        self._content: bytes = None

        return
    
    def to_bytes(self, encoding: str = "utf-8") -> bytes:
        
        result = bytearray(f"{self.version} {self.status_code} {self.status}\r\n", encoding=encoding)

        headers = self.headers

        for k, v in headers.items():
            result.extend(f"{k}: {v}\r\n".encode(encoding=encoding))
        result.extend("\r\n".encode(encoding=encoding))

        if self._content is not None:
            result.extend(self._content)
        
        return bytes(result)
    
    @property
    def content(self) -> bytes:
        return self._content
    
    @content.setter
    def content(self, content: bytes | bytearray | str, encoding: str = "utf-8"):

        if isinstance(content, bytes):
            self._content = content
        elif isinstance(content, bytearray):
            self._content = bytes(content)
        elif isinstance(content, str):
            self._content = content.encode(encoding=encoding)
        else:
            raise TypeError(f"Response content can only be 'bytes', 'bytearray' or 'str', not '{type(content)}'")
        
        self.headers["Content-Length"] = len(self._content)