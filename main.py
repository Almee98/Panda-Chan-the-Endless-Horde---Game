import panda3d
import random
from GameObject import *
from panda3d.core import loadPrcFile
# Load configuration settings from config.py
loadPrcFile("Panda3D2/config.prc")

from direct.showbase.ShowBase import ShowBase
from direct.showbase.ShowBaseGlobal import globalClock
from direct.task.TaskManagerGlobal import taskMgr
from panda3d.core import WindowProperties, BoundingSphere
from panda3d.core import AmbientLight, DirectionalLight
from panda3d.core import Vec4, Vec3
from panda3d.core import CollisionTraverser, CollisionHandlerPusher, CollisionTube
from panda3d.core import CollisionNode, CollisionSphere


class Game(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)

        self.disableMouse()

        properties = WindowProperties()
        properties.setSize(950, 600)
        self.win.requestProperties(properties)

        self.exitFunc = self.cleanup

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

        # setting up the music
        music = self.loader.loadMusic("music/Defending-the-Princess-Haunted_v002.ogg")
        music.setLoop(True)
        music.setVolume(0.075)
        music.play()

        # setting up the sound effect for enemy spawning
        self.enemySpawnSound = self.loader.loadSfx("music/enemySpawn.ogg")

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

        # We ask pusher to "in"-pattern of the form “%fn-into-%in”.
        # "%fn" will be replaced with "from" collision object and "%in" will be replaced with "into" collision object.
        self.pusher.add_in_pattern("%fn-into-%in")

        # receiving those events (works similar to key-events)
        self.accept("trapEnemy-into-wall", self.stopTrap)
        self.accept("trapEnemy-into-trapEnemy", self.stopTrap)
        self.accept("trapEnemy-into-player", self.trapHitsSomething)
        self.accept("trapEnemy-into-walkingEnemy", self.trapHitsSomething)


        # Tubes are defined by their start-points, end-points, and radius.
        # In this first case, the tube goes from (-8, 0, 0) to (8, 0, 0),
        # and has a radius of 0.2.
        wallSolid = CollisionTube(-8.0, 0, 0, 8.0, 0, 0, 0.2)
        wallNode = panda3d.core.CollisionNode("wall")
        wallNode.addSolid(wallSolid)
        wall = self.render.attachNewNode(wallNode)
        wall.setY(8.0)

        wallSolid = CollisionTube(-8.0, 0, 0, 8.0, 0, 0, 0.2)
        wallNode = panda3d.core.CollisionNode("wall")
        wallNode.addSolid(wallSolid)
        wall = self.render.attachNewNode(wallNode)
        wall.setY(-8.0)

        wallSolid = CollisionTube(0, -8.0, 0, 0, 8.0, 0, 0.2)
        wallNode = panda3d.core.CollisionNode("wall")
        wallNode.addSolid(wallSolid)
        wall = self.render.attachNewNode(wallNode)
        wall.setX(8.0)

        wallSolid = CollisionTube(0, -8.0, 0, 0, 8.0, 0, 0.2)
        wallNode = panda3d.core.CollisionNode("wall")
        wallNode.addSolid(wallSolid)
        wall = self.render.attachNewNode(wallNode)
        wall.setX(-8.0)

        # Adding task to task manager
        self.updateTask = taskMgr.add(self.update, "update")

        # We start with no Player character
        self.player = None

        # Our enemies, traps, and "dead enemies"
        self.enemies = []
        self.trapEnemies = []

        self.deadEnemies = []

        # Setting up some spawn points
        # These spawn points are positions spaced evenly along the walls,
        # and when spawning an enemy we'll randomly choose one as the location of the enemy.
        self.spawnPoints = []
        numPointsPerWall = 5
        for i in range(numPointsPerWall):
            coord = 7.0 / numPointsPerWall + 0.5
            self.spawnPoints.append(Vec3(-7.0, coord, 0))
            self.spawnPoints.append(Vec3(7.0, coord, 0))
            self.spawnPoints.append(Vec3(coord, -7.0, 0))
            self.spawnPoints.append(Vec3(coord, 7.0, 0))

        # Values to control when to spawn enemies, and
        # how many enemies there may be at once
        self.initialSpawnInterval = 1.0
        self.minimumSpawnInterval = 0.2
        self.spawnInterval = self.initialSpawnInterval
        self.spawnTimer = self.spawnInterval
        self.maxEnemies = 2
        self.maximumMaxEnemies = 20

        self.numTrapsPerSide = 2

        self.difficultyInterval = 5.0
        self.difficultyTimer = self.difficultyInterval

        # Start the game!
        self.startGame()

    def startGame(self):
        self.cleanup()

        self.player = Player()

        self.maxEnemies = 2
        self.spawnInterval = self.initialSpawnInterval

        self.difficultyTimer = self.difficultyInterval

        sideTrapSlots = [
            [],
            [],
            [],
            []
        ]
        trapSlotDistance = 0.4
        slotPos = -8 + trapSlotDistance
        while slotPos < 8:
            if abs(slotPos) > 1.0:
                sideTrapSlots[0].append(slotPos)
                sideTrapSlots[1].append(slotPos)
                sideTrapSlots[2].append(slotPos)
                sideTrapSlots[3].append(slotPos)
            slotPos += trapSlotDistance

        # Create one trap on each side, repeating
        # for however many traps there should be
        # per side.
        for i in range(self.numTrapsPerSide):
            # Note that we "pop" the chosen location,
            # so that it won't be chosen again.
            slot = sideTrapSlots[0].pop(random.randint(0, len(sideTrapSlots[0]) - 1))
            trap = TrapEnemy(Vec3(slot, 7.0, 0))
            self.trapEnemies.append(trap)

            slot = sideTrapSlots[1].pop(random.randint(0, len(sideTrapSlots[1]) - 1))
            trap = TrapEnemy(Vec3(slot, -7.0, 0))
            self.trapEnemies.append(trap)

            slot = sideTrapSlots[2].pop(random.randint(0, len(sideTrapSlots[2]) - 1))
            trap = TrapEnemy(Vec3(7.0, slot, 0))
            trap.moveInX = True
            self.trapEnemies.append(trap)

            slot = sideTrapSlots[3].pop(random.randint(0, len(sideTrapSlots[3]) - 1))
            trap = TrapEnemy(Vec3(-7.0, slot, 0))
            trap.moveInX = True
            self.trapEnemies.append(trap)

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
            trap.movementSound.stop()
            trap.stopSound.play()

    def trapHitsSomething(self, entry):
        collider = entry.getFromNodePath()
        if collider.hasPythonTag("owner"):
            trap = collider.getPythonTag("owner")
            # playing the impact sound
            trap.impactSound.play()

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

        # If the player is dead, or we're not
        # playing yet, ignore this logic.
        if self.player is not None:
            if self.player.health > 0:
                self.player.update(self.keyMap, dt)

                # Wait to spawn an enemy...
                self.spawnTimer -= dt
                if self.spawnTimer <= 0:
                    # Spawn one!
                    self.spawnTimer = self.spawnInterval
                    self.spawnEnemy()

                # Update all enemies and traps
                [enemy.update(self.player, dt) for enemy in self.enemies]
                [trap.update(self.player, dt) for trap in self.trapEnemies]

                # Find the enemies that have just
                # died, if any
                newlyDeadEnemies = [enemy for enemy in self.enemies if enemy.health <= 0]
                # And re-build the enemy-list to exclude
                # those that have just died.
                self.enemies = [enemy for enemy in self.enemies if enemy.health > 0]

                # Newly-dead enemies should have no collider,
                # and should play their "die" animation.
                # In addition, increase the player's score.
                for enemy in newlyDeadEnemies:
                    enemy.collider.removeNode()
                    enemy.actor.play("die")
                    self.player.score += enemy.scoreValue
                if len(newlyDeadEnemies) > 0:
                    self.player.updateScore()

                self.deadEnemies += newlyDeadEnemies

                # Check our "dead enemies" to see
                # whether they're still animating their
                # "die" animation. In not, clean them up,
                # and drop them from the "dead enemies" list.
                enemiesAnimatingDeaths = []
                for enemy in self.deadEnemies:
                    deathAnimControl = enemy.actor.getAnimControl("die")
                    if deathAnimControl is None or not deathAnimControl.isPlaying():
                        enemy.cleanup()
                    else:
                        enemiesAnimatingDeaths.append(enemy)
                self.deadEnemies = enemiesAnimatingDeaths

                # Make the game more difficult over time!
                self.difficultyTimer -= dt
                if self.difficultyTimer <= 0:
                    self.difficultyTimer = self.difficultyInterval
                    if self.maxEnemies < self.maximumMaxEnemies:
                        self.maxEnemies += 1
                    if self.spawnInterval > self.minimumSpawnInterval:
                        self.spawnInterval -= 0.1


        return task.cont

    def spawnEnemy(self):
        if len(self.enemies) < self.maxEnemies:
            spawnPoint = random.choice(self.spawnPoints)

            newEnemy = WalkingEnemy(spawnPoint)

            self.enemySpawnSound.play()

            self.enemies.append(newEnemy)

    def cleanup(self):
        # Call our various cleanup methods,
        # empty the various lists,
        # and make the player "None" again.

        for enemy in self.enemies:
            enemy.cleanup()
        self.enemies = []

        for enemy in self.deadEnemies:
            enemy.cleanup()
        self.deadEnemies = []

        for trap in self.trapEnemies:
            trap.cleanup()
        self.trapEnemies = []

        if self.player is not None:
            self.player.cleanup()
            self.player = None

    def quit(self):
        # Clean up, then exit

        self.cleanup()

        base.userExit()
game = Game()
game.run()
