# Accelerator 29: Geospatial & Time-Series Analytics

## Overview
Advanced geospatial and time-series analytics with forecasting and spatial indexing.

## Features
### Geospatial
- **Geocoding**: Forward and reverse geocoding
- **Spatial Operations**: Proximity search, buffers, intersections
- **Spatial Indexing**: H3, S2, GeoHash
- **Routing**: Shortest path, route optimization, isochrones

### Time-Series
- **Forecasting**: Prophet, ARIMA, SARIMA, LSTM
- **Anomaly Detection**: Z-score, isolation forest, autoencoder
- **Spatio-Temporal**: Trajectory analysis, event detection

## Quick Start
```bash
docker build -t accelerator-29 .
docker run -p 8029:8029 accelerator-29
```

## Dependencies
- GeoPandas 0.14.2
- H3 3.7.6
- Prophet 1.1.5
