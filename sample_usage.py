from httpserver import HttpServer

host = "0.0.0.0"
port = 80

server = HttpServer(host, port)
server.web_folder = r"C:\Users\Marcello\Downloads\Oxer Free Website Template - Free-CSS.com\oxer-html"

server.serve()