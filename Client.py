from tkinter import *
from tkinter import messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os, subprocess, re
from datetime import datetime
import json

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3
	
	# Initiation..
	def __init__(self, master, serveraddr, serverport,fileName,ip):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = None
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		self.fileName=fileName
		self.my_ip=ip
		self.rtpSocket = None
		self.resposta=None

	def createWidgets(self):
		"""Build GUI."""
		# Create Setup button
		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = "Setup"
		self.setup["command"] = self.setupMovie
		self.setup.grid(row=1, column=0, padx=2, pady=2)
		
		# Create Play button		
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=1, padx=2, pady=2)
		
		# Create Pause button			
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=2, padx=2, pady=2)
		
		# Create Teardown button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=3, padx=2, pady=2)
		
		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 
	
	def setupMovie(self):
		"""Setup button handler."""
		if self.state == self.INIT:
			self.sendRtspRequest(self.SETUP)
			
	# Talvez tenhamos de alterar isto
	def exitClient(self):
		"""Teardown button handler."""
		self.sendRtspRequest(self.TEARDOWN)		
		self.master.destroy() # Close the gui window
		try:
			os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)  # Delete the cache image from video
		except FileNotFoundError:
			pass

	def pauseMovie(self):
		"""Pause button handler."""
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)
	
	def playMovie(self):
		"""Play button handler."""
		if self.state == self.READY:
			# Create a new thread to listen for RTP packets
			self.playEvent = threading.Event()
			self.playEvent.clear()
			self.sendRtspRequest(self.PLAY)
			threading.Thread(target=self.listenRtp).start()
	
	def listenRtp(self):		
		"""Listen for RTP packets."""
		while True:
			try:
				data = self.rtpSocket.recv(20480)
				if data:
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)
					
					currFrameNbr = rtpPacket.seqNum()
										
					if currFrameNbr > self.frameNbr: # Discard the late packet
						print("Current Seq Num: " + str(currFrameNbr))
						self.frameNbr = currFrameNbr
						self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
					else:
						print(f'foram despejados {self.frameNbr - currFrameNbr} pacotes ')
			except Exception as ex:
			 	# Stop listening upon requesting PAUSE or TEARDOWN
				if self.playEvent.isSet():
			 		break
				
			# 	# Upon receiving ACK for TEARDOWN request,
			# 	# close the RTP socket
				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					self.rtpSocket = None
					break
					
	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""
		cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
		file = open(cachename, "wb")
		file.write(data)
		file.close()
		
		return cachename
	
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		photo = ImageTk.PhotoImage(Image.open(imageFile))
		self.label.configure(image = photo, height=288) 
		self.label.image = photo
		
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.rtspSocket.connect((self.serverAddr, self.serverPort))
		except:
			messagebox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)
	
	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""	

		# Setup request
		if requestCode == self.SETUP and self.state == self.INIT:
			threading.Thread(target=self.recvRtspReply).start()
			# Update RTSP sequence number.
			self.rtspSeq += 1
			print('\nSetup event.\n')
			
			# Write the RTSP request to be sent.
			request = {
				'hostname': self.my_ip,
				'stream_name':self.fileName,
				'stream_port': None,
				'state':self.SETUP,
				'latencia': self.medir_latencia(self.serverAddr),
				'path': [self.my_ip],
				'sequenceNumber': self.rtspSeq
			} 
			
			# Keep track of the sent request.
			self.requestSent = self.SETUP
		
		# Play request
		elif requestCode == self.PLAY and self.state == self.READY:
			if self.rtpSocket == None:
				self.openRtpPort()
			# Update RTSP sequence number.
			self.rtspSeq += 1
			print('\nPLAY event\n')
            # Write the RTSP request to be sent.
			request = {
				'hostname': self.my_ip,
				'stream_name':self.fileName,
				'stream_port': self.rtpPort,
				'state':self.PLAY,
				'tempo': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
				'path': self.resposta['path'],
				'sequenceNumber': self.rtspSeq
			} 

            # Keep track of the sent request.
			self.requestSent = self.PLAY 
			self.state = self.PLAYING
		
		# Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			# Update RTSP sequence number.
			self.rtspSeq += 1
			print('\nPAUSE event\n')

            # Write the RTSP request to be sent.
			request = {
				'hostname': self.my_ip,
				'stream_name':self.fileName,
				'stream_port': self.rtpPort,
				'state':self.PAUSE,
				'tempo': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
				'path': self.resposta['path'],
				'sequenceNumber': self.rtspSeq
			} 

            # Keep track of the sent request.
			self.requestSent = self.PAUSE
			self.state = self.READY
			
		# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
			# Update RTSP sequence number.
			self.rtspSeq += 1
			print('\nTEARDOWN event\n')

            # Write the RTSP request to be sent.
			request = {
				'hostname': self.my_ip,
				'stream_name':self.fileName,
				'stream_port': self.rtpPort,
				'state':self.TEARDOWN,
				'latencia': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
				'path': self.resposta['path'],
				'sequenceNumber': self.rtspSeq
			} 
			self.teardownAcked = 1

            # Keep track of the sent request.
			self.requestSent = self.TEARDOWN
		else:
			return
		
		# Send the RTSP request using rtspSocket.
		destAddr = (self.serverAddr, self.serverPort)
		self.rtspSocket.sendto(json.dumps(request).encode('utf-8'), destAddr)

		print('\nData sent: \n')
		print(request)
		print('-------------------------------------')
	
	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		while True:
			reply = self.rtspSocket.recv(1024)
			
			if reply: 
				self.parseRtspReply(reply.decode("utf-8"))
			
			# Close the RTSP socket upon requesting Teardown
			if self.requestSent == self.TEARDOWN:
				self.rtspSocket.shutdown(socket.SHUT_RDWR)
				self.rtspSocket.close()
				break

	def parseRtspReply(self, data):
		"""Parse the RTSP reply from the server."""
		message = json.loads(data)

		#if int(lines[0].split(' ')[1]) == 404 or int(lines[0].split(' ')[1]) == 500:
		#	next_server = self.nextServer(self.serverAddr)
		#	
		#	if next_server is not None:
		#		self.serverAddr, self.serverPort = next_server
		#	else:
		#		print("Não existem servidores com o vídeo disponível.")

		# Process only if the server reply's sequence number is the same as the request's
		if message['sequenceNumber'] == self.rtspSeq:
			session = message['stream_port']
			# New RTSP session ID
			if self.sessionId == 0:
				self.sessionId = session
			
			# Process only if the session ID is the same
			if self.sessionId == session:
				if session != 404: 
					if self.requestSent == self.SETUP:
						# Update RTSP state.
						self.state = self.READY
						print(f"Data received:{message}\n")
						self.resposta=message
						self.rtpPort=message['stream_port']
						# Open RTP port. 
					elif self.requestSent == self.PLAY:
						
						self.state = self.PLAYING
						
						print('\nPLAY sent\n')
					elif self.requestSent == self.PAUSE:
						self.state = self.READY
						
						# The play thread exits. A new thread is created on resume.
						self.playEvent.set()
					elif self.requestSent == self.TEARDOWN:
						self.state = self.INIT
						
						# Flag the teardownAcked to close the socket.
						self.teardownAcked = 1 
	

	

	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""

		# Create a new datagram socket to receive RTP packets from the server
		self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		
		# Set the timeout value of the socket to 0.5sec
		self.rtpSocket.settimeout(0.5)
		
		try:
			print(self.my_ip)
			# Bind the socket to the address using the RTP port given by the client user
			self.rtpSocket.bind((self.my_ip, self.rtpPort))			

			print('\nBind \n')
		except Exception as ex:
			messagebox.showwarning(f'Unable to Bind', f'Unable to bind PORT={self.rtpPort}\nErro:{ex}')

	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		self.pauseMovie()
		if messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
			self.exitClient()
		else: # When the user presses cancel, resume playing.
			self.playMovie()

	def medir_latencia(self,host):
		resultado = subprocess.run(['ping', '-c', '1', host], capture_output=True, text=True, timeout=10)
		match = re.search(r"time=(\d+(\.\d+)?)", resultado.stdout)
		if match:
			return float(match.group(1))
		else:
			return 1000
   

