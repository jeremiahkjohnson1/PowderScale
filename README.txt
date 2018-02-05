clean_resize_move_images.py
	- if necessary
	- adjust resize values and directories


generate vector 
	opencv_createsamples -info info_p.dat -w 75 -h 45 -vec beam_positives.vec
	opencv_createsamples -info info_s.dat -w 75 -h 28 -vec scale_positives.vec


npos = 575
nneg = 1731

train cascade
	opencv_traincascade -data info-beam -vec beam_positives.vec -bg bg_n_s.txt -numPos 500 -numNeg 1600  -w 75 -h 45 -precalcValBufSize 2048 -precalcIdxBufSize 2048

opencv_traincascade -data info-scale -vec scale_positives.vec -bg bg_n_p.txt -numPos 220 -numNeg 800 -w 75 -h 28



	


useful links:
https://docs.opencv.org/2.4/doc/user_guide/ug_traincascade.html
