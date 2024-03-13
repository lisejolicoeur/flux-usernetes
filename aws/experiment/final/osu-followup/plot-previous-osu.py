#!/usr/bin/env python3

import argparse
import os
import json
import time
import fnmatch

from metricsoperator.metrics.network.osu_benchmark import parse_barrier_section, parse_multi_section
import metricsoperator.utils as utils
import seaborn as sns
import matplotlib.pyplot as plt
import pandas

plt.style.use("bmh")
here = os.path.dirname(os.path.abspath(__file__))


def get_parser():
    parser = argparse.ArgumentParser(
        description="Run OSU Benchmarks Metric and Get Output",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--results",
        help="directory with raw results data",
        default=os.path.join(here, "2-nodes", "results"),
    )
    parser.add_argument(
        "--out",
        help="directory to save parsed results",
        default=os.path.join(here, "img"),
    )
    return parser



def recursive_find(base, pattern="*.*"):
    """
    Recursively find and yield files matching a glob pattern.
    """
    for root, _, filenames in os.walk(base):
        for filename in fnmatch.filter(filenames, pattern):
            yield os.path.join(root, filename)


def find_inputs(input_dir):
    """
    Find inputs (results files)
    """
    files = []
    for filename in recursive_find(input_dir, pattern="*.out"):
        # We only have data for small
        files.append(filename)
    return files


def main():
    """
    Run the main plotting operation!
    """
    parser = get_parser()
    args, _ = parser.parse_known_args()

    # Output images and data
    outdir = os.path.abspath(args.out)
    indir = os.path.abspath(args.results)
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # Find input files (skip anything with test)
    files = find_inputs(indir)
    if not files:
        raise ValueError(f"There are no input files in {indir}")

    # This does the actual parsing of data into a formatted variant
    df = parse_data(files)
    df.to_csv(os.path.join(outdir, f"osu-usernetes-2-nodes.csv"))
    plot_results(df, outdir)


def plot_results(df, img):
    """
    Plot result images to file
    """
    # Separate x and y - latency (y) is a function of size (x)        
    x = "size"
    y = "average_latency_us"

    # for sty in plt.style.available:
    ax = sns.lineplot(
        data=df, x=x, y=y, markers=True, dashes=True, errorbar=("ci", 95), hue="experiment",
    )
    plt.title(f"average latency (y) as a function of {x} (x) on 2 nodes")
    ax.set_xlabel(x + " (logscale)", fontsize=16)
    ax.set_ylabel("Average latency (logscale)", fontsize=16)
    ax.set_xticklabels(ax.get_xmajorticklabels(), fontsize=14)
    ax.set_yticklabels(ax.get_yticks(), fontsize=14)
    plt.xscale("log")
    plt.yscale("log")
    plt.tight_layout()
    plt.savefig(os.path.join(img, f"osu-allreduce-2-nodes-by-experiment.png"))
    plt.clf()
    plt.close()

def parse_data(files):
    """
    Given a listing of files, parse into results data frame
    """
    df_reduce = pandas.DataFrame(
        columns=[
            "ranks",
            "experiment",
            "iteration",
            "size",
            "average_latency_us",
            "nodes",
        ]
    )
    reduce_idx = 0
    
    for filename in files:
        parsed = os.path.relpath(filename, here)
        pieces = parsed.split(os.sep)
        experiment = pieces[-2]
        filebase = pieces[-1]
        if experiment.startswith("_"):
            continue
        # barrier and allreduce, ranks are relevant
        iteration = int(filebase.split("-")[-1].replace(".out", ""))
        nodes = 2
        tasks = 32
        
        # Save CPU line
        # This is a list, each a json result, 20x
        item = utils.read_file(filename)
        if "usernetes" == experiment:
            top = item.split('\n')[0:22]
            top = [x for x in top if x]
            item = "\n".join(top)

        result = parse_multi_section(item.split('\n'))
        for row in result['matrix']:
            df_reduce.loc[reduce_idx, :] = [tasks, experiment, iteration, row[0], row[1], nodes]
            reduce_idx +=1
        
    return df_reduce


if __name__ == "__main__":
    main()
