## SVO to AVI batch Converter app for ZED camera systems

This tool provides a simple and efficient workflow for processing multiple .svo or .svo2 files, saving you from the tedious task of converting them one by one through the command line.

<img src="images/app.png" alt="Alt text" width="600">

## Features
- Batch Conversion: Process an entire folder of .svo and .svo2 files in one go.

- Modern UI: A sleek, full-black user interface with custom-drawn rounded frames.
- Real-time Progress:
   - An overall progress bar tracks the entire batch of files.
   - A per-file progress bar shows the status of the current conversion.
- Dynamic Progress Bar: The current file's progress bar animates with a color gradient from red to blue for a clear visual indicator.
- Full Control: A Start/Stop button allows you to begin and interrupt the conversion process at any time.
- Clean Log Output: A dedicated log panel shows important status messages and errors without being cluttered by raw progress data.

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
-----------------------------------------------------------------------------------------------------------------------------------------------------------

## Setup and Installation

Follow these steps to get the project running on your local machine.

1. Clone the Repository
First, clone this repository to your computer using Git:






