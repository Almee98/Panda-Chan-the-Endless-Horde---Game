from direct.showbase.ShowBase import ShowBase
from direct.showbase.ShowBaseGlobal import globalClock
from direct.task.TaskManagerGlobal import taskMgr
from panda3d.core import WindowProperties
from panda3d.core import AmbientLight
from panda3d.core import DirectionalLight
from panda3d.core import Vec4, Vec3
from panda3d.core import CollisionTraverser
from panda3d.core import CollisionHandlerPusher
from panda3d.core import CollisionSphere, CollisionNode
from panda3d.core import CollisionTube
from direct.actor.Actor import Actor
from GameObject import *


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
        self.tempActor = Actor("models/panda_chan/act_p3d_chan",
                               {"walk": "models/panda_chan/a_p3d_chan_run"})
        self.tempActor.reparentTo(self.render)
        # # Setting Panda Chan's position in front of the camera
        # self.tempActor.setPos(0, 7, 0)

        # Rotating the child node of Panda Chan (models aren’t usually loaded as single nodes,
        # but rather tend to have at least one child-node containing the models themselves) on z-axis using the setH function
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

        self.accept("w", self.updateKeyMap, ["up", True])
        self.accept("w-up", self.updateKeyMap, ["up", False])
        self.accept("s", self.updateKeyMap, ["down", True])
        self.accept("s-up", self.updateKeyMap, ["down", False])
        self.accept("a", self.updateKeyMap, ["left", True])
        self.accept("a-up", self.updateKeyMap, ["left", False])
        self.accept("d", self.updateKeyMap, ["right", True])
        self.accept("d-up", self.updateKeyMap, ["right", False])
        self.accept("mouse1", self.updateKeyMap, ["shoot", True])
        self.accept("mouse1-up", self.updateKeyMap, ["shoot", False])

        # Adding task to task manager
        self.updateTask = taskMgr.add(self.update, "update")

        self.cTrav = CollisionTraverser()
        # Panda should now automatically update that traverser!

        # prevents nominated solid objects from intersecting other solid objects.
        # We’ll store our reference to it, because we want to be able to add and remove objects as called for.
        self.pusher = CollisionHandlerPusher()

        # Creating a collision-object
        colliderNode = CollisionNode("player")
        # Add a collision-sphere centred on (0, 0, 0), and with a radius of 0.3
        colliderNode.addSolid(CollisionSphere(0, 0, 0, 0.3))
        collider = self.tempActor.attachNewNode(colliderNode)
        collider.show()

        # The pusher wants a collider, and a NodePath that
        # should be moved by that collider's collisions.
        # In this case, we want our player-Actor to be moved.
        base.pusher.addCollider(collider, self.tempActor)
        # The traverser wants a collider, and a handler
        # that responds to that collider's collisions
        base.cTrav.addCollider(collider, self.pusher)

        # Allows pusher's responses to be restricted to the horizontal (not 3D because we're playing on a flat surface)
        self.pusher.setHorizontal(True)

        # Tubes are defined by their start-points, end-points, and radius.
        # In this first case, the tube goes from (-8, 0, 0) to (8, 0, 0),
        # and has a radius of 0.2.
        wallSolid = CollisionTube(-8.0, 0, 0, 8.0, 0, 0, 0.2)
        wallNode = CollisionNode("wall")
        wallNode.addSolid(wallSolid)
        wall = self.render.attachNewNode(wallNode)
        wall.setY(8.0)

        wallSolid = CollisionTube(-8.0, 0, 0, 8.0, 0, 0, 0.2)
        wallNode = CollisionNode("wall")
        wallNode.addSolid(wallSolid)
        wall = self.render.attachNewNode(wallNode)
        wall.setY(-8.0)

        wallSolid = CollisionTube(0, -8.0, 0, 0, 8.0, 0, 0.2)
        wallNode = CollisionNode("wall")
        wallNode.addSolid(wallSolid)
        wall = self.render.attachNewNode(wallNode)
        wall.setX(8.0)

        wallSolid = CollisionTube(0, -8.0, 0, 0, 8.0, 0, 0.2)
        wallNode = CollisionNode("wall")
        wallNode.addSolid(wallSolid)
        wall = self.render.attachNewNode(wallNode)
        wall.setX(-8.0)

        self.player = Player()

        self.tempEnemy = WalkingEnemy(Vec3(5, 0, 0))

    # updating the state of the game with key press and release
    def updateKeyMap(self, controlName, controlState):
        self.keyMap[controlName] = controlState
        print(controlName, "set to", controlState)


    # Method that accepts a task and returns a "looping task"....? I don't know how to frame it
    def update(self, task):
        # Get the amount of time since the last update
        dt = globalClock.getDt()

        self.player.update(self.keyMap, dt)

        self.tempEnemy.update(self.player, dt)

        # # If any movement keys are pressed, use the above time
        # # to calculate how far to move the character, and apply that.
        # if self.keyMap["up"]:
        #     self.tempActor.setPos(self.tempActor.getPos() + Vec3(0, 5.0 * dt, 0))
        # if self.keyMap["down"]:
        #     self.tempActor.setPos(self.tempActor.getPos() + Vec3(0, -5.0 * dt, 0))
        # if self.keyMap["left"]:
        #     self.tempActor.setPos(self.tempActor.getPos() + Vec3(-5.0 * dt, 0, 0))
        # if self.keyMap["right"]:
        #     self.tempActor.setPos(self.tempActor.getPos() + Vec3(5.0 * dt, 0, 0))
        # if self.keyMap["shoot"]:
        #     print("Zap!")

        return task.cont


game = Game()
game.run()
