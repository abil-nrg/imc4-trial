from io import StringIO
import re
import ast
import pandas as pd
import json
from pathlib import Path

def parse_log_backtester(filepath: str | Path):
    """
    Loads a backtester file, cleans it up, and returns DataFrames.
    """
    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"The file at {path} does not exist.")
    
    try:
        # LOAD
        data = path.read_text()
    except Exception as e:
        raise IOError(f"Failed to read the file: {e}")

    try:
        def extract_section(pattern, text, name):
            match = re.search(pattern, text, re.DOTALL)
            if not match:
                raise ValueError(f"Could not find section '{name}' in the log file.")
            return match.group(1).strip()

        sandbox_raw = extract_section(r"Sandbox logs:(.*?)Activities log:", data, "Sandbox")
        activities_raw = extract_section(r"Activities log:(.*?)Trade History:", data, "Activities").replace(";", ",")
        trade_raw = extract_section(r"Trade History:\s*\[(.*?)\]", data, "Trade History")

        # CLEAN UP Activities
        df_activity = pd.read_csv(StringIO(activities_raw))

        # CLEAN UP Trades
        clean_trade_string = trade_raw.strip()
        if not clean_trade_string.startswith('['):
            clean_trade_string = f"[{clean_trade_string}]"
            
        try:
            trade_data = ast.literal_eval(clean_trade_string)
            df_trades = pd.DataFrame(trade_data)
        except (SyntaxError, ValueError) as e:
            print(f"Warning: Failed to parse Trade History as JSON/list. Returning empty DF. Error: {e}")
            df_trades = pd.DataFrame()

        # Placeholder for Sandbox processing
        df_sandbox = None
        
        return df_activity, df_trades, df_sandbox

    except ValueError as ve:
        print(f"Data Formatting Error: {ve}")
        return None, None, None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None, None, None

def parse_official(filepath: str | Path):
    """
    Loads an official JSON log file and returns DataFrames.
    """
    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"The official log file at {path} does not exist.")
    try:
        with path.open('r') as f:
            data = json.load(f)
            
        required_keys = ['activitiesLog', 'tradeHistory']
        for key in required_keys:
            if key not in data:
                raise KeyError(f"Missing required key '{key}' in JSON file.")

        # Process Activities Log
        act_log = data['activitiesLog'].rstrip().replace(";", ",")
        df_activity = pd.read_csv(StringIO(act_log))
        
        df_trades = pd.DataFrame(data['tradeHistory'])
        
        df_sandbox = None

        return df_activity, df_trades, df_sandbox

    except json.JSONDecodeError as e:
        print(f"JSON Parsing Error: Failed to decode JSON from {path}. Error: {e}")
        return None, None, None
    except KeyError as e:
        print(f"Data Schema Error: {e}")
        return None, None, None
    except Exception as e:
        print(f"An unexpected error occurred while parsing official log: {e}")
        return None, None, None

def parse(filepath: str | Path):
    """
    Routes the file to the correct parser based on the filename.
    If the filename contains no '-' or '_', it is treated as an official log.
    """
    path = Path(filepath)
    
    if not path.exists():
        print(f"Error: File {path} not found.")
        return None, None, None

    # Get the filename without extension
    filename = path.stem
    
    # Check for the absence of '-' and '_'
    if "-" not in filename and "_" not in filename:
        return parse_official(path)
    else:
        return parse_log_backtester(path)