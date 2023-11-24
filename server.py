import socket
from socket import SO_REUSEADDR, SOL_SOCKET
from PIL import Image, ImageTk
from ServerWorker import ServerWorker

def stream(streamer_info):
    # streamer_info = (node_id, port_streaming, is_server, MAX_CONN, file_id, message['nearest_server'])
    nodes_interested = []

    rtsp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    rtsp_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    rtsp_socket.bind((streamer_info[0], streamer_info[1]))

    rtsp_socket.listen(5)
    print(f"[{streamer_info[0]} à escuta em {streamer_info[1]}]\n")
    # Receber informação sobre cliente (ip,porta) através da sessão RTSP/TCP
    while True:
        client_socket, client_address = rtsp_socket.accept()
        client_info = {}
        client_info = {'rtspSocket': client_socket,'address':client_address}
        print(f"Conexão estabelecida com {client_info['address']}\n")
        ServerWorker(client_info).run()

    rtsp_socket.close()
