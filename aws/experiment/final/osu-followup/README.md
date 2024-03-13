# OSU Performance Analysis

We built osu_allreduce.c with the customized logic:

<details>

<summary>osu_allreduce.c</summary>

```cpp
root@flux-osu-efa-0:/opt/osu-benchmark/src/osu-micro-benchmarks-5.8/mpi/collective# cat osu_allreduce.c 
#define BENCHMARK "OSU MPI%s Allreduce Latency Test"
/*
 * Copyright (C) 2002-2021 the Network-Based Computing Laboratory
 * (NBCL), The Ohio State University.
 *
 * Contact: Dr. D. K. Panda (panda@cse.ohio-state.edu)
 *
 * For detailed copyright and licensing information, please refer to the
 * copyright file COPYRIGHT in the top level OMB directory.
 */
#include <osu_util_mpi.h>

int main(int argc, char *argv[])
{
    int i, numprocs, rank, size;
    double latency = 0.0, t_start = 0.0, t_stop = 0.0;
    double timer=0.0;
    double avg_time = 0.0, max_time = 0.0, min_time = 0.0;
    float *sendbuf, *recvbuf;
    int po_ret;
    int errors = 0;
    size_t bufsize;
    options.bench = COLLECTIVE;
    options.subtype = LAT;

    set_header(HEADER);
    set_benchmark_name("osu_allreduce");
    po_ret = process_options(argc, argv);

    if (PO_OKAY == po_ret && NONE != options.accel) {
        if (init_accel()) {
            fprintf(stderr, "Error initializing device\n");
            exit(EXIT_FAILURE);
        }
    }

    MPI_CHECK(MPI_Init(&argc, &argv));
    MPI_CHECK(MPI_Comm_rank(MPI_COMM_WORLD, &rank));
    MPI_CHECK(MPI_Comm_size(MPI_COMM_WORLD, &numprocs));

    switch (po_ret) {
        case PO_BAD_USAGE:
            print_bad_usage_message(rank);
            MPI_CHECK(MPI_Finalize());
            exit(EXIT_FAILURE);
        case PO_HELP_MESSAGE:
            print_help_message(rank);
            MPI_CHECK(MPI_Finalize());
            exit(EXIT_SUCCESS);
        case PO_VERSION_MESSAGE:
            print_version_message(rank);
            MPI_CHECK(MPI_Finalize());
            exit(EXIT_SUCCESS);
        case PO_OKAY:
            break;
    }

    if (numprocs < 2) {
        if (rank == 0) {
            fprintf(stderr, "This test requires at least two processes\n");
        }

        MPI_CHECK(MPI_Finalize());
        exit(EXIT_FAILURE);
    }

    if (options.max_message_size > options.max_mem_limit) {
        if (rank == 0) {
            fprintf(stderr, "Warning! Increase the Max Memory Limit to be able to run up to %ld bytes.\n"
                            "Continuing with max message size of %ld bytes\n", 
                            options.max_message_size, options.max_mem_limit);
        }
        options.max_message_size = options.max_mem_limit;
    }

    options.min_message_size /= sizeof(float);
    if (options.min_message_size < MIN_MESSAGE_SIZE) {
        options.min_message_size = MIN_MESSAGE_SIZE;
    }

    bufsize = sizeof(float)*(options.max_message_size/sizeof(float));
    if (allocate_memory_coll((void**)&sendbuf, bufsize, options.accel)) {
        fprintf(stderr, "Could Not Allocate Memory [rank %d]\n", rank);
        MPI_CHECK(MPI_Abort(MPI_COMM_WORLD, EXIT_FAILURE));
    }
    set_buffer(sendbuf, options.accel, 1, bufsize);

    bufsize = sizeof(float)*(options.max_message_size/sizeof(float));
    if (allocate_memory_coll((void**)&recvbuf, bufsize, options.accel)) {
        fprintf(stderr, "Could Not Allocate Memory [rank %d]\n", rank);
        MPI_CHECK(MPI_Abort(MPI_COMM_WORLD, EXIT_FAILURE));
    }
    // First test set this line set_buffer(recvbuf, options.accel, 0, bufsize);
    // Second test removed it
    
    print_preamble(rank);

    for (size=options.min_message_size; size*sizeof(float) <= options.max_message_size; size *= 2) {

        if (size > LARGE_MESSAGE_SIZE) {
            options.skip = options.skip_large;
            options.iterations = options.iterations_large;
        }

        MPI_CHECK(MPI_Barrier(MPI_COMM_WORLD));

        timer=0.0;
        for (i=0; i < options.iterations + options.skip ; i++) {
            if (options.validate) {
                set_buffer_float(sendbuf, 1, size, i, options.accel);
                set_buffer_float(recvbuf, 0, size, i, options.accel);
                MPI_CHECK(MPI_Barrier(MPI_COMM_WORLD));
            }
            t_start = MPI_Wtime();
            MPI_CHECK(MPI_Allreduce(sendbuf, recvbuf, size, MPI_FLOAT, MPI_SUM, MPI_COMM_WORLD ));
            t_stop=MPI_Wtime();

            if (options.validate) {
                errors += validate_reduction(recvbuf, size, i, numprocs, options.accel);
            }

            if (i>=options.skip){
                timer+=t_stop-t_start;
            }
            MPI_CHECK(MPI_Barrier(MPI_COMM_WORLD));
        }
        latency = (double)(timer * 1e6) / options.iterations;

        MPI_CHECK(MPI_Reduce(&latency, &min_time, 1, MPI_DOUBLE, MPI_MIN, 0,
                MPI_COMM_WORLD));
        MPI_CHECK(MPI_Reduce(&latency, &max_time, 1, MPI_DOUBLE, MPI_MAX, 0,
                MPI_COMM_WORLD));
        MPI_CHECK(MPI_Reduce(&latency, &avg_time, 1, MPI_DOUBLE, MPI_SUM, 0,
                MPI_COMM_WORLD));
        avg_time = avg_time/numprocs;

        if (options.validate) {
            print_stats_validate(rank, size * sizeof(float), avg_time, min_time,
                                max_time, errors);
        } else {
            print_stats(rank, size * sizeof(float), avg_time, min_time, max_time);
        }
        MPI_CHECK(MPI_Barrier(MPI_COMM_WORLD));
    }

    set_buffer(recvbuf, options.accel, 0, bufsize);
    print_preamble(rank);

    for (size=options.min_message_size; size*sizeof(float) <= options.max_message_size; size *= 2) {

        if (size > LARGE_MESSAGE_SIZE) {
            options.skip = options.skip_large;
            options.iterations = options.iterations_large;
        }

        MPI_CHECK(MPI_Barrier(MPI_COMM_WORLD));

        timer=0.0;
        for (i=0; i < options.iterations + options.skip ; i++) {
            if (options.validate) {
                set_buffer_float(sendbuf, 1, size, i, options.accel);
                set_buffer_float(recvbuf, 0, size, i, options.accel);
                MPI_CHECK(MPI_Barrier(MPI_COMM_WORLD));
            }
            t_start = MPI_Wtime();
            MPI_CHECK(MPI_Allreduce(sendbuf, recvbuf, size, MPI_FLOAT, MPI_SUM, MPI_COMM_WORLD ));
            t_stop=MPI_Wtime();

            if (options.validate) {
                errors += validate_reduction(recvbuf, size, i, numprocs, options.accel);
            }

            if (i>=options.skip){
                timer+=t_stop-t_start;
            }
            MPI_CHECK(MPI_Barrier(MPI_COMM_WORLD));
        }
        latency = (double)(timer * 1e6) / options.iterations;

        MPI_CHECK(MPI_Reduce(&latency, &min_time, 1, MPI_DOUBLE, MPI_MIN, 0,
                MPI_COMM_WORLD));
        MPI_CHECK(MPI_Reduce(&latency, &max_time, 1, MPI_DOUBLE, MPI_MAX, 0,
                MPI_COMM_WORLD));
        MPI_CHECK(MPI_Reduce(&latency, &avg_time, 1, MPI_DOUBLE, MPI_SUM, 0,
                MPI_COMM_WORLD));
        avg_time = avg_time/numprocs;

        if (options.validate) {
            print_stats_validate(rank, size * sizeof(float), avg_time, min_time,
                                max_time, errors);
        } else {
            print_stats(rank, size * sizeof(float), avg_time, min_time, max_time);
        }
        MPI_CHECK(MPI_Barrier(MPI_COMM_WORLD));
    }

    free_buffer(sendbuf, options.accel);
    free_buffer(recvbuf, options.accel);

    MPI_CHECK(MPI_Finalize());

    if (NONE != options.accel) {
        if (cleanup_accel()) {
            fprintf(stderr, "Error cleaning up device\n");
            exit(EXIT_FAILURE);
        }
    }

    return EXIT_SUCCESS;
}
```

