## ADS-B Data

This project contains the code for the GCMB Project [adsb/adsb](https://gcmb.io/adsb/adsb).

The Python program connects to [ADSBHub](https://www.adsbhub.org/) and consumes data via
the SBS1 format (CSV). It publishes the flight locations to [GCMB](https://gcmb.io) via MQTT.

## Running locally

To run locally, put the GCMB password in an `.env` file:

```
GCMB_PASSWORD=xxx
```

Please note that ADSBHub will not allow the connection on port 5002 if you are not publishing
data from at least one ADS-B station. 

