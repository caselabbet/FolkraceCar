import pyrealsense2 as rs
import numpy as np
from numpy.linalg import svd
import time
import threading as mt

class PathPlanner:
    def __init__(self, pipeline):
        """
        Gradient decent solving path planner ## todo Evaluate against other methods of path planning
        :param Car: Object to give driving vector
        """
        self.pipe = pipeline
        self.running = False
        self.decimate_val  = 0.1 # todo get good value
        # Processing blocks
        self.pc = rs.pointcloud()
        self.decimate = rs.decimation_filter()
        #self.decimate.set_option(rs.option.filter_magnitude, 2 ** self.decimate_val)
        # self.colorizer = rs.colorizer()
        self.w = 0
        self.h = 0
        self.ground_plane = self.get_ground_plane()
        try:
            # Get stream profile and camera intrinsics
            profile = self.pipe.get_active_profile()
            depth_profile = rs.video_stream_profile(profile.get_stream(rs.stream.depth))
            depth_intrinsics = depth_profile.get_intrinsics()
            self.w, self.h = depth_intrinsics.width, depth_intrinsics.height
        except RuntimeError as err:
            print(err)

    def start(self):
        self.running = True
        path_plan = mt.Thread(target=self.path_plan, name='path_planner')
        try:
            path_plan.start()
        except Exception as err:
            print("Error: unable to start path_planner thread, err: {}".format(err))
        return path_plan

    def end(self):
        self.running = False

    def get_ground_plane(self):
        """
        Estimate ground plain using Least square
        todo evaluate usage of RANSAC
        :return: groudn plain origin and rotation
        """

        pos, normal = self.planeFit()

        rot = np.eye(3)  # todo calculate rotation matrix

        return pos, rot, normal

    def planeFit(self):
        """
        Original code from: https://stackoverflow.com/a/18968498

        p, n = planeFit(points)

        Given an array, points, of shape (d,...)
        representing points in d-dimensional space,
        fit an d-dimensional plane to the points.

        :return: a point, p, on the plane (the point-cloud centroid),
        and the normal, n.
        """
        points = self.process_cloud()

        points = np.reshape(points, (np.shape(points)[0], -1))  # Collapse trialing dimensions
        assert points.shape[0] <= points.shape[1], "There are only {} points in {} dimensions.".format(points.shape[1],
                                                                                                       points.shape[0])
        ctr = points.mean(axis=1)
        x = points - ctr[:, np.newaxis]
        M = np.dot(x, x.T)  # Could also use np.cov(x) here.
        return ctr, svd(M)[0][:, -1]

    def process_cloud(self):
        try:
            # Wait for a coherent pair of frames: depth and color
            frames = self.pipe.wait_for_frames()

            depth_frame = frames.get_depth_frame()

            depth_frame = self.decimate.process(depth_frame)

            # Grab new intrinsics (may be changed by decimation)
            depth_intrinsics = rs.video_stream_profile(
                depth_frame.profile).get_intrinsics()
            w, h = depth_intrinsics.width, depth_intrinsics.height

            depth_image = np.asanyarray(depth_frame.get_data())

            #depth_colormap = np.asanyarray(
            #    colorizer.colorize(depth_frame).get_data())

            #if state.color:
            #    mapped_frame, color_source = color_frame, color_image
            #else:
            #    mapped_frame, color_source = depth_frame, depth_colormap

            points = self.pc.calculate(depth_frame)
            #self.pc.map_to(mapped_frame)

            # Pointcloud data to arrays
            v, t = points.get_vertices(), points.get_texture_coordinates()
            verts = np.asanyarray(v).view(np.float32).reshape(-1, 3)  # xyz
            #texcoords = np.asanyarray(t).view(np.float32).reshape(-1, 2)  # uv
        except:
            verts = np.zeros((3, 3))

        return np.transpose(verts)

    def path_plan(self):
        while self.running:
            self.ground_plane = self.get_ground_plane()
            time.sleep(0.1)

        print('Path planner ended')