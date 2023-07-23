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

        self.disableMouse()

        properties = WindowProperties()
        properties.setSize(950, 600)
        self.win.requestProperties(properties)

        mainLight = DirectionalLight("main light")
        self.mainLightNodePath = self.render.attachNewNode(mainLight)
        # Turn it around by 45 degrees, and tilt it down by 45 degrees
        self.mainLightNodePath.setHpr(45, -45, 0)
        self.render.setLight(self.mainLightNodePath)

        # ambient lighting
        self.ambientLight = AmbientLight("ambient light")
        self.ambientLight.setColor(Vec4(0.2, 0.2, 0.2, 1))
        self.ambientLightNodePath = self.render.attachNewNode(self.ambientLight)
        self.render.setLight(self.ambientLightNodePath)

        # setting the shading to give more depth to the scene
        self.render.setShaderAuto()

        # Setting up the environment using the loadModel method
        self.environment = self.loader.loadModel("models/Environment/environment")
        self.environment.reparentTo(self.render)

        self.camera.setPos(0, 0, 32)
        self.camera.setP(-90)

        self.keyMap = {
            "up": False,
            "down": False,
            "left": False,
            "right": False,
            "shoot": False
        }

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

        # prevents nominated solid objects from intersecting other solid objects.
        # We’ll store our reference to it, because we want to be able to add and remove objects as called for.
        self.pusher = CollisionHandlerPusher()
        self.cTrav = CollisionTraverser()
        # Panda should now automatically update that traverser!

        # Allows pusher's responses to be restricted to the horizontal
        # (not 3D because we're playing on a flat surface)
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

        # Adding task to task manager
        self.updateTask = taskMgr.add(self.update, "update")

        self.player = Player()

        self.tempEnemy = WalkingEnemy(Vec3(5, 0, 0))

        self.tempTrap = TrapEnemy(Vec3(-2, 7, 0))

        # We ask pusher to "in"-pattern of the form “%fn-into-%in”.
        # "%fn" will be replaced with "from" collision object and "%in" will be replaced with "into" collision object.
        self.pusher.add_in_pattern("%fn-into-%in")

        # receiving those events (works similar to key-events)
        self.accept("trapEnemy-into-wall", self.stopTrap)
        self.accept("trapEnemy-into-trapEnemy", self.stopTrap)
        self.accept("trapEnemy-into-player", self.trapHitsSomething)
        self.accept("trapEnemy-into-walkingEnemy", self.trapHitsSomething)

    # updating the state of the game with key press and release
    def updateKeyMap(self, controlName, controlState):
        self.keyMap[controlName] = controlState
        print(controlName, "set to", controlState)

    def stopTrap(self, entry):
        collider = entry.getFromNodePath()
        if collider.hasPythonTag("owner"):
            trap = collider.getPythonTag("owner")
            trap.moveDirection = 0
            trap.ignorePlayer = False

    def trapHitsSomething(self, entry):
        collider = entry.getFromNodePath()
        if collider.hasPythonTag("owner"):
            trap = collider.getPythonTag("owner")

            # We don't want stationary traps to do damage,
            # so ignore the collision if the "moveDirection" is 0
            if trap.moveDirection == 0:
                return

            collider = entry.getIntoNodePath()
            if collider.hasPythonTag("owner"):
                obj = collider.getPythonTag("owner")
                if isinstance(obj, Player):
                    if not trap.ignorePlayer:
                        obj.alterHealth(-1)
                        trap.ignorePlayer = True
                else:
                    obj.alterHealth(-10)


    # Method that accepts a task and returns a "looping task"....? I don't know how to frame it
    def update(self, task):
        # Get the amount of time since the last update
        dt = globalClock.getDt()

        self.player.update(self.keyMap, dt)

        self.tempEnemy.update(self.player, dt)

        self.tempTrap.update(self.player, dt)

        return task.cont


game = Game()
game.run()
