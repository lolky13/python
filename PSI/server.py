import socket
from socket import SHUT_RDWR
import threading
from _thread import *

#messages definition

SERVER_CONFIRMATION = ''#<16-bitové číslo v decimální notaci>\a\b	#Zpráva s potvrzovacím kódem. Může obsahovat maximálně 5 čísel a ukončovací sekvenci \a\b.
SERVER_MOVE	=       '102 MOVE\a\b'.encode('utf-8')	#Příkaz pro pohyb o jedno pole vpřed
SERVER_TURN_LEFT =	'103 TURN LEFT\a\b'.encode('utf-8')	#Příkaz pro otočení doleva
SERVER_TURN_RIGHT =	'104 TURN RIGHT\a\b'.encode('utf-8')	#Příkaz pro otočení doprava
SERVER_PICK_UP =	'105 GET MESSAGE\a\b'.encode('utf-8')	#Příkaz pro vyzvednutí zprávy
SERVER_LOGOUT =	    '106 LOGOUT\a\b'.encode('utf-8')	#Příkaz pro ukončení spojení po úspěšném vyzvednutí zprávy
SERVER_KEY_REQUEST = '107 KEY REQUEST\a\b'  #Žádost serveru o Key ID pro komunikaci
SERVER_OK =	        '200 OK\a\b'.encode('utf-8')	#kladné potvrzení
SERVER_LOGIN_FAILED = '300 LOGIN FAILED\a\b'.encode('utf-8')	#Nezdařená autentizace
SERVER_SYNTAX_ERROR = '301 SYNTAX ERROR\a\b'.encode('utf-8')	#Chybná syntaxe zprávy
SERVER_LOGIC_ERROR = '302 LOGIC ERROR\a\b'.encode('utf-8')   #Zpráva odeslaná ve špatné situaci
SERVER_KEY_OUT_OF_RANGE_ERROR = '303 KEY OUT OF RANGE\a\b'.encode('utf-8')  #Key ID není v očekávaném rozsahu

CLIENT_RECHARGING =	'RECHARGING'	#Robot se začal dobíjet a přestal reagovat na zprávy.
CLIENT_FULL_POWER =	'FULL POWER'	#Robot doplnil energii a opět příjímá příkazy.

CLIENT_USERNAME_LEN = 18
CLIENT_KEY_ID_LEN = 3
CLIENT_CONFIRMATION_LEN = 5
CLIENT_OK_LEN = 10
CLIENT_RECHARGING_LEN = 10
CLIENT_FULL_POWER_LEN = 10
CLIENT_MESSAGE_LEN = 98

CLIENT_KEY = 32037, 29295, 13603, 29533, 21952
SERVER_KEY = 23019, 32037, 18789, 16443, 18189

UNINICIALIZED = 0
UP = 1
RIGHT = 2
DOWN = 3
LEFT = 4


def extract3(data):     #check if the client OK message is fine
    try:
        tmp = data.split(' ')
        if len(tmp) > 3:
            return 9999, 9999, True
        tmp[1] = int(tmp[1])
        tmp[2] = int(tmp[2])
        tmp1 = tmp[0] + ' ' + str(tmp[1]) + ' ' + str(tmp[2])
        if tmp1 != data:
            return 9999, 9999, True
        return tmp[1], tmp[2], False
    except Exception as ex:
        return 9999, 9999, True

def addHash(data):
    hash = 0
    for char in data:
        hash += ord(char)
    hash *= 1000
    hash %= 65536
    return hash

def addClientHash(clientHash, myHash):
    if not clientHash.isdigit():
        return -2, 1
    clientHash = int(clientHash)
    if clientHash < 0 or clientHash > 4:
        return -1, 1
    return (myHash + SERVER_KEY[clientHash]) % 65536, CLIENT_KEY[clientHash]

def cmpHash(data, hash, key):
    data += 65536 - key
    data %= 65536
    return data == hash

def dataWithout(data):
    tmpData = ''
    counter = 0
    for char in data:
        if data[counter] == '\a' and data[counter+1] == '\b':
            return tmpData
        counter += 1
        tmpData += char



