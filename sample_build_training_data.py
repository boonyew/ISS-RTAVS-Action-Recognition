import argparse
import logging
import time

import cv2
import numpy as np
import pandas as pd
import os

import pyautogui
from collections import deque

from tf_pose.estimator import TfPoseEstimator
from tf_pose.networks import get_graph_path, model_wh

logger = logging.getLogger('TfPoseEstimator-WebCam')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

fps_time = 0


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


def clamp(n, minn, maxn):
    return max(min(maxn, n), minn)


def extract_action(humans_prediction):
    frame_data = []
    if len(humans_prediction) > 0:

        neck = humans_prediction[0].body_parts.get(1)
        # ideal neck, 0.5, 0.3 <=y
        if neck is not None:
            x_off = neck.x - 0.5
            y_off = neck.y - 0.3
        else:
            return frame_data

        for i in range(0, 18 + 1):
            # print('i:', i)
            part = humans_prediction[0].body_parts.get(i)
            if part is not None:
                frame_data.append(part.x-x_off)
                frame_data.append(part.y-y_off)
                frame_data.append(part.score)
                # if (i == 1):
                    # print('neck:', part.x, ':', part.y)
                    # ideal neck, 0.5, 0.3 <=y
            else:
                frame_data.append(0)
                frame_data.append(0)
                frame_data.append(0)

    return frame_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='tf-pose-estimation realtime webcam')
    parser.add_argument('--camera', type=int, default=0)

    # 656x368, 0x0
    parser.add_argument('--resize', type=str, default='0x0',
                        help='if provided, resize images before they are processed. default=0x0, Recommends : 432x368 or 656x368 or 1312x736 ')
    parser.add_argument('--resize-out-ratio', type=float, default=4.0,
                        help='if provided, resize heatmaps before they are post-processed. default=1.0')

    parser.add_argument('--model', type=str, default='mobilenet_v2_large',
                        help='cmu / mobilenet_thin / mobilenet_v2_large / mobilenet_v2_small')
    parser.add_argument('--show-process', type=bool, default=False,
                        help='for debug purpose, if enabled, speed for inference is dropped.')

    parser.add_argument('--tensorrt', type=str, default="False",
                        help='for tensorrt process.')
    args = parser.parse_args()
    files = os.listdir('./data/training/')
    logger.debug('initialization %s : %s' % (args.model, get_graph_path(args.model)))
    w, h = model_wh(args.resize)
    if w > 0 and h > 0:
        e = TfPoseEstimator(get_graph_path(args.model), target_size=(w, h), trt_bool=str2bool(args.tensorrt))
    else:
        e = TfPoseEstimator(get_graph_path(args.model), target_size=(432, 368), trt_bool=str2bool(args.tensorrt))
    logger.debug('cam read+')
    # cam = cv2.VideoCapture(args.camera)
    for file in files:
        filename = './data/training/' + file
        cam = cv2.VideoCapture(filename)
        ret_val, image = cam.read()
        logger.info('cam image=%dx%d' % (image.shape[1], image.shape[0]))

        screen_width, screen_height = pyautogui.size()
        # xq = deque(maxlen=4)
        # yq = deque(maxlen=4)

        action_df = pd.DataFrame()
        while True:
            ret_val, image = cam.read()
            if not ret_val:
                break

            image = cv2.flip(image, 1)  # mirror image.

            # logger.debug('image process+')
            humans = e.inference(image, resize_to_default=(w > 0 and h > 0), upsample_size=args.resize_out_ratio)

            # logger.debug('postprocess+', humans)
            image = TfPoseEstimator.draw_humans(image, humans, imgcopy=False)

            # logger.debug('show+')
            cv2.putText(image,
                        "%s FPS: %f" % (file, 1.0 / (time.time() - fps_time)),
                        (10, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (0, 255, 0), 2)
            cv2.imshow('tf-pose-estimation result', image)
            fps_time = time.time()
            if cv2.waitKey(1) == 27:
                break

            frame_data = extract_action(humans)

            #            print('frame:', len(frame_data))
            if len(frame_data) > 0:
                action_df = action_df.append([frame_data])

            # logger.debug('finished+')

        #        print('frame:', frame_data)
        datafile = filename.replace('training', 'training-csv')

        action_df.to_csv(datafile + '.csv', index=None, header=None)

    cv2.destroyAllWindows()

'''
tf_pose.common import CocoPart
    Nose = 0
    Neck = 1
    RShoulder = 2
    RElbow = 3
    RWrist = 4
    LShoulder = 5
    LElbow = 6
    LWrist = 7
    RHip = 8
    RKnee = 9
    RAnkle = 10
    LHip = 11
    LKnee = 12
    LAnkle = 13
    REye = 14
    LEye = 15
    REar = 16
    LEar = 17
    Background = 18
'''
