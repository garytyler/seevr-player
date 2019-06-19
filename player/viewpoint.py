import logging

from vlc import VideoViewpoint

from . import comm, vlc_objects

log = logging.getLogger(__name__)


class ViewpointManager:
    """Handles setting viewpoint in VLC media player object."""

    def __init__(self, url):
        self.media_player = vlc_objects.media_player
        self.client = comm.RemoteInputClient(url=url)
        self.curr_yaw = self.curr_pitch = self.curr_roll = 0

        self.vp = VideoViewpoint()
        self.vp.field_of_view = 80

        self.media_player.newframe.connect(self.on_newframe)

    def on_newframe(self):
        new_motion_state = self.client.get_new_motion_state()
        if new_motion_state:
            self.set_new_viewpoint(*new_motion_state)

    def set_new_viewpoint(self, yaw, pitch, roll):
        self.vp.yaw, self.vp.pitch, self.vp.roll = -yaw, -pitch, -roll
        errorcode = self.media_player.video_update_viewpoint(
            p_viewpoint=self.vp, b_absolute=True
        )
        if errorcode != 0:
            log.error("Error setting viewpoint")

    def trigger_redraw(self):
        """Force a redraw of the video frame to correct the displayed aspect ratio
        of a 360 video.

        The redraw is triggered by a hack... setting a new viewpoint with an
        unobservable differential applied to the yaw value. This is probably only
        necessary because of the the implementation of viewpoints in vlclib 3.0, and
        will hopefully be unnecessary in 4.0.
        """
        differential = 0.01 ** 20  # (0.01 ** 22) is max effective differential
        self.set_new_viewpoint(
            self.curr_yaw + differential, self.curr_pitch, self.curr_roll
        )
