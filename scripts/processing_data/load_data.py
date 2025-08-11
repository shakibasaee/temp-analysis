import pandas as pd
import os

def load_data(file_path, delimiter=",", encoding = "utf-8"):
    if isinstance (file_path, str):
        if not os.path.exists(file_path):
            raise FileNotFoundError (f"{file_path} not found!")
        file_obj = open(file_path, mode="r", encoding="utf-8")
        df = pd.read_csv(file_obj, delimiter= delimiter)

    else:
        df = pd.read_csv(file_path, delimiter = delimiter)

    return df