class Robot:        #class for navigating the robot to the goal
    def __init__(self):
        self.dir = UNINICIALIZED
        self.preCo = None
        self.preTurn = False
        self.setCourse = False
        self.obs = 0
        self.bounces = 0
        self.start = True
        self.startTurn = False

    def move(self,x,y):
        if x == 0 and y == 0:       #at 0,0
            return SERVER_PICK_UP, False
        if self.start and self.preCo == None:   #second move
            self.preCo = (x,y)
            return SERVER_MOVE, False
        
        if self.start and self.preCo == (x,y):  #third or fourth move
            if self.startTurn:
                self.start = False
                return SERVER_MOVE, False
            self.startTurn = True
            return SERVER_TURN_LEFT, False
        
        self.start = False

        if self.bounces > 19:
            return SERVER_LOGOUT, True
        
        if self.dir == UNINICIALIZED:
            if x > self.preCo[0]:
                self.dir = RIGHT
            elif x < self.preCo[0]:
                self.dir = LEFT
            elif y < self.preCo[1]:
                self.dir = DOWN
            elif y > self.preCo[1]:
                self.dir = UP
        if self.obs > 0:        #dokoncuji obchazeni prekazky na 0
            self.obs -= 1
            if self.obs == 6 or self.obs == 4 or self.obs == 3 or self.obs == 1:
                self.preCo = (x,y)
                return SERVER_MOVE, False
            elif self.obs == 5 or self.obs == 2:
                return SERVER_TURN_RIGHT, False
            return SERVER_TURN_LEFT, False
        
        if self.setCourse:          #druhe otoceni, kdyz jdu od stredu
            self.setCourse = False
            return SERVER_TURN_LEFT, False
        
        if self.preTurn:            #krok po otoceni
            self.preTurn = False
            return SERVER_MOVE, False
        
        if  abs(x) > abs(self.preCo[0]) or abs(y) > abs(self.preCo[1]):     #jdu od stredu, potrebuji se otocit
            self.setCourse = True
            self.preTurn = True
            if self.dir == LEFT:
                self.dir = RIGHT
            elif self.dir == RIGHT:
                self.dir = LEFT
            elif self.dir == UP:
                self.dir = DOWN
            elif self.dir == DOWN:
                self.dir = UP
            self.preCo = (x,y)
            return SERVER_TURN_LEFT, False
        
        if x == 0 and y == self.preCo[1] and x == self.preCo[0]: #obchazim prekazku, ktera je na x == 0
            self.bounces += 1
            self.obs = 7
            return SERVER_TURN_LEFT, False
        
        if y == 0 and y == self.preCo[1] and x == self.preCo[0]: #obchazim prekazku, ktera je na y == 0
            self.obs = 7
            self.bounces += 1
            return SERVER_TURN_LEFT, False
        
        if x == 0:          #jsem na x == 0, tudiz se chci nasmerovat na cil 
            if y > 0:
                if self.dir == LEFT:
                    self.preTurn = True
                    self.dir = DOWN
                    return SERVER_TURN_LEFT, False
                elif self.dir == RIGHT:
                    self.preTurn = True
                    self.dir = DOWN
                    return SERVER_TURN_RIGHT, False
                self.preCo = (x,y)
                return SERVER_MOVE, False
            elif y < 0:
                if self.dir == LEFT:
                    self.preTurn = True
                    self.dir = UP
                    return SERVER_TURN_RIGHT, False
                elif self.dir == RIGHT:
                    self.preTurn = True
                    self.dir = UP
                    return SERVER_TURN_LEFT, False
                self.preCo = (x,y)
                return SERVER_MOVE, False
            
        if y == 0:          #jsem na y == 0, tudiz se chci nasmerovat na cil 
            if x > 0:
                if self.dir == DOWN:
                    self.preTurn = True
                    self.dir = LEFT
                    return SERVER_TURN_RIGHT, False
                elif dir == UP:
                    self.preTurn = True
                    self.dir = LEFT
                    return SERVER_TURN_LEFT, False
                self.preCo = (x,y)
                return SERVER_MOVE, False
            elif x < 0:
                if self.dir == DOWN:
                    self.preTurn = True
                    self.dir = RIGHT
                    return SERVER_TURN_LEFT, False
                elif dir == UP:
                    self.preTurn = True
                    self.dir = RIGHT
                    return SERVER_TURN_RIGHT, False
                self.preCo = (x,y)
                return SERVER_MOVE, False
        
        if x == self.preCo[0] and y == self.preCo[1]:       #naboural jsem do prekazky, ktera je mimo osy
            self.preTurn = True
            self.bounces += 1
            if self.dir == LEFT:
                if y > 0:
                    self.dir = DOWN
                    return SERVER_TURN_LEFT, False
                self.dir = UP
                return SERVER_TURN_RIGHT, False
            if self.dir == RIGHT:
                if y > 0:
                    self.dir = DOWN
                    return SERVER_TURN_RIGHT, False
                self.dir = UP
                return SERVER_TURN_LEFT, False
            if self.dir == DOWN:
                if x > 0:
                    self.dir = LEFT
                    return SERVER_TURN_RIGHT, False
                self.dir = RIGHT
                return SERVER_TURN_LEFT, False
            if self.dir == UP:
                if x > 0:
                    self.dir = LEFT
                    return SERVER_TURN_LEFT, False
                self.dir = RIGHT
                return SERVER_TURN_RIGHT, False
        self.preCo = (x,y)          #kdyz ani jedno nenastalo, tak jdu dal
        return SERVER_MOVE, False
            

