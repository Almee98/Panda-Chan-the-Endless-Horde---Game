from panda3d.core import Vec3, Vec2
from direct.actor.Actor import Actor
from panda3d.core import CollisionSphere, CollisionNode
from direct.showbase.ShowBase import ShowBase
from panda3d.core import CollisionRay, CollisionHandlerQueue
from panda3d.core import BitMask32

import math
from panda3d.core import Plane, Point3



FRICTION = 150.0

class GameObject(ShowBase):
    def __init__(self, pos, modelName, modelAnims, maxHealth, maxSpeed, colliderName):
        self.actor = Actor(modelName, modelAnims)
        self.actor.reparentTo(render)
        self.actor.setPos(pos)

        self.maxHealth = maxHealth
        self.health = maxHealth

        self.maxSpeed = maxSpeed

        self.velocity = Vec3(0, 0, 0)
        self.acceleration = 300.0

        self.walking = False

        colliderNode = CollisionNode(colliderName)
        colliderNode.addSolid(CollisionSphere(0, 0, 0, 0.3))
        self.collider = self.actor.attachNewNode(colliderNode)
        # See below for an explanation of this!
        self.collider.setPythonTag("owner", self)

    def update(self, dt):
        # If we're going faster than our maximum speed,
        # set the velocity-vector's length to that maximum
        speed = self.velocity.length()
        if speed > self.maxSpeed:
            self.velocity.normalize()
            self.velocity *= self.maxSpeed
            speed = self.maxSpeed

        # If we're walking, don't worry about friction.
        # Otherwise, use friction to slow us down.
        if not self.walking:
            frictionVal = FRICTION*dt
            if frictionVal > speed:
                self.velocity.set(0, 0, 0)
            else:
                frictionVec = -self.velocity
                frictionVec.normalize()
                frictionVec *= frictionVal

                self.velocity += frictionVec

        # Move the character, using our velocity and
        # the time since the last update.
        self.actor.setPos(self.actor.getPos() + self.velocity*dt)

    def alterHealth(self, dHealth):
        self.health += dHealth

        if self.health > self.maxHealth:
            self.health = self.maxHealth

    def cleanup(self):
        # Remove various nodes, and clear the Python-tag--see below!

        if self.collider is not None and not self.collider.isEmpty():
            self.collider.clearPythonTag("owner")
            base.cTrav.removeCollider(self.collider)
            base.pusher.removeCollider(self.collider)

        if self.actor is not None:
            self.actor.cleanup()
            self.actor.removeNode()
            self.actor = None

        self.collider = None

