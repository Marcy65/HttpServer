basic http server written in Python using sockets

it can serve simple static web pages that, by default, are located in a folder called "web_folder" that should be in the same folder as the main python file

however, it's also possible to set a custom folder by setting the HttpServer.web_folder attribute

to remove logs, import logging and pass the required logging level in the constructor

there are some sample web pages in the web_folder folder that were used just for testing