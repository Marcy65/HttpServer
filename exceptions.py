class MalformedHttpRequest(Exception):
    """
    Raised when the client sends a request that is not well formed
    """

class UnexpectedConnectionClose(Exception):
    """
    Raised when the client asks for the connection to be closed while the server expects data continuation
    """