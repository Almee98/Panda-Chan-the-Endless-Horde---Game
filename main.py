from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties

from direct.actor.Actor import Actor


class Game(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        properties = WindowProperties()
        properties.setSize(950, 600)
        self.win.requestProperties(properties)

        self.disableMouse()

        # Setting up the environment using the loadModel method
        self.environment = self.loader.loadModel("models/Environment/environment")
        self.environment.reparentTo(self.render)

        # Creating a Panda Chan actor
        self.tempActor = Actor("models/p3d_samples/models/act_p3d_chan", {"walk": "models/p3d_samples/models/a_p3d_chan_run"})
        self.tempActor.reparentTo(self.render)
        # # Setting Panda Chan's position in front of the camera
        # self.tempActor.setPos(0, 7, 0)

        # Rotating the child node of Panda Chan (models aren’t usually loaded as single nodes, but rather tend to have at least one child-node containing the models themselves) on z-axis using the setH function
        self.tempActor.getChild(0).setH(180)

        # Making Panda Chan walk
        self.tempActor.loop("walk")

        # Move the camera to a position high above the screen
        # --that is, offset it along the z-axis.
        self.camera.setPos(0, 0, 32)
        # Tilt the camera down by setting its pitch.
        self.camera.setP(-90)

game = Game()
game.run()