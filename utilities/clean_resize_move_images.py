import os
import xml.etree.ElementTree as ET
import numpy as np
import shutil
import cv2


tmp_dir = 'TmpImg/'
beam_dir = 'Beam/'
scale_dir = 'Scale/'
bad_dir = 'Bad/'

scale_pics_to_use = 10
beam_pics_to_use  = 10 # 1/X number of beam pics to use in negative samples for scale training



#p res = 300x180, new set = 240x102
#p ratio = 1.703, new set = 2.4

#s res = 280x175, new set = 350x160
#s ratio = 1.64, new set = 2.89

s_ratio = 2.6
p_ratio = 1.7


def resize():
	
	cleanup()
	test = [];
	for img in os.listdir(tmp_dir):
		fid, fext = os.path.splitext(img)

		
		if fext == '.xml':
			filename=tmp_dir + img
			image_file = tmp_dir + fid + '.jpg'
			data = readxml(filename)
			
			tmp_return = processImageFiles(data, image_file, fid)
	inspect('info_s.dat')
	inspect('info_p.dat')
def cleanup():
	directories = [beam_dir, scale_dir, bad_dir]

	for d in directories:
		try:
			shutil.rmtree(d)
		except:
			print("error removing %s"% d)

	files = ['info_s.dat', 'info_p.dat', 'bg_n_p.txt', 'bg_n_s.txt', 'bad_objects.txt']

	for f in files:
		try:
			os.remove(f)
		except:
			print("error removing %s"% f)
	for d in directories:
		try:
			os.mkdir(d)
		except:
			print("could not create dir %s"% d)




def processImageFiles(data, image_file, fid):

	nn = 1
	scale_track = 1
	beam_track = 1
	
	for line in data:
		
		class_obj = line[0]
		x = line[1]
		y = line[2]
		w = line[3]
		h = line[4]

		if class_obj == 'n':
			main_file =  openimage(image_file)
			n_file = bad_dir + fid + '_' + str(nn)+'.jpg'
			nn = nn+1
			crop_img = main_file[y:y+h, x:x+w]
			
			cv2.imwrite(n_file, crop_img)
			line =n_file + '\n'
			with open('bg_n_s.txt','a') as f:
				f.write(line)
			with open('bg_n_p.txt','a') as f:
				f.write(line)

		elif class_obj == 'ns':
			main_file =  openimage(image_file)
			n_file = bad_dir + fid + '_' + str(nn)+'.jpg'
			nn = nn+1
			crop_img = main_file[y:y+h, x:x+w]
			tmp_r = w/h;
			dim=(100, int(100/tmp_r))
			resized = cv2.resize(crop_img, dim, interpolation= cv2.INTER_AREA)
			cv2.imwrite(n_file, resized)
			line =n_file + '\n'
			with open('bg_n_s.txt','a') as f:
				f.write(line)

		elif class_obj == 's':
			main_file =  openimage(image_file)
			
			coords = getCoordinates(x,y,w,h,s_ratio, main_file) #x,y,w,h
			s_file = scale_dir + fid +'.jpg'
			x_crop = coords[0]
			y_crop = coords[1]
			w_crop = coords[2]
			h_crop = coords[3]

			crop_img = main_file[y_crop:y_crop+h_crop, x_crop:x_crop+w_crop]
			cv2.imwrite(s_file, crop_img)
			line =s_file + '\n'

			if scale_track == 1:
				with open('bg_n_s.txt','a') as f:
					f.write(line)
			else:
				scale_track += 1
				
				if scale_track > scale_pics_to_use:
					scale_track = 1


			line = ("%s 1 0 0 %i %i\n" % (s_file, w_crop, h_crop))

			with open('info_s.dat','a') as f:
				f.write(line)
			
		elif class_obj == 'p':
			main_file =  openimage(image_file)
			
			coords = getCoordinates(x,y,w,h,p_ratio, main_file) #x,y,w,h
			p_file = beam_dir + fid +'.jpg'
			x_crop = coords[0]
			y_crop = coords[1]
			w_crop = coords[2]
			h_crop = coords[3]

			crop_img = main_file[y_crop:y_crop+h_crop, x_crop:x_crop+w_crop]
			cv2.imwrite(p_file, crop_img)
			line =p_file + '\n'
			if beam_track == 1:
				with open('bg_n_p.txt','a') as f:
					f.write(line)
			else:
				beam_track += 1
				
				if beam_track > beam_pics_to_use:
					beam_track = 1
			

			line = ("%s 1 0 0 %i %i\n" % (p_file, w_crop, h_crop))

			with open('info_p.dat','a') as f:
				f.write(line)
		else:
			print(class_obj)
			with open('bad_objects.txt','a') as f:
				f.write(image_file + '\n')

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

		
	

