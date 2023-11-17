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

    def __init__(self,rps,cls,nos,ip,port_flooding):
        self.rps=rps 
        self.cls=cls
        self.nos=nos
        self.my_ip=ip
        self.port_flooding=port_flooding
        self.sockets={}
        self.streams={'videoA':{'stream_port':100}}
        self.streamings={}
        
    def run(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            s.bind((self.my_ip, self.port_flooding))
            s.listen(5)  # Permita até 5 conexões pendentes
            print(f"[{self.my_ip} à escuta em {self.port_flooding}]\n")
            while True:
                client_socket, client_address = s.accept()
                print(f"Conexão estabelecida com {client_address}")
                self.sockets[client_address]={'socket':client_socket,'client':[]}

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
                self.sockets[address]['client'] = [message['hostname']]
                print(f"Recebi: {message} de {address}\n")

                process_message = threading.Thread(target=self.rec, args=(s, message, address))
                process_message.start()

            except Exception as ex:
                # Trate outras exceções não especificadas
                print(f"Erro desconhecido: {ex}\nConeçao com {address} fechada\n")
                self.sockets.pop(address)
                s.close()
                break  # Saia do loop ou tome outras medidas, dependendo do caso

    def rec(self,s,m,address):
        #ja sabe o caminho da stream
        #vai abrir um socket para receber pacotes da stream e enviar para o proximo nodo
        # e vai pedir a stream ou se ja tiver a receber a stream so começa a enviar os pacotes
        if m['state'] == self.PLAY:
            my_index = m['path'].index(self.my_ip)
            if my_index == len(m['path'])-1:
                self.start_stream(m,address)
            else:
                self.wait_stream(s,m,address)
        elif m['state'] == self.SETUP:
            #envia para o nodo anterior o caminho escolhido
            m['saltos']=m['saltos']+1
            m['path'].append(self.my_ip)
            ant_node = m['path'][-2]

            if m['stream_name'] in self.streams.keys():
                m['stream_port']=self.streams[m['stream_name']]['stream_port']
            else:
                m['stream_port']=404
                
            self.send_tcp(m,(ant_node,self.port_flooding ))
    
    def start_stream(self,message,address):
        self.streamings[message['stream_name']]['send_to'].append(address[0])

    def wait_stream(self,s,message,address):
        my_index = message['path'].index(self.my_ip)
        prox_node = message['path'][my_index+1]
        self.streamings[message['stream_name']]['send_to'].append(address[0])
        self.send_tcp(m,(node,port_flooding ))

    def send_stream(self,s,stream,prox_node):
        s.bind((prox_node,message['stream_port']))

        # Socket de envio
        udp_socket_enviar = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Loop principal para receber e enviar mensagens
        while True:
            # Recebe dados do socket (o segundo valor retornado é o endereço
            #  do remetente)
            dados, endereco_remetente = s.recvfrom(1024)

            # Exibe a mensagem recebida
            print(f"Recebido: {dados.decode('utf-8')} de {endereco_remetente}\n")
            for node in self.streamings[stream]['send_to']:
            # Envia a mensagem para os dois destinos diferentes
                udp_socket_enviar.sendto(dados, (node,message['stream_port']))
        
        s.close()
        udp_socket_enviar.close()

    def send_tcp(self,message,address):
        if address in self.sockets.keys():
            s = self.sockets[address]['socket']
            if message['hostname'] not in self.sockets[address]['client']:
                self.sockets[address]['client'].append(message['hostname'])

            message_data = json.dumps(message)
            s.sendto(message_data.encode('utf-8'), address)
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect(address)
            except socket.error as connect_error:
                print(f"Erro ao conectar com {address}: {connect_error}")
                s.close()
                return  None
            self.sockets[address]={'client':[message['hostname']],'socket':s}

            message_data = json.dumps(message)
            s.sendto(message_data.encode('utf-8'), address)

            handle = threading.Thread(target=self.handle_tcp_client, args=(s,address))
            handle.start()
        
        print(f"Envidados: {message} para {address}\n")