#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  6 20:37:25 2018

@author: malvika
Loads data required and creates feature matrix specific for tissues.
Loads the Pan cancer model and standard scaler to classifies genes for a
given each tissue
"""
import os
import pickle
import glob
import pandas as pd
import identifyTSGOG as ito


def findLabel(row):
    """
    Find label for the given data based on max probaility. Labels are assigned
    based on max probability.
    """
    if row["Max score"] == row["TSG"]:
        label = "TSG"
    elif row["Max score"] == row["OG"]:
        label = "OG"
    return label


def findCumLabel(row, cv=5):
    """
    Find label for the given data based on multiple cv models. Labels are
    assigned based on mode.
    """
    labels = [row["Label_{}".format(x)] for x in range(cv) if
              row["top_stat_{}".format(x)] == 1]
    countTSG = labels.count("TSG")
    countOG = labels.count("OG")
    if countTSG > countOG:
        return "TSG"
    elif countOG > countTSG:
        return "OG"
    else:
        return "Unlabelled"


def findTop(row, treshold):
    """
    """
    if row["Max score"] >= treshold:
        return 1
    else:
        return 0


# TODO: Set path
PATH = "/set/absolute/path/to/IdentifyTSGOG"
os.chdir(PATH)

# Folder to save results
folderPath = "/output/TissueSpecificAnalyisis"
os.makedirs(PATH + folderPath, exist_ok=True)

Kfolds = 5
percentile = 5
sc = [None] * Kfolds
rfc = [None] * Kfolds
for fold in range(Kfolds):
    os.chdir(PATH + "/output/RandomForest/CV/{}".format(fold))
    # Load scaler fit
    fname = "cosmicStdScale.pkl"
    with open(fname, 'rb') as f:
        sc[fold] = pickle.load(f)
    # Load the model
    fname = "randIterRFv5Model_allFeat.pkl"
    with open(fname, 'rb') as f:
        rfc[fold] = pickle.load(f)

os.chdir(PATH + "/data/FeatureMat/tissues")
tiss_files = glob.glob('*.pkl')
for file in tiss_files:
    prob_df = pd.DataFrame()
    os.chdir(PATH + "/data/FeatureMat/tissues")
    with open(file, 'rb') as f:
        features_cd = pickle.load(f)
    # Drop rows where all entries are Nan
    tsg_og_feat = features_cd[:-1].dropna(subset=list(features_cd.columns[0:-1]))

    for fold in range(Kfolds):
        # Standard scaling
        all_std = pd.DataFrame(sc[fold].transform(tsg_og_feat.iloc[:, 0:-1]),
                               index=tsg_og_feat.index,
                               columns=tsg_og_feat.iloc[:, 0:-1].columns)

        # Prediction of novel driver genes
        novel_prob = pd.DataFrame(rfc[fold].predict_proba(all_std),
                                  index=all_std.index,
                                  columns=rfc[fold].classes_).sort_values(
                                          by=["TSG"], ascending=False)
        # Print to file
        os.makedirs("{}{}/{}".format(PATH, folderPath, file[5:-4]),
                    exist_ok=True)
        os.chdir("{}{}/{}".format(PATH, folderPath, file[5:-4]))
        filename = "prob_{}{}.txt".format(file[5:-4], fold)
        novel_prob.to_csv(filename, sep="\t", header=True, index=True)
        # Find labels based on scores
        novel_prob["Max score"] = (novel_prob.apply(max, axis=1))
        novel_prob["Label"] = (novel_prob.apply(findLabel, axis=1))
        rank = int(len(novel_prob) * percentile / 100)
        treshold = sorted(novel_prob["Max score"], reverse=True)[rank]
        novel_prob["top_stat"] = (novel_prob.apply(findTop, axis=1,
                                                   treshold=treshold))
        novel_prob = novel_prob.drop(["OG", "TSG"], axis=1)
        prob_df = prob_df.join(novel_prob.add_suffix("_{}".format(fold)),
                               how="outer")

    prob_df["Label"] = prob_df.apply(findCumLabel, axis=1)
    os.chdir("{}{}/{}".format(PATH, folderPath, file[5:-4]))
    fname = "CVpredictions.txt"
    prob_df.to_csv(fname, sep="\t", index_label="Gene name")
