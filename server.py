import socket
import threading
from socket import SO_REUSEADDR, SOL_SOCKET
from PIL import Image, ImageTk
from ServerWorker import ServerWorker
from datetime import datetime
import os
import time
import json

class Server:
    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3
    
    SETUP_REPLY = 4
    SETUP_STREAMS = 5

    def __init__(self,rp,ip,port_flooding,localizaçao):
        self.rp=rp
        self.my_ip=ip
        self.port_flooding=port_flooding

        self.socket=self.connectToServer()
        self.streamings=self.search_streams(localizaçao)
        handle = threading.Thread(target=self.handle_tcp_client, args=(self.socket,)).start()    

    def connectToServer(self):
        rp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        rp_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        rp_socket.connect((self.rp, self.port_flooding))
        return rp_socket

    def search_streams(self,localizaçao):
        arquivos_na_pasta = os.listdir(localizaçao)
        streams={}
        for video in arquivos_na_pasta:
            st = ServerWorker(video,self.rp,self.socket)
            streams[video]=st
        return streams

    def handle_tcp_client(self,s):
        request = {
				'hostname': self.my_ip,
				'stream_name':list(self.streamings.keys()),
                'tempo': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
				'state':self.SETUP_STREAMS
		} 

        destAddr = (self.rp, self.port_flooding)
        self.socket.sendto(json.dumps(request).encode('utf-8'), destAddr)
        
        while True:
            try:
                message = json.loads(s.recv(1024).decode('utf-8'))
                print(f"Recebi: {message} de {(self.rp,self.port_flooding)}\n")
                st = self.streamings[message['stream_name']]
                process_message = threading.Thread(target=st.run, args=(message,)).start()
                
            
            except Exception as ex:
                # Trate outras exceções não especificadas
                print(f"Erro desconhecido: {ex}\nConeçao com {(self.rp,self.port_flooding)} fechada\n\n")
                s.close()

                time.sleep(5)
                self.socket=self.connectToServer()
                break  # Saia do loop ou tome outras medidas, dependendo do caso
