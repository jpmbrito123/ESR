from datetime import datetime, time, timedelta
import json
import os
import re
import socket
import sys
import threading
import time
import logging
from tkinter import Tk
from logging import FileHandler
from socket import SO_REUSEADDR, SOL_SOCKET

class Rp:
    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3
    SETUP_REPLY = 4

    def __init__(self,rps,cls,nos,ip,port_flooding):
        self.rps=rps 
        self.cls=cls
        self.nos=nos
        self.my_ip=ip
        self.port_flooding=port_flooding
        self.sockets={}
        self.streamings={'videoA':{'stream_port':2000,'come_from_path':[self.my_ip,"10.0.1.10"],'send_to':[],'clients':{},'state':self.SETUP}}
        #self.streamings={}
        
    def run(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            s.bind((self.my_ip, self.port_flooding))
            s.listen(5)  # Permita até 5 conexões pendentes
            print(f"[{self.my_ip} à escuta em {self.port_flooding}]\n")
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
                print(f"Erro desconhecido: {ex}\nConeçao com {address} fechada\n\n")
                s.close()
                break  # Saia do loop ou tome outras medidas, dependendo do caso

    def rec(self,s,m,address):
        #ja sabe o caminho da stream
        #vai abrir um socket para receber pacotes da stream e enviar para o proximo nodo
        # e vai pedir a stream ou se ja tiver a receber a stream so começa a enviar os pacotes
        if m['state'] == self.PLAY:
            my_index = m['path'].index(self.my_ip)
            self.streamings[m['stream_name']]['send_to'].append(address[0])
            if self.streamings[m['stream_name']]['state']==self.SETUP_REPLY:
                    message=m.copy()
                    message['path']=self.streamings[message['stream_name']]['come_from_path']
                    self.send_tcp(message,(message['path'][1],self.port_flooding))

        elif m['state'] == self.SETUP:
            #envia para o nodo anterior o caminho escolhido
            m['saltos']=m['saltos']+1
            m['path'].append(self.my_ip)
            ant_node = m['path'][-2]

            if m['stream_name'] in self.streamings.keys():
                m['stream_port']=self.streamings[m['stream_name']]['stream_port']
                if self.streamings[m['stream_name']]['state']==self.SETUP:
                    message=m.copy()
                    message['path']=self.streamings[message['stream_name']]['come_from_path']
                    self.send_tcp(message,(message['path'][1],self.port_flooding))
                #if m['hostname'] not in self.streamings[m['stream_name']]['clients'].keys():
                self.streamings[m['stream_name']]['clients'][m['hostname']]=m['path']
                self.send_tcp(m,(ant_node,self.port_flooding ))
            else:
                m['stream_port']=404
                self.send_tcp(m,(ant_node,self.port_flooding ))
        elif m['state'] == self.SETUP_REPLY:
            m['path']=self.streamings[m['stream_name']]['clients'][m['hostname']]
            m['state']=self.SETUP

            self.streamings[m['stream_name']]['state']=self.SETUP_REPLY
            s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            send_stream = threading.Thread(target=self.send_stream, args=(s1,m['stream_name'],self.streamings[m['stream_name']]['come_from_path'][1]))
            send_stream.start()

            ant_node = m['path'][-2]
            self.send_tcp(m,(ant_node,self.port_flooding ))

    def send_stream(self, s, stream, ant_node):
        try:
            stream_port = self.streamings[stream]['stream_port']
            print(f"[A abrir socket para receber stream de [{(ant_node, stream_port)}]\n")
            s.bind((self.my_ip, stream_port))
            
            udp_socket_enviar = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            print(f"[Socket de stream aberta de {self.my_ip}] para [{(ant_node, stream_port)}]\n")
            while True:
                try:
                    dados, endereco_remetente = s.recvfrom(20480)
                    
                    for node in self.streamings[stream]['send_to']:
                        try:
                            udp_socket_enviar.sendto(dados, (node, stream_port))
                        except socket.error as sendto_error:
                            print(f"Erro ao enviar para {node}: {sendto_error}\n")
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
        message_data = json.dumps(message)
        if address[0] in self.sockets.keys():
            s = self.sockets[address[0]]['socket']
            if message['hostname'] not in self.sockets[address[0]]['client']:
                self.sockets[address[0]]['client'].append(message['hostname'])

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

            s.sendto(message_data.encode('utf-8'), address)

            handle = threading.Thread(target=self.handle_tcp_client, args=(s,address))
            handle.start()
        
        print(f"\n[{self.my_ip}] enviou para [{address}]")
        print(f"{message}\n")