# 皮影机器人上位机 使用说明

## 环境依赖
- Python 3.7 及以上
- PyQt5
- PyQtWebEngine
- numpy
- rclpy 及 ROS2 相关依赖

安装依赖示例：
```bash
pip install pyqt5 pyqtwebengine numpy
# ROS2 相关依赖请参考ROS2官方文档安装
```

## 主要功能
- 导入剧本：支持导入JSON格式的动作剧本并自动执行。
- 生成剧本：支持实时录制和视频检测生成剧本，自动保存串口动作。
- 实时检测：可实时显示检测到的动作信息。
- 支持两路串口（serial_usb、serial_zdt）动作的录制与回放。

## 启动方法
在终端进入项目目录，运行：
```bash
# 配置tros.b humble环境
source /opt/tros/humble/setup.bash

# 从tros.b的安装路径中拷贝出运行示例需要的配置文件。
cp -r /opt/tros/${TROS_DISTRO}/lib/mono2d_body_detection/config/ .

# 配置USB摄像头
export CAM_TYPE=usb

# 启动launch文件
ros2 launch mono2d_body_detection mono2d_body_detection.launch.py

python3 robot_gui.py
```

## 剧本录制与回放
- 录制剧本：
  1. 进入“生成剧本”页面，点击“实时录制生成剧本”，按提示操作开始/结束录制。
  2. 录制过程中所有串口动作（包括serial_usb和serial_zdt）都会被记录。
  3. 录制结束后会生成JSON剧本文件。
- 视频检测生成剧本：
  1. 点击“视频检测生成剧本”，选择视频文件，等待生成。
  2. 生成的剧本文件会保存在视频同级目录下。
- 回放剧本：
  1. 进入“导入剧本”页面，选择剧本文件。
  2. 点击“运行剧本”即可自动按剧本内容控制机器人。

## 注意事项
- 请确保串口设备已正确连接，端口号与波特率设置正确。
- ROS2相关节点需正常运行，确保能接收到/hobot_mono2d_body_detection话题。
- 剧本文件格式为JSON，内容示例：
```json
[
  {"func": "set_angle_24", "args": [90, 45], "interval": 0.5},
  {"func": "zdt_position_control", "args": [1, 1, 500, 500, 400, 1234, true, 0], "interval": 0.5}
]
```
- serial_usb和serial_zdt为两路独立串口，动作不会互相影响。

## 联系方式
如有问题请联系开发者。
