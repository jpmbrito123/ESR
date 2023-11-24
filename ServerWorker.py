from random import randint
import sys, traceback, threading, socket
import json

from VideoStream import VideoStream
from RtpPacket import RtpPacket


class ServerWorker:
    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3

    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    OK_200 = 0
    FILE_NOT_FOUND_404 = 1
    CON_ERR_500 = 2

    clientInfo = {}

    def __init__(self, clientInfo):
        self.clientInfo = clientInfo

    def run(self):
        threading.Thread(target=self.recvRtspRequest).start()

    def recvRtspRequest(self):
        """Receive RTSP request from the client."""
        connSocket = self.clientInfo['rtspSocket']
        while True:
            try:
                data = json.loads(connSocket.recv(1024).decode("utf-8"))
                if data:
                    print(f"Data received:{data}\n")
                    self.processRtspRequest(data)
            except Exception as ex:
                # Trate outras exceções não especificadas
                print(f"Erro desconhecido: {ex}\nConeçao com {self.clientInfo['address']} fechada\n\n")
                self.clientInfo['rtspSocket'].close()
                break  # Saia do loop ou tome outras medidas, dependendo do caso

    def processRtspRequest(self, data):
        """Process RTSP request sent from the client."""
        # Get the request type
        requestType = data['state']

        # Get the media file name
        filename = data['stream_name']

        # Get the RTSP sequence number
        seq = data['sequenceNumber']

        # Process SETUP request
        if requestType == self.SETUP:
            if self.state == self.INIT:
                # Update state
                print("processing SETUP\n")

                try:
                    self.clientInfo['videoStream'] = VideoStream(filename)
                    self.state = self.READY
                except IOError as io:
                    self.state = self.READY
                    print(f"Erro ao abrir ficheiro:{io}")
                    #self.send_tcp(self.FILE_NOT_FOUND_404)

                # Generate a randomized RTSP session ID
                self.clientInfo['session'] = randint(100000, 999999)
                
                # Send RTSP reply
                self.send_tcp(data)

                # Get the RTP/UDP port from the last line
                self.clientInfo['rtpPort'] = data['stream_port']

        # Process PLAY request
        elif requestType == self.PLAY:
            if self.state == self.READY:
                print("processing PLAY\n")
                self.state = self.PLAYING

                # Create a new thread and start sending RTP packets
                self.clientInfo['event'] = threading.Event()
                self.clientInfo['worker'] = threading.Thread(target=self.sendRtp)
                self.clientInfo['worker'].start()

        # Process PAUSE request
        elif requestType == self.PAUSE:
            if self.state == self.PLAYING:
                print("processing PAUSE\n")
                self.state = self.READY

                self.clientInfo['event'].set()

                self.send_tcp(self.OK_200, seq[1])

        # Process TEARDOWN request
        elif requestType == self.TEARDOWN:
            print("processing TEARDOWN\n")

            self.clientInfo['event'].set()

            self.send_tcp(self.OK_200, seq[1])

            # Close the RTP socket
            self.clientInfo['rtpSocket'].close()

    def sendRtp(self):
        """Send RTP packets over UDP."""
        while True:
            self.clientInfo['event'].wait(0.05)

            # Stop sending if request is PAUSE or TEARDOWN
            if self.clientInfo['event'].isSet():
                break

            data = self.clientInfo['videoStream'].nextFrame()
            if data:
                frameNumber = self.clientInfo['videoStream'].frameNbr()
                try:
                    address = self.clientInfo['address'][0]
                    port = int(self.clientInfo['rtpPort'])
                    self.clientInfo['rtpSocket'].sendto(self.makeRtp(data, frameNumber), (address, port))
                except:
                    print("Connection Error")
                # print('-'*60)
                # traceback.print_exc(file=sys.stdout)
                # print('-'*60)

    def makeRtp(self, payload, frameNbr):
        """RTP-packetize the video data."""
        version = 2
        padding = 0
        extension = 0
        cc = 0
        marker = 0
        pt = 26  # MJPEG type
        seqnum = frameNbr
        ssrc = 0

        rtpPacket = RtpPacket()

        rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)

        return rtpPacket.getPacket()

    def send_tcp(self, data):
        self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"\n[Socket de stream aberta para:{self.clientInfo['address']}]")

        data['state']=4
        message_data = json.dumps(data)
        connSocket = self.clientInfo['rtspSocket']
        connSocket.send(message_data.encode('utf-8'))
        
        print(f"\n[] enviei para [{self.clientInfo['address']}]")
        print(f"{data}\n")

    def send(self):
        # Verificar o tipo de solicitação e o estado do cliente
        if self.request_type == self.SETUP and self.state == self.INIT:
            self.handle_setup_request()
        elif self.request_type == self.PLAY and self.state == self.READY:
            self.handle_play_request()
        elif self.request_type == self.PAUSE and self.state == self.PLAYING:
            self.handle_pause_request()
        elif self.request_type == self.TEARDOWN and self.state != self.INIT:
            self.handle_teardown_request()

    def handle_setup_request(self):
        # Incrementar o número de sequência RTSP
        self.rtspSeq += 1
        print('\nSETUP event\n')

        # Construir a solicitação RTSP SETUP
        request = f"""SETUP {self.fileName} RTSP/1.0\r
     CSeq: {self.rtspSeq}\r
     Transport: RTP/UDP; client_port= {self.rtpPort}\r
     \r"""

        # Manter o controle da solicitação enviada
        self.requestSent = self.SETUP

        # Enviar a solicitação RTSP usando rtspSocket
        self.send_rtsp_request(request)

    def handle_play_request(self):
        # Incrementar o número de sequência RTSP
        self.rtspSeq += 1
        print('\nPLAY event\n')

        # Construir a solicitação RTSP PLAY
        request = f"""PLAY {self.fileName} RTSP/1.0\r
     CSeq: {self.rtspSeq}\r
     Session: {self.sessionId}\r
     \r"""

        # Manter o controle da solicitação enviada
        self.requestSent = self.PLAY

        # Enviar a solicitação RTSP usando rtspSocket
        self.send_rtsp_request(request)

    def handle_pause_request(self):
        # Incrementar o número de sequência RTSP
        self.rtspSeq += 1
        print('\nPAUSE event\n')

        # Construir a solicitação RTSP PAUSE
        request = f"""PAUSE {self.fileName} RTSP/1.0\r
     CSeq: {self.rtspSeq}\r
     Session: {self.sessionId}\r
     \r"""

        # Manter o controle da solicitação enviada
        self.requestSent = self.PAUSE

        # Enviar a solicitação RTSP usando rtspSocket
        self.send_rtsp_request(request)

    def handle_teardown_request(self):
        # Incrementar o número de sequência RTSP
        self.rtspSeq += 1
        print('\nTEARDOWN event\n')

        # Construir a solicitação RTSP TEARDOWN
        request = f"""TEARDOWN {self.fileName} RTSP/1.0\r
     CSeq: {self.rtspSeq}\r
     Session: {self.sessionId}\r
     \r"""

        # Manter o controle da solicitação enviada
        self.requestSent = self.TEARDOWN

        # Enviar a solicitação RTSP usando rtspSocket
        self.send_rtsp_request(request)

    def send_rtsp_request(self, request):
        # Enviar a solicitação RTSP usando rtspSocket
        destAddr = (self.serverAddr, self.serverPort)
        self.rtspSocket.sendto(request.encode('utf-8'), destAddr)

        print('\nData sent:\n' + request)
