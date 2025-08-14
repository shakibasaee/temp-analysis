import pandas as pd
import os

def load_data(file_path, file_type, **kwargs):
    if isinstance (file_path, str):
        if not os.path.exists(file_path):
            raise FileNotFoundError (f"{file_path} not found!")
        if (file_type == "csv"):
            kwargs.setdefault("delimiter", ",")
            kwargs.setdefault("encoding", "utf-8")
            df = pd.read_csv(file_path, **kwargs)
        elif (file_type == "excel"):
            kwargs.setdefault("sheet_name", "sheet1")
            kwargs.setdefault("header", "1")
            df = pd.read_excel(file_path, **kwargs)
        elif (file_type == "json"):
            kwargs.setdefault("structur", "record")
            kwargs.setdefault("lines", "Yes")
            kwargs.setdefault("encoding", "utf-8")

            df = pd.read_json(file_path, **kwargs)

    return df