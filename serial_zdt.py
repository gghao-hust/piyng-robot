import serial
import time

# 初始化串口
ser_zdt = serial.Serial(
    port='/dev/ttyS1',  # 请根据实际串口号修改
    baudrate=115200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

#串口初始化
def ser_init_usb(ser2):
    try:
        ser2 = serial.Serial(
        port='/dev/ttyS1',  # 请根据实际串口号修改
        baudrate=115200,
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

def enable_motor(ser, address, enable_status, sync_flag=0x00):
    """
    电机使能控制函数
    :param ser: 串口对象
    :param address: 电机地址
    :param enable_status: 使能状态 (0x00: 不使能, 0x01: 使能)
    :param sync_flag: 多机同步标志 (默认0x00)
    :return: 命令执行状态 (True: 成功, False: 失败)
    """
    # 构建命令
    command = [address, 0xF3, 0xAB, enable_status, sync_flag]
    
    # 计算校验字节
    checksum = sum(command) & 0xFF
    command.append(checksum)
    
    # 发送命令
    ser_send_usb(ser, command, len(command))
    
    # 等待并读取响应
    response = ser.read(4)  # 读取4字节响应
    
    if len(response) == 4:
        # 验证响应
        if response[0] == address and response[1] == 0xF3:
            return True
    return False



def position_control(ser, address, direction, acc_speed, dec_speed, max_speed, position, is_absolute=False, sync_flag=0x00):
    """
    梯形曲线位置模式控制函数
    :param ser: 串口对象
    :param address: 电机地址
    :param direction: 方向 (0x00: 正方向, 0x01: 负方向)
    :param acc_speed: 加速加速度 (单位: RPM/s)
    :param dec_speed: 减速加速度 (单位: RPM/s)
    :param max_speed: 最大速度 (单位: RPM)
    :param position: 位置角度 (单位: 0.1度)
    :param is_absolute: 是否绝对位置 (False: 相对位置, True: 绝对位置)
    :param sync_flag: 多机同步标志 (默认0x00)
    :return: 命令执行状态 (True: 成功, False: 失败)
    """
    # 构建命令
    command = [address, 0xFD, direction]
    
    # 添加加速加速度 (2字节)
    acc_bytes = [(acc_speed >> 8) & 0xFF, acc_speed & 0xFF]
    command.extend(acc_bytes)
    
    # 添加减速加速度 (2字节)
    dec_bytes = [(dec_speed >> 8) & 0xFF, dec_speed & 0xFF]
    command.extend(dec_bytes)
    
    # 添加最大速度 (2字节)
    speed_bytes = [(max_speed >> 8) & 0xFF, max_speed & 0xFF]
    command.extend(speed_bytes)
    
    # 添加位置角度 (4字节)
    pos_bytes = [(position >> 24) & 0xFF, (position >> 16) & 0xFF,
                 (position >> 8) & 0xFF, position & 0xFF]
    command.extend(pos_bytes)
    
    # 添加位置模式标志
    command.append(0x01 if is_absolute else 0x00)
    
    # 添加同步标志
    command.append(sync_flag)
    
    # 计算校验字节
    command.append(0x6B)
    
    # 发送命令
    ser_send_usb(ser, command, len(command))
    
    # 等待并读取响应
    response = ser.read(4)  # 读取4字节响应
    
    if len(response) == 4:
        # 验证响应
        if response[0] == address and response[1] == 0xFD:
            if response[2] == 0x02:  # 成功状态
                return True
            elif response[2] == 0xE2:  # 条件不满足
                print("条件不满足：可能触发了堵转保护或电机未使能")
    return False

# 使用示例
#enable_motor(ser_zdt,1,0x01,sync_flag=0x00)
#time.sleep(1)
#position_control(ser_zdt, 0x01, 0x01, 100, 20, 20, 200, True, 0x00)

enable_motor(ser_zdt,1,0x01,sync_flag=0x00)