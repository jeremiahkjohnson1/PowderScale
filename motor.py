from threading import Thread
from imutils.video import VideoStream
from transitions import Machine
from transitions.extensions.states import add_state_features,Timeout
import time
import sys
import queue
import logging

from com_monitor import ComMonitorThread, get_last_item_from_queue 
from com_monitor import get_all_item_from_queue

import cv2

LOG_FORMAT = "%(asctime)s , %(message)s"
LEVEL = logging.DEBUG

logging.basicConfig(filename = "motor_log.Log", level = LEVEL, format = LOG_FORMAT)

#################################################
#################################################
#    Defining object 'Object" to be tracked

#################################################
#################################################		
		

class Object(object):

	def __init__(self):
	
		#filtered object position tracker  
		#one item for each attribute of a rectangle object size (x,y,w,h)
		self.mov_avg = [None, None, None, None]
		
		#empty array for moving average buffer.  
		#one list for each attribute of a rectangle object size (x,y,w,h)
		self.mov_avg_buff = [[],[],[],[]]  
		
		#averaging window length.  If only one object is detected, windown length is number of frames
		self.buff_len = 10
		
		#read last know zero point from params file
		self.zero =self.get_zeros()
		
		#initialize buffer for capturing new zero points - on user request
		self.zero_points = []
		
		
	def update(self, o):
		buff = self.mov_avg_buff
		buff_len = self.buff_len

		if len(o)==0:
			o=[[None,None,None,None]]
			print('no object')
		tmp_buff =[[obj[i]  for obj in o] for i in range(4)]
		#update filtered position
		avg =  [[self.movingAverage(tmp_buff[i][j],buff[i],buff_len) for i in range(len(tmp_buff))] for j in range(len(tmp_buff[0]))][-1]
				
		self.mov_avg = avg
		self.mov_avg_buff = buff
		return avg		

	def movingAverage(self,j,buf, buflen):
		"""
			Moving average to track object position.  Called from Update.
			Inputs are j - current instant position
				buf - buffer array
				buflen - max size of buffer
		"""
			
		if j and len(buf)<buflen:
			buf.append(j)
		#FIFO buffer	
		elif j:
			last = buf.pop(0)
			buf.append(j)
		elif len(buf)>0:
			last = buf.pop(0)
		
		if len(buf)>0:	
			movAvg = int(sum(buf)/len(buf))
			return movAvg#, buf
		else:
			return None
			
	def get_zeros(self):
		"""
			Read last known zero point
			
			TODO Only save last point instead of appending
		"""
		
		zeros = []
		try:
			with open('params.dat') as fp:
				lines = fp.readlines()
			last_line = lines[-1]
			params = last_line.split(',')
			x=int(params[0])
			y=int(params[1])
			w=int(params[2])
			h=int(params[3])
			X1 = x-w   #wide zero line
			X2 = x+w	#wide zero line
			Y = y+int(h/2) #zero through middle of rectangle
			
			zeros.append(y)
			zeros.append(X1)
			zeros.append(X2)
			zeros.append(Y)
			

		except:
			zeros = None
			
		return zeros
	def capture_zero(self):
		
		if self.mov_avg[0]:
			x = self.mov_avg[0]
			y = self.mov_avg[1]
			w = self.mov_avg[2]
			h = self.mov_avg[3]

			self.zero_points.append([x,y,w,h])
			
		else:
			return False
			 
		if len(self.zero_points)>=30:
			x_0_sum = 0
			y_0_sum = 0
			w_0_sum = 0
			h_0_sum = 0
			
			for point in self.zero_points:
				x_0_sum += point[0]
				y_0_sum += point[1]
				w_0_sum += point[2]
				h_0_sum += point[3]
			n = len(self.zero_points)
			y_0 = int(y_0_sum/n)
			x_0 =  int(x_0_sum/n)
			w_0 =  int(w_0_sum/n)
			h_0 =  int(h_0_sum/n)
			
			X1_0 = x_0-w_0   #wide zero line
			X2_0 = x_0+w_0	#wide zero line
			Y_0 = y_0+int(h_0/2) #zero through middle of rectangle	
			
			self.zero = [y_0, X1_0,X2_0,Y_0]
			
			return True
		else:
			return False
		
		
#################################################
#################################################
#    Defining State Machine

#################################################
#################################################		
		

@add_state_features(Timeout)
class CustomStateMachine(Machine):
	pass

