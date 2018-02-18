from threading import Thread
from imutils.video import VideoStream
from imutils.video import FPS
import argparse
import imutils
import time
import cv2

beam_cascade = cv2.CascadeClassifier('info-beam/cascade.xml')
#scale_cascade = cv2.CascadeClassifier('info-scale/cascade.xml')


		

def resize():
	vs  = VideoStream(src=1, usePiCamera=False, resolution=(1366, 768), framerate=32).start()
	#fps = FPS()
	#fps.start()
	#stream = cv2.VideoCapture(1)
	#stream.set(3, 640)
	#stream.set(4, 480)
	img = 1005
	show = True
	start_time = time.process_time()
	num_frames = 0
	while num_frames < 30:
		
		#grab the frame and reside to width of 400 pixels
		frame = vs.read()
		gray_image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		beams = beam_cascade.detectMultiScale(gray_image)
		#scales = scale_cascade.detectMultiScale(gray_image)
		if show:
			for (x, y, w, h) in beams:
				cv2.rectangle(frame, (x,y), (x+w+20, y+h+20), (0,255,0),2)
			#for (x, y, w, h) in scales:
				#cv2.rectangle(frame, (x,y), (x+w+20, y+h+20), (255,0,0),2)

			#print('%i, %i' %(w,h))
	
		cv2.imshow("Frame", frame)

		key = cv2.waitKey(1) & 0xFF
		num_frames += 1
		#if q was pressed break
		if key== ord("q"):
			break
		elif key==ord("c"):
			name = "TmpImg/"+str(img)+'.jpg'
			gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
			img = img + 1
			cv2.imwrite(name, gray)
		#fps.update()
	#cleanup
	#fps.stop
	stop_time = time.process_time()
	fps = 30/(stop_time - start_time)
	print("[INFO] approx FPS: {:.2f}".format(fps))
	cv2.destroyAllWindows()
	vs.stop

if __name__ == '__main__':
	resize()

