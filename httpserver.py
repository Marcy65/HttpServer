import socket
import threading
import os
import logging
from pathlib import Path
from httprequest import HttpRequest
from httpresponse import HttpResponse
from exceptions import MalformedHttpRequest, UnexpectedConnectionClose

class HttpServer:

    def __init__(self, host: str = "0.0.0.0", port: int = 80, logging_level = logging.INFO):
        
        self.host = host
        self.port = port
        self.default_page = "/index.html"
        self.web_folder = os.path.join(Path(__file__).parent.absolute(), "web_folder")
        self._socket: socket.socket = None

        logging.basicConfig(
            level=logging_level,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )
        
        self._logger = logging.getLogger(__name__)

        return
    
    def serve(self):

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self._socket.bind((self.host, self.port))
        self._socket.listen(5)
        self._logger.info(f"Serving {self.host}:{self.port}")

        while True:
            
            client_connection, client_address = self._socket.accept()
            self._logger.info(f"{client_address[0]}:{client_address[1]}: Accepted connection")

            client_thread = threading.Thread(target=self._handle_client_connection, args=(client_connection, client_address))
            client_thread.start()

        return

    def _handle_client_connection(self, connection: socket.socket, address):

        connection.settimeout(30)

        try:
            keep_alive = True
            while keep_alive:
                
                recv_buffer = bytearray()
                recv_bufsize = 1024
                # Keep listening until a valid end of headers sequence is received or the connection is closed
                while b"\r\n\r\n" not in recv_buffer:
                    recv_chunk = connection.recv(recv_bufsize)
                    if recv_chunk:
                        recv_buffer.extend(recv_chunk)
                    else:
                        return
                
                headers_end = recv_buffer.find(b"\r\n\r\n") + 4
                request = HttpServer._parse_headers(recv_buffer[:headers_end])
                recv_buffer = recv_buffer[headers_end:]

                if "Transfer-Encoding" in request.headers and request.headers["Transfer-Encoding"] == "chunked":
                    request.raw_body, request.body = HttpServer._parse_chunked_encoding(recv_buffer, connection)

                if "Content-Length" in request.headers and "Transfer-Encoding" not in request.headers:
                    request.raw_body, request.body = HttpServer._parse_content_length(recv_buffer, connection, request)

                if request.body is not None:
                    body_end = len(request.raw_body)
                    recv_buffer = recv_buffer[body_end:]
                
                if "Connection" in request.headers and request.headers["Connection"] == "close":
                    keep_alive = False

                response = self._handle_request(request)
                self._logger.info(f"{address[0]}:{address[1]}: {request.method} {request.path} {response.status_code} {response.status}")
                
                connection.sendall(response.to_bytes())

        except socket.timeout:
            self._logger.info(f"{address[0]}:{address[1]}: Connection timed out")

        except MalformedHttpRequest:
            self._logger.warning(f"{address[0]}:{address[1]}: Client sent a malformed request")
        
        except UnexpectedConnectionClose:
            self._logger.warning(f"{address[0]}:{address[1]}: Connection was closed unexpectedly")

        finally:
            connection.shutdown(socket.SHUT_RDWR)
            connection.close()
            self._logger.info(f"{address[0]}:{address[1]} Connection closed")

        return
    
    @staticmethod
    def _parse_headers(headers: bytearray) -> HttpRequest:
        
        try:

            request_line_start = 0
            request_line_end = headers.find(b"\r\n")
            request_line = headers[request_line_start:request_line_end]
            method, path, version = request_line.split(b" ", maxsplit=2)

            header_lines_start = request_line_end + 2
            header_lines_end = headers.find(b"\r\n\r\n")
            header_lines = headers[header_lines_start:header_lines_end]
            header_lines = header_lines.splitlines()

            headers = {}
            for header in header_lines:
                key, value = header.split(b": ", maxsplit=1)
                headers[key.decode()] = value.decode()

            request = HttpRequest()
            request.method = method.decode()
            request.path = path.decode()
            request.version = version.decode()
            request.headers = headers

        except:
            raise MalformedHttpRequest()

        return request
    
    @staticmethod
    def _parse_chunked_encoding(recv_buffer: bytearray, connection: socket.socket) -> tuple[bytearray]:

        body = bytearray()
        content_start = 0
        chunk_length_start = content_start

        while True:
            
            chunk_length_end = recv_buffer.find(b"\r\n", chunk_length_start)
            recv_bufsize = 4096
            while chunk_length_end == -1:
                recv_chunk = connection.recv(recv_bufsize)
                if recv_chunk:
                    recv_buffer.extend(recv_chunk)
                    chunk_length_end = recv_buffer.find(b"\r\n", chunk_length_start)
                else:
                    raise UnexpectedConnectionClose()
            
            chunk_length = recv_buffer[chunk_length_start:chunk_length_end]
            chunk_length = int(chunk_length, base=16)

            if chunk_length == 0:
                break

            chunk_start = chunk_length_end + 2
            chunk_end = chunk_start + chunk_length

            recv_bufsize = 4096
            while len(recv_buffer) < chunk_end:
                recv_chunk = connection.recv(recv_bufsize)
                if recv_chunk:
                    recv_buffer.extend(recv_chunk)
                else:
                    raise UnexpectedConnectionClose()

            body.extend(recv_buffer[chunk_start:chunk_end])
            chunk_length_start = chunk_end + 2

        content_end = chunk_length_end + 4
        raw_body = recv_buffer[content_start:content_end]

        return (raw_body, body)
    
    def _parse_content_length(recv_buffer: bytearray, connection: socket.socket, request: HttpRequest) -> tuple[bytearray]:

        content_length = int(request.headers["Content-Length"])
        content_start = 0
        content_end = content_start + content_length

        recv_bufsize = 4096
        while len(recv_buffer) < content_end:
            recv_chunk = connection.recv(recv_bufsize)
            if recv_chunk:
                recv_buffer.extend(recv_chunk)
            else:
                raise UnexpectedConnectionClose()
        
        raw_body = recv_buffer[content_start:content_end]
        body = raw_body
        
        return (raw_body, body)

    def _handle_request(self, request: HttpRequest) -> HttpResponse:

        requested_file = request.path
        if requested_file == "/":
            requested_file = self.default_page
        
        requested_file = requested_file.lstrip("/")
        requested_path = os.path.abspath(os.path.join(self.web_folder, requested_file))

        response = HttpResponse()
        response.version = "HTTP/1.1"
        response.headers["Server"] = "HttpServer/1.0"

        if request.method.upper() not in ["GET"]:
            response.status_code = 405
            response.status = "Method Not Allowed"
            response.headers["Content-Type"] = "text/html; charset=utf-8"
            response.content = f"""
            <!DOCTYPE HTML">
            <html><head>
            <title>405 Method Not Allowed</title>
            </head><body>
            <h1>405 Method Not Allowed</h1>
            <p>The method <code>{request.method}</code> is inappropriate for this URL.</p>
            </body></html>
            """.encode(encoding="utf-8")

            return response
            
        try:
            # Check whether the requested file is within the specified web directory folder
            if not os.path.commonpath([self.web_folder, requested_path]) == self.web_folder:
                raise FileNotFoundError()

            with open(requested_path, "rb") as f:
                requested_content = f.read()
        except FileNotFoundError:
            response.status_code = 404
            response.status = "Not Found"
            response.headers["Content-Type"] = "text/html; charset=utf-8"
            response.content = f"""
            <!DOCTYPE HTML">
            <html><head>
            <title>404 Not Found</title>
            </head><body>
            <h1>404 Not Found</h1>
            <p>The requested URL was not found on this server.</p>
            </body></html>
            """.encode(encoding="utf-8")

            return response
        
        response.status_code = 200
        response.status = "OK"
        response.content = requested_content

        response.headers["Content-Type"] = HttpServer.get_mime_type(requested_path)

        return response
    
    @staticmethod
    def get_mime_type(file_path: str) -> str:

        mime_types = {
            ".html": "text/html",
            ".htm": "text/html",
            ".txt": "text/plain",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".xml": "application/xml",
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".ico": "image/x-icon",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff",
            ".svg": "image/svg+xml", 
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
            ".mp4": "video/mp4",
            ".avi": "video/x-msvideo", 
            ".mov": "video/quicktime",
            ".wmv": "video/x-ms-wmv", 
            ".zip": "application/zip",
            ".tar": "application/x-tar", 
            ".gz": "application/gzip",
            ".7z": "application/x-7z-compressed", 
            ".csv": "text/csv",
            ".ppt": "application/vnd.ms-powerpoint",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".doc": "application/msword", 
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
            ".xls": "application/vnd.ms-excel",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".jsonl": "application/jsonlines",
            ".webp": "image/webp",
            ".bin": "application/octet-stream",
            ".exe": "application/octet-stream"
        }

        extension = os.path.splitext(file_path)[1]
        
        return mime_types.get(extension.casefold(), "application/octet-stream")