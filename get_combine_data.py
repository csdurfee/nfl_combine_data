## https://www.pro-football-reference.com/draft/2010-combine.htm

import requests
import pandas as pd
import numpy as np
import time
import random
import os

from scipy.sparse import csr_matrix

YEAR_RANGE = range(2000, 2026)
TARGET_DIR = "combine_data/"

NUMERIC_COLS = ['Wt', '40yd', 'Vertical', 'Bench', 'Broad Jump', '3Cone', 'Shuttle']

## the value indicates whether metric should be sorted ascending or descending
## False => the lowest score will be a 99 (smaller values are better, eg sprint time)
## True  => the highest score will be a 99 (larger values are better, eg vertical jump)
COMBINE_METRICS = { '40yd'      : False,  
                    'Vertical'  : True,  
                    'Bench'     : True, 
                    'Broad Jump': True, 
                    '3Cone'     : False, 
                    'Shuttle'   : False
                }

GENERAL_POSITION_MAP = {
        'ILB': 'LB',
        'OLB': 'LB',
        'DE': 'DL',
        'DT': 'DL',
        'OG': 'OL',
        'C': 'OL',
        'G': 'OL',
        'P': 'ST',
        'K': 'ST',
        #'EDGE': 'LB', # if something happens to me, it's because some football nerd got mad at this
        'FB': 'RB',     # ...or this one
        'OT': 'OL',
        'SAF': 'S',
        'CB/WR': 'CB', # Travis Hunter LOL
    }

POSITION_NAME_MAP = {
    "CB": "Cornerback",
    "DL": "Defensive Line",
    "FB": "Fullback",
    "LB": "Linebacker",
    "OL": "Offensive Line",
    "QB": "Quarterback",
    "RB": "Running Back",
    "S": "Safety",
    "TE": "Tight End",
    "WR": "Wide Receiver"

}
DECILE_NAME_MAP = {
    "pos_d_40yd": "40 Yard Dash",
    "pos_d_Broad Jump": "Broad Jump",
    'pos_d_Vertical': "Vertical Leap",
    'pos_d_Shuttle': "Shuttle", # TODO: Fix description
    'pos_d_3Cone': "3 Cone Drill",
    'pos_d_Bench': "Bench Press"
}

QUANTILE_NAME_MAP = {
    "q_40yd": "40 Yard Dash",
    "q_Vertical": "Vertical Leap",
    "q_Broad Jump": "Broad Jump",
    "q_Bench": "Bench Press",
    "q_Shuttle": "Shuttle",
    "q_3Cone": "3 Cone Drill"
}

EXTRACT_DRAFTED = r"(?P<tm>.+) / (?P<rnd>\d+).+ / (?P<pick>\d+).+ / (?P<yr>.+)"

DROP_COLS = ['College'] # this is a link to college stats.

SKIP_POSITIONS = ["ST"] # these are sparse, generally not interesting


def get_base_data():
    dataframes = []
    for year in YEAR_RANGE:
        target_file = f"{TARGET_DIR}{year}-combine.json"
        if not os.path.exists(target_file):
            url = f"https://www.pro-football-reference.com/draft/{year}-combine.htm"
            r = requests.get(url)

            df = pd.read_html(r.content)[0]
            with open(target_file, "w") as f:
                f.write(df.to_json())
            time.sleep(6 * random.random()) # don't crawl too hard
        else:
            df = pd.read_json(target_file)

        df['CombineYear'] = year
        dataframes.append(df)
    ## TODO: here. should rewrite this so it serializes the dataframe for next time.
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

    return all_data.join(extracted)

def fix_positions(all_data):
    all_data.loc[all_data.Pos == "DB", "Pos"] = "S" # curse you, Minkah Fitzpatrick
    all_data.loc[all_data.Pos == "LS", "Pos"] = "C" # long snappers
    return all_data

def get_positions(all_data, pos_key='Pos'):
    all_positions = list(set(all_data[pos_key].values))
    return all_positions

def add_general_positions(data):
    data['general_position'] = data.Pos.replace(GENERAL_POSITION_MAP)
    return data


def get_quantiles(all_data, position_key='Pos'):
    """
    Calculates overall quantiles for each player's score
    Calculates quantiles for current position for each player's score.
    """
    quantile_columns = []
    decile_columns = []

    quantile_data = pd.DataFrame(index=all_data.index)
    ## overall quantiles
    for metric in COMBINE_METRICS.keys():
        asc = COMBINE_METRICS[metric]
        quantiles = pd.qcut(all_data[metric].rank(method="first", ascending=asc), 100, labels=False)
        column_label = f"q_{metric}"
        quantile_data[column_label] = quantiles
        quantile_columns.append(column_label)

    ## quantiles for each position
    for metric in COMBINE_METRICS.keys():
        col_name = f"pos_d_{metric}"
        decile_columns.append(col_name)
        quantile_data[col_name] = np.nan
        positions = get_positions(all_data, position_key)
        #print(f"positions are {positions}")
        for position in positions:
            position_players = all_data[all_data[position_key] == position]

            pos_with_metric = sum(~position_players[metric].isna())

            # we can't split up into deciles unless there are at least 10 of position + metric combo
            if pos_with_metric < 10:
                #print(f"on position {position}, can't do metric {metric}")
                pass
            else:
                asc = COMBINE_METRICS[metric]
                deciles_for_pos = pd.qcut(position_players[metric].rank(method="first", ascending=asc), 10, labels=False)
                quantile_data.loc[position_players.index, col_name] = deciles_for_pos

    # calculate mean decile score to get a 0-9 score for all-around athleticism
    # this is flawed:
    # 1) some events are more important for some positions (eg. CB and speed, OL and strength)
    # 2) not every athlete does every event and might actually skip events they think they'll do bad at
    # 3) I didn't actually show the events are all normally distributed, so adding them up isn't necessarily
    #    going to give us another normal distribution
    quantile_data['composite_score'] = quantile_data[decile_columns].mean(axis=1)

    return quantile_data

