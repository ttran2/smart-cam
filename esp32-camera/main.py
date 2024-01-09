import hashlib
import socket
import time
import _thread
import struct
import binascii

import camera
import network

from machine import Pin, PWM, reset
from servo import Servo
# from smooth_servo import SmoothServo


SSID = "SmartCam"
PASSWORD = "securepassword"


# setup camera flash
cam_flash = Pin(4, Pin.OUT)
def flash():
    cam_flash.value(1)
    time.sleep(0.1)
    cam_flash.value(0)
flash()

# initialize the camera
for i in range(5):
    camera.deinit()
    cam = camera.init()
    print("Camera ready: ", cam)
    if cam:
        break
    time.sleep(2)
else:
    print('Timeout')
    reset()
camera.framesize(10)

# setup access point
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid=SSID, password=PASSWORD, channel=1)
print('[WiFi Hotspot]')
print('SSID: ', SSID)
print('IP address: ', ap.ifconfig()[0])

# setup servos
pan_servo = Servo(14)
tilt_servo = Servo(15)
pan_servo.write(90)
tilt_servo.write(90)
# pan_smooth_servo = SmoothServo(pan_servo)
# tilt_smooth_servo = SmoothServo(tilt_servo)
# _thread.start_new_thread(pan_smooth_servo.run, ())
# _thread.start_new_thread(tilt_smooth_servo.run, ())


def unmask_payload(mask, payload):
    return bytes(b ^ mask[i % 4] for i, b in enumerate(payload))


def handle_binary_frame(data):
    fin = (data[0] & 0b10000000) != 0
    opcode = data[0] & 0b00001111
    masked = (data[1] & 0b10000000) != 0
    payload_len = data[1] & 0b01111111
    mask_offset = 2

    if payload_len == 126:
        payload_len = struct.unpack(">H", data[2:4])[0]
        mask_offset = 4
    elif payload_len == 127:
        payload_len = struct.unpack(">Q", data[2:10])[0]
        mask_offset = 10

    if masked:
        mask = data[mask_offset:mask_offset + 4]
        mask_offset += 4
        payload = data[mask_offset:mask_offset + payload_len]
        payload = unmask_payload(mask, payload)
    else:
        payload = data[mask_offset:mask_offset + payload_len]

    decoded_data = None
    if opcode == 1:  # Text frame
        decoded_data = payload.decode('utf-8')
    return opcode, decoded_data


def send_websocket_message(client, message):
    encoded_data = message.encode('utf-8')
    message_len = len(encoded_data)
    header = bytearray()

    header.append(0b10000001)  # FIN bit set and Opcode for text frame

    if message_len < 126:
        header.append(message_len)
    elif message_len < (1 << 16):  # 2^16
        header.append(126)
        header.extend(struct.pack('>H', message_len))
    else:
        header.append(127)
        header.extend(struct.pack('>Q', message_len))

    client.send(header + encoded_data)


def handle_websocket(client, addr):
    print("Websocket established with " + str(addr))
    while True:
        try:
            data = client.recv(1024)
            if not data:
                continue
            opcode, decoded_data = handle_binary_frame(data)
            if opcode == 8:
                print(str(addr) + " disconnected")
            elif opcode != 1:  # https://www.apollographql.com/docs/ios/v0-legacy/api/ApolloWebSocket/enums/WebSocket.OpCode/
                print("Unknown websocket opcode: " + str(opcode))
            if not decoded_data:
                break
            print("received: '" + decoded_data + "'")
            parsed = decoded_data.split()
            cmd = parsed[0].upper()
            arg_count = len(parsed) - 1
            msg = "success"

            if cmd == "PING" and arg_count == 0:
                msg = "PONG"

            elif cmd == "FLASH" and arg_count == 1:
                flash_toggle = parsed[1].lower()
                if flash_toggle == "on":
                    cam_flash.value(1)
                elif flash_toggle == "off":
                    cam_flash.value(0)
                else:
                    msg = "ERROR: Unknown Flash argument - " + flash_toggle

            elif cmd == "FRAMESIZE" and arg_count == 1:
                # https://github.com/shariltumin/esp32-cam-micropython-2022/blob/main/firmwares-20230717/Note.md
                frame_size_key = int(parsed[1])
                if 1 <= frame_size_key <= 18:
                    camera.framesize(frame_size_key)
                else:
                    msg = "ERROR: Unknown Camera Frame Size - " + str(frame_size_key)

            elif cmd == "MOVE" and arg_count == 2:
                pan_value = float(parsed[1])
                tilt_value = float(parsed[2])
                pan_servo.write(pan_value)
                tilt_servo.write(tilt_value)
                # pan_smooth_servo.target = pan_value
                # tilt_smooth_servo.target = tilt_value
            else:
                msg = "ERROR: Unknown Command - " + cmd + " (with " + str(arg_count) + " arguments)"
            send_websocket_message(client, msg)

        except OSError as e:
            print("WebSocket OSError:", e)
            break
    client.close()


def base64_encode(data):
    return binascii.b2a_base64(data, newline=False).decode('utf-8')


def handle_request(client, addr):
    print("New request from " + str(addr))
    try:
        request = client.recv(1024)
        request = request.decode('utf-8')
        if 'GET /camera' in request:
            client.send(b"HTTP/1.1 200 OK\r\nContent-Type: multipart/x-mixed-replace;boundary=frame\r\n\r\n")
            while True:
                frame = camera.capture()
                client.send(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        elif 'Upgrade: websocket' in request:
            websocket_key = None
            for line in request.split('\r\n'):
                if line.startswith("Sec-WebSocket-Key: "):
                    websocket_key = line[19:]
            if websocket_key is not None:
                magic_string = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
                response_key = base64_encode(hashlib.sha1((websocket_key + magic_string).encode()).digest())
                response = (
                    "HTTP/1.1 101 Switching Protocols\r\n"
                    "Upgrade: websocket\r\n"
                    "Connection: Upgrade\r\n"
                    "Sec-WebSocket-Accept: " + response_key + "\r\n"
                    "\r\n"
                )
                client.send(response.encode('utf-8'))
                handle_websocket(client, addr)
        else:
            client.send("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<!doctype html><html><body><img src=\"/stream\"></body></html>")
    except OSError as e:
        if e.args[0] == 104:
            print("Connection reset by peer")
        else:
            print("Unexpected OSError:" + str(e))
    except UnicodeError as e:
        print("Unicode Error: " + str(e))
    client.close()


# Listen for connections
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(5)
print('Listening for connections on', addr)
flash()

while True:
    client, addr = s.accept()
    _thread.start_new_thread(handle_request, (client, addr))
