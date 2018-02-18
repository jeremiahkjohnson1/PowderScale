from threading import Thread
from imutils.video import VideoStream
from imutils.video import FPS
import argparse
import imutils
import time
import os
import cv2

beam_cascade = cv2.CascadeClassifier('info-beam/cascade.xml')
#scale_cascade = cv2.CascadeClassifier('info-scale/cascade.xml')
false_pos_dir = 'FalseBeams/'
manual_pos_dir = 'ManualBeams/'
mode = 'capture'
ix = 0
iy = 0
drawing = False

def getCoordinates(x,y,w,h,ratio, img):
	height, width = img.shape[:2]
	
	desired_height = w/ratio

	if desired_height > h:
		actual_width = w
		diff = int((desired_height-h)/2)
		y_desired = y-diff
		actual_height = h+diff
		
		if y_desired+actual_height>height:
			actual_y = height-actual_height
		elif y_desired<0:
			actual_y = 0
		else:
			actual_y = y_desired
		actual_x = x
	

	elif desired_height<h:
		actual_height = int(desired_height)
		desired_width = int(h*ratio)
		diff = int((desired_width-w)/2)
		x_desired = x-diff
		actual_width = w+diff
		if x_desired+actual_width>width:
			actual_x = width-actual_width
		elif x_desired<0:
			actual_x= 0
		else:
			actual_x = x_desired
		actual_y = y
	else:
		actual_x = x
		actual_y=y
		actual_width = w
		actual_height = h

	coords = [actual_x, actual_y, actual_width, actual_height]
	return coords
	
	
def get_images(tmp_dir):

	imgs = []
	for img in os.listdir(tmp_dir):
		fid, fext = os.path.splitext(img)
		
		if fext == '.jpg':
			fid = tmp_dir + img
			imgs.append(fid)
	return imgs
	
def get_roi(event,x,y,flags,param):
	global frame, clone

	if event == cv2.EVENT_LBUTTONDOWN:
		savefalsepos(x,y,beams,clone)

	if event == cv2.EVENT_RBUTTONDOWN:
		savemanualpos(x,y,beams,clone)
		
def savemanualpos(x1,y1,beams,clone,draw = True):
	global manual_pos_dir
	img_num = 0
	print('length: ',len(beams))
	if len(beams)>0:
		for x,y,w,h in beams:
			in_beam = (x1>x and x1<x+w and y1>y and y1<y+h)
			
		
			if in_beam or draw:
				coords = getCoordinates(x,y,w,h,1.7, clone)
				fid = find_fid(manual_pos_dir)
			
				x_crop = coords[0]
				y_crop = coords[1]
				w_crop = coords[2]
				h_crop = coords[3]
				crop_img = clone[y_crop:y_crop+h_crop, x_crop:x_crop+w_crop]
				cv2.imwrite(fid, crop_img)
				line = ("%s 1 0 0 %i %i\n" % (fid, w_crop, h_crop))
				with open('manual_beams.txt','a') as f:
						f.write(line)
		
		
def savefalsepos(x1,y1,beams,clone):
	global false_pos_dir
	img_num = 0
	
	for x,y,w,h in beams:
		in_beam = (x1>x and x1<x+w and y1>y and y1<y+h)
		
		
		if in_beam:
			fid = find_fid(false_pos_dir)
			crop_img = clone[y-10:y+h+10, x-10:x+w+10]
			cv2.imwrite(fid, crop_img)
			line =fid + '\n'
			with open('manual_false_beams.txt','a') as f:
					f.write(line)
			
def find_fid(false_pos_dir):
	img_num = 0
	
	base = 'capture_'
	found = False
	
	while found == False:
		try_fid = ('%s%s%s%s' %(false_pos_dir,base,str(img_num),'.jpg'))
		print("Searching for: %s" % try_fid)
		if os.path.exists(try_fid): 
			img_num = img_num + 1
		else:
			found = True
			print("found")
	
	return try_fid
		

def resize():
	global frame,mode,beams, clone
	vs  = VideoStream(src=0, usePiCamera=False, resolution=(1366, 768), framerate=32).start()
	
	#fps = FPS()
	#fps.start()
	#stream = cv2.VideoCapture(1)
	#stream.set(3, 640)
	#stream.set(4, 480)
	img = 1005
	show = True
	start_time = time.process_time()
	#num_frames = 0
	while True:
		
		#grab the frame and reside to width of 400 pixels
		frame = vs.read()
		gray_image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		clone = gray_image.copy()
		
		beams = beam_cascade.detectMultiScale(gray_image)
		#scales = scale_cascade.detectMultiScale(gray_image)
		if show:
			for (x, y, w, h) in beams:
				cv2.rectangle(frame, (x,y), (x+w+20, y+h+20), (0,255,0),2)
			#for (x, y, w, h) in scales:
				#cv2.rectangle(frame, (x,y), (x+w+20, y+h+20), (255,0,0),2)

			#print('%i, %i' %(w,h))
	
		cv2.imshow("Frame", frame)
		
		if mode == 'draw':
			cv2.setMouseCallback("Frame", draw_roi)
		else:
			cv2.setMouseCallback("Frame", get_roi)

		key = cv2.waitKey(1) & 0xFF
		#num_frames += 1
		#if q was pressed break
		if key== ord("q"):
			break
		elif key==ord("c"):
			name = "TmpImg/"+str(img)+'.jpg'
			img = img + 1
			cv2.imwrite(name, gray_image)
		elif key == ord("s"):
			if mode == 'draw':
				mode = 'capture'
			else:
				mode = 'draw'
			
		#fps.update()
	#cleanup
	#fps.stop
	#stop_time = time.process_time()
	#fps = 30/(stop_time - start_time)
	#print("[INFO] approx FPS: {:.2f}".format(fps))
	cv2.destroyAllWindows()
	vs.stop
	
def draw_roi(event,x,y,flags,param):
	global frame, clone, ix, iy, drawing

	if event == cv2.EVENT_LBUTTONDOWN:
		drawing = True
		ix,iy = x,y

	elif event == cv2.EVENT_MOUSEMOVE:
		if drawing == True:
			cv2.rectangle(frame,(ix,iy),(x,y),(0,255,0),5)

	elif event == cv2.EVENT_LBUTTONUP:
		drawing = False
		ix1,iy1 = x,y
		cv2.rectangle(frame,(ix,iy),(x,y),(0,255,0),5)
		
		x1 = min(ix, ix1)
		x2 = max(ix, ix1)
		y1 = min(iy, iy1)
		y2 = max(iy, iy1)
		w = x2-x1
		h = y2-y1
		
		beams = [[x1, y1, w, h]]
		print("drawing done...sending to save")
		savemanualpos(x,y,beams,clone,draw =True)
		
		#coords = getCoordinates(x1,y1,w,h, 1.7, frame)

if __name__ == '__main__':
	resize()

