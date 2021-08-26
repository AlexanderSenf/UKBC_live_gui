# UKBC live GUI examples

This project displays a variety of graphs based on CSV files in a directory. One option displays a scatterplot of values for all files in a directory and updates automatically if files are added or removed from the directory. The other option presents five heatmap plots for each file in the directory, and repeats the process every 30 minutes.
## Requirements
The project was written using Python 3.6 in Ubuntu 18.04 running in WSL2 on a Windows 10 host, using VcXsrv as X server for display ([installation instructions](https://stackoverflow.com/questions/43397162/show-matplotlib-plots-and-other-gui-in-ubuntu-wsl1-wsl2)). It has been tested running Python 3.9 in Windows 10 directly as well.
## Installation
The project can be run from this repository:

    git clone https://github.com/AlexanderSenf/UKBC_live_gui.git
    cd UKBC_live_gui
    pip install -r requirements [or pip3]
    python display_csv/display_csv.py [or python3]
It should also be possible to `pip` install it from GitHub directly:
```bash
pip install git+git://github.com/AlexanderSenf/UKBC_live_gui.git#egg=display_csv
```
## Assumptions
The project is built with these assumptions:

 - File names in a specified directory all follow a standard naming scheme comprised of 4 components: `{timestamp}_{?}-{?}-{array}.csv`.  The timestamp and array number are used in the display.
 - Each file contains three sets of values for the array: `ROX`, `FAM`, `VIC`. Based on the provided example it is assumed that each file contains the array measurements in groups separated by space.
 - It is assumed that each file contains a complete set of data. There is no code added to deal with missing values.
## Requirement Assessment
This is an assessment of how each of the stated requirements has been interpreted and implemented.
### Part 1
Part one implements a live view if the range of values in all files in a directory, and is updated automatically if files are added or removed. There are three graphs, showing values for each of the three values.
#### Produce software to provide live graphing of ROX, FAM and VIC values from ePCR Nexar array files as they are created and placed in specific directories
A plot containing three subgraphs is created. The graphs are oriented in a vertical display by default. This places the plot of values for the same date in the same position horizontally across the plot. This might make it easier to compare values for each day.
Upon start, the specified directory is scanned and any existing files are used to create the initial graph. If there are none, the graph is empty.
Once started, the process will monitor the the specified directory. If files are added, or deleted, the graph is re-created to reflect the current content of the directory.
The polling interval for the directory can be specified, the default value is 5 seconds.
#### Values within files for ROX, VIX and FAM must be grouped by date and plotted on a live time series scatter plot similar to the one depicted below
The date is derived from the filename, which starts with a timestamp. The display is ordered based on the timestamp.
#### The display should show 3 plots, one each for ROX, FAM and VIC
This is implemented by showing three subplots in the same graph, one for each of the values.
#### The software should be able to run 24/7
Once started the process will continue until interrupted (e.g. by `CTRL-C`).
#### As files are added or removed from the directory path, the software should remove/add the respective value(s) contained in the file(s)
The process keeps all files in a local cache; if a change is detected in the directory  then files are either added or removed from the cache immediately (add/remove are the only file system actions monitored).
Every change to the cache triggers a re-drawing of the graph, so what is displayed always reflects what is in the directory.
#### The software should be able to take a directory as an input via configuration
This is interpreted to me an option provided upon start-up, with a default set in the code. An alternative interpretation could be to read that value from an environment variable, or a configuration file. 
#### Program must be able to read multiple files and work via files being placed in a live directory
All files in a directory are read and the contents added to a display.
#### Should be able to be compiled and deployed on any windows machine or server
This is interpreted to mean that it allows for installation via `pip` to produce an `egg`. This GitHub repository should allow for that with the instructions provided at the top. An alternative interpretation could have meant to compile the code into a `.pyc` file.
#### Within scripting, the software should have efficient memory and resource management
This is a bit vague. There is a certain correspondence between what is produced (a display of values in screen) and the amount of data for which that makes sense. For example, while the code should be able a million files, the resulting display would be entirely meaningless. So it can be assumed that there is an upper limit to the amount of data handled at each point in time. This limitation allows for all the data to be kept in a memory cache (in this case a dictionary containing sets of values) that is updated according to addition and deletion of files in the directory. 
The expected upper limit of files also allows for a some code re-use to balance memory efficiency concerns. The same code is used for both scatter plot and heatmap, so the script actually keeps two sets of values for each file, to make it easier to handle the data for each use case. The heatmap code uses Pandas dataframes to represent the data for each dye value in each file. This is inefficient from a resource point of view, but efficient from a coding point of view.
A production version of this code would address handling the data in a much more robust way, and seek to clarify the parameters within which the code should be able to function.
### Part 2
Part two displays five heatmaps for the same set of files, and updates the displays every 30 minutes.
#### Produce a heatmap for each file for the ROX, VIC and FAM values and normalised FAM (=FAM/ROX) and normalised VIC (=VIC/ROX)
This is a bit vague. This produces 5 graphs for each file in a directory that contains multiple files. This already precludes the possibility to display everything on screen at the same time. At the minimum this produces each heatmap in sequence, and displays the map on screen; this is the interpretation chosen in this implementation.
This would provide a basis to show the customer and clarify how they would like the graphs to be handled in the final product.
#### Heatmap display for each file should show five heatmaps for each of the above
Five heatmaps are generated for each file. One for each of the three dye values, and two normalised maps based some calculation.
#### The heatmap should display the value for each well position in a grid format with upper and lower bounds as defined below:
* ROX: Vmax = 5000, Vmin = 1500
* FAM: Vmax = 50000, Vmin = 0
* VIC: Vmax = 20000, Vmin = 0
* Normalised FAM: Vmax = 17, Vmin= 0, values between 4 and 8 highlighted
* Normalised VIC: Vmax = 10, Vmin = 0, values between 2 and 2.5 highlighted

These values are hard-coded in constants in the code, and applied to the data upon generating each individual display. This would allow for an easy change where the values could be placed in a config file in the future, if the customer would foresee changes to these values. 
#### Heatmap should display the array barcode, wells processed, wells average and colour coded scale
The array code (assumed to be the bar code) is in the title of each graph. The assumption is always that the data files are complete, which means that the number of wells processed is constant (although I would seek to clarify that with the customer for the final version of the product). 
*The wells average display is currently missing from the graph.*
#### The scheduling for heatmaps being produced should be every 30 mins, with the appropriate folder structure and naming conventions
Once the final heatmap has been displayed, there is a 30 minute wait until the whole process repeats. The process can be started as a blocking process, which keeps running until an interruption (e.g. `CTRL-C`), or it can spawn a separate process, which runs on it own. This would have to be stopped using its process ID.
This requirement points towards graphs being generated as image files and stored in a certain location; which would be quite sensible; but nothing is specified in any more detail. This would be one of the first questions I would ask the customer, and one of the first use cases to present, to ensure that the final product meets needs and expectations.
## Comments
I usually work on back end code, not on GUI components; so this was quite a fun and very different project to do. My limited interest and experience in GUIs means that the code is not the most optimal solution to each task, but it does its job, and Python allows me to do it fairly quickly. If I had more than just a couple of hours to spend on this project, I would have chosen to write this as a [TraitsUI](https://github.com/enthought/traitsui) application, which is designed for use cases just like this.