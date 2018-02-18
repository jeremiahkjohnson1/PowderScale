import time
import cv2
import os

all_lines = []

files = ['manual_beams.txt', 'manual_false_beams.txt']

for f in files:
	with open(f) as fp:
		lines = fp.readlines()
	for l in lines:
		all_lines.append(l)


for line in all_lines:
	params = line.strip().split(' ')
	img = cv2.imread(params[0])
	gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	cv2.imwrite(params[0], gray_image)
	
	print('%i, %s' %(len(img.shape),params[0]))
		