</details>
And then ran for 60 iterations, the final in [osu/no-set-buffer](osu/no-set-buffer).

Then we ran strace for the same, saving a log for each process.

```
for i in $(seq 1 60); do 
echo $i; 
  mkdir -p $i
  flux run -N2 -n32 sh -c 'strace /opt/osu-benchmark/src/osu-micro-benchmarks-5.8/bin/libexec/osu-micro-benchmarks/mpi/collective/osu_allreduce 2> ${i}/strace.out.$FLUX_TASK_ID'
done
```

Here is an example output:

```
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ------------------
 21.87    0.008327           7      1101       459 openat
 16.82    0.006404          17       358           munmap
 14.37    0.005472           6       826           read
 10.77    0.004100          10       388           mmap
  7.16    0.002727           3       741           close
  5.75    0.002190           4       474        57 newfstatat
  4.83    0.001838           8       209           mprotect
  4.46    0.001700           9       177           write
  3.22    0.001225          14        86         5 ioctl
  1.28    0.000487           7        62        42 connect
  1.27    0.000482           5        92           socket
  1.18    0.000450           6        68        44 readlinkat
  1.04    0.000395           6        62           getdents64
  0.75    0.000287           5        56           recvmsg
  0.61    0.000231          38         6         2 mkdirat
  0.49    0.000188           3        53           setsockopt
  0.46    0.000177           9        18           sendto
  0.39    0.000147           6        24           brk
  0.29    0.000111           2        40           getsockname
  0.28    0.000105          26         4         1 unlinkat
  0.25    0.000096           4        20           bind
  0.20    0.000077           9         8         2 statfs
  0.20    0.000077           3        25           lseek
  0.19    0.000071           2        28           fcntl
  0.17    0.000065           7         9           uname
  0.14    0.000054           6         9         4 faccessat
  0.13    0.000051           3        13           sched_getaffinity
  0.13    0.000049           9         5           sendmsg
  0.12    0.000046           3        15           getpid
  0.11    0.000042          14         3           rt_sigprocmask
  0.11    0.000041           3        12           geteuid
  0.11    0.000040          20         2           shutdown
  0.10    0.000039          39         1           clone
  0.08    0.000032           3        10           getsockopt
  0.08    0.000031           3         9           getuid
  0.06    0.000022          22         1           shmdt
  0.05    0.000019           4         4           futex
  0.04    0.000016          16         1           ftruncate
  0.04    0.000016           2         6           getgid
  0.04    0.000015           2         6           getegid
  0.04    0.000014           0       430           ppoll
  0.04    0.000014          14         1           shmget
  0.04    0.000014           7         2           shmctl
  0.04    0.000014          14         1           shmat
  0.03    0.000013           6         2           listen
  0.03    0.000012           6         2           pipe2
  0.03    0.000012          12         1           clock_nanosleep
  0.02    0.000008           4         2           eventfd2
  0.02    0.000007           1         4           getrandom
  0.02    0.000007           0        21         1 faccessat2
  0.02    0.000006           0         9           rt_sigaction
  0.02    0.000006           6         1           prctl
  0.02    0.000006           6         1           sysinfo
  0.00    0.000001           1         1           gettid
  0.00    0.000000           0         1           getcwd
  0.00    0.000000           0         1           set_tid_address
  0.00    0.000000           0         1           set_robust_list
  0.00    0.000000           0         1           execve
  0.00    0.000000           0         1           prlimit64
  0.00    0.000000           0         1           rseq
------ ----------- ----------- --------- --------- ------------------
100.00    0.038076           6      5516       617 total
```

