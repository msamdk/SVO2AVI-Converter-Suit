## SVO to AVI Converter Suite for ZED camera systems

A user-friendly desktop application for batch converting and trimming ZED SVO files to the AVI format. This tool provides a graphical user interface (GUI) to simplify the video export process, leveraging the power of the Stereolabs ZED SDK. You can also clone the zed-sdk repository from [here](https://github.com/stereolabs/zed-sdk.git). 

<img src="images/batch conv.png" alt="Alt text" width="800">
<img src="images/trim settings.png" alt="Alt text" width="800">

You can find the main svo to avi conversion script in the following path of the zed-sdk repository of stereolabs. But i have added the script in this repository.

```txt
zed sdk -> recording -> export -> svo -> python -> svo_export.py
```


## Features

* **Batch Conversion**: Convert multiple `.svo` or `.svo2` files from a selected folder in one go.
* **Video Trimming**: A dedicated tab to load a single SVO file, preview its contents, and select specific start and end frames for export.
* **Interactive Preview**: A visual timeline slider allows you to scrub through the video. Play/pause controls are included for easy navigation.
* **Precise Frame Selection**: Set trim points using intuitive "In" and "Out" buttons or by manually typing in the exact frame numbers.
* **Real-time Feedback**: View detailed conversion logs and monitor progress with both individual and overall progress bars.
* **Modern UI**: A clean, themed interface built with Tkinter for a better user experience.
* **Built-in Documentation**: A handy documentation tab explaining the core features of the application.

--------------------------------------------------------------------------------------------------------------------------------------------------
## Requirements
Before you begin, ensure you have the following installed:

- Python 3.x

- ZED SDK: This is the most crucial requirement. You must install the SDK from the Stereolabs website.

  - ➡️ Download the [ZED SDK](https://www.stereolabs.com/en-dk/developers/release/5.0).
  - Important: During the ZED SDK installation, make sure to install the Python API. follow the instructions of the documentation in the official website of the stereolabs website
  - [ZED documentation - Python](https://www.stereolabs.com/en-dk/developers/release/5.0](https://www.stereolabs.com/docs/development/python/install)).
    

- Required Python Libraries:
    - pyzed (This is installed with the ZED SDK's Python API)
    - opencv-python
    - numpy
    - Pillow
-----------------------------------------------------------------------------------------------------------------------------------------------------------

## Setup and Installation

Follow these steps to get the project running on your local machine.

1. Clone the Repository
First, clone this repository to your computer using Git:

```bash
git clone <repository-url>
cd <path to the cloned repository>
```

2. Verify ZED SDK and Python API
Ensure your ZED SDK and the pyzed wrapper are installed correctly. You can test this by trying to import the library in a Python shell:

```python
import pyzed.sl as sl
```
If you don't get an error, you're good to go. If you do, please reinstall the ZED SDK and ensure you select the Python API for your Python version during setup.

3. Install Python Dependencies
The svo_export.py script requires OpenCV and NumPy. You can install them using pip:

```bash
pip install opencv-python numpy Pillow
```

--------------------------------------------------------------------------------------------------------------------------------------------------------------

## How to Use 
1. File Placement: Make sure both svo_export.py and batch_converter_gui.py are in the same directory.
2. Run the Application: Open your terminal, navigate to the project directory, and run the GUI script:

```bash
python batch_converter_gui.py
```
3. Select Folders:

  - Click "Browse..." to select the Input Directory containing your .svo or .svo2 files.
  - Click "Browse..." again to select the Output Directory where the converted .avi files will be saved.

4. Start Converting
  - Click the "Start Conversion" button.
  - Watch the progress bars and log update in real-time.
  - If you need to interrupt the process, click the red "Stop Conversion" button.
--------------------------------------------------------------------------------------------------------------------------------------------------------------
## File Structure

- svo_export.py: The original command-line conversion script provided by Stereolabs. This script is called as a subprocess by the GUI for each file.
- batch_converter_gui.py: The main application file that provides the graphical user interface and batch processing logic. This is the file you run.
- README.md: This file.

--------------------------------------------------------------------------------------------------------------------------------------------------------------

## License
- The batch converter GUI (batch_converter_gui.py) is released under the MIT License.
- Please note that the svo_export.py script is provided by Stereolabs and is subject to its own license, which can be found in the header of the file.







