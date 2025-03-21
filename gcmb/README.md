## ADS-B

This project contains the live positions of aircraft collected via [ADS-B](https://en.wikipedia.org/wiki/Automatic_Dependent_Surveillance%E2%80%93Broadcast) data. 
The data originates from [ADSBHub](https://www.adsbhub.org/).

## Stats

In the last 15 minutes, data from <Value topic="adsb/adsb/stats/flights_seen_in_last_15m" /> flights was received.

## Format

Latitude and longitude information can be found in the following topics: `adsb/adsb/flights/{callsign}/location`.
The format on that topic is: `{latitude},{longitude}`, e.g. `51.5074,-0.1278`.

## Terms of use

Based on the [terms of use of ADBSHub](https://www.adsbhub.org/howtogetdata.php):

There are no restrictions on how the users will use the data.
Everybody is allowed to publish the data for free or to use it for commercial purposes.

