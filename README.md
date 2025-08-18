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
* **Real-time Frame count**: The frame number is displayed as an overlay on the video to get the precise frame for analysis
* **Modern UI**: A clean, themed interface built with Tkinter for a better user experience.
* **Built-in Documentation**: A handy documentation tab explaining the core features of the application.

--------------------------------------------------------------------------------------------------------------------------------------------------
## Requirements
Before you begin, ensure you have the following installed:

- **Python 3.7+**

- **ZED SDK**: This is the most crucial requirement. You must install the SDK from the Stereolabs website.

  - ➡️ Download the [ZED SDK](https://www.stereolabs.com/en-dk/developers/release/5.0).
  - Important: During the ZED SDK installation, make sure to install the Python API. follow the instructions of the documentation in the official website of the stereolabs website
  - [ZED documentation - Python](https://www.stereolabs.com/en-dk/developers/release/5.0](https://www.stereolabs.com/docs/development/python/install)).
  - 
 - **NVIDIA CUDA**: The ZED SDK requires a compatible version of the NVIDIA CUDA Toolkit.   

- **Required Python Libraries**: (Use the requirements.txt file)
    - pyzed (This is installed with the ZED SDK's Python API)
    - opencv-python
    - numpy
    - Pillow
 
  
-----------------------------------------------------------------------------------------------------------------------------------------------------------

## Setup and Installation

Follow these steps to get the project running on your local machine.

**Step 1. Clone the Repository**
First, clone this repository to your computer using Git:

```bash
git clone <repository-url>
cd <path to the cloned repository>
```
**Step 2. Install Required Python Libraries**
The necessary Python packages are listed in the `requirements.txt` file. Install them using pip:
```bash
pip install -r requirements.txt
```

**Step 3. Verify ZED SDK and Python API**
Ensure your ZED SDK and the pyzed wrapper are installed correctly. You can test this by trying to import the library in a Python shell:

```python
import pyzed.sl as sl
```
If you don't get an error, you're good to go. If you do, please reinstall the ZED SDK and ensure you select the Python API for your Python version during setup.


--------------------------------------------------------------------------------------------------------------------------------------------------------------

## How to Use 
1. File Placement: Make sure both svo_export.py and svo_conv.py are in the same directory.
2. Run the Application: Open your terminal, navigate to the project directory, and run the GUI script:

```bash
python svo_conv.py
```

**For Batch Conversion**
* Navigate to the **Batch Conversion** tab.
* Click **Browse** to select the **Input Directory** containing your SVO files.
* Click **Browse** to choose the **Output Directory** where the converted AVI files will be saved.
* Press **Start Conversion** to begin the process.

**3. For Trimming a Single Video**
* Navigate to the **Trim Settings** tab.
* Under "Select Files & Convert", click **Browse** to select a single **Input Video File** (.svo or .svo2).
* The video will load in the preview panel. Use the **timeline slider** or the **▶/⏸** button to find the segment you want to trim.
* Use the **✂ In** and **✂ Out** buttons to mark the start and end points of your clip. For more precision, you can type frame numbers directly into the **Start/End Frame** boxes and press `Enter`.
* Select an **Output Directory**.
* Click **Start Conversion** to export only the trimmed section.

--------------------------------------------------------------------------------------------------------------------------------------------------------------
## File Structure

- svo_export.py: The original command-line conversion script provided by Stereolabs. This script is called as a subprocess by the GUI for each file.
- svo_conv.py: The main application file that provides the graphical user interface and file converter logic. This is the file you run.
- README.md: This file explains the steps to follow for deploying the svo converter suit.

--------------------------------------------------------------------------------------------------------------------------------------------------------------

## License
- The batch converter GUI (batch_converter_gui.py) is released under the MIT License.

## Acknowledgments

This application was developed by **Samitha Thilakarathna**, a PhD student at DTU Aqua, Technical University of Denmark.

It is built upon the original SVO export script provided by Stereolabs in the ZED SDK and is designed to enhance its functionality for specific research and application needs.







