#!/usr/bin/python3

import csv
import os
import re
import string
import time
from datetime import datetime
from multiprocessing import Process
from pathlib import Path

import click
import matplotlib.pyplot as plt
import pandas as pd
import psutil
import seaborn as sns
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

DYE_PLOT = {"ROX": 0, "VIC": 1, "FAM": 2}
DYE_HEAT = {0: "ROX", 1: "VIC", 2: "FAM"}
DIM_X = 20  # 1..19
DIM_Y = 16  # 'P'
WELL_ROWS = list(string.ascii_uppercase[:DIM_Y])
WELL_COLS = [i for i in range(1, DIM_X)]
HEAT_TITLES = {0: "ROX values", 1: "VIC values", 2: "FAM values", 3: "Normalized FAM values", 4: "Normalized VIC values"}
HEAT_BOUNDS = {0: [1500, 5000], 1: [0, 20000], 2: [0, 50000], 3: [0, 17], 4: [0, 10]}
HEAT_HIGHLIGHT = {0: [None, None], 1: [None, None], 2: [None, None], 3: [4, 8], 4: [2, 2.5]}


class DataFile:
    """Handle one file: derive date from filename, parse contents"""

    dye_values = {}  # Values for scatter plot
    dye_plates = {}  # Well representation for heatmap

    def __init__(self, filepath):
        self._filepath = filepath
        self._components = re.split("_|-", os.path.splitext(self.filename)[0])
        self._parse()

    @property
    def array(self):
        return self._components[3]

    @property
    def filename(self):
        return os.path.basename(self._filepath)

    @property
    def filepath(self):
        return self._filepath

    @property
    def timestamp(self):
        return datetime.strptime(self._components[0], "%Y%m%d%H%M%S")

    @property
    def filedate(self):
        return f"{self.array} {self.timestamp.date()}"

    @property
    def keys(self):
        return self.dye_values.keys

    @property
    def dyes(self):
        return self.dye_values

    def __str__(self):
        return f"File: {self.filepath}"

    def __eq__(self, other):
        return self.filepath == other

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    def values(self, dye):
        return self.dye_values[dye]

    def dataframe(self, dye_key):
        if dye_key == 3:  # Normalized FAM
            df = self.dye_plates["FAM"].astype(dtype=float).div(self.dye_plates["ROX"].astype(dtype=float))
        elif dye_key == 4:  # Normalized VIC
            df = self.dye_plates["VIC"].astype(dtype=float).div(self.dye_plates["ROX"].astype(dtype=float))
        else:
            df = self.dye_plates[DYE_HEAT[dye_key]].astype(dtype=float)
        # Apply Vmin, Vmax limits to returned values
        return df.clip(HEAT_BOUNDS[dye_key][0], HEAT_BOUNDS[dye_key][1])

    def _parse(self):
        """Extract file content. Assume 3 space-separated dyes in one file, with layout:
        dye,[ROX,VIC,FAM]
        <>,1,[...]
        [A, B, C, ..],value,[...]
        Assumed dimensions are [A, .. P] by [1, .. 24] based on well array.
        """
        with open(self.filepath) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=",")
            for row in readCSV:
                if len(row) == 0:
                    # Blank lines indicate separation between dyes
                    dye_key = None
                elif row[0] == "<>":
                    # Skip headers
                    continue
                elif row[0] == "Dye":
                    # Assign values to correct dye
                    dye_key = row[1]
                    self.dye_values[dye_key] = set()
                    self.dye_plates[dye_key] = pd.DataFrame(columns=WELL_COLS, index=WELL_ROWS)
                else:
                    # Store all values in Set (for scatter) and DataFrame (for heatmap)
                    self.dye_values[dye_key].update(set(row[1:]))
                    self.dye_plates[dye_key].loc[row[0]] = row[1:]


# Live Graph Functionality


