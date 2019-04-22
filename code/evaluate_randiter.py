#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  6 20:37:25 2018

@author: malvika
Loads feature matrix "feat_maxmul002.pkl". Uses model to classify TSG and OG.
Compares Old, New and all feature sets. Fit each feature set, estimates
paramters for different random seeds and uses mode of n_estimator and
corresponding parameters for model. Ranks the features.
"""
import os
import pickle
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import accuracy_score, f1_score, precision_score
from sklearn.metrics import recall_score
import numpy as np


def getBestParam(Acc_var):
    """
    Get best n_estimator using min variance and other parameters
    """
    max_counts = ([list(Acc_var["n_estimator"]).count(x) for x in
                   list(set(Acc_var["n_estimator"]))])
    max_est = ([x for x in list(set(Acc_var["n_estimator"])) if
                list(Acc_var["n_estimator"]).count(x) == max(max_counts)])
    if len(max_est) == 1:
        best_nEst = max_est[0]
        acc = max(Acc_var[Acc_var["n_estimator"] == best_nEst]["Accuracy"])
    else:
        acc = 0
        for est in max_est:
            if acc < max(Acc_var[Acc_var["n_estimator"] == est]["Accuracy"]):
                acc = max(Acc_var[Acc_var["n_estimator"] == est]["Accuracy"])
                best_nEst = est
    maxf = list(Acc_var[(Acc_var["n_estimator"] == best_nEst) &
                        (Acc_var["Accuracy"] == acc)]["max_features"])[0]
    maxd = list(Acc_var[(Acc_var["n_estimator"] == best_nEst) &
                        (Acc_var["Accuracy"] == acc)]["max_depth"])[0]
    crit = list(Acc_var[(Acc_var["n_estimator"] == best_nEst) &
                        (Acc_var["Accuracy"] == acc)]["criterion"])[0]
    return [best_nEst, maxf, maxd, crit]

# TODO: Set path
PATH = "/home/malvika/Documents/code/IdentificationOfTSG-OG"
DATAPATH = "/home/malvika/Documents/code/data/IdentificationOfTSG-OG"
os.chdir(PATH)
#PATH = "/home/symec-02-01/Documents/IdentificationOfTSG-OG"
#DATAPATH = "/home/symec-02-01/Documents/data/IdentificationOfTSG-OG"
#os.chdir(PATH)
# Folder to save results
folderPath = "/TSG_OG_classifier/evalRandIter"
os.makedirs(PATH + folderPath, exist_ok=True)

# Random seed list to iterate over
# TODO: change the numRandIter to the number of random iterations requires
numRandIter = 320
evalRandIter = [10, 20, 40, 80, 160, 320]
RANDLIST = range(0, numRandIter)
N_EST = range(5, 31)
K_Folds = 5

# TODO: Load feature matrices
os.chdir(PATH + "/TSG_OG_classifier/data/FeatureMat")
fname = "feat_keepv2_MM002.pkl"
with open(fname, 'rb') as f:
    features_cd = pickle.load(f)

# Drop rows where all entries are Nan
features_cd = features_cd[:-1].dropna(subset=list(features_cd.columns[0:-1]))
# Split data
X, y = features_cd.iloc[:, 0:-1], features_cd.loc[:, "Label"]
# Get TSG and OG list
TSGlist = list(features_cd[features_cd["Label"] == "TSG"].index)
OGlist = list(features_cd[features_cd["Label"] == "OG"].index)
# Extract features only for TSG and OG and drop rows if all columns are Nan
X_tsgog = X.loc[TSGlist+OGlist].dropna(how='all')
y_tsgog = y[TSGlist+OGlist].dropna(how='all')
# Get data for unlabelled genes
Unlab = X.drop(TSGlist+OGlist)
Unlab = Unlab.dropna(how='all')
# get list of labels
lab = list(set(y_tsgog))
cols = list(X_tsgog.columns)

# Stratified k-fold
skf = StratifiedKFold(n_splits=K_Folds, random_state=3)
skf.get_n_splits(X_tsgog, y_tsgog)
# Analyse for each feature set for different random seed
Acc_var_cols = ["CV fold", "random_seed", "n_estimator", "max_features",
                "max_depth", "criterion", "Accuracy"]
Acc_var = pd.DataFrame(columns=Acc_var_cols)
for idx, (train_index, test_index) in enumerate(skf.split(X_tsgog, y_tsgog)):
    # Define training and test set
    X_train, X_test = X_tsgog.iloc[train_index], X_tsgog.iloc[test_index]
    y_train, y_test = y_tsgog.iloc[train_index], y_tsgog.iloc[test_index]

    # Scaling
    sc = StandardScaler()
    sc.fit(X_train)
    # Scale data
    X_train = pd.DataFrame(sc.transform(X_train), index=X_train.index,
                           columns=X_train.columns)
    X_test = pd.DataFrame(sc.transform(X_test), index=X_test.index,
                          columns=X_test.columns)
    Unlab_std = pd.DataFrame(sc.transform(Unlab), index=Unlab.index,
                             columns=Unlab.columns)

    # Parameters for grid search
    param_rfc = {'max_features': ['sqrt', 'log2'], 'max_depth': [2, 3, 4],
                 'criterion': ['gini', 'entropy'], 'n_estimators': N_EST}

    for rand_seed in RANDLIST:
        # Find best features for first random seed using grid search
        rfc = RandomForestClassifier(random_state=rand_seed)
        gs = GridSearchCV(estimator=rfc, param_grid=param_rfc,
                          scoring='accuracy', cv=5, verbose=1)
        gs = gs.fit(X_train, y_train)

        # Save best params estimated for the given random seed
        nest = gs.best_params_['n_estimators']
        maxf = gs.best_params_['max_features']
        maxd = gs.best_params_['max_depth']
        crit = gs.best_params_['criterion']
        accv = gs.best_score_
        # Save stats
        Acc_var.loc[len(Acc_var)] = [idx, rand_seed, nest, maxf, maxd, crit,
                                     accv]

        if rand_seed + 1 in evalRandIter:
            os.makedirs("{}{}/seed{}/CV{}".format(PATH, folderPath, rand_seed,
                        idx), exist_ok=True)
            # Get best parameters
            temp_data = Acc_var[Acc_var["CV fold"] == idx]
            [best_nEst, maxf, maxd, crit] = getBestParam(temp_data)
            # Classification using best params
            rfc = RandomForestClassifier(random_state=3,
                                         n_estimators=best_nEst,
                                         max_features=maxf,
                                         max_depth=maxd,
                                         criterion=crit)
            rfc.fit(X_train, y_train)
            # predict labels for training set and test set
            y_pred = rfc.predict(X_test)
            tr_pred = rfc.predict(X_train)
            # Print to file gene labels and prediction
            gene_pred = pd.DataFrame(index=list(X_train.index) +
                                     list(X_test.index))
            gene_pred["Label"] = (list(y_train) + list(y_test))
            gene_pred["Predictions"] = (list(tr_pred) + list(y_pred))
            os.chdir("{}{}/seed{}/CV{}".format(PATH, folderPath, rand_seed,
                     idx))
            fname = "TrainingTest_predictions"
            gene_pred.to_csv(fname, sep="\t", index_label="Gene")
            # calculate metrics and print to o/p file
            f1_tr = f1_score(y_train, tr_pred, average=None, labels=lab)
            f1_ts = f1_score(y_test, y_pred, average=None, labels=lab)
            p_tr = precision_score(y_train, tr_pred, average=None, labels=lab)
            p_ts = precision_score(y_test, y_pred, average=None, labels=lab)
            r_tr = recall_score(y_train, tr_pred, average=None, labels=lab)
            r_ts = recall_score(y_test, y_pred, average=None, labels=lab)
            a_tr = accuracy_score(y_train, tr_pred)
            a_ts = accuracy_score(y_test, y_pred)
            # Feature ranking
            importances = rfc.feature_importances_
            indices = np.argsort(importances)[::-1]
            os.chdir("{}{}/seed{}/CV{}".format(PATH, folderPath, rand_seed,
                     idx))
            with open("Rank_seed{}_{}".format(rand_seed, idx), 'w') as f:
                f.write("# {}\n".format("\t".join(cols)))
                f.write("# Number of features: {:02d}\n".format(len(cols)))
                f.write("# Shape of training set : " +
                        "{}\n".format(X_train.shape))
                f.write("# Shape of test set : " +
                        "{}\n".format(X_test.shape))
                f.write("# Best features:\n")
                f.write("#\tn_estimator:{}\n".format(best_nEst))
                f.write("#\tmax_features:{}\n".format(maxf))
                f.write("#\tmax_depth:{}\n".format(maxd))
                f.write("#\tcriterion:{}\n\n".format(crit))
                f.write("\tTraining\t\tTest\t\n")
                f.write("\t{}\t{}\t{}\t".format(lab[0], lab[1], lab[0]) +
                        "{}\n".format(lab[1]))
                f.write("Accuracy\t{:1.4f}\t\t{:1.4f}\t\n".format(a_tr,
                                                                  a_ts))
                f.write("F1 score\t{:1.4f}\t{:1.4f}\t{:1.4f}\t{:1.4f}\n".format(
                        f1_tr[0], f1_tr[1], f1_ts[0], f1_ts[1]))
                f.write("Precision\t{:1.4f}\t{:1.4f}\t{:1.4f}\t{:1.4f}\n".format(p_tr[0], p_tr[1], p_ts[0], p_ts[1]))
                f.write("Recall\t{:1.4f}\t{:1.4f}\t{:1.4f}\t{:1.4f}\n".format(
                        r_tr[0], r_tr[1], r_ts[0], r_ts[1]))
                f.write("\n\nFeature Ranking\n")
                for rank in range(X_train.shape[1]):
                    f.write("{:02d}\t{}\t{}\t{:1.4f}\n".format(rank + 1,
                            indices[rank],
                            X_train.columns[indices[rank]],
                            importances[indices[rank]]))

# Print to file for given feature matrix
os.chdir("{}{}".format(PATH, folderPath))
filename = "AccVar.txt"
Acc_var.to_csv(filename, sep="\t", header=True, index=False)
