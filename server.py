import pickle
import socket 
import time
import threading
import sys

class Sp:
    def __init__(self,name):
        self.name=name
        self.cache = cache()
    
    def setCache(self, cache):
        self.cache=cache

    def addto_cache(self,line,org,default):
        self.cache.add_line(line,org,default)
       

def cliente(Spp,endereco):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    porta = 1050
    s.bind((endereco, porta ))

    while True:
        (msg, add) = s.recvfrom(1024)

        threading.Thread(target=Spp.responde, args=(msg,add,s,)).start()

def TTZ(Spp,endereco):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    porta = 1060
    s.bind((endereco, porta ))
    s.listen()

    while True:
        connection, add = s.accept()
        threading.Thread(target=TZ, args=(Spp,connection,add,)).start()
        

def TZ(Spp,connection,add):
    None


#existem duas threads uma para tratar dos clientes e uma para tratar dos pedidos de transferencia de zona
def main():
    if len(sys.argv)>2:
        Spp = Sp(sys.argv[1])

        threading.Thread(target=cliente,args=(Spp,sys.argv[2])).start()
        threading.Thread(target=TTZ,args=(Spp,sys.argv[2])).start()
    else:
        print("error with name")

main()