class Player(GameObject):
    def __init__(self):
        GameObject.__init__(self,
                            Vec3(0, 0, 0),
                            "models/panda_chan/act_p3d_chan",
                              {
                                  "stand" : "models/panda_chan/a_p3d_chan_idle",
                                  "walk" : "models/panda_chan/a_p3d_chan_run"
                              },
                            5,
                            10,
                            "player")

        # Panda-chan faces "backwards", so we just turn
        # the first sub-node of our Actor-NodePath
        # to have it face as we want.
        self.actor.getChild(0).setH(180)

        # Since our "Game" object is the "ShowBase" object,
        # we can access it via the global "base" variable.
        base.pusher.addCollider(self.collider, self.actor)
        base.cTrav.addCollider(self.collider, base.pusher)

        # adding a BitMask on the Player character with a value of 1 (For 'from' and 'into' masks).
        # Later, a BitMask of a different value is added to the ray (so the both don't collide)
        mask = BitMask32()
        mask.setBit(1)

        # This is the important one for preventing ray-collisions.
        self.collider.node().setIntoCollideMask(mask)

        mask = BitMask32()
        mask.setBit(1)

        self.collider.node().setFromCollideMask(mask)

        # A nice laser-beam model to show our laser
        self.beamModel = loader.loadModel("models/BambooLaser/bambooLaser")
        self.beamModel.reparentTo(self.actor)
        self.beamModel.setZ(1.5)
        # This prevents lights from affecting this particular node
        self.beamModel.setLightOff()
        # We don't start out firing the laser, so
        # we have it initially hidden.
        self.beamModel.hide()

        # death ray
        self.ray = CollisionRay(0, 0, 0, 0, 1, 0)

        rayNode = CollisionNode("playerRay")
        rayNode.addSolid(self.ray)

        self.rayNodePath = render.attachNewNode(rayNode)
        self.rayQueue = CollisionHandlerQueue()

        # We want this ray to collide with things, so
        # tell our traverser about it. However, note that,
        # unlike with "CollisionHandlerPusher", we don't
        # have to tell our "CollisionHandlerQueue" about it.
        base.cTrav.addCollider(self.rayNodePath, self.rayQueue)

        # adding a BitMask on the ray with a different value than the bit mask of Player.
        mask = BitMask32()

        # Note that we set a different bit here!
        # This means that the ray's mask and
        # the collider's mask don't match, and
        # so the ray won't collide with the
        # collider.
        mask.setBit(2)
        rayNode.setFromCollideMask(mask)

        mask = BitMask32()
        rayNode.setIntoCollideMask(mask)

        self.damagePerSecond = -5.0

        self.actor.loop("stand")

        # This stores the previous position of the mouse,
        # as a fall-back in case we don't get a good position
        # on a given update.
        self.lastMousePos = Vec2(0, 0)

        # Construct a plane facing upwards, and centred at (0, 0, 0)
        self.groundPlane = Plane(Vec3(0, 0, 1), Vec3(0, 0, 0))

        # This vector is used to calculate the orientation for
        # the character's model. Since the character faces along
        # the y-direction, we use the y-axis.
        self.yVector = Vec2(0, 1)
        

    def update(self, keys, dt):
        GameObject.update(self, dt)

        self.walking = False

        # If any movement keys are pressed, use the above time
        # to calculate how far to move the character, and apply that.
        if keys["up"]:
            self.walking = True
            self.velocity.addY(self.acceleration*dt)
        if keys["down"]:
            self.walking = True
            self.velocity.addY(-self.acceleration*dt)
        if keys["left"]:
            self.walking = True
            self.velocity.addX(-self.acceleration*dt)
        if keys["right"]:
            self.walking = True
            self.velocity.addX(self.acceleration*dt)

        # Run the appropriate animation for our current state.
        if self.walking:
            standControl = self.actor.getAnimControl("stand")
            if standControl.isPlaying():
                standControl.stop()

            walkControl = self.actor.getAnimControl("walk")
            if not walkControl.isPlaying():
                self.actor.loop("walk")
        else:
            standControl = self.actor.getAnimControl("stand")
            if not standControl.isPlaying():
                self.actor.stop("walk")
                self.actor.loop("stand")

        # If we're pressing the "shoot" button, check
        # whether the ray has hit anything, and if so,
        # examine the collision-entry for the first hit.
        # If the thing hit has an "owner" Python-tag, then
        # it's a GameObject, and should try to take damage--
        # with the exception if "TrapEnemies",
        # which are invulnerable.
        if keys["shoot"]:
            if self.rayQueue.getNumEntries() > 0:
                self.rayQueue.sortEntries()
                rayHit = self.rayQueue.getEntry(0)
                hitPos = rayHit.getSurfacePoint(render)

                hitNodePath = rayHit.getIntoNodePath()
                print(hitNodePath)
                if hitNodePath.hasPythonTag("owner"):
                    hitObject = hitNodePath.getPythonTag("owner")
                    if not isinstance(hitObject, TrapEnemy):
                        hitObject.alterHealth(self.damagePerSecond * dt)

                # Find out how long the beam is, and scale the
                # beam-model accordingly.
                beamLength = (hitPos - self.actor.getPos()).length()
                self.beamModel.setSy(beamLength)

                self.beamModel.show()
        else:
            # If we're not shooting, don't show the beam-model.
            self.beamModel.hide()

        # It's possible that we'll find that we
        # don't have the mouse--such as if the pointer
        # is outside of the game-window. In that case,
        # just use the previous position.
        mouseWatcher = base.mouseWatcherNode
        if mouseWatcher.hasMouse():
            mousePos = mouseWatcher.getMouse()
        else:
            mousePos = self.lastMousePos

        mousePos3D = Point3()
        nearPoint = Point3()
        farPoint = Point3()

        # Get the 3D line corresponding with the
        # 2D mouse-position.
        # The "extrude" method will store its result in the
        # "nearPoint" and "farPoint" objects.
        base.camLens.extrude(mousePos, nearPoint, farPoint)

        # Get the 3D point at which the 3D line
        # intersects our ground-plane.
        # Similarly to the above, the "intersectsLine" method
        # will store its result in the "mousePos3D" object.
        self.groundPlane.intersectsLine(mousePos3D,
                                        render.getRelativePoint(base.camera, nearPoint),
                                        render.getRelativePoint(base.camera, farPoint))

        # constructing a vector from the player’s position to the point, and take just the horizontal part of it,
        # since we’re not interested in any difference in z-position
        firingVector = Vec3(mousePos3D - self.actor.getPos())
        firingVector2D = firingVector.getXy()
        firingVector2D.normalize()
        firingVector.normalize()

        # find the angle that it makes with the positive y-axis –
        # this is the angle at which to face our player-character
        heading = self.yVector.signedAngleDeg(firingVector2D)

        self.actor.setH(heading)

        if firingVector.length() > 0.001:
            self.ray.setOrigin(self.actor.getPos())
            self.ray.setDirection(firingVector)

        self.lastMousePos = mousePos

    # Overriding the cleanup() method of the GameObject class
    def cleanup(self):
        base.cTrav.removeCollider(self.rayNodePath)

        GameObject.cleanup(self)

