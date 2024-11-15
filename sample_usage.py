from httpserver import HttpServer

host = "0.0.0.0"
port = 80

server = HttpServer(host, port)

server.serve()