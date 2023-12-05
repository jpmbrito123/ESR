from datetime import datetime, time, timedelta
import json
import os
import re
import socket
import sys
import threading
import time
import subprocess, re
import logging
from tkinter import Tk
from logging import FileHandler
from socket import SO_REUSEADDR, SOL_SOCKET

#import Client
from server import Server
from Client import Client
from Rp import Rp
port_flooding =12345

class Nodo:
    my_ip=None
    streamings={} 
    my_type=None
    rp = None
    cls = []
    nos = []
    sv = []
    sockets = {}
    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3

    def parseFile(self,node):
        with open('/home/core/Desktop/ESR/fase2/test.json', 'r') as arquivo:
            # Carregar os dados do arquivo JSON para um dicionário
            dados = json.load(arquivo)[node]
        self.rp = dados["RP"]
        self.cls = dados["CL"]
        self.nos = dados["NO"]
        self.sv = dados["SV"]
        self.my_type = dados["type"]
        self.my_ip = dados["ip"]
            

    def run(self,name):
        self.parseFile(name)

        if self.my_type == "Rp":
            rp = Rp(self.cls,self.nos,self.my_ip,port_flooding)
            rp.run()
        elif self.my_type == "Server":
            Server(self.rp,self.my_ip,port_flooding,"/home/core/Desktop/ESR/fase2/"+name+"/")
        elif self.my_type == "Client":
            if os.environ.get('DISPLAY', '') == '':
                print('Nenhum display encontrado... Usar DISPLAY :0.0')
                os.environ.__setitem__('DISPLAY', ':0.0')
            
            root = Tk()
            app = Client(root, self.nos[0], port_flooding,"videoA.Mjpeg",self.my_ip)
            app.master.title("RTPClient")	
            root.mainloop()
        else:
            self.listening()
    
    def listening(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', port_flooding))
            s.listen(5)  # Permita até 5 conexões pendentes
            print(f"[{self.my_ip} à escuta em {port_flooding}]\n")
            while True:
                client_socket, client_address = s.accept()
                print(f"Conexão estabelecida com {client_address}\n")
                self.sockets[client_address[0]]={'port':client_address[1],'socket':client_socket,'client':[]}

                handle = threading.Thread(target=self.handle_tcp_client, args=(client_socket,client_address))
                handle.start()
        except Exception as e:
            print(f"Erro durante o listen: {e}")
        finally:
            s.close()


    def handle_tcp_client(self,s,address):
        while True:
            try:
                message = json.loads(s.recv(1024).decode('utf-8'))
                self.sockets[address[0]]['client'] = [message['hostname']]
                print(f"Recebi: {message} de {address}\n")

                process_message = threading.Thread(target=self.rec, args=(s, message, address))
                process_message.start()

            except Exception as ex:
                # Trate outras exceções não especificadas
                print(f"Erro desconhecido: {ex}\nConeçao com {address} fechada\n")
                self.sockets.pop(address[0])
                s.close()
                break  # Saia do loop ou tome outras medidas, dependendo do caso

    def rec(self,s,m,address):
        #ja sabe o caminho da stream
        #vai abrir um socket para receber pacotes da stream e enviar para o proximo nodo
        # e vai pedir a stream ou se ja tiver a receber a stream so começa a enviar os pacotes
        if m['state'] == self.PLAY:
            my_index = m['path'].index(self.my_ip)
            if(m['stream_name'] not in self.streamings.keys()):
                    self.streamings[m['stream_name']]={'ip':m['path'][my_index+1],"port":m['stream_port'],'send_to':[[m['path'][my_index-1],1]],'pause':[]}
                    #criar socket para enviar a stream
                    s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    send_stream = threading.Thread(target=self.send_stream, args=(s1,m['stream_name'],m['path'][my_index-1]))
                    send_stream.start()
            else:
                add=False
                for no in self.streamings[m['stream_name']]['send_to']:
                    if no[0]==address[0]:
                        no[1]+=1
                        add = True          
                        break
                if not add:
                    self.streamings[m['stream_name']]['send_to'].append([address[0],1])
                if m['hostname'] in self.streamings[m['stream_name']]['pause']:
                    self.streamings[m['stream_name']]['pause'].remove(m['hostname'])

            self.send_tcp(m,(m['path'][my_index+1],port_flooding ))
        elif m['state'] == self.SETUP:
            #envia para o nodo anterior o caminho escolhido

            if m['stream_port']:
                node = m['path'].index(self.my_ip)
                ant_node = m['path'][node+1]
                prox_node = m['path'][node-1]

                self.send_tcp(m,(prox_node,port_flooding ))
            #esta a procura de um caminho
            #se tiver a stream manda a mensagem de volta com a porta se nao tiver manda aos nodos vizinhos execeto o anterior
            elif self.my_ip not in m['path']:
                m['path'].append(self.my_ip)
                for nodes in [self.nos,[self.rp],self.sv]:
                    for node in nodes:
                        if node!=address[0] and node!="":
                            message = m.copy()
                            if (m['stream_name'] not in self.streamings) or (node!=self.streamings[m['stream_name']]['ip']) :
                                message['latencia']+=self.medir_latencia(node)
                            self.send_tcp(message,(node,port_flooding ))
        elif m['state'] == self.PAUSE:
            my_index = m['path'].index(self.my_ip)
            prox_node = m['path'][my_index+1]
            for no in self.streamings[m['stream_name']]['send_to']:
                    if no[0]==address[0]:
                        if no[1]==1:
                            self.streamings[m['stream_name']]['send_to'].remove(no)
                        else:    
                            no[1]-=1
                        break
            self.streamings[m['stream_name']]['pause'].append(m['hostname'])           
            self.send_tcp(m,(prox_node,port_flooding ))
        elif m['state'] == self.TEARDOWN:
            my_index = m['path'].index(self.my_ip)
            prox_node = m['path'][my_index+1]
            for no in self.streamings[m['stream_name']]['send_to']:
                    if no[0]==address[0]:
                        if no[1]==1:
                            self.streamings[m['stream_name']]['send_to'].remove(no)
                        else:    
                            no[1]-=1
                        break          
            self.send_tcp(m,(prox_node,port_flooding ))

    def send_stream(self, s, stream, prox_node):
        try:
            stream_port = self.streamings[stream]['port']
            s.bind(('0.0.0.0', stream_port))
            
            udp_socket_enviar = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            print(f"\n[Socket de stream aberta de {self.my_ip}] para [{prox_node}]")
            while True:
                try:
                    if len(self.streamings[stream]['send_to'])==0 and len(self.streamings[stream]['pause'])==0:
                        s.close()
                        udp_socket_enviar.close()
                        self.streamings.pop(stream)
                        print(f"Sockets udp para a stream {stream} fechada \n")
                        break
                    dados, endereco_remetente = s.recvfrom(20480)
                    
                    for node in self.streamings[stream]['send_to']:
                        try:
                            udp_socket_enviar.sendto(dados, (node[0], stream_port))
                        except socket.error as sendto_error:
                            print(f"Erro ao enviar para {node[0]}: {sendto_error}\n")
                            # Adicione lógica de tratamento de erro específica para falha ao enviar para um nó
                except socket.error as recvfrom_error:
                    print(f"Erro ao receber dados: {recvfrom_error}\n")
                    # Adicione lógica de tratamento de erro específica para falha ao receber dados

        except socket.error as bind_error:
            print(f"Erro ao fazer bind do socket: {bind_error}\n")

        except Exception as ex:
            print(f"Erro desconhecido: {ex}\n")

        finally:
            s.close()

    def send_tcp(self,message,address):
        if address[0] in self.sockets.keys():
            s = self.sockets[address[0]]['socket']
            if message['hostname'] not in self.sockets[address[0]]['client']:
                self.sockets[address[0]]['client'].append(message['hostname'])

            message_data = json.dumps(message)
            s.sendto(message_data.encode('utf-8'), (address[0],self.sockets[address[0]]['port']))
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect(address)
                print(f"Conexão estabelecida com {address}\n")
            except Exception as ex:
                print(f"Erro ao conectar com {address}: {ex}\n")
                s.close()
                return  None
      
            self.sockets[address[0]]={'port':address[1],'client':[message['hostname']],'socket':s}
            message_data = json.dumps(message)
            s.sendto(message_data.encode('utf-8'), address)

            handle = threading.Thread(target=self.handle_tcp_client, args=(s,address))
            handle.start()
        
        print(f"\n[{self.my_ip}] enviou para [{address}]")
        print(f"{message}\n")
        
    def medir_latencia(self,host):
        resultado = subprocess.run(['ping', '-c', '2', host], capture_output=True, text=True, timeout=10)
        match = re.search(r"time=(\d+(\.\d+)?)", resultado.stdout)
        if match:
            return float(match.group(1))
        else:
            return 1000
   

    


nodo = Nodo()

nodo.run(sys.argv[1])
