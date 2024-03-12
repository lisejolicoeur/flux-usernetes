#!/usr/bin/env python3

import matplotlib.pyplot as plt
import seaborn as sns
import json

with open("test-predict.json", "r") as fd:
    data = json.loads(fd.read())


sns.set_style("whitegrid")

x = data["y_true"]
for model, y_pred in data["y_pred"].items():
    print(model)
    df = pandas.DataFrame()
    df["x"] = x
    df["y"] = y_pred

    if "ricecake" in model:
        title = "Linear Regression Predicting LAMMPS Wall Times from Problem Size"
        saveas = "linear-regression"
        color = "mediumslateblue"
    elif "quirky-rabbit" in model:
        title = "Passive Aggressive Regression Predicting LAMMPS Wall Times from Problem Size"
        saveas = "pa-regression"
        color = "orangered"
    else:
        title = (
            "Bayesian Linear Regression Predicting LAMMPS Wall Times from Problem Size"
        )
        saveas = "bayesian-regression"
        color = "royalblue"

    print(title)
    plt.figure(figsize=(12, 8))
    ax = sns.scatterplot(
        data=df,
        x="x",
        y="y",
        edgecolor="none",
        color=color,
        size=8,
        legend=None,
        alpha=0.8,
    )
    plt.title(title)
    ax.set_xlabel("Predicted time (seconds)", fontsize=16)
    ax.set_ylabel("Actual time (seconds)", fontsize=16)
    ax.set_xticklabels(ax.get_xmajorticklabels(), fontsize=14)
    ax.set_yticklabels(ax.get_yticks(), fontsize=14)
    plt.savefig(f"{saveas}-lammps.png")
    plt.clf()
