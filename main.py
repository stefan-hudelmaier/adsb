#!/usr/bin/env python3
import os
import queue
from argparse import ArgumentParser

import paho.mqtt.client as mqtt
import socket
import time
import logging
import sys
from threading import Thread

from sbs1 import parse
from dotenv import load_dotenv
from cachetools import TTLCache

load_dotenv()

broker = 'gcmb.io'
port = 8883
client_id = 'adsb/adsb/data-generator/pub'
username = os.environ['MQTT_USERNAME']
password = os.environ['MQTT_PASSWORD']

sbs1_host = os.environ.get('SBS1_HOST', 'localhost')
sbs1_port = int(os.environ.get('SBS1_PORT', '5002'))

root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

# Keys are icao24
flights_cache = TTLCache(maxsize=100_000, ttl=60 * 15)

message_queue = queue.Queue(maxsize=100000)


def connect_mqtt():
    def on_connect(client, userdata, flags, rc, properties):
        if rc == 0:
            print("Connected to MQTT Broker")
        else:
            print(f"Failed to connect, return code {rc}")

    mqtt_client = mqtt.Client(client_id=client_id,
                              callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.tls_set(ca_certs='/etc/ssl/certs/ca-certificates.crt')
    mqtt_client.username_pw_set(username, password)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = lambda client, userdata, disconnect_flags, reason_code, properties: print(
        f"Disconnected from MQTT Broker, return code {reason_code}")
    mqtt_client.connect(broker, port)
    return mqtt_client


def publish(client, topic, msg):
    result = client.publish(topic, msg, retain=True)
    status = result[0]
    if status == 0:
        print(f"Sent '{msg}' to topic {topic}")
    else:
        print(f"Failed to send message to topic {topic}, reason: {status}")


def publish_stats(mqtt_client):
    while True:
        time.sleep(5)
        publish(mqtt_client, "adsb/adsb/stats/flights_seen_in_last_15m", f'{len(flights_cache)}')
        publish(mqtt_client, "adsb/adsb/stats/queue_size", f'{message_queue.qsize()}')


def consume_from_adsb_hub():
    callsigns = {}

    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"Connecting to {sbs1_host}:{sbs1_port}")
        s.connect((sbs1_host, sbs1_port))
        stream = socket.SocketIO(s, mode='rb')
        while not stream.closed:
            try:
                data = stream.readline()
                # print(data)
                parsed_data = parse(data.decode('utf-8'))
                if parsed_data is None:
                    continue
                # print(parsed_data)
                icao24 = parsed_data['icao24']
                callsign = parsed_data['callsign']
                if callsign is not None:
                    callsigns[icao24] = callsign
                    # print(callsign)

                lat = parsed_data['lat']
                lon = parsed_data['lon']

                callsign = callsigns[icao24] if icao24 in callsigns else None

                if callsign is not None:
                    flights_cache[icao24] = None

                message_queue.put({'icao24': icao24, 'callsign': callsign, 'lat': lat, 'lon': lon})

            except Exception as e:
                print(f"Caught exception")
                print(e)
        print("Socket closed, reconnecting")
        time.sleep(5)


def publish_queue_message(mqtt_client):
    while True:
        try:
            message = message_queue.get()
            icao24 = message['icao24']
            callsign = message['callsign']
            lat = message['lat']
            lon = message['lon']

            if lat is not None and lon is not None and callsign is not None:
                # print(f"Flight: {callsigns.get(icao24, 'Unknown')}, Lat: {lat}, Lon: {lon}")
                topic = f"adsb/adsb/flights/{callsign}/location"
                publish(mqtt_client, topic, f'{lat},{lon}')

        except Exception as e:
            print(f"Caught exception")
            print(e)


def main():
    mqtt_client = connect_mqtt()

    publish_stats_thread = Thread(target=publish_stats, args=(mqtt_client,))
    publish_stats_thread.start()

    adsb_hub_thread = Thread(target=consume_from_adsb_hub, args=())
    adsb_hub_thread.start()

    mqtt_publish_thread = Thread(target=publish_queue_message, args=(mqtt_client,))
    mqtt_publish_thread.start()

    mqtt_client.loop_forever()


if __name__ == '__main__':
    main()
