#!/usr/bin/env python3

import argparse
import collections
import fnmatch
import os

import matplotlib.pyplot as plt
import pandas
import seaborn as sns

plt.style.use("bmh")
here = os.path.dirname(os.path.abspath(__file__))


def get_parser():
    parser = argparse.ArgumentParser(
        description="Estimate LAMMPS runtimes for AWS + Usernetes",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--data",
        help="data file with estimates",
        default=os.path.join(here, "results", "estimated-times.csv"),
    )
    parser.add_argument(
        "--out",
        help="directory to save image",
        default=os.path.join(here, "img"),
    )
    return parser


def main():
    """
    Run the main plotting operation!
    """
    parser = get_parser()
    args, _ = parser.parse_known_args()

    # Output images and data
    outdir = os.path.abspath(args.out)
    data_file = os.path.abspath(args.data)
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # This does the actual parsing of data into a formatted variant
    # Has keys results, iters, and columns
    import IPython

    IPython.embed()
    df = pandas.read_csv(args.data)
    df.columns = ["problem-size", "nodes", "experiment", "seconds"]
    plot_results(df, outdir)


def plot_results(df, outdir):
    """
    Plot lammps results
    """
    # Plot each!
    colors = sns.color_palette("hls", 16)
    hexcolors = colors.as_hex()
    types = list(df.experiment.unique())
    types.sort()

    # ALWAYS double check this ordering, this
    # is almost always wrong and the colors are messed up
    palette = collections.OrderedDict()
    for t in types:
        palette[t] = hexcolors.pop(0)

    # Make a plot for each problem size
    for problem_size in df["problem-size"].unique():
        subset = df[df["problem-size"] == problem_size]
        make_plot(
            subset,
            title=f"Problem Size {problem_size} for LAMMPS For HPC/Usernetes Setup",
            tag=f"usernetes-flux-estimate-{problem_size}",
            ydimension="seconds",
            xdimension="nodes",
            palette=palette,
            outdir=outdir,
            ext="png",
            plotname=f"usernetes-flux-estimate-{problem_size}",
            hue="experiment",
            xlabel="Nodes",
            ylabel="Time (seconds)",
        )


def make_plot(
    df,
    title,
    tag,
    ydimension,
    xdimension,
    palette,
    xlabel,
    ylabel,
    ext="pdf",
    plotname="lammps",
    hue="experiment",
    outdir="img",
):
    """
    Helper function to make common plots.
    """
    plotfunc = sns.scatterplot
    ext = ext.strip(".")
    plt.figure(figsize=(12, 8))
    sns.set_style("dark")
    ax = plotfunc(x=xdimension, y=ydimension, s=200, hue=hue, data=df, palette=palette)
    plt.title(title)
    ax.set_xlabel(xlabel, fontsize=16)
    ax.set_ylabel(ylabel, fontsize=16)
    ax.set_xticklabels(ax.get_xmajorticklabels(), fontsize=14)
    ax.set_yticklabels(ax.get_yticks(), fontsize=14)
    plt.savefig(os.path.join(outdir, f"{tag}_{plotname}.{ext}"))
    plt.clf()


if __name__ == "__main__":
    main()
