import argparse
import logging
import time

import cv2
import numpy as np
# import uinput
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='tf-pose-estimation realtime webcam')
    parser.add_argument('--camera', type=int, default=0)

    parser.add_argument('--resize', type=str, default='0x0',
                        help='if provided, resize images before they are processed. default=0x0, Recommends : 432x368 or 656x368 or 1312x736 ')
    parser.add_argument('--resize-out-ratio', type=float, default=4.0,
                        help='if provided, resize heatmaps before they are post-processed. default=1.0')

    parser.add_argument('--model', type=str, default='mobilenet_thin',
                        help='cmu / mobilenet_thin / mobilenet_v2_large / mobilenet_v2_small')
    parser.add_argument('--show-process', type=bool, default=False,
                        help='for debug purpose, if enabled, speed for inference is dropped.')

    parser.add_argument('--tensorrt', type=str, default="False",
                        help='for tensorrt process.')
    args = parser.parse_args()

    logger.debug('initialization %s : %s' % (args.model, get_graph_path(args.model)))
    w, h = model_wh(args.resize)
    if w > 0 and h > 0:
        e = TfPoseEstimator(get_graph_path(args.model), target_size=(w, h), trt_bool=str2bool(args.tensorrt))
    else:
        e = TfPoseEstimator(get_graph_path(args.model), target_size=(432, 368), trt_bool=str2bool(args.tensorrt))
    logger.debug('cam read+')
    cam = cv2.VideoCapture(args.camera)
    ret_val, image = cam.read()
    logger.info('cam image=%dx%d' % (image.shape[1], image.shape[0]))

    screen_width, screen_height = pyautogui.size()
    xq = deque(maxlen=4)
    yq = deque(maxlen=4)

    while True:
        ret_val, image = cam.read()
        image = cv2.flip(image, 1)  # mirror image.

        # logger.debug('image process+')
        humans = e.inference(image, resize_to_default=(w > 0 and h > 0), upsample_size=args.resize_out_ratio)

        # logger.debug('postprocess+', humans)
        image = TfPoseEstimator.draw_humans(image, humans, imgcopy=False)

        # logger.debug('show+')
        cv2.putText(image,
                    "FPS: %f" % (1.0 / (time.time() - fps_time)),
                    (10, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 255, 0), 2)
        cv2.imshow('tf-pose-estimation result', image)
        fps_time = time.time()
        if cv2.waitKey(1) == 27:
            break

        if len(humans) > 0:
            leftWrist = humans[0].body_parts.get(4)  # due to mirror input.
            leftElbow = humans[0].body_parts.get(3)
            leftShoulder = humans[0].body_parts.get(2)

        if leftWrist is not None and leftShoulder is not None:
            # left shoulder is the centre of screen, so, wrist movement relative to that for comfortable movement.
            xq.append(clamp(int((leftWrist.x - leftShoulder.x) * 8 * screen_width + screen_width), 0, screen_width))
            yq.append(
                clamp(int((leftWrist.y - leftShoulder.y) * 2 * screen_height + screen_height / 2), 0, screen_height))
            logger.debug('que:', xq, yq)

            pyautogui.moveTo(int(np.mean(list(xq))), int(np.mean(list(yq))))
            # pyautogui.moveTo(int((leftWrist.x - leftShoulder.x) * 8 * screen_width + screen_width),
            #                  int((leftWrist.y - leftShoulder.y) * 2 * screen_height + screen_height / 2))

            # pyautogui.moveTo(int(leftWrist.x * screen_width), int(leftWrist.y * screen_height))

        # logger.debug('finished+')

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
