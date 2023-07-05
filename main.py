from direct.showbase.ShowBase import ShowBase
from direct.showbase.ShowBaseGlobal import globalClock
from direct.task.TaskManagerGlobal import taskMgr
from panda3d.core import WindowProperties

from direct.actor.Actor import Actor

from panda3d.core import AmbientLight

from panda3d.core import DirectionalLight

from panda3d.core import Vec4, Vec3

class Game(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)

        self.keyMap = {
            "up": False,
            "down": False,
            "left": False,
            "right": False,
            "shoot": False
        }

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

        # ambient lighting
        self.ambientLight = AmbientLight("ambient light")
        self.ambientLight.setColor(Vec4(0.2, 0.2, 0.2, 1))
        self.ambientLightNodePath = self.render.attachNewNode(self.ambientLight)
        self.render.setLight(self.ambientLightNodePath)

        mainLight = DirectionalLight("main light")
        self.mainLightNodePath = self.render.attachNewNode(mainLight)
        # Turn it around by 45 degrees, and tilt it down by 45 degrees
        self.mainLightNodePath.setHpr(45, -45, 0)
        self.render.setLight(self.mainLightNodePath)

        # setting the shading to give more depth to the scene
        self.render.setShaderAuto()

        # Method that accepts a task and returns a "looping task"....? I don't know how to frame it
        def update(task):
            # Get the amount of time since the last update
            dt = globalClock.getDt()

            # If any movement keys are pressed, use the above time
            # to calculate how far to move the character, and apply that.
            if self.keyMap["up"]:
                self.tempActor.setPos(self.tempActor.getPos() + Vec3(0, 5.0 * dt, 0))
            if self.keyMap["down"]:
                self.tempActor.setPos(self.tempActor.getPos() + Vec3(0, -5.0 * dt, 0))
            if self.keyMap["left"]:
                self.tempActor.setPos(self.tempActor.getPos() + Vec3(-5.0 * dt, 0, 0))
            if self.keyMap["right"]:
                self.tempActor.setPos(self.tempActor.getPos() + Vec3(5.0 * dt, 0, 0))
            if self.keyMap["shoot"]:
                print("Zap!")
            return task.cont

        # Adding task to task manager
        self.updateTask = taskMgr.add(update, "update")

        # updating the state of the game with key press and release
        def updateKeyMap(self, controlName, controlState):
            self.keyMap[controlName] = controlState
            print(controlName, "set to", controlState)


        self.accept("w", updateKeyMap, [self,"up", True])
        self.accept("w-up", updateKeyMap, [self,"up", False])
        self.accept("s", updateKeyMap, [self,"down", True])
        self.accept("s-up", updateKeyMap, [self,"down", False])
        self.accept("a", updateKeyMap, [self,"left", True])
        self.accept("a-up", updateKeyMap, [self,"left", False])
        self.accept("d", updateKeyMap, [self,"right", True])
        self.accept("d-up", updateKeyMap, [self,"right", False])
        self.accept("mouse1", updateKeyMap, [self,"shoot", True])
        self.accept("mouse1-up", updateKeyMap, [self,"shoot", False])

game = Game()
game.run()