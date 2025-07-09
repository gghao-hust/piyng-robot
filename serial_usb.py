import serial
import time


# 初始化串口
ser = serial.Serial(
    port='/dev/ttyUSB0',  # 请根据实际串口号修改
    baudrate=1000000,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

#串口初始化
def ser_init_usb(ser2):
    try:
        ser2 = serial.Serial(
        port='/dev/ttyUSB0',  # 请根据实际串口号修改
        baudrate=1000000,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1)
        ser2.close()
        ser2.open()

    except serial.SerialException as e:
        print(f"串口打开失败: {e}")

# 发送数据
#ser.write(b"Hello STM32\n")

# 接收数据
#response = ser.readline().decode('utf-8').strip()
#print(f"Received: {response}")

def ser_send_usb(sn, lis, num):  # 串口发送
    li2 = bytearray(lis[:num])
    by = bytes(li2)
    sn.write(by)

def send_point_usb(sn,center_x,center_y):
    point = [0x77, 0x33, 0, 0, 0, 0, int(center_x / 100), int(center_x % 100),int(center_y / 100), int(center_y % 100),0x88]
    ser_send_usb(sn, point, 11)
    print(f"发送数据: {[hex(x) for x in point]}")

def send_servo(sn,left_hand,left_arm,right_hand,right_arm,left_leg,right_leg):
    angle_left_hand= [0xFF,0xFF, 0,0x09,0x03,0x2A]


#发送角度指令
def send_angle_usb(sn,id ,pos,spd):
    #前缀数组
    prefix=[0xFF,0xFF,id,0x09,0x03,0x2A]
    #角度数据
    data=[ (pos >> 8) & 0xFF,pos& 0xFF,0x00,0x00,spd & 0xFF,(spd >> 8) & 0xFF]
    #数据合并
    send_data = prefix + data
    # 计算校验和
    checksum = 0
    i=0
    for byte in send_data:
        if i<2:
            i+=1
            continue
        checksum = (byte+checksum)& 0xFF
    checksum = ~(checksum)& 0xFF
    send_data.append(checksum)
    print(send_data)
    
    # 发送数据
    ser_send_usb(sn, send_data, len(send_data))

send_angle_usb(ser,4,0x0100,0x02e8)


def send_angle(sn,id,angle):
    pos=int((angle)/310*0x0400)
    send_angle_usb(sn,id,pos,3000)


def set_angle_1(angle):
    send_angle(ser,1,(110-(angle-180)+360)%360)


def set_angle_2(angle):
    #if (angle>0 and angle<250) or angle>300:
        send_angle(ser,2,69+angle)
   # else :
    #    send_angle(ser,2,69+angle-360)

def set_angle_3(angle):
    send_angle(ser,3,(160-(angle-180)+360)%360)


def set_angle_4(angle):
    send_angle(ser,4,(150-(angle-180)+360)%360)


def set_angle_13(angle_1,angle_3):
    if angle_1<90:
        angle_1=90
    elif angle_1>230:
        angle_1=230   
    set_angle_1(angle_1)

    set_angle_3(angle_3-angle_1+180)

def set_angle_24(angle_2,angle_4):
    if angle_2>270:
        angle_2-=360


    set_angle_2(angle_2)
    set_angle_4(angle_4-angle_2+180)



set_angle_13(180,90)
set_angle_24(0,90)
