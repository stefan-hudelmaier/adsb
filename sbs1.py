"""
SBS-1 parser in python

The parser is a Python conversion of the JavaScript one in the node-sbs1
project by John Wiseman (github.com/wiseman/node-sbs1)

Copied from https://github.com/kanflo/ADS-B-funhouse/blob/master/sbs1.py
"""

from typing import *
from datetime import datetime
import logging
import dateutil.parser


ES_IDENT_AND_CATEGORY = 1
ES_SURFACE_POS = 2
ES_AIRBORNE_POS = 3
ES_AIRBORNE_VEL = 4
SURVEILLANCE_ALT = 5
SURVEILLANCE_ID = 6
AIR_TO_AIR = 7
ALL_CALL_REPLY = 8

def parse(msg: str) -> Union[None, Dict[str, Union[str, int, float, bool, datetime]]]:
    """Parse message from the feed output by dump1090 on port 30003

    A dict is returned withAn SBS-1 message has the following attributes:

        messageType : string
        transmissionType : sbs1.TransmissionType
        sessionID : int
        aircraftID : int
        icao24 : string
        flightID : int
        generatedDate : datetime
        loggedDate : datetime
        callsign : string
        altitude : int
        groundSpeed : int
        track : int
        lat : float
        lon : float
        verticalRate : int
        squawk : int
        alert : bool
        emergency : bool
        spi : bool
        onGround : bool

    None is returned if the message was not valid

    A field not present in the parsed message will be set to None. For a
    description of the attributes, please see github.com/wiseman/node-sbs1
    """
    if msg is None:
        return None
    sbs1 = {}
    parts = msg.lstrip().rstrip().split(',')
    try:
#            logging.debug("%s   %s   %s" % (parts[1], parts[4], ",".join(parts[10:])))
        sbs1["messageType"] = parse_string(parts, 0)
        if sbs1["messageType"] != "MSG":
            return None
        sbs1["transmissionType"] = parse_int(parts, 1)
        sbs1["sessionID"] = parse_string(parts, 2)
        sbs1["aircraftID"] = parse_string(parts, 3)
        sbs1["icao24"] = parse_string(parts, 4)
        sbs1["flightID"] = parse_string(parts, 5)
        sbs1["generatedDate"] = parse_datetime(parts, 6, 7)
        sbs1["loggedDate"] = parse_datetime(parts, 8, 9)
        sbs1["callsign"] = parse_string(parts, 10)
        if sbs1["callsign"]:
            sbs1["callsign"] = sbs1["callsign"].rstrip()
        sbs1["altitude"] = parse_int(parts, 11)
        sbs1["groundSpeed"] = parse_float(parts, 12)
        sbs1["track"] = parse_float(parts, 13)
        sbs1["lat"] = parse_float(parts, 14)
        sbs1["lon"] = parse_float(parts, 15)
        sbs1["verticalRate"] = parse_int(parts, 16)
        sbs1["squawk"] = parse_int(parts, 17)
        sbs1["alert"] = parse_bool(parts, 18)
        sbs1["emergency"] = parse_bool(parts, 19)
        sbs1["spi"] = parse_bool(parts, 20)
        sbs1["onGround"] = parse_bool(parts, 21)
    except IndexError as e:
        logging.error("Failed to init sbs1 message from '%s'" % (msg), exc_info=True)
        return None
    return sbs1

def parse_string(array: List, index: int):
    """Parse string at given index in array
    Return string or None if string is empty or index is out of bounds"""
    try:
        value = array[index]
        if len(value) == 0:
            return None
        else:
            return value
    except ValueError as e:
        return None
    except TypeError as e:
        return None
    except IndexError as e:
        return None

def parse_bool(array: List, index: int):
    """Parse boolean at given index in array
    Return boolean value or None if index is out of bounds or type casting failed"""
    try:
        return bool(int(array[index]))
    except ValueError as e:
        return None
    except TypeError as e:
        return None
    except IndexError as e:
        return None

def parse_int(array: List, index: int):
    """Parse int at given index in array
    Return int value or None if index is out of bounds or type casting failed"""
    try:
        return int(array[index])
    except ValueError as e:
        return None
    except TypeError as e:
        return None
    except IndexError as e:
        return None

def parse_float(array: List, index: int):
    """Parse float at given index in array
    Return float value or None if index is out of bounds or type casting failed"""
    try:
        return float(array[index])
    except ValueError as e:
        return None
    except TypeError as e:
        return None
    except IndexError as e:
        return None

def parse_datetime(array: List, date_index: int, time_index: int):
    """Parse date and time at given indexes in array
    Return datetime value or None if indexes are out of bounds or type casting failed"""
    date = parse_string(array, date_index)
    time = parse_string(array, time_index)
    d = None
    if date is not None and time is not None:
      try:
        d = dateutil.parser.parse("%s %s" % (date, time))
      except ValueError:
        d = None
      except TypeError:
        d = None
    return d