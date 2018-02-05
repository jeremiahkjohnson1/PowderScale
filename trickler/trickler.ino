//constants

//Motor pins

#define IN1 8
#define IN2 9
#define IN3 10
#define IN4 11
boolean Direction = true;
int Steps_Read = 0;
int Steps_Write = 0;
int Steps;
boolean Continuous = false;


const int ledPin = 2; //diagnostic LED
const int switch1_in = 12; //slow switch
const int photo_in = 5; //analog 5

//init changing variables
int buttonState = 0;

//1 second task rate
unsigned long REFRESH_INTERVAL = 900; //micros
unsigned long lastRefreshTime = 0;
unsigned long last_write = 0;

//serial message
const byte buffSize = 40;
char inputBuffer[buffSize];
const char startMarker = '<';
const char endMarker = '>';
byte bytesRecvd = 0;
boolean readInProgress = false;
boolean newDataFromPC = false;
char msg1[buffSize] = {0};


int msg2 = 0;
float msg3 = 0.0; // fraction of servo range to move



void setup() {
  // put your setup code here, to run once:
  //Set pin modes

  pinMode(ledPin, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(switch1_in, INPUT);
  

  //initiate serial comm
  Serial.begin(9600);
}

void loop() {
  // put your main code here, to run repeatedly:
  getDataFromPC();  
  replyToPC();
  buttonState = digitalRead(switch1_in);

  if (buttonState==LOW){
     //turn on
     digitalWrite(ledPin, HIGH);
     //motorControl(1,0); //
     Steps_Write = 200;
     REFRESH_INTERVAL = 900;
     replymanualpc();
     
  } else {
     //turn off

     //if nothing
     digitalWrite(ledPin, LOW);

     if (Steps_Read == 32767){
      Continuous = true; 
     } else {
      Continuous = false;
     }

     if (Continuous == true){
      Steps_Write = 200;
     } else {
      Steps_Write = Steps_Read;
     }
  }
     last_write = micros();
     motorControl(Steps_Write, last_write);  // msg2 is number of steps commanded from PC.  abstracted var name for future msg def



  //stepper(10); //need to update with variable
  
  
}

void motorControl(int Steps_Write, unsigned long last_call){
  int steps_left = Steps_Write;
  while(steps_left>0){
    unsigned long now = micros();
    if(now-lastRefreshTime >= REFRESH_INTERVAL && now-last_call>=REFRESH_INTERVAL)
  {
    //Serial.print(analogRead(photo_in));
    //Serial.print("\n");
    lastRefreshTime = micros();

    stepper(1);
    steps_left--;
  }
  }
  
}

//============

void stepper(int xw){
  for (int x=0;x<xw;x++){
    switch(Steps){
       case 0:
         digitalWrite(IN1, LOW); 
         digitalWrite(IN2, LOW);
         digitalWrite(IN3, LOW);
         digitalWrite(IN4, HIGH);
       break; 
       case 1:
         digitalWrite(IN1, LOW); 
         digitalWrite(IN2, LOW);
         digitalWrite(IN3, HIGH);
         digitalWrite(IN4, HIGH);
       break; 
       case 2:
         digitalWrite(IN1, LOW); 
         digitalWrite(IN2, LOW);
         digitalWrite(IN3, HIGH);
         digitalWrite(IN4, LOW);
       break; 
       case 3:
         digitalWrite(IN1, LOW); 
         digitalWrite(IN2, HIGH);
         digitalWrite(IN3, HIGH);
         digitalWrite(IN4, LOW);
       break; 
       case 4:
         digitalWrite(IN1, LOW); 
         digitalWrite(IN2, HIGH);
         digitalWrite(IN3, LOW);
         digitalWrite(IN4, LOW);
       break; 
       case 5:
         digitalWrite(IN1, HIGH); 
         digitalWrite(IN2, HIGH);
         digitalWrite(IN3, LOW);
         digitalWrite(IN4, LOW);
       break; 
         case 6:
         digitalWrite(IN1, HIGH); 
         digitalWrite(IN2, LOW);
         digitalWrite(IN3, LOW);
         digitalWrite(IN4, LOW);
       break; 
       case 7:
         digitalWrite(IN1, HIGH); 
         digitalWrite(IN2, LOW);
         digitalWrite(IN3, LOW);
         digitalWrite(IN4, HIGH);
       break; 
       default:
         digitalWrite(IN1, LOW); 
         digitalWrite(IN2, LOW);
         digitalWrite(IN3, LOW);
         digitalWrite(IN4, LOW);
       break; 
    }
    
    SetDirection();
  }
} 

//============

void SetDirection(){
if(Direction==1){ Steps++;}
if(Direction==0){ Steps--; }
if(Steps>7){Steps=0;}
if(Steps<0){Steps=7; }
}

//============

void getDataFromPC() {

    // receive data from PC and save it into inputBuffer
    
  if(Serial.available() > 0) {

    char x = Serial.read();

      // the order of these IF clauses is significant
      
    if (x == endMarker) {
      readInProgress = false;
      newDataFromPC = true;
      inputBuffer[bytesRecvd] = 0;
      parseData();
    }
    
    if(readInProgress) {
      inputBuffer[bytesRecvd] = x;
      bytesRecvd ++;
      if (bytesRecvd == buffSize) {
        bytesRecvd = buffSize - 1;
      }
    }

    if (x == startMarker) { 
      bytesRecvd = 0; 
      readInProgress = true;
    }
  }
}

//============
 
void parseData() {

    // split the data into its parts

    //msg1 can be
      //MTRCNTRL
    //msg2
      //number of steps per update cycle
    //msg3
      //REFRESH INTERVAL

    
    
  char * strtokIndx; // this is used by strtok() as an index
  
  strtokIndx = strtok(inputBuffer,",");      // get the first part - the string
  strcpy(msg1, strtokIndx); // copy it to msg1
  
  strtokIndx = strtok(NULL, ","); // this continues where the previous call left off
  msg2 = atoi(strtokIndx);     // convert this part to an integer
  
  strtokIndx = strtok(NULL, ","); 
  msg3 = atof(strtokIndx);     // convert this part to a float

  REFRESH_INTERVAL = msg3;
  Steps = msg2;

}

//============

void replyToPC() {

  if (newDataFromPC) {
    newDataFromPC = false;
    Serial.print("<");
    Serial.print("MTRCNTRL");
    Serial.print(",");
    Serial.print(Steps_Write);
    Serial.print(",");
    Serial.print(REFRESH_INTERVAL);
    Serial.println(">");
  }
}

//============

void replymanualpc(){

    Serial.print("<");
    Serial.print("Man");
    Serial.print(",");
    Serial.print(200);
    Serial.print(",");
    Serial.print(REFRESH_INTERVAL);
    Serial.println(">");
}

