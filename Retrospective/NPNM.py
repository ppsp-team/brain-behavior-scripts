#!/usr/bin/env python
# coding=utf-8

# ==============================================================================
# title : NPNM.py
# description : Nonparametric normative modeling based on age of participants
# author : Guillaume Dumas, Human Genetics & Cognitive Functions, Institut Pasteur
# date : 2017
# version : 1.0
# usage : python NPNM.py
# python_version : 2.7, 3.6
# license : BSD (3-clause)
# ==============================================================================

import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.sandbox.regression.predstd import wls_prediction_std

# Load phenotypes
data = pd.read_csv("phenotypes.csv")

# Normalize the raw data globally
data.loc[:, 'score'] = (data.loc[:, 'score'] - np.nanmean(data.loc[:, 'score'])) / np.nanstd(data.loc[:, 'score'])

# Check the range of Age and Score
min_age = np.min(data.loc[:, 'age'])
max_age = np.max(data.loc[:, 'age'])
min_score = np.min(data.loc[:, 'score'])
max_score = np.max(data.loc[:, 'score'])

# Define smoothness of the LOESS
griddef_age = 360 / 2  # half a year
kernel_age = griddef_age * 5
x = np.arange(min_age, max_age + kernel_age, griddef_age)

# Select CTR to run the normative model
sel = data.loc[(data.ctr == True), ['age', 'score']].values
d = sel[:, :1]

# Init
zm = np.zeros(x.shape[0])
zstd = np.zeros(x.shape[0])
zci = np.zeros([x.shape[0], 2])

# Calculate LOESS
for i, xx in enumerate(x):
    mu = np.array(xx)
    w = (abs(d - mu) < kernel_age) * 1.
    idx = np.argwhere(w).flatten()
    YY = sel[idx, 1]
    XX = sel[idx, 0] - mu
    try:
        mod = sm.WLS(YY, sm.tools.add_constant(XX),
                     missing='drop',
                     weight=w[idx],
                     hasconst=True).fit()
        zm[i] = mod.params[0]
        prstd, iv_l, iv_u = wls_prediction_std(mod, [0, 0])
        zci[i, :] = mod.conf_int()[0, :]  # [iv_l, iv_u]
        zstd[i] = prstd
    except:
        zm[i] = np.nan
        zci[i] = np.nan
        zstd[i] = np.nan


def normative_model(r):
    """Function to compute the normative score."""
    idage = np.argmin(np.abs(r['age'] - x))
    m = zm[idage]
    std = zstd[idage]
    nmodel = (r['score'] - m) / std
    return nmodel


# Apply the normative model to all the data
data.loc[:, 'nmodel'] = data.apply(normative_model, axis=1)

# Calculate ranks associated with the normative scores
data.loc[(data.nmodel <= -2), 'rank'] = -2
data.loc[(data.nmodel > -2) * (data.nmodel <= -1), 'rank'] = -1
data.loc[(data.nmodel > -1) * (data.nmodel <= +1), 'rank'] = 0
data.loc[(data.nmodel > +1) * (data.nmodel <= +2), 'rank'] = 1
data.loc[(data.nmodel > +2), 'rank'] = 2

data.to_csv("phenotypes_npnm.csv")
