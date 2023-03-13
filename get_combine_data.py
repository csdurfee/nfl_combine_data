## https://www.pro-football-reference.com/draft/2010-combine.htm

import requests
import pandas as pd
import numpy as np
import time
import random
import os

YEAR_RANGE = range(2000, 2021)
TARGET_DIR = "combine_data/"

NUMERIC_COLS = ['Wt', '40yd', 'Vertical', 'Bench', 'Broad Jump', '3Cone', 'Shuttle']

COMBINE_METRICS = ['40yd', 'Vertical', 'Bench', 'Broad Jump', '3Cone', 'Shuttle']

EXTRACT_DRAFTED = r"(?P<tm>.+) / (?P<rnd>\d+).+ / (?P<pick>\d+).+ / (?P<yr>.+)"

DROP_COLS = ['College'] # this is a link to college stats.

def get_data():
    dataframes = []
    
    for year in YEAR_RANGE:
        target_file = f"{TARGET_DIR}{year}-combine.htm"
        if not os.path.exists(target_file):
            url = f"https://www.pro-football-reference.com/draft/{year}-combine.htm"
            r = requests.get(url)

            with open(target_file, "w") as f:
                f.write(str(r.content))
            df = pd.read_html(r.content)[0]
            time.sleep(6 * random.random()) # don't crawl too hard
        else:
            df = pd.read_html(target_file)[0]

        df['CombineYear'] = year
        dataframes.append(df)
    return dataframes

def process_data(dataframes):
    all_data = pd.concat(dataframes, ignore_index=True)


    ## these are header rows, not actual players.
    all_data = all_data.drop(all_data[all_data.Wt == "Wt"].index, axis=0)

    all_data[NUMERIC_COLS] = all_data[NUMERIC_COLS].astype(float)

    all_data = all_data.drop(DROP_COLS, axis=1)

    all_data = fix_positions(all_data)

    extracted = all_data["Drafted (tm/rnd/yr)"].str.extract(EXTRACT_DRAFTED)

    ## I think there are some years where teams lose their picks, so the draft number may not be right
    ## not all drafted players go to the combine, so it would be non-trivial to figure out the real number.
    ## using floats here because there are NaN values for players not drafted.

    extracted['DraftNumber'] = extracted.pick.astype(float) + (32 * (extracted.rnd.astype(float) - 1))

    ## TODO? Height?

    return all_data.join(extracted)

def fix_positions(all_data):
    all_data.loc[all_data.Pos == "DB", "Pos"] = "S" # curse you, Minkah Fitzpatrick
    all_data.loc[all_data.Pos == "LS", "Pos"] = "C" # long snappers

    return all_data

def get_positions(all_data):
    all_positions = list(set(all_data.Pos.values))
    return all_positions


def get_quantiles(all_data):
    """
    Calculates overall quantiles for each player's score
    Calculates quantiles for current position for each player's score.
    """
    quantile_data = pd.DataFrame(all_data.index)
    ## overall quantiles
    for metric in COMBINE_METRICS:
        quantiles = pd.qcut(all_data[metric].rank(method="first"), 100, labels=False)
        column_label = f"q_{metric}"
        quantile_data[column_label] = quantiles 

    ## quantiles for each position
    """
    all_data.loc[all_data.Pos == "OLB", "foo"] = pd.qcut(all_data[all_data.Pos == "OLB"] \
        .Bench.rank(method="first"), 100, labels=False)
    """
    for metric in COMBINE_METRICS:
        col_name = f"pos_d_{metric}"
        quantile_data[col_name] = np.nan
        for position in get_positions(all_data):
            position_players = all_data[all_data.Pos == position]

            pos_with_metric = sum(~position_players[metric].isna())

            # we can't split up into deciles unless there are at least 10 of position + metric combo
            if pos_with_metric < 10:
                print(f"on position {position}, can't do metric {metric}")
            else:
                deciles_for_pos = pd.qcut(position_players[metric].rank(method="first"), 10, labels=False)
                # I don't know if this works or not...
                quantile_data[col_name] = deciles_for_pos
            
    # FIXME: some metrics have a high "good" score (bench press), others have a low "good" score (40 yard dash)
    # the percentiles/deciles should be so that 1 is bad and 10 (or 100) is good for all of them.

    return all_data.join(quantile_data)

if __name__ == '__main__':
    dataframes = get_data()

    processed_data = process_data(dataframes)


    