Note that if we set paranoid to 1 we could have done perf, but this is actually Ok for
what we need to see.

We wound up running OSU again, just for size 2, to confirm that the size 2 was comparable across cases.


```bash
# This is where the example is
flux exec --rank all mkdir -p /home/ubuntu/osu
cd /home/ubuntu/osu

# Create output directory for results
mkdir -p ./results/bare-metal-with-usernetes
flux exec --rank all -x 0 mkdir -p /home/ubuntu/osu
```

And run the experiments:

```bash
for i in $(seq 1 20); do 
    echo "Running iteration $i"
    flux run -N 2 --ntasks 32 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_allreduce  |& tee ./results/bare-metal-with-usernetes/osu_allreduce-${i}.out
done
```

Now let's run the same OSU benchmarks with a container.

```bash
flux exec --rank all --dir /home/ubuntu/osu singularity pull docker://ghcr.io/rse-ops/osu-benchmarks-efa:ubuntu-22.04
container=/home/ubuntu/osu/osu-benchmarks-efa_ubuntu-22.04.sif

# Create output directory for results
mkdir -p ./results/container-with-usernetes
```

Now the experiment loop again

```console
for i in $(seq 1 20); do 
    echo "Running iteration $i"
    flux run -N 2 --ntasks 32 -c 1 -o cpu-affinity=per-task singularity exec $container osu_allreduce  |& tee ./results/container-with-usernetes/osu_allreduce-${i}.out
done
```
Do the same for OSU, on bare metal, with and without a container.


```bash
cd /home/ubuntu/osu
```

Now let's run the same OSU benchmarks with a container.

```bash
# Create output directory for results
mkdir -p ./results/container
```

Now the experiment loop again

```console
for i in $(seq 1 20); do 
    echo "Running iteration $i"
    flux run -N 2 --ntasks 32 -c 1 -o cpu-affinity=per-task singularity exec $container osu_allreduce  |& tee ./results/container/osu_allreduce-${i}.out
done
```

Do the same for OSU, on bare metal, with and without a container.

```bash
mkdir -p ./results/bare-metal
for i in $(seq 1 20); do 
    echo "Running iteration $i"
    flux run -N 2 --ntasks 32 -c 1 -o cpu-affinity=per-task /usr/local/libexec/osu-micro-benchmarks/mpi/collective/osu_allreduce  |& tee ./results/bare-metal/osu_allreduce-${i}.out
done
```
