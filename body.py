import rclpy
from rclpy.node import Node
from ai_msgs.msg import PerceptionTargets
import math
import time
import numpy as np
import serial_usb
import serial_zdt
import argparse
import json

serial_zdt.enable_motor(serial_zdt.ser_zdt,1,0x01,sync_flag=0x00)
# 定义计算关键点对的参数
'''
CALCULATION_PAIRS = [
    ("6-5中心点", 6, 5),
    ("6-8连线", 6, 8),
    ("10-8连线", 8, 10),
    ("5-7连线", 5, 7),
    ("7-9连线", 7, 9),
    ("12-16连线", 12, 16),
    ("11-15连线", 11, 15)
]
'''
CALCULATION_PAIRS = [
    ("6-5中心点", 5, 6), 
    ("6-8连线", 5, 7),
    ("10-8连线", 7, 9),
    ("5-7连线", 6, 8),
    ("7-9连线", 8, 10),
    ("12-16连线", 12, 16),
    ("11-15连线", 11, 15)
]
def calculate_angle(p1, p2):
    """计算两点间角度（相对于x轴，顺时针为正）
    Args:
        p1: 参考点
        p2: 目标点
    Returns:
        角度值（度）
    """
    try:
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        angle = math.degrees(math.atan2(dy, dx))
        # 将角度转换为顺时针方向，0度对应x轴
        angle = (360-angle)%360
        return angle
    except AttributeError:
        return None

def calculate_center_point(points):
    """返回指定点的位置作为中心点"""
    if len(points) > 0:
        # 使用第一个点作为中心点（通常是鼻子位置）
        return points[0].x, points[0].y
    return None, None

