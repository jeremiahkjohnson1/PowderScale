from threading import Thread
from imutils.video import VideoStream
import argparse
import imutils
import time
import serial
import sys, random
import queue
from numpy import mean

from com_monitor import ComMonitorThread, get_last_item_from_queue 
from com_monitor import get_all_item_from_queue

import cv2

class scale(object):
	def __init__(self):
		self.monitor_active = False
		self.com_monitor = None
		self.data_q = None
		self.error_q = None
		self.send_q = None
		self.endMarker = '>'
		self.startMarker = '<'
		self.newData = False
		self.readInProgress = False
		self.inputBuffer = ''
		self.bytesRecvd = 0
		self.vs  = VideoStream(src=1, usePiCamera=False, resolution=(1366, 768), framerate=32).start()
		self.steps = 0
		self.ardFreqSend =900
		self.captureZero = True
		self.ardSteps = 0
		self.ardUpdate = 900
		
		self.b_x_zero = None
		self.b_y_zero = None
		self.b_w_zero = None
		self.b_h_zero = None
		#self.s_x_zero = []
		#self.s_y_zero = []
		#self.s_w_zero = []
		#self.s_h_zero = []
		
		self.zeroX1 = None
		self.zeroX2 = None
		self.zeroY1 = 20
		
		self.captureZero = False
		self.b_x = []
		self.b_y = []
		self.b_w = []
		self.b_h = []
		#self.s_x = []
		#self.s_y = []
		#self.s_w = []
		#self.s_h = []
		
		self.b_x_mov = None
		self.b_y_mov = None
		self.b_w_mov = None
		self.b_h_mov = None
		#self.s_x_mov = None
		#self.s_y_mov = None
		#self.s_w_mov = None
		#self.s_h_mov = None
		
		self.b_x_movBuf = []
		self.b_y_movBuf = []
		self.b_w_movBuf = []
		self.b_h_movBuf = []
		#self.s_x_movBuf = []
		#self.s_y_movBuf = []
		#self.s_w_movBuf = []
		#self.s_h_movBuf = []
		
		self.movAvgLen = 10
		
		self.beam_cascade = cv2.CascadeClassifier('info-beam/cascade.xml')
		#self.scale_cascade = cv2.CascadeClassifier('info-scale/cascade.xml')
		
		self.adjust = False
		self.adjustInProgress = None
		self.adjustTimeWait = .25
		self.adjustTimestamp = 0
		
		self.time_now = 0
		self.elapsed_time = 0
		 
		self.FASTSTEPS = 12000
		self.FASTWAIT = 900
		self.SLOWSTEPS = 300
		self.SLOWWAIT = 2000
		
		
	def read_serial_data(self):
		
		qdata = get_all_item_from_queue(self.data_q)
		
		for i in range(len(qdata)):
			if qdata[i] == self.endMarker:
				self.readInProgress = False
				self.newData = True
				#print('received from ard ' + self.inputBuffer)
				self.parseData()
				
			if self.readInProgress:
				self.inputBuffer=self.inputBuffer+(qdata[i])
				
			if qdata[i] == self.startMarker:
				self.readInProgress = True;
				self.inputBuffer = ''
	def write_serial_data(self, send_steps, update_freq):
		msg = "<MtrCntl," +str(send_steps) + "," + str(update_freq) +">"
		self.send_q.put(msg)
				
	def parseData(self):
		inputMsg = self.inputBuffer.split(",")
		self.ardMsg = inputMsg[0]
		self.ardSteps = inputMsg[1]
		self.ardUpdate = inputMsg[2]
		self.newData = False
		
		

	def start(self):
		""" Start the monitor: com_monitor thread and the update
			timer
		"""
		if self.com_monitor is not None :
			return
        
		self.data_q = queue.Queue()
		self.error_q = queue.Queue()
		self.send_q = queue.Queue()
		self.com_monitor = ComMonitorThread(
			self.data_q,
			self.error_q,
			self.send_q,
			'/dev/ttyACM0',9600)
		self.com_monitor.start()
        
		com_error = get_last_item_from_queue(self.error_q)
		if com_error is not None:
			self.com_monitor = None

		self.monitor_active = True      
		
		self.stream()

	def stream(self):
		i = 0
		self.start_time = time.process_time()
		self.read_serial_data()
		
		while True:
			
			self.processFrame()
			
			cv2.imshow("Frame", self.frame)

			key = cv2.waitKey(1) & 0xFF

			#if q was pressed break
			if key== ord("q"):
				break
			elif key== ord("z"):
				self.captureZero = True
			elif key == ord("g"):
				self.steps = 1000
				self.ardFreqSend = 900
				self.write_serial_data(self.steps, self.ardFreqSend)
				
			elif key == ord("h"):
				self.steps = 300
				self.ardFreqSend = 2000
				self.write_serial_data(self.steps, self.ardFreqSend)
			elif key == ord("n"):
				self.adjust = True
			
			self.time_now = time.process_time()	
			self.elapsed_time = self.time_now + self.start_time	
			
			if self.adjust:
				self.motorControl()
		
		
			if  self.elapsed_time>.25:
				self.read_serial_data()
				#msg = "<MtrCntl," +str(self.steps) + "," + str(self.ardFreqSend) +">"
				#self.send_q.put(msg)
				self.start_time = time.process_time()
				self.steps = 0
				i+=1
				if self.b_y_zero:
					print("y: %i   zero: %i" % (self.b_y_mov, self.b_y_zero))
				#print(self.b_y_mov)
				#print(self.b_y_zero)

		self.on_stop()
		
	def motorControl(self):
		elapsed = self.time_now - self.adjustTimestamp
		
		if elapsed > self.adjustTimeWait:
			if self.b_y_mov > self.b_x_zero + 20:
				self.steps = 32767
				self.ardFreqSend = self.FASTWAIT
				self.adjustTimeWait = .1
				
			elif self.b_y_mov>self.b_y_zero + 10:
				self.steps = self.FASTSTEPS
				self.ardFreqSend = self.SLOWWAIT
				self.adjustTimeWait = 0.5
				
			elif self.b_y_mov>self.b_y_zero + 1:
				self.steps = self.SLOWSTEPS
				self.ardFreqSend = self.SLOWWAIT
				self.adjustTimeWait = 0.8
			else:
				self.steps = 0
				self.ardFreqSend = 900
				self.adjust = False
				self.adjustTimeWait = 0.5
			self.adjustTimestamp = time.process_time()
		self.write_serial_data(self, self.steps, self.ardFreqSend)
		
	def capture_zero(self):
		num_b = len(self.b_x)
		#num_s = len(self.s_x)
		self.b_x_zero = int(sum(self.b_x)/num_b)
		self.b_y_zero = int(sum(self.b_y)/num_b)
		self.b_w_zero = int(sum(self.b_w)/num_b)
		self.b_h_zero = int(sum(self.b_h)/num_b)
		#self.s_x_zero = sum(self.s_x)/num_s
		#self.s_y_zero = sum(self.s_y)/num_s
		#self.s_w_zero = sum(self.s_w)/num_s
		#self.s_h_zero = sum(self.s_h)/num_
		
		self.zeroX1 = self.b_x_zero - self.b_w_zero
		self.zeroX2 = self.b_x_zero + self.b_w_zero
		self.zeroY1 = self.b_y_zero + int(self.b_h_zero/2)
		
		self.captureZero = False
		self.b_x = []
		self.b_y = []
		self.b_w = []
		self.b_h = []
		#self.s_x = []
		#self.s_y = []
		#self.s_w = []
		#self.s_h = []
		line = ("%i,%i,%i,%i\n" % (self.b_x_zero, 	self.b_y_zero,self.b_w_zero,self.b_h_zero))#,self.s_x_zero,self.s_y_zero,self.s_w_zero,self.s_h_zero))
		with open("params.dat", 'a') as fp:
			fp.write(line)
			
	def processFrame(self):
		#grab the frame and reside to width of 400 pixels
			x1 = 0
			x2 = 0
			y1 = 0
			y2 = 0
			self.frame = self.vs.read()
			gray_image = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
			beams = self.beam_cascade.detectMultiScale(gray_image)
			#scales = self.scale_cascade.detectMultiScale(gray_image)
			
				
			
			for (b_x, b_y, b_w, b_h) in beams:
				
				
				self.b_x_mov = self.movingAverage(b_x, self.b_x_movBuf, self.movAvgLen)
				self.b_y_mov = self.movingAverage(b_y, self.b_y_movBuf, self.movAvgLen)
				self.b_w_mov = self.movingAverage(b_w, self.b_w_movBuf, self.movAvgLen)
				self.b_h_mov = self.movingAverage(b_h, self.b_h_movBuf, self.movAvgLen)
				
				if self.captureZero:	
					self.b_x.append(b_x)
					self.b_y.append(b_y)
					self.b_w.append(b_w)
					self.b_h.append(b_h)
				
			#for (s_x, s_y, s_w, s_h) in scales:
				
				#if self.captureZero:
					#self.s_x.append(s_x)
					#self.s_y.append(s_y)
					#self.s_w.append(s_w)
					#self.s_h.append(s_h)
					
				#self.s_x_mov = self.movingAverage(s_x, self.s_x_movBuf, self.movAvgLen)
				#self.s_y_mov = self.movingAverage(s_y, self.s_y_movBuf, self.movAvgLen)
				#self.s_w_mov = self.movingAverage(s_w, self.s_w_movBuf, self.movAvgLen)
				#self.s_h_mov = self.movingAverage(s_h, self.s_h_movBuf, self.movAvgLen)
				
			if self.b_y_zero:
				cv2.line(self.frame, (self.zeroX1,self.zeroY1),(self.zeroX2,self.zeroY1),(0,0,255),5)
			
			if self.b_x_mov:
				cv2.rectangle(self.frame, (self.b_x_mov,self.b_y_mov), (self.b_x_mov+self.b_w_mov, self.b_y_mov+self.b_h_mov), (0,255,0),2)
				x1 = self.b_x_mov-int(self.b_w_mov/2)
				x2 = self.b_x_mov+int(self.b_w_mov/2)
				y1 = self.b_y_mov+int(self.b_h_mov/2)
				y2 = y1
				
				cv2.line(self.frame, (x1,y1),(x2,y2),(0,255,0),3)
				
			
			#if self.s_x_mov:
				#cv2.rectangle(self.frame, (self.s_x_mov,self.s_y_mov), (self.s_x_mov+self.s_w_mov, self.s_y_mov+self.s_h_mov), (255,0,0),2)
					
			if self.captureZero and len(self.b_x)>30:
				self.capture_zero()
		
			#self.writeData()
			
	def writeData(self):
		timestamp = time.process_time()
		
		try:
			line = ("%f,%i,%i,%i,%i,%i,%i\n" % (timestamp,self.b_x_mov, self.b_y_mov,self.b_w_mov,self.b_h_mov, self.ardSteps, self.steps))
		
			
			with open ("scale_tracking.csv", 'a') as f:	
				f.write(line)
		
		except:
			pass	
			
			
	def movingAverage(self, j,buf, buflen):
		if len(buf) < buflen:
			buf.append(j)
			
		else:
			last = buf.pop(0)
			buf.append(j)
			
		movAvg = int(sum(buf)/len(buf))
		return movAvg
		
		
	def on_stop(self):
		if self.com_monitor is not None:
			self.com_monitor.join(0.01)
			self.com_monitor = None
		#cleanup
		cv2.destroyAllWindows()
		self.vs.stop
			

def main():
	s = scale()
	s.start()

if __name__ == '__main__':
	main()
