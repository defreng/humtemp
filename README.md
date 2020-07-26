# humtemp
A high-performance microservice for aggregating timeseries metrics (temperature, humidity) that are pushed by sensors (lab rooms).

It is designed to easily scale to 100.000s of metrics pushes per second with the current implementation.

# User Guide
## Configuration
The application can be configured using environment variables (which are specified in `src/humtemp/configuration.py`):

* `HUMTEMP_REDIS_HOST`: Hostname of the Redis instance to connect to (default: localhost)
* `HUMTEMP_REDIS_PORT`: Port of the Redis instance`(default: 6379)
* `HUMTEMP_REDIS_DB`: DB index in Redis which should be used (default: 0)
* `HUMTEMP_BUCKET_OFFSET`: humtemp divides the time into buckets. Bucket boundaries will be aligned to this offset. Use ISO-8601 notation. (Default: `1970-01-01T00:00:00+00:00`)
* `HUMTEMP_BUCKET_DURATION`: How large (in terms of duration) every bucket is in seconds (Default: `86400` [1 day])
* `HUMTEMP_BUCKET_RETENTION`: How many old buckets should be kept in the database (Default: 2. This means that the current and last day will be available for querying with the API)

## Scalability
The service was able to handle ~1000 requests/sec with two container instances being deployed on a single t2.micro instance.

Redis database load for this was under 10% on a single t2.micro instance.

## Deployment
The Application is deployed on AWS. See the following images for a schematic of the application- and network architecture:

### Application Architecture
![AWS application architecture](/docs/aws_logical.png)

### Network Architecture
![AWS network architecture](/docs/aws_network.png)

# Development
## Local Development
This repository uses [poetry](https://python-poetry.org/) for dependency management and builds.

To initialize an isolated Python environment for development, run these commands:
```
poetry env use /path/to/python3.8
poetry install
```

Afterwards, the application can be started using:
```
poetry run python -m uvicorn humtemp.main:app --reload
```

* API Base URL: http://localhost:8000/
* API Documentation: http://localhost:8000/redoc

## Local Testing
```
poetry run pytest tests/
```
 
The integration tests need a local redis database to be running. See below at "Local Deployment" how to set one up.

## Local Deployment
It's easiest to utilize `docker-compose` to build the image and deploy it locally, including the necessary Redis database:

```
docker-compose build
docker-compose up
```

## AWS Deployment
Use the following commands to publish the Docker image to the private AWS Container Registry:

```
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 718314285581.dkr.ecr.us-east-1.amazonaws.com

docker-compose build
docker tag humtemp:latest 718314285581.dkr.ecr.us-east-1.amazonaws.com/humtemp:latest
docker push 718314285581.dkr.ecr.us-east-1.amazonaws.com/humtemp:latest
```

Unfortunately, I wasn't able to do further automation of the infrastructure setup due to time constraints - although I would love to see a fully automated, "every-commit-to-production" pipeline using tools like terraform or the AWS cli.

This would also make it a lot easier to no longer use the terrible ":latest" tag on the Docker images for more reproducible deployments and rollback options.

# Design Considerations
The AWS Free-Tier limited the options on potential services that could be used. I would have loved to use more "managed" solutions, such as AWS Fargate for serverless container deployment - and EKS for a full-blown Kubernetes cluster and compatibility with provider independent tools like Helm.

In general, the task itself would also fit nicely into the serverless AWS Lambda pattern, due to the insanely spiky loads.

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

![DataModel](/docs/datamodel.png)

The idea is to aggregate incoming observations into buckets already when writing data to the DB. It is not necessary to keep records of every individual measurement (30s interval).

There are separate buckets for every lab ID. The individual bucket identifier contains the lab ID, as well as the start-time of the bucket.

**Advantages:**
* Every "POST /observation" request can independently identify the bucket key where the data needs to be added.
* Summing up the observations in the bucket can be done by very fast, atomic operations on Redis
* When requesting the lab summary, the results can be presented immediately without expensive aggregation computation.

## Monitoring
All the normal monitoring should be done for the application deployment. By this I mean things like:
* Number of available instances (health check using `/summary` API)
* CPU and memory utilization of every instance
* Number of successful (=status code 200) / failed requests

However, the CPU and memory utilization, as well as the number of requests will be very spiky. Therefore, it will be hard to define fixed thresholds for alerting.

So it would make sense to look at these metrics (especially the number of successful requests) at a daily granularity, e.g. "number of successful requests / day", as this number should be fairly constant.