class BodyPoseSubscriber(Node):
    def __init__(self, mode="realtime", serial_file="serial_record.json", data_callback=None):
        super().__init__('body_pose_subscriber')
        self.mode = mode
        self.serial_file = serial_file
        self.serial_records = []  # 串口发送记录
        self.last_send_time = None
        self.replay_index = 0
        self.replay_start_time = None
        self.replay_data = []
        self._serial_save_frame_count = 0  # 新增：用于计数每3帧保存一次
        self.data_callback = data_callback  # 新增：回调函数
        if self.mode == "replay" and self.serial_file:
            self.load_serial_file()
        if self.mode == "realtime":
            self.subscription = self.create_subscription(
                PerceptionTargets,
                '/hobot_mono2d_body_detection',
                self.listener_callback,
                10
            )
        else:
            # 回放模式下，定时器驱动
            self.timer = self.create_timer(0.01, self.replay_serial_callback)

    def save_serial_file(self):
        if self.serial_file:
            with open(self.serial_file, 'w') as f:
                json.dump(self.serial_records, f, ensure_ascii=False, indent=2)

    def load_serial_file(self):
        try:
            with open(self.serial_file, 'r') as f:
                self.replay_data = json.load(f)
        except Exception as e:
            self.get_logger().error(f'读取串口记录文件失败: {e}')
            self.replay_data = []

    def record_serial(self, func_name, args):
        now = time.time()
        interval = 0
        if self.last_send_time is not None:
            interval = now - self.last_send_time
        self.last_send_time = now
        # 每3帧保存一次
        self._serial_save_frame_count += 1
        if self._serial_save_frame_count == 3:
            self.serial_records.append({
                "func": func_name,
                "args": args,
                "interval": interval
            })
            self._serial_save_frame_count = 0
            # 可选：定期保存
            if len(self.serial_records) % 20 == 0:
                self.save_serial_file()

    def listener_callback(self, msg):
        if self.mode != "realtime":
            return
        self.get_logger().info(f'帧率: {msg.fps}')
        display_lines = []  # 新增：用于收集显示内容
        for target in msg.targets:
            self.get_logger().info(f'目标类型: {target.type}, 跟踪ID: {target.track_id}')
            for point in target.points:
                for p in point.point:
                    p.x = 640- p.x
                self.get_logger().info(f'关键点类型: {point.type}')
                left_hand = left_arm = right_hand = right_arm = left_leg = right_leg = 0
                try:
                    center_x, center_y = calculate_center_point(point.point)
                    if center_x is not None and center_y is not None:
                        position = int(center_x * 1000 / 48)
                        self.get_logger().info(f'中心点位置: ({center_x:.2f}, {center_y:.2f}), 舵机位置: {position}')
                        print(position)
                        serial_zdt.position_control(serial_zdt.ser_zdt, 0x01, 0x01, 500, 500, 400, position, True, 0x00)
                        display_lines.append(f'中心点位置: ({center_x:.2f}, {center_y:.2f}), 舵机位置: {position}')
                        # 新增：记录zdt串口操作
                        self.record_serial("zdt_position_control", [0x01, 0x01, 500, 500, 400, position, True, 0x00])
                    for desc, idx1, idx2 in CALCULATION_PAIRS:
                        if idx1 < len(point.point) and idx2 < len(point.point):
                            p1 = point.point[idx1]
                            p2 = point.point[idx2]
                            if "中心点" in desc:
                                center_x = (p1.x + p2.x) / 2
                                self.get_logger().info(f'{desc}: 中心点x坐标 = {center_x:.2f}')
                                display_lines.append(f'{desc}: 中心点x坐标 = {center_x:.2f}')
                            else:
                                angle = calculate_angle(p1, p2)
                                if angle is not None:
                                    if desc == "10-8连线":
                                        left_hand = angle
                                    elif desc == "6-8连线":
                                        left_arm = angle
                                    elif desc == "7-9连线":
                                        right_hand = angle
                                    elif desc == "5-7连线":
                                        right_arm = angle
                                    elif desc == "12-16连线":
                                        left_leg = angle
                                    elif desc == "11-15连线":
                                        right_leg = angle
                                    self.get_logger().info(f'{desc}: 角度 = {angle:.1f}°')
                                    display_lines.append(f'{desc}: 角度 = {angle:.1f}°')
                    # 串口发送并记录
                    if ((right_arm > 0 and right_arm < 250) or right_arm > 300) and (right_arm < 90 or right_arm > 300):
                        if (math.cos(math.radians(right_hand)) + math.cos(math.radians(right_hand)) > 0):
                            serial_usb.set_angle_24((right_arm), right_hand)
                            self.record_serial("set_angle_24", [float(right_arm), float(right_hand)])
                            self.get_logger().info(f'控制右臂舵机: 角度={right_arm:.1f}°, 手部角度={right_hand:.1f}°')
                    if left_arm > 90 and left_arm < 260:
                        serial_usb.set_angle_13(left_arm, left_hand)
                        self.record_serial("set_angle_13", [float(left_arm), float(left_hand)])
                        self.get_logger().info(f'控制左臂舵机: 角度={left_arm:.1f}°, 手部角度={left_hand:.1f}°')
                    self.get_logger().info(f'角度汇总: 左臂={left_arm:.1f}°, 左手={left_hand:.1f}°, 右臂={right_arm:.1f}°, 右手={right_hand:.1f}°, 左腿={left_leg:.1f}°, 右腿={right_leg:.1f}°')
                    display_lines.append(f'角度汇总: 左臂={left_arm:.1f}°, 左手={left_hand:.1f}°, 右臂={right_arm:.1f}°, 右手={right_hand:.1f}°, 左腿={left_leg:.1f}°, 右腿={right_leg:.1f}°')
                except Exception as e:
                    self.get_logger().error(f'处理姿态数据时发生错误: {e}')
                    display_lines.append(f'处理姿态数据时发生错误: {e}')
        # 退出时保存串口记录
        self.save_serial_file()
        # 新增：调用回调
        if self.data_callback is not None:
            try:
                self.data_callback('\n'.join(display_lines))
            except Exception as e:
                self.get_logger().error(f'回调函数调用失败: {e}')

    def replay_serial_callback(self):
        if self.mode != "replay" or not self.replay_data:
            return
        if self.replay_index >= len(self.replay_data):
            self.get_logger().info('串口回放结束')
            return
        item = self.replay_data[self.replay_index]
        # 按时间间隔sleep
        if self.replay_index == 0:
            self.replay_start_time = time.time()
        else:
            interval = item.get("interval", 0)
            time.sleep(interval)
        func = item.get("func")
        args = item.get("args", [])
        # 直接调用串口发送
        if func == "set_angle_24":
            serial_usb.set_angle_24(*args)
        elif func == "set_angle_13":
            serial_usb.set_angle_13(*args)
        self.get_logger().info(f'回放串口: {func} {args}')
        self.replay_index += 1

def main(args=None, data_callback=None, stop_flag_func=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['realtime', 'replay'], default='realtime', help='选择模式: 实时检测或回放')
    parser.add_argument('--serial_file', type=str, default='serial_record.json', help='串口数据保存/读取文件')
    args = parser.parse_args()
    rclpy.init(args=None)
    node = BodyPoseSubscriber(mode=args.mode, serial_file=args.serial_file, data_callback=data_callback)
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.1)
            if stop_flag_func is not None and stop_flag_func():
                break
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