def openimage(image_file):
	frame = cv2.imread(image_file)
	return frame

def readxml(fid):
    tree = ET.parse(fid)
    root = tree.getroot()
    #root[0].text #folder  #for c in root: c.attribute, c.tag
    data = []
	

    for c in root:
    
        if 'object' in c.tag:
            if c[0].text == 'p': #pointer
                Pxmin = int(c[4][0].text) #0 xmin, 1 ymin, 2 xmax, 3 xmax  
                Pymin = int(c[4][1].text)
                Pxmax = int(c[4][2].text)
                Pymax = int(c[4][3].text)
                Pw = Pxmax-Pxmin
                Ph = Pymax-Pymin
                data.append(['p', Pxmin, Pymin, Pw, Ph])

            elif c[0].text == 's': #scale
                Sxmin = int(c[4][0].text) #0 xmin, 1 ymin, 2 xmax, 3 xmax  
                Symin = int(c[4][1].text)
                Sxmax = int(c[4][2].text)
                Symax = int(c[4][3].text)
                Sw = Sxmax-Sxmin
                Sh = Symax-Symin
                data.append(['s', Sxmin, Symin, Sw, Sh])
            elif c[0].text == 'n': #scale
                Nxmin = int(c[4][0].text) #0 xmin, 1 ymin, 2 xmax, 3 xmax  
                Nymin = int(c[4][1].text)
                Nxmax = int(c[4][2].text)
                Nymax = int(c[4][3].text)
                Nw = Nxmax-Nxmin
                Nh = Nymax-Nymin
                data.append(['n', Nxmin, Nymin, Nw, Nh])
            elif c[0].text == 'ns': #scale
                Nsxmin = int(c[4][0].text) #0 xmin, 1 ymin, 2 xmax, 3 xmax  
                Nsymin = int(c[4][1].text)
                Nsxmax = int(c[4][2].text)
                Nsymax = int(c[4][3].text)
                Nsw = Nsxmax-Nsxmin
                Nsh = Nsymax-Nsymin
                data.append(['ns', Nsxmin, Nsymin, Nsw, Nsh])
            else:
                Nxmin = int(0) #0 xmin, 1 ymin, 2 xmax, 3 xmax  
                Nymin = int(0)
                Nxmax = int(0)
                Nymax = int(0)
                Nw = 0
                Nh = 0
                obj_name = c[0].text
                data.append([obj_name, Nxmin, Nymin, Nw, Nh])

    return data
def inspect(inspect_file):
	print(inspect_file)

	with open(inspect_file) as fp:
		line = fp.readline()
		
		while line:
			try:
				vals = line.split( )
				img = cv2.imread(vals[0])
				w = img.shape[1]
				h = img.shape[0]
				
				if int(vals[2])>0:
				    print("High X")
				    print(vals[0])
				elif int(vals[3])>0:
				    print("High Y")
				    print(vals[0])
				if int(vals[4])!=w:
				    print("mismatch width")
				    print(vals[0])
				    print(vals[4])
				    print(vals[5])
				    print(w)
				    print(h)
				if int(vals[5])!=h:
				    print("mismatch height")
				    print(vals[0])
				line = fp.readline()
			except:
				print('Error with file %s'% vals[0])
				line = fp.readline()
if __name__ == '__main__':
	resize()
