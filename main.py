#!/usr/bin/env python3
import os
import queue
import uuid
import math

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

log_level = os.environ.get('LOG_LEVEL', 'INFO')
print("Using log level", log_level)

logger = logging.getLogger()
logger.setLevel(log_level)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Keys are icao24
flights_cache = TTLCache(maxsize=100_000, ttl=60 * 15)

# For measuring throughput
messages_cache = TTLCache(maxsize=100_000, ttl=60)

message_queue = queue.Queue(maxsize=100000)

start_time = time.time()

def connect_mqtt():
    def on_connect(client, userdata, flags, rc, properties):
        if rc == 0:
            logger.info("Connected to MQTT Broker")
        else:
            logger.error(f"Failed to connect, return code {rc}")

    mqtt_client = mqtt.Client(client_id=client_id,
                              callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.tls_set(ca_certs='/etc/ssl/certs/ca-certificates.crt')
    mqtt_client.username_pw_set(username, password)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = lambda client, userdata, disconnect_flags, reason_code, properties: logger.warning(
        f"Disconnected from MQTT Broker, return code {reason_code}")
    mqtt_client.connect(broker, port)
    return mqtt_client


def publish(client, topic, msg):
    result = client.publish(topic, msg, retain=True)
    status = result[0]
    if status == 0:
        logger.debug(f"Sent '{msg}' to topic {topic}")
        messages_cache[uuid.uuid4()] = None
    else:
        logger.warn(f"Failed to send message to topic {topic}, reason: {status}")


def publish_stats(mqtt_client):
        while True:
            try:
                time.sleep(5)
                flights_seen = len(flights_cache)
                queue_size = message_queue.qsize()
                messages_per_minute = len(messages_cache)

                # Rounded to seconds
                running_for = math.floor(time.time() - start_time)
                print(f"Flights seen: {flights_seen}, Queue size: {queue_size}, Messages per minute: {messages_per_minute}, Running for: {running_for} seconds")

                publish(mqtt_client, "adsb/adsb/stats/flights_seen_in_last_15m", f'{flights_seen}')
                publish(mqtt_client, "adsb/adsb/stats/queue_size", f'{queue_size}')
                publish(mqtt_client, "adsb/adsb/stats/messages_per_minute", f'{messages_per_minute}')
            except Exception as e:
                logger.error(f"Caught exception when publishing stats")
                logger.error(e)


def consume_from_adsb_hub():
    callsigns = {}

    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logger.info(f"Connecting to {sbs1_host}:{sbs1_port}")
        s.connect((sbs1_host, sbs1_port))
        f = s.makefile("rb")
        while True:
            try:
                data = f.readline()

                if data == b'':
                    break
                parsed_data = parse(data.decode('utf-8'))
                if parsed_data is None:
                    continue
                icao24 = parsed_data['icao24']
                callsign = parsed_data['callsign']
                if callsign is not None:
                    callsigns[icao24] = callsign

                lat = parsed_data['lat']
                lon = parsed_data['lon']

                callsign = callsigns[icao24] if icao24 in callsigns else None

                if callsign is not None:
                    flights_cache[icao24] = None

                message_queue.put({'icao24': icao24, 'callsign': callsign, 'lat': lat, 'lon': lon})

            except Exception as e:
                logger.error(f"Caught exception")
                logger.error(e)
        logger.info("Socket closed, reconnecting")
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
            logger.error(f"Caught exception")
            logger.error(e)


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