class MotorMachine(CustomStateMachine):
	#https://github.com/pytransitions/transitions/issues/198
	
	def __init__(self,video_source):
		
		states = ['off','on','continuous','trickle', 'shutting_down', 'zero',
			 {'name': 'waiting', 'timeout': 0.5, 'on_timeout': 'timeout'}]
		
		self.logger = logging.getLogger()


		
		Machine.__init__(self, states=states,initial='off')
		#machine.add_transition('heat', 'solid', 'gas', conditions='is_flammable')
		self.add_transition(trigger='autoPressed', source='*',dest='on')
		#self.add_transition(trigger='update', source='*',dest='on',conditions='is_zerod')
		self.add_transition(trigger='update', source='on',dest='off',conditions='is_at_target')
		#self.add_transition(trigger='update', source='continuous',dest='off',conditions='is_at_target')
		self.add_transition(trigger='update', source='on',dest='continuous',conditions='is_far')
		self.add_transition(trigger='update', source='on',dest='trickle',conditions='is_near')
		self.add_transition(trigger='update', source='continuous',dest='off',conditions='is_at_target')
		self.add_transition(trigger='update', source='continuous',dest='trickle',conditions='is_near')
		self.add_transition(trigger='update', source='trickle',dest='off',conditions='is_at_target')
		self.add_transition(trigger='update', source='waiting',dest='continuous', conditions='is_manual')
		self.add_transition(trigger='shutdown', source='*',dest='shutting_down',after='on_stop')
		self.add_transition(trigger='zeroPressed', source='*',dest='zero')
		self.add_transition(trigger='zeroComplete', source='zero',dest='off')
		self.add_transition(trigger='touch', source = ['zero','off'], dest = '=')
		self.add_transition(trigger='wait', source='trickle',dest='waiting')
		
		#auto key dictionary
			#0: no key/unknown key
			#1: n - auto
			#2: g - fast manual
			#3: h - slow manual
			#13: z - zero
			#14: q - quit/shutdown
			#15: unknown/error
			
		self.auto_key = {ord('n'):1,ord('g'):2, ord('h'):3,ord('z'):13, ord('q'):14,}
		
		self.auto = 0
		
		self.auto_events = {0:'',1:self.autoPressed, 2:'', 3:'', 13:self.zeroPressed, 14:self.shutdown}
		self.next_event = self.touch
		
		self.beam_tracker = Object()
		self.vs  = VideoStream(src=video_source, usePiCamera=False, resolution=(640, 480), framerate=30).start()
		
		self.beam_cascade = cv2.CascadeClassifier('info-beam/cascade.xml')
				
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
		
		if com_error:
			print("Error Communicationg")
			
		self.inputBuffer = ''
		self.endMarker = '>'
		self.startMarker = '<'
		self.newData = False
		self.readInProgress = False
		self.inputBuffer = ''
		
		
			
	###############
	##  Conditions
	##############
	 
	def is_auto_pressed(self):
		
		if self.auto==1:
			print("checking auto")
			return True
		else:
			return False
			
	def is_zero_pressed(self):
		if self.auto==13:
			return True
		else:
			return False
			
	def is_manual(self):
		print("checking")
		if self.auto==2:
			return True
		else:
			return False
			
	def is_shutdown_request(self):
		
		if self.auto==14:
			return True
			print("Shutting Down Now")
		else:
			return False
			
	def is_at_target(self):
		if self.distance <= 1:
			return True
		else:
			return False
		
	def is_far(self):
		if self.distance>20:
			return True
		else:
			return False
	def is_near(self):
		if self.distance<=20 and not self.is_at_target():
			return True
		else:
			return False
	def is_zerod(self):
		if self.beam_tracker.zero[0]:
			return True
		else:
			return False
   
	###############
	##  Call Backs
	##############
	def on_enter_continuous(self):
		print ("\tcontinuous mode")
		self.write_serial_data(send_steps=32767, update_freq=900)
		self.next_event = self.update
		
	def on_enter_zero(self):
		done = self.beam_tracker.capture_zero()
		if not done:
			self.next_event =  self.touch 
		else: self.next_event = self.off
		
	def on_enter_off(self):
			self.next_event = self.touch

	def on_enter_waiting(self):
			self.next_event = self.update
			
	def on_enter_on(self):
		self.next_event = self.update
	#def on_enter_on(self, auto, distance):
		#print("\ton")
		#if self.is_far(auto,distance):
		#	self.to_continuous(auto, distance)
		#elif self.is_at_target(auto,distance):
		#	self.to_off(auto,distance)
		#elif self.is_near(auto, distance):
		#	self.to_trickle(auto, distance)
	
	def on_enter_trickle(self):
		print("\ttrickling")
		self.write_serial_data(send_steps=300, update_freq=2000)
		self.next_event = self.wait
			
	def on_exit_continuous(self):
		print ("\texiting continuous")
		self.write_serial_data(send_steps=0, update_freq=900)
		
	def timeout(self):
		print("Timeout!")
		print(self.auto)
		print(self.distance)
		self.to_on()
		
	def on_stop(self):  # to do: add state, transition, on_enter to shut down arduino
		if self.com_monitor is not None:
			self.com_monitor.join(0.01)
			self.com_monitor = None
		#cleanup
		cv2.destroyAllWindows()
		self.vs.stop
		
	###############
	##  State Handling
	##############
	
	
	def run(self):
		while True:
			self.read_serial_data(self.data_q, self.readInProgress, self.newData)
			self.next_frame()
			
			print(self.state)
			if self.beam_tracker.mov_avg[0] and self.beam_tracker.zero:
				self.distance = self.beam_tracker.mov_avg[1]- self.beam_tracker.zero[1]
			else:
				self.distance = None
			
			next_event = self.eventHandler()
			
			if next_event:
				next_event()
	
	def eventHandler(self):
		
		next_event = ''
		if self.auto:  #manual override of current states
				next_event =self.auto_events[self.auto]
		
		if next_event:
			return next_event
		else:
			return self.next_event
		
				
			
	
	###############
	##  Image Processing
	##############
		
	def next_frame(self):
		new_frame = self.processFrame()
			
		cv2.imshow("Frame", new_frame)
		
		key = cv2.waitKey(1) & 0xFF
		
		#print(key)	 
		try:
			self.auto = self.auto_key[key]
			#print(self.auto, key)
		except:
			self.auto =0 #unknown
			#print("unknown")
			
		
	def processFrame(self):
			frame = self.vs.read()
			beams = self.detect(frame)
			
			z = self.beam_tracker.zero
		
			x,y,w,h = self.beam_tracker.update(beams)
			#print('%i %i %i %i' % (x,y,w,h))
			
			if z:
				self.drawline(frame, (z[1],z[3]),(z[2],z[3]),(0,0,255),5)
			
			if x and y and w and h:
				#cv2.rectangle(frame, (x,y), (x+w), y+h), (0,255,0),2)
				x1 = x-int(w/2)
				x2 = x+int(w/2)
				y1 = y+int(h/2)
				y2 = y1
				
				self.drawline(frame, (x1,y1),(x2,y1),(0,255,0),3)
		
			return frame
			
	def drawline(self,f,points1,points2, color, linewidth):
		cv2.line(f, points1,points2,color,linewidth)
		
	def detect(self,frame):
		gray_image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		beams = self.beam_cascade.detectMultiScale(gray_image,minNeighbors=1,)
		
		if len(beams) == 0:
			return []
		
		return beams
		
	
	###############
	##  Arduino Communication
	##############	
		
	def read_serial_data(self, data_q, readInProgress, newData):
		readInProgress = self.readInProgress
		qdata = get_all_item_from_queue(data_q)
		
		for i in range(len(qdata)):
			if qdata[i] == self.endMarker:
				readInProgress = False
				newData = True
				print('received from ard ' + self.inputBuffer)
				#self.parseData()
				
			if readInProgress:
				self.inputBuffer=self.inputBuffer+(qdata[i])
				
			if qdata[i] == self.startMarker:
				self.readInProgress = True;
				self.inputBuffer = ''
				
	def write_serial_data(self, send_steps, update_freq):
		msg = "<MtrCntl," +str(send_steps) + "," + str(update_freq) +">"
		self.send_q.put(msg)
	
				
	def parseData(self):
		try:
			inputMsg = self.inputBuffer.split(",")
			self.ardMsg = inputMsg[0]
			self.ardSteps = inputMsg[1]
			self.ardUpdate = inputMsg[2]
		except:
			print("error parsing serial")
			print(self.inputBuffer)
		self.newData = False
	
		

def main():
	m = MotorMachine(3)
	m.run()

if __name__ == '__main__':
	main() 
