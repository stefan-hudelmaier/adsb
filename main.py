#!/usr/bin/env python3
import os

import paho.mqtt.client as mqtt
import socket
import time
import logging
import sys
import bufsock
from threading import Thread

from sbs1 import parse
from dotenv import load_dotenv
from cachetools import TTLCache

load_dotenv()

broker = 'gcmb.io'
port = 8883
client_id = 'adsb/adsb/data-generator/pub'
username = 'adsb/adsb/data-generator'
password = os.environ['GCMB_PASSWORD']

root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

# Keys are icao24
flights_cache = TTLCache(maxsize=100_000, ttl=60 * 15)


def connect_mqtt():
    def on_connect(client, userdata, flags, rc, properties):
        if rc == 0:
            print("Connected to MQTT Broker")
        else:
            print(f"Failed to connect, return code {rc}")

    client = mqtt.Client(client_id=client_id,
                         callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.tls_set(ca_certs='/etc/ssl/certs/ca-certificates.crt')
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client


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
        topic = "adsb/adsb/stats/flights_seen_in_last_15m"
        publish(mqtt_client, topic, f'{len(flights_cache)}')


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("127.0.0.1", 5002))
    bs = bufsock.bufsock(s)

    mqtt_client = connect_mqtt()

    callsigns = {}

    publish_stats_thread = Thread(target=publish_stats, args=(mqtt_client,))
    publish_stats_thread.start()

    while True:
        try:
            data = bs.readto(b'\n')
            print(data)
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

            if lat is not None and lon is not None and callsign is not None:
                print(f"Flight: {callsigns.get(icao24, 'Unknown')}, Lat: {lat}, Lon: {lon}")
                topic = f"adsb/adsb/flights/{callsign}/location"
                publish(mqtt_client, topic, f'{lat}, {lon}')

            mqtt_client.loop(timeout=0.01)

        except KeyboardInterrupt:
            print('Interrupted')
            publish_stats_thread.join()
            mqtt_client.disconnect()
            break
        except Exception as e:
            print(f"Caught exception")
            print(e)


if __name__ == '__main__':
    main()
