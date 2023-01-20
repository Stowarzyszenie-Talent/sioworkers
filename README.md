# sioworkers

`sioworkers` is the task runner used by [SIO2](https://github.com/sio2project/oioioi) - the platform for running algorithmic/competitive programming contests. It handles all kinds of asynchronously run jobs - ranging from compiling submissions, to executing them in a supervised, sandboxed environment.

# Installation

```
$ pip install .      # for production deployments
$ pip install .[dev] # with development dependencies
```

# Tests

All tests in this project are being mnanaged with `tox`, which is simply invoked by running:

```console
$ tox
```

in the main directory.

Alternatively you can also invoke the various tests directly.

## Unit tests

```console
$ TEST_SANDBOXES=1 NO_JAVA_TESTS=1 pytest -v .
```
This allows you to enable/disable sandboxed and Java tests.

## Twisted
```console
$ trial sio/sioworkersd/twisted_t
```

# Docker

An official Docker image for sioworkers is available at (TODO: update this when the image location is decided).

```console
$ docker run --rm \
  --network=sio2-network \
  --cap-add=ALL \
  --privileged \
  -e "SIOWORKERSD_HOST=oioioi" \
  -e "WORKER_ALLOW_RUN_CPU_EXEC=true" \
  -e "WORKER_CONCURRENCY=1" \
  -e "WORKER_RAM=1024" \
  --memory="1152m" \
  --cpus=2.0 \
  <TODO: container tag here>
```

Notes:
* `--privileged` is only needed if Sio2Jail is used for judging submissions (ie. `WORKER_ALLOW_RUN_CPU_EXEC` is set to `true`),
* You can limit the memory/CPUs available to the container how you usually would in the container runtime of your choice,
  the container will determine how many workers it should expose to OIOIOI based on that.
  * You can also manually override the amount of available workers/memory by specifying the `WORKER_CONCURRENCY` and `WORKER_RAM` (in MiB) environment variables.
* 128 MiB is reserved for processes in the container other than the submission being judged. That is, if you want
  the maximum memory available to a judged program to be 1024 MiB, limit the container's memory to
  128 MiB + (number of workers) * 1024 MiB.

Equivalent Docker Compose configuration:

```yaml
version: '3.8'

...

worker:
  image: <TODO: container tag here>
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 1152m
  cap_add:
    - ALL
  privileged: true
  environment:
    SIOWORKERSD_HOST: 'web'
    WORKER_ALLOW_RUN_CPU_EXEC: 'true'
    # these *will* override any automatic detection of available
    # memory/cpu cores based on container limits!
    WORKER_CONCURRENCY: '1'
    WORKER_RAM: '1024'
```

## Environment variables

The container exposes two environment variables, from which only `SIOWORKERSD_HOST` is required.

* `SIOWORKERSD_HOST` - name of the host on which the `sioworkersd` service is available (usually the same as the main OIOIOI instance)
* `WORKER_ALLOW_RUN_CPU_EXEC` - marks this worker as suitable for judging directly on the CPU (without any isolation like Sio2Jail).
  This is used in some contest types (for instance, ACM style contests), however it isn't needed when running the regular OI style
  contests.
