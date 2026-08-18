(08/14/2026)

# Explanation of the flight_data folder

This folder contains typed logic for retrieving and formatting flight data.

The provider adapter returns provider-independent models. It does not expose
the provider response to the rest of the project.

# Data provider
For now, we will use [adsb.lol](https://api.adsb.lol/docs)

*NOTE: In the future we may switch to [Airplanes.live](https://airplanes.live/) which is a community-driven ADS-B aggregator. But we do not yet have the infrastrcture to feed into the community.*

# Functionality

The first supported function is nearby-aircraft retrieval.

## Nearby
Get all aircraft in a specified nautical-mile radius around a latitude and a longitude.

Endpoint: /v2/lat/{lat}/lon/{lon}/dist/{radius}
<br>e.g. https://api.adsb.lol/v2/lat/40/lon/-74/dist/20

Create a `Position` for the center point. Use `NearbyQuery` for the position
and radius. Use `AdsbLolClient.nearby` to retrieve a `NearbySnapshot`.

The client preserves aircraft without current coordinates. Their `position`
field is `None`. The client does not use `lastPosition` as a fallback.

The module does not add retries, caching, rate-limit handling, authentication,
or display logic at this stage.
