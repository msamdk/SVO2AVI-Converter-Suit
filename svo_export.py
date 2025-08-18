########################################################################
#
# Copyright (c) 2022, STEREOLABS.
#
# All rights reserved.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
########################################################################

import sys
import pyzed.sl as sl
import numpy as np
import cv2
from pathlib import Path
import enum
import argparse
import os 

class AppType(enum.Enum):
    LEFT_AND_RIGHT = 1
    LEFT_AND_DEPTH = 2
    LEFT_AND_DEPTH_16 = 3


def progress_bar(percent_done, bar_length=50):
    #Display a progress bar
    done_length = int(bar_length * percent_done / 100)
    bar = '=' * done_length + '-' * (bar_length - done_length)
    sys.stdout.write('[%s] %i%s\r' % (bar, percent_done, '%'))
    sys.stdout.flush()


def main(opt):
    # Get input parameters
    svo_input_path = opt.input_svo_file
    output_dir = opt.output_path_dir
    avi_output_path = opt.output_avi_file 
    output_as_video = True     
    app_type = AppType.LEFT_AND_RIGHT
    if opt.mode == 1 or opt.mode == 3:
        app_type = AppType.LEFT_AND_DEPTH
    if opt.mode == 4:
        app_type = AppType.LEFT_AND_DEPTH_16
    
    # Check if exporting to AVI or SEQUENCE
    if opt.mode !=0 and opt.mode !=1:
        output_as_video = False

    if not output_as_video and not os.path.isdir(output_dir):
        sys.stdout.write("Input directory doesn't exist. Check permissions or create it.\n",
                         output_dir, "\n")
        exit()

    # Specify SVO path parameter
    init_params = sl.InitParameters()
    init_params.set_from_svo_file(svo_input_path)
    init_params.svo_real_time_mode = False  # Don't convert in realtime
    init_params.coordinate_units = sl.UNIT.MILLIMETER  # Use milliliter units (for depth measurements)

    # Create ZED objects
    zed = sl.Camera()

    # Open the SVO file specified as a parameter
    err = zed.open(init_params)
    if err != sl.ERROR_CODE.SUCCESS:
        sys.stdout.write(repr(err))
        zed.close()
        exit()
    
    # Get image size
    image_size = zed.get_camera_information().camera_configuration.resolution
    width = image_size.width
    height = image_size.height
    width_sbs = width * 2
    
    # Prepare side by side image container equivalent to CV_8UC4
    svo_image_sbs_rgba = np.zeros((height, width_sbs, 4), dtype=np.uint8)

    # Prepare single image containers
    left_image = sl.Mat()
    right_image = sl.Mat()
    depth_image = sl.Mat()

    video_writer = None
    if output_as_video:
        # Create video writer with MPEG-4 part 2 codec
        video_writer = cv2.VideoWriter(avi_output_path,
                                       cv2.VideoWriter_fourcc('M', '4', 'S', '2'),
                                       max(zed.get_camera_information().camera_configuration.fps, 25),
                                       (width_sbs, height))
        if not video_writer.isOpened():
            sys.stdout.write("OpenCV video writer cannot be opened. Please check the .avi file path and write "
                             "permissions.\n")
            zed.close()
            exit()
    
    rt_param = sl.RuntimeParameters()

    # --- MODIFIED: Start SVO conversion to AVI/SEQUENCE with trimming ---
    nb_frames = zed.get_svo_number_of_frames()
    
    # Validate start frame
    if not (0 <= opt.start_frame < nb_frames):
        print(f"\nError: --start_frame ({opt.start_frame}) is out of SVO bounds (0-{nb_frames-1}).")
        zed.close()
        exit()

    # Determine the end frame for the loop
    end_frame = min(opt.end_frame, nb_frames) if opt.end_frame != -1 else nb_frames
    
    # Validate end frame
    if end_frame <= opt.start_frame:
        print(f"\nError: --end_frame ({end_frame}) must be greater than --start_frame ({opt.start_frame}).")
        zed.close()
        exit()
    
    # Set the SVO position to the desired start frame
    zed.set_svo_position(opt.start_frame)
    
    sys.stdout.write(f"Converting SVO from frame {opt.start_frame} to {end_frame}... Use Ctrl-C to interrupt.\n")

    frames_to_process = end_frame - opt.start_frame
    frames_processed = 0

    while frames_processed < frames_to_process:
        err = zed.grab(rt_param)
        if err == sl.ERROR_CODE.SUCCESS:
            svo_position = zed.get_svo_position()

            # Retrieve SVO images
            zed.retrieve_image(left_image, sl.VIEW.LEFT)

            if app_type == AppType.LEFT_AND_RIGHT:
                zed.retrieve_image(right_image, sl.VIEW.RIGHT)
            elif app_type == AppType.LEFT_AND_DEPTH:
                zed.retrieve_image(right_image, sl.VIEW.DEPTH)
            elif app_type == AppType.LEFT_AND_DEPTH_16:
                zed.retrieve_measure(depth_image, sl.MEASURE.DEPTH)

            if output_as_video:
                # Copy the left image to the left side of SBS image
                svo_image_sbs_rgba[0:height, 0:width, :] = left_image.get_data()

                # Copy the right image to the right side of SBS image
                svo_image_sbs_rgba[0:, width:, :] = right_image.get_data()

                # Convert SVO image from RGBA to RGB
                ocv_image_sbs_rgb = cv2.cvtColor(svo_image_sbs_rgba, cv2.COLOR_RGBA2RGB)

                # Write the RGB image in the video
                video_writer.write(ocv_image_sbs_rgb)
            else:
                # Generate file names
                filename1 = output_dir +"/"+ ("left%s.png" % str(svo_position).zfill(6))
                filename2 = output_dir +"/"+ (("right%s.png" if app_type == AppType.LEFT_AND_RIGHT
                                             else "depth%s.png") % str(svo_position).zfill(6))
                # Save Left images
                cv2.imwrite(str(filename1), left_image.get_data())

                if app_type != AppType.LEFT_AND_DEPTH_16:
                    # Save right images
                    cv2.imwrite(str(filename2), right_image.get_data())
                else:
                    # Save depth images (convert to uint16)
                    cv2.imwrite(str(filename2), depth_image.get_data().astype(np.uint16))

            # Display progress based on the trimmed segment
            frames_processed += 1
            progress_bar(frames_processed / frames_to_process * 100, 30)

        elif err == sl.ERROR_CODE.END_OF_SVOFILE_REACHED:
            sys.stdout.write("\nSVO end has been reached unexpectedly. Exiting.\n")
            break
        else:
            sys.stdout.write(f"\nError grabbing frame: {err}. Exiting.\n")
            break

    if output_as_video:
        # Close the video writer
        video_writer.release()

    zed.close()
    print("\nConversion finished.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--mode', type = int, required=True, help= " Mode 0 is to export LEFT+RIGHT AVI. \n Mode 1 is to export LEFT+DEPTH_VIEW Avi. \n Mode 2 is to export LEFT+RIGHT image sequence. \n Mode 3 is to export LEFT+DEPTH_View image sequence. \n Mode 4 is to export LEFT+DEPTH_16BIT image sequence.")
    parser.add_argument('--input_svo_file', type=str, required=True, help='Path to the .svo file')
    parser.add_argument('--output_avi_file', type=str, help='Path to the output .avi file, if mode includes a .avi export', default = '')
    parser.add_argument('--output_path_dir', type = str, help = 'Path to a directory, where .png will be written, if mode includes image sequence export', default = '')
    
    # --- NEW: Added start and end frame arguments ---
    parser.add_argument('--start_frame', type=int, default=0, help='Frame to start the export from')
    parser.add_argument('--end_frame', type=int, default=-1, help='Frame to end the export at (-1 means end of file)')

    opt = parser.parse_args()
    if opt.mode > 4 or opt.mode < 0 :
        print("Mode shoud be between 0 and 4 included. \n Mode 0 is to export LEFT+RIGHT AVI. \n Mode 1 is to export LEFT+DEPTH_VIEW Avi. \n Mode 2 is to export LEFT+RIGHT image sequence. \n Mode 3 is to export LEFT+DEPTH_View image sequence. \n Mode 4 is to export LEFT+DEPTH_16BIT image sequence.")
        exit()
    if not opt.input_svo_file.endswith(".svo") and not opt.input_svo_file.endswith(".svo2"): 
        print("--input_svo_file parameter should be a .svo file but is not : ",opt.input_svo_file,"Exit program.")
        exit()
    if not os.path.isfile(opt.input_svo_file):
        print("--input_svo_file parameter should be an existing file but is not : ",opt.input_svo_file,"Exit program.")
        exit()
    if opt.mode < 2 and len(opt.output_avi_file)==0:
        print("In mode ",opt.mode,", output_avi_file parameter needs to be specified.")
        exit()
    if opt.mode < 2 and not opt.output_avi_file.endswith(".avi"):
        print("--output_avi_file parameter should be a .avi file but is not : ",opt.output_avi_file,"Exit program.")
        exit()
    if opt.mode >=2  and len(opt.output_path_dir)==0 :
        print("In mode ",opt.mode,", output_path_dir parameter needs to be specified.")
        exit()
    if opt.mode >=2 and not os.path.isdir(opt.output_path_dir):
        print("--output_path_dir parameter should be an existing folder but is not : ",opt.output_path_dir,"Exit program.")
        exit()
    main(opt)