def get_data(drafted_only=True, position_key='Pos'):
    dataframes = get_base_data()
    processed_data = process_data(dataframes)
    processed_data = add_general_positions(processed_data)
    if drafted_only:
        players_to_analyze = processed_data[~processed_data.DraftNumber.isna()]
    else:
        players_to_analyze = processed_data

    ## if drafted_only, quantiles will be calculated from just drafted players.
    q_data = get_quantiles(players_to_analyze, position_key)
    all_data = players_to_analyze.join(q_data)

    return all_data

def top_players_at_position(all_data, n_players=50):
    """
    This is for the PCA analysis plot.
    """
    player_ids = []
    sample = all_data.groupby(by="general_position").composite_score.nlargest(n_players)
    for row in sample.items():
        if row[0][0] not in SKIP_POSITIONS:
            player_ids.append(row[0][1])
    return all_data.loc[player_ids]

def most_corr_with_draft_pos(all_data, flat_rows=True):
    """
    For each position in all_data, return a sorted Series of most->least important exercises
    """
    corr_with = {}
    abs_corrs = all_data.groupby(by="general_position").corr(numeric_only=True)["DraftNumber"].abs()
    for (idx, value) in abs_corrs.items():
        if idx[0] not in SKIP_POSITIONS:
            if idx[0] not in corr_with:
                corr_with[idx[0]] = {}
            if idx[1].startswith("pos_d"):
                corr_with[idx[0]][idx[1]] = value
    
    corr_series = {}
    for (idx, value) in corr_with.items():
        position_series = pd.Series(value).fillna(0)
        with_rank = pd.DataFrame({"value": position_series, "rank": position_series.rank(ascending=False)}).sort_values("rank")
        corr_series[idx] = with_rank
    ## now turn these into a flat list (I could probably make the above work with the right altair knowledge, but this is faster)
    if not flat_rows:
        return corr_series
    else:
        return_rows = []
        for (position, dataframe) in corr_series.items():
            for row in dataframe.iterrows():
                # position, exercise name, rank, value
                this_row = [position, unmunge_exercise_name(row[0]), int(row[1]["rank"]), row[1]["value"]]
                return_rows.append(this_row)
        return_df = pd.DataFrame(return_rows, columns=["Position", "Event", "Rank", "Importance"])

        return return_df



def unmunge_exercise_name(colname):
    if colname in DECILE_NAME_MAP:
        return DECILE_NAME_MAP[colname]
    else:
        return colname

def quantiles_as_eav(all_data, position='all', position_key='Pos'):
    # filter data to just this posision
    if position == 'all':
        filtered_data = all_data
    else:
        filtered_data = all_data[all_data[position_key] == position]
    # remove positions that don't have enough data to be interesting.
    filtered_data = filtered_data[~all_data[position_key].isin(SKIP_POSITIONS)]

    quantile_cols = list(filtered_data.columns[filtered_data.columns.str.startswith("q_")])
    quantile_cols.append(position_key)
    quantile_data = filtered_data.loc[:, quantile_cols]

    # rename quantile columns
    # why is this here?
    #quantile_data = quantile_data.rename(NAME_MAP, axis=1)
    
    # this works correctly (I verified same data) but is a mess
    mess = quantile_data.pivot(columns=position_key).unstack().reset_index().dropna()
    eav_format = mess.drop("level_2", axis=1).rename({0: "result", position_key: "position", "level_0": "event"}, axis=1)

    # now swap in full names for exercises and positions.
    eav_format.event = eav_format.event.replace(to_replace=QUANTILE_NAME_MAP)

    eav_format.position = eav_format.position.replace(to_replace=POSITION_NAME_MAP)
    return eav_format

def get_norm_data(all_data):
    quant_cols = [x for x in all_data.columns if x.startswith("q_")]
    X = all_data[quant_cols]
    X_norm = X.fillna(49.5) - 49.5 # note: percentiles go from 0..99
    return X_norm

def get_sparse_data(all_data):
    X_norm = get_norm_data(all_data)
    X_sparse = csr_matrix(X_norm)
    return X_sparse
    

def get_pca_coords(general_pos_data=None):
    from sklearn.decomposition import TruncatedSVD
    if not general_pos_data:
        general_pos_data = get_data(True, 'general_position')

    X_norm = get_norm_data(general_pos_data)

    X_sparse = csr_matrix(X_norm)

    svd = TruncatedSVD(n_components=2)
    svd.fit(X_sparse)

    transformed = svd.transform(X_sparse)
    return transformed # x,y coordinates for all rows