def extractData(recData,conn,stage):
    recData = recData.decode('utf-8')
    if recData == '':
        return recData, 0, 0

    while recData[len(recData) - 2] != '\a' or recData[len(recData) - 1] != '\b':
        if '\a\b' not in recData and not checkLength(recData,stage,len(recData)-1):
            return recData, 0, 1
        conn.settimeout(1)
        tmp = conn.recv(1024)
        tmp = tmp.decode('utf-8')
        recData += tmp
    
    counter = 0
    data = ''
    amount = 0
    jo = False
    dataJo = [data]
    while True:
        if recData[counter] == '\a' and recData[counter+1] == '\b':
            if counter == len(recData) - 2 and not amount:
                if not checkLength(data,stage, len(data)):
                    return data, 0, 1
                return data, 0, 0
            if counter == len(recData) - 2 and amount:
                dataJo.append(data)
                return dataJo, amount + 1, 0
            counter += 2    #multiple messages
            amount += 1
            jo = True
        else:
            if jo:
                jo = False
                dataJo.append(data)
                data = ''
            else:
                data += recData[counter]
                counter += 1

def checkLength(data,stage, length):        #kontroluji delku zprav
    #print('check:', data, stage, length)
    if 'RECHARGING' in data or 'FULL POWER' in data:
        return length <= CLIENT_RECHARGING_LEN
    if data == '':
        return True
    if stage == 0:
        return length <= CLIENT_USERNAME_LEN
    if stage == 1:
        return length <= CLIENT_KEY_ID_LEN
    if stage == 2:
        return length <= CLIENT_CONFIRMATION_LEN
    if stage == 3:
        return length <= CLIENT_OK_LEN
    return length <= CLIENT_MESSAGE_LEN

def handleRobot(conn):
    print("connection established")
    nameInt = 0
    hash = 0
    stage = 0
    key = 0
    recharge = False
    mulMsg = False
    data = ''
    arrPos = 1
    arrCnt = 0
    robot = Robot()
    conn.settimeout(1)
    try:
        while True:
            if not mulMsg:
                data = conn.recv(1024)
                tmpData, arrCnt, jo = extractData(data, conn, stage)
            if jo == 1 and stage != 1:
                conn.sendall(SERVER_SYNTAX_ERROR)
                break
            if jo == 1 and stage == 1:
                conn.sendall(SERVER_LOGIN_FAILED)
                break
            if arrCnt:
                mulMsg = True
                data = tmpData[arrPos]
                arrPos += 1
                arrCnt -= 1
                if not arrCnt:
                    arrPos = 1
                    mulMsg = False
            else:
                data = tmpData
                
            print ('data =', data)
            if data == '':
                continue
            if '\a\b' in data:
                data = dataWithout(data)
            if data == CLIENT_RECHARGING:
                conn.settimeout(5)
                recharge = True
                continue
            if data == CLIENT_FULL_POWER and not recharge:
                conn.sendall(SERVER_LOGIC_ERROR)
                break
            if data == CLIENT_FULL_POWER:
                recharge = False
                conn.settimeout(1)
                continue
            if recharge:
                conn.sendall(SERVER_LOGIC_ERROR)
                break

            if stage == 0:      #prijato username
                nameInt = addHash(data)
                msg = SERVER_KEY_REQUEST.encode('utf=8')
                conn.sendall(msg)
                stage += 1
                continue
            if stage == 1:      #prijato key id od klienta
                hash, key = addClientHash(data, nameInt)
                if hash == -2:
                    conn.sendall(SERVER_SYNTAX_ERROR)
                    break
                if hash == -1:
                    conn.sendall(SERVER_KEY_OUT_OF_RANGE_ERROR)
                    break
                conf = str(hash)
                conf += '\a\b'
                conf = conf.encode('utf-8')
                conn.sendall(conf)
                stage += 1
                continue
            if stage == 2:      #confirmation od klienta
                if not data.isdigit():
                    conn.sendall(SERVER_SYNTAX_ERROR)
                    break
                if cmpHash(int(data), nameInt, key):
                    conn.sendall(SERVER_OK)
                    conn.sendall(SERVER_MOVE)
                    stage += 1
                    continue
                else:
                    conn.sendall(SERVER_LOGIN_FAILED)
                    break
            if stage == 3:      #navigovani robota
                if data != '' and data[0] == 'O' and data[1] == 'K' and data[2] == ' ':
                    x, y, end = extract3(data)
                    if end:
                        conn.sendall(SERVER_SYNTAX_ERROR)
                        break
                    #print (x, y)
                    pohyb, ukoncit = robot.move(x, y)
                    conn.sendall(pohyb)
                    if ukoncit:
                        break
                    if x == 0 and y == 0:
                        stage += 1
                    continue 
                else:
                    conn.sendall(SERVER_LOGOUT)
                    break
            if stage == 4:
                #print(stage)
                conn.sendall(SERVER_LOGOUT)
                break
    except socket.timeout:
        print('timeout')
    finally:
        conn.close()

def main():
    host = ""
    port = 1234
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    print("Starting server on", host, ':',port)
    s.listen(1)
    print("socket is listening")
    try:
        while True:
            c, addr = s.accept()
            # lock acquired by client
            threading.Lock().acquire()
            print('Connected to :', addr[0], ':', addr[1])
            # Start a new thread and return its identifier
            start_new_thread(handleRobot, (c,))
    except KeyboardInterrupt:
        try:
            s.shutdown(SHUT_RDWR)
            s.close()
        except:
            s.close()

if __name__ == "__main__":
    main()