import time
import cv2
import os


tmp_dir = 'TmpImg/'
false_pos_dir = 'FalseBeams/'

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
		drawing = True
		savefalsepos(x,y,beams,clone)

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
		
	
def run():
	global frame, beams, clone
	beam_cascade = cv2.CascadeClassifier('info-beam/cascade.xml')
	imgs = get_images(tmp_dir)
	offset = 0
	go = True
	i = 0
	while go:
		img = imgs[i]
		offset = 0
		
		frame = cv2.imread(img)
		clone = frame.copy()
		beams = beam_cascade.detectMultiScale(frame)
		
		for (x, y, w, h) in beams:
			cv2.rectangle(frame, (x,y), (x+w+20, y+h+20), (0,255,0),2)
				
		cv2.imshow("Frame", frame)
		cv2.setMouseCallback("Frame", get_roi)
			
		key = cv2.waitKey(1) & 0xFF
		#num_frames += 1
		#if q was pressed break
		if key== ord("q"):
			go = False
		elif key==ord("n"):
			i = i + 1
		elif key == ord("b"):
			i = i -1

			
	cv2.destroyAllWindows()
	
if __name__ == '__main__':
	run()
			
			
		