class FileWatchLoop:
    """Main loop watching for changes in a directory"""

    def __init__(self, dirpath, interval=5):
        self.dirPath = dirpath
        self.observer = Observer()
        self.watch_interval = interval

    def run(self):
        # Load existing csv files in directory into list
        _files = [DataFile(Path(self.dirPath, f)) for f in os.listdir(self.dirPath) if f.endswith(".csv")]

        # Observe changes in the directory
        event_handler = Handler(_files)
        self.observer.schedule(event_handler, self.dirPath, recursive=True)
        self.observer.start()
        try:
            print(f"Observer Started. {len(_files)} files already present. Press CTRL-C to stop.")
            while True:
                time.sleep(self.watch_interval)
        except:
            self.observer.stop()
            print("Observer Stopped")

        self.observer.join()


class Handler(FileSystemEventHandler):
    """Handler for change events in directory. Redraw graphs after changes"""

    def __init__(self, files):
        self._files = files
        self._p = Process(target=self._draw)
        self._p.start()  # Display Graph while file watcher loop continues

    def __del__(self):
        self._p.join()

    def _draw(self):
        # Plot values for each dye in separate graph, sorted by date and value
        fig, axs = plt.subplots(3)
        for f in sorted(self._files):
            for dye in f.dyes:
                values = sorted(list(f.values(dye)))
                axs[DYE_PLOT[dye]].scatter([f.filedate] * len(values), values)
                axs[DYE_PLOT[dye]].set(xlabel="Barcode date", ylabel=f"{dye} values")

        plt.show()

    def on_any_event(self, event):
        # Ignore diretory events, only act on adding/deleting files
        if event.is_directory:
            return None
        elif event.event_type == "created":
            self._files.append(DataFile(event.src_path))
        elif event.event_type == "deleted":
            self._files.remove(event.src_path)
        else:
            return None

        # re-draw graph upon add/delete change
        psutil.Process(self._p.pid).terminate()
        self._p = Process(target=self._draw)
        self._p.start()


# Heatmap Functionality


def gen_heatmaps(dirpath, interval=30):
    """Read all files in specified directory, generate 5 heatmaps for each file. Repeat every 30 minutes"""

    try:
        while True:
            files = [DataFile(Path(dirpath, f)) for f in os.listdir(dirpath) if f.endswith(".csv")]
            for f in files:  # Sequentially show heatmaps for all files
                for key in range(0, 5):  # Sequentially show heatmaps for all 5 subgraphs
                    sns.heatmap(
                        f.dataframe(key), annot=True, vmin=HEAT_HIGHLIGHT[key][0], vmax=HEAT_HIGHLIGHT[key][1], fmt="g"
                    )
                    plt.title(f"Array {f.array} {HEAT_TITLES[key]}")
                    plt.xlabel("Well position x")
                    plt.ylabel("Well position y")
                    plt.show()

            time.sleep(interval * 60)  # interval is interpreted as minutes
    except:
        print("Heatmap loop Stopped")


@click.group()
@click.option("--dirpath", "-d", default="data", help="Path where CSV files are")
@click.pass_context
def cli(ctx, dirpath):
    ctx.ensure_object(dict)
    ctx.obj["dirpath"] = dirpath


@cli.command()
@click.option("--interval", "-i", default=5, help="Interval time (seconds) to check for directory changes")
@click.pass_context
def graph(ctx, interval):
    """Display graphs for data in CSV file in directory.
    This function monitors a specified directory for files, and displays
    the values within each file in separate graphs based on dye.
    """
    graphwatch = FileWatchLoop(ctx.obj["dirpath"], interval)
    graphwatch.run()


@cli.command()
@click.option("--detached", "-d", is_flag=True, default=False, help="Spawn separate process")
@click.pass_context
def heatmap(ctx, detached):
    """Display a heatmap.
    This function receives a directory and produces 5 heatmaps for each CSV file.
    """
    if detached:
        p = Process(target=gen_heatmaps(ctx.obj["dirpath"], 30))
        p.start()
        print(f"Started heatmap background process with PID {p.pid}.")
    else:
        print("Heatmap loop started. Press CTRL-C to stop.")
        gen_heatmaps(ctx.obj["dirpath"], 30)


if __name__ == "__main__":
    """Call the process command."""
    cli()
