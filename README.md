# humtemp
A high-performance microservice for aggregating timeseries metrics (temperature, humidity) that are pushed by sensors (lab rooms).

It is designed to easily scale to 100.000s of metrics pushes per second with the current implementation.

# User Guide

# Development
## Local Development

## Local Deployment

## AWS Deployment

# Design Considerations
## Choice of Database
The main concern with this service is to achieve sufficient performance with minimal cost. At the same time, the usecase doesn't require support for classical ACID transactions - and it is tolerable to lose a few seconds of data in case of database instance failures.

This lead to the choice of the Redis in-memory key-value store as database backend for the application:
* The amount of data that is stored is small (~ 50k rows per day, A few bytes per row). This can easily be held in memory.
* Redis offers great performance for given hardware resources
* Redis offers persistence to disk and cluster functionality to support failure recovery and future horitzontal scaling options
* AWS offers a managed Redis service (AWS ElastiCache)

Currently, the Redis database implementation in the "humtemp" microservice is the limiting factor in scaling this application, as only a single-instance Redis deployment is supported.

If necessary, this limitation can be relaxed to **infinite horizontal scalability** by adding support for multiple, independent Redis database instances. This can be easily achieved by sharding buckets to individual Redis instances (for example based on hashes of the lab identifier).

## Data Model
Redis requires a flat data model.

![DataModel](/docs/images/datamodel.png)

The idea is to aggregate incoming observations into buckets already when writing data to the DB. It is not necessary to keep records of every individual measurement (30s interval).

There are separate buckets for every lab ID. The individual bucket identifier contains the lab ID, as well as the start-time of the bucket.

**Advantages:**
* Every "POST /observation" request can independently identify the bucket key where the data needs to be added.
* Summing up the observations in the bucket can be done by very fast, atomic operations on Redis
* When requesting the lab summary, the results can be presented immediately without expensive aggregation computation.
## Monitoring
