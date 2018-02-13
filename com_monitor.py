import queue
import threading
import time

import serial


class ComMonitorThread(threading.Thread):
    """Adopted from https://github.com/eliben/code-for-blog/blob/master/2009/plotting_data_monitor/com_monitor.py 

		A thread for monitoring a COM port. The COM port is 
        opened when the thread is started.
    
        data_q:
            Queue for received data. Items in the queue are
            (data, timestamp) pairs, where data is a binary 
            string representing the received data, and timestamp
            is the time elapsed from the thread's start (in 
            seconds).
        
        error_q:
            Queue for error messages. In particular, if the 
            serial port fails to open for some reason, an error
            is placed into this queue.
        
        port:
            The COM port to open. Must be recognized by the 
            system.
        
        port_baud/stopbits/parity: 
            Serial communication parameters
        
        port_timeout:
            The timeout used for reading the COM port. If this
            value is low, the thread will return data in finer
            grained chunks, with more accurate timestamps, but
            it will also consume more CPU.
    """
    def __init__(   self, 
                    data_q, error_q, send_q,
                    port_num,
                    port_baud,
					port_byte =serial.EIGHTBITS,
                    port_stopbits=serial.STOPBITS_ONE,
                    port_parity=serial.PARITY_NONE,
                    port_timeout=0.1):
        threading.Thread.__init__(self)
        
        self.serial_port = None
        self.serial_arg = dict( port=port_num,
                                baudrate=port_baud,
                                stopbits=port_stopbits,
                                parity=port_parity,
                                timeout=port_timeout)

        self.data_q = data_q
        self.error_q = error_q
        self.send_q = send_q
        self.elapsed = .1
        
        self.alive = threading.Event()
        self.alive.set()
        
    def run(self):
        try:
            if self.serial_port: 
                self.serial_port.close()
            self.serial_port = serial.Serial(**self.serial_arg)
        except: #(serial.SerialException, e):
            self.error_q.put('error')#e.message)
            return
        
        # Restart the clock
        self.start_time = time.process_time()
        while self.alive.isSet():
            # Reading 1 byte, followed by whatever is left in the
            # read buffer, as suggested by the developer of 
            # PySerial.
            # 
            data = self.serial_port.read(1).decode('utf8')
            #data += self.serial_port.read(self.serial_port.inWaiting()).decode('utf8')
            
            if len(data) > 0:
                self.data_q.put((data))

            send_data = get_last_item_from_queue(self.send_q)
			
            if send_data:
                write_string = send_data.encode('utf-8')
                self.serial_port.write(write_string)
                print("sending: %s" % send_data)
             
            
        # clean up
        if self.serial_port:
            self.serial_port.close()

    def join(self, timeout=None):
        self.alive.clear()
        threading.Thread.join(self, timeout)
        
def get_last_item_from_queue(q):
    result = None
    while not q.empty():
        result = q.get(False)
			
    return result
    
def get_all_item_from_queue(q):
    result = []
    while not q.empty():
        result.append(q.get(False))
			
    return result
		