class Enemy(GameObject):
    def __init__(self, pos, modelName, modelAnims, maxHealth, maxSpeed, colliderName):
        GameObject.__init__(self, pos, modelName, modelAnims, maxHealth, maxSpeed, colliderName)

        # This is the number of points to award
        # if the enemy is killed.
        self.scoreValue = 1

    def update(self, player, dt):
        # In short, update as a GameObject, then
        # run whatever enemy-specific logic is to be done.
        # The use of a separate "runLogic" method
        # allows us to customise that specific logic
        # to the enemy, without re-writing the rest.

        GameObject.update(self, dt)

        self.runLogic(player, dt)

        # As with the player, play the appropriate animation.
        if self.walking:
            walkingControl = self.actor.getAnimControl("walk")
            if not walkingControl.isPlaying():
                self.actor.loop("walk")
        else:
            spawnControl = self.actor.getAnimControl("spawn")
            if spawnControl is None or not spawnControl.isPlaying():
                attackControl = self.actor.getAnimControl("attack")
                if attackControl is None or not attackControl.isPlaying():
                    standControl = self.actor.getAnimControl("stand")
                    if not standControl.isPlaying():
                        self.actor.loop("stand")


    def runLogic(self, player, dt):
        pass

class WalkingEnemy(Enemy):
    def __init__(self, pos):
        Enemy.__init__(self, pos,
                       "models/SimpleEnemy/simpleEnemy",
                       {
                        "stand" : "models/SimpleEnemy/simpleEnemy-stand",
                        "walk" : "models/SimpleEnemy/simpleEnemy-walk",
                        "attack" : "models/SimpleEnemy/simpleEnemy-attack",
                        "die" : "models/SimpleEnemy/simpleEnemy-die",
                        "spawn" : "models/SimpleEnemy/simpleEnemy-spawn"
                        },
                       3.0,
                       7.0,
                       "walkingEnemy")

        self.attackDistance = 0.75

        self.acceleration = 100.0

        # A reference vector, used to determine
        # which way to face the Actor.
        # Since the character faces along
        # the y-direction, we use the y-axis.
        self.yVector = Vec2(0, 1)

        # Note that this is the same bit as we used for the ray!
        mask = BitMask32()
        mask.setBit(2)

        self.collider.node().setIntoCollideMask(mask)

    def runLogic(self, player, dt):
        # In short: find the vector between
        # this enemy and the player.
        # If the enemy is far from the player,
        # use that vector to move towards the player.
        # Otherwise, just stop for now.
        # Finally, face the player.

        vectorToPlayer = player.actor.getPos() - self.actor.getPos()

        vectorToPlayer2D = vectorToPlayer.getXy()
        distanceToPlayer = vectorToPlayer2D.length()

        vectorToPlayer2D.normalize()

        heading = self.yVector.signedAngleDeg(vectorToPlayer2D)

        if distanceToPlayer > self.attackDistance*0.9:
            self.walking = True
            vectorToPlayer.setZ(0)
            vectorToPlayer.normalize()
            self.velocity += vectorToPlayer*self.acceleration*dt
        else:
            self.walking = False
            self.velocity.set(0, 0, 0)

        self.actor.setH(heading)

class TrapEnemy(Enemy):
    def __init__(self, pos):
        Enemy.__init__(self, pos,
                       "models/SlidingTrap/trap",
                       {
                           "stand": "models/SlidingTrap/trap-stand",
                           "walk": "models/SlidingTrap/trap-walk",
                       },
                       100.0,
                       10.0,
                       "trapEnemy")

        base.pusher.addCollider(self.collider, self.actor)
        base.cTrav.addCollider(self.collider, base.pusher)

        self.moveInX = False

        self.moveDirection = 0

        # This will allow us to prevent multiple
        # collisions with the player during movement
        self.ignorePlayer = False

        # Trap-enemies should hit both the player and "walking" enemies,
        # so we set _both_ bits here!
        mask = BitMask32()
        mask.setBit(2)
        mask.setBit(1)

        self.collider.node().setIntoCollideMask(mask)

        mask = BitMask32()
        mask.setBit(2)
        mask.setBit(1)

        self.collider.node().setFromCollideMask(mask)

    def runLogic(self, player, dt):
        if self.moveDirection != 0:
            self.walking = True
            if self.moveInX:
                self.velocity.addX(self.moveDirection * self.acceleration * dt)
            else:
                self.velocity.addY(self.moveDirection * self.acceleration * dt)
        else:
            self.walking = False
            diff = player.actor.getPos() - self.actor.getPos()
            if self.moveInX:
                detector = diff.y
                movement = diff.x
            else:
                detector = diff.x
                movement = diff.y

            if abs(detector) < 0.5:
                self.moveDirection = math.copysign(1, movement)

    def alterHealth(self, dHealth):
        pass