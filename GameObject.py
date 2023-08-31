from panda3d.core import Vec4, Vec3, Vec2
from direct.actor.Actor import Actor
from panda3d.core import CollisionSphere, CollisionNode
from direct.showbase.ShowBase import ShowBase
from panda3d.core import CollisionRay, CollisionHandlerQueue
from panda3d.core import BitMask32

import math
import random
from panda3d.core import Plane, Point3
from panda3d.core import CollisionSegment
from direct.gui.OnscreenText import OnscreenText
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import TextNode
from panda3d.core import PointLight 
from panda3d.core import AudioSound


FRICTION = 150.0

class GameObject(ShowBase):
    def __init__(self, pos, modelName, modelAnims, maxHealth, maxSpeed, colliderName):
        self.actor = Actor(modelName, modelAnims)
        self.actor.reparentTo(render)
        self.actor.setPos(pos)

        # initializing the sound that will play when an enemy dies as None
        # This is updated in the alterHealth method
        self.deathSound = None

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
        previousHealth = self.health
        self.health += dHealth

        if self.health > self.maxHealth:
            self.health = self.maxHealth

        if previousHealth > 0 and self.health <= 0 and self.deathSound is not None:
            self.deathSound.play()

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

        self.laserSoundNoHit = loader.loadSfx("music/laserNoHit.ogg")
        self.laserSoundNoHit.setLoop(True)
        self.laserSoundHit = loader.loadSfx("music/laserHit.ogg")
        self.laserSoundHit.setLoop(True)

        self.hurtSound = loader.loadSfx("music/FemaleDmgNoise.ogg")

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

        # Displaying Player's health.
        # Player's health will be displayed as a row of heart icons.
        self.score = 0

        self.scoreUI = OnscreenText(text="0",
                                    pos=(-1.3, 0.825),
                                    mayChange=True,
                                    align=TextNode.ALeft)

        self.healthIcons = []
        for i in range(self.maxHealth):
            icon = OnscreenImage(image="models/UI/health.png",
                                 pos=(-1.275 + i * 0.075, 0, 0.95),
                                 scale=0.04)
            # Since our icons have transparent regions,
            # we'll activate transparency.
            icon.setTransparency(True)
            self.healthIcons.append(icon)

            # A hit-flash will appear when the walking enemy will get hit with the laser.
            self.beamHitModel = loader.loadModel("models/BambooLaser/bambooLaserHit")
            self.beamHitModel.reparentTo(render)
            self.beamHitModel.setZ(1.5)
            self.beamHitModel.setLightOff()
            self.beamHitModel.hide()

            self.beamHitPulseRate = 0.15
            self.beamHitTimer = 0

            self.beamHitLight = PointLight("beamHitLight")
            self.beamHitLight.setColor(Vec4(0.1, 1.0, 0.2, 1))
            # These "attenuation" values govern how the light
            # fades with distance. They are, respectively,
            # the constant, linear, and quadratic coefficients
            # of the light's falloff equation.
            # I experimented until I found values that
            # looked nice.
            self.beamHitLight.setAttenuation((1.0, 0.1, 0.5))
            self.beamHitLightNodePath = render.attachNewNode(self.beamHitLight)
            # Note that we haven't yet applied the light to
            # a NodePath, and so it won't yet illuminate
            # anything.

            # displaying damage taken by the Player
            self.damageTakenModel = loader.loadModel("models/BambooLaser/playerHit")
            self.damageTakenModel.setLightOff()
            self.damageTakenModel.setZ(1.0)
            self.damageTakenModel.reparentTo(self.actor)
            self.damageTakenModel.hide()

            self.damageTakenModelTimer = 0
            self.damageTakenModelDuration = 0.15

    def update(self, keys, dt):
        GameObject.update(self, dt)

        self.walking = False

        # If any movement keys are pressed, use the above time
        # to calculate how far to move the character, and apply that.
        if keys["up"]:
            self.walking = True
            self.velocity.addY(self.acceleration * dt)
        if keys["down"]:
            self.walking = True
            self.velocity.addY(-self.acceleration * dt)
        if keys["left"]:
            self.walking = True
            self.velocity.addX(-self.acceleration * dt)
        if keys["right"]:
            self.walking = True
            self.velocity.addX(self.acceleration * dt)

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
                scoredHit = False

                self.rayQueue.sortEntries()
                rayHit = self.rayQueue.getEntry(0)
                hitPos = rayHit.getSurfacePoint(render)

                hitNodePath = rayHit.getIntoNodePath()
                print(hitNodePath)
                if hitNodePath.hasPythonTag("owner"):
                    hitObject = hitNodePath.getPythonTag("owner")
                    if not isinstance(hitObject, TrapEnemy):
                        hitObject.alterHealth(self.damagePerSecond * dt)
                        scoredHit = True

                # Find out how long the beam is, and scale the
                # beam-model accordingly.
                beamLength = (hitPos - self.actor.getPos()).length()
                self.beamModel.setSy(beamLength)

                self.beamModel.show()

                if scoredHit:
                    # We've hit something, so stop the "no-hit" sound
                    # and play the "hit something" sound
                    if self.laserSoundNoHit.status() == AudioSound.PLAYING:
                        self.laserSoundNoHit.stop()
                    if self.laserSoundHit.status() != AudioSound.PLAYING:
                        self.laserSoundHit.play()

                    self.beamHitModel.show()

                    self.beamHitModel.setPos(hitPos)
                    self.beamHitLightNodePath.setPos(hitPos + Vec3(0, 0, 0.5))

                    # If the light hasn't already been set here, set it
                    if not render.hasLight(self.beamHitLightNodePath):
                        # Apply the light to the scene, so that it
                        # illuminates things
                        render.setLight(self.beamHitLightNodePath)
                else:
                    # We're firing, but hitting nothing, so
                    # stop the "hit something" sound, and play
                    # the "no-hit" sound.
                    if self.laserSoundHit.status() == AudioSound.PLAYING:
                        self.laserSoundHit.stop()
                    if self.laserSoundNoHit.status() != AudioSound.PLAYING:
                        self.laserSoundNoHit.play()

                    # If the light has been set here, remove it
                    # See explanation in the tutorial-text below...
                    if render.hasLight(self.beamHitLightNodePath):
                        # Clear the light from the scene, so that it
                        # no longer illuminates anything
                        render.clearLight(self.beamHitLightNodePath)

                    self.beamHitModel.hide()
        else:
            # If we're not shooting, don't show the beam-model.
            self.beamModel.hide()

            self.beamHitModel.hide()

            # We're not firing, so stop both the
            # "hit something" and "no-hit" sounds
            if self.laserSoundNoHit.status() == AudioSound.PLAYING:
                self.laserSoundNoHit.stop()
            if self.laserSoundHit.status() == AudioSound.PLAYING:
                self.laserSoundHit.stop()

            if render.hasLight(self.beamHitLightNodePath):
                # Clear the light from the scene, so that it
                # no longer illuminates anything
                render.clearLight(self.beamHitLightNodePath)


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

        # run a timer, and use the timer in a sine-function
        # to pulse the scale of the beam-hit model. When the timer
        # runs down (and the scale is at its lowest), reset the timer
        # and randomise the beam-hit model's rotation.
        self.beamHitTimer -= dt
        if self.beamHitTimer <= 0:
            self.beamHitTimer = self.beamHitPulseRate
            self.beamHitModel.setH(random.uniform(0.0, 360.0))
        self.beamHitModel.setScale(math.sin(self.beamHitTimer * 3.142 / self.beamHitPulseRate) * 0.4 + 0.9)

        # altering damage taken by the Player.
        if self.damageTakenModelTimer > 0:
            self.damageTakenModelTimer -= dt
            self.damageTakenModel.setScale(2.0 - self.damageTakenModelTimer / self.damageTakenModelDuration)
            if self.damageTakenModelTimer <= 0:
                self.damageTakenModel.hide()

    # Updating the score
    def updateScore(self):
        self.scoreUI.setText(str(self.score))

    # modifying player's health after taking damage.
    def alterHealth(self, dHealth):
        self.hurtSound.play()

        # altering the Player's health based on the damage taken.
        self.damageTakenModel.show()
        self.damageTakenModel.setH(random.uniform(0.0, 360.0))
        self.damageTakenModelTimer = self.damageTakenModelDuration

        GameObject.alterHealth(self, dHealth)

        self.updateHealthUI()

    # updating the hearts on screen to display the modified health of the player.
    def updateHealthUI(self):
        for index, icon in enumerate(self.healthIcons):
            if index < self.health:
                icon.show()
            else:
                icon.hide()


    # Overriding the cleanup() method of the GameObject class
    def cleanup(self):
        # Cleaning up the health after quitting the game.
        self.laserSoundHit.stop()
        self.laserSoundNoHit.stop()

        self.scoreUI.removeNode()
        for icon in self.healthIcons:
            icon.removeNode()

        self.beamHitModel.removeNode()

        base.cTrav.removeCollider(self.rayNodePath)

        render.clearLight(self.beamHitLightNodePath)
        self.beamHitLightNodePath.removeNode()

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

        self.actor.play("spawn")

        # This "deathSound" is the one that will be used by the logic
        self.deathSound = loader.loadSfx("music/enemyDie.ogg")
        self.attackSound = loader.loadSfx("music/enemyAttack.ogg")

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

        # Creating a "melee attack" for the walking enemy.
        # The Player will take damage from this attack.

        self.attackSegment = CollisionSegment(0, 0, 0, 1, 0, 0)

        segmentNode = CollisionNode("enemyAttackSegment")
        segmentNode.addSolid(self.attackSegment)

        # A mask that matches the player's, so that
        # the enemy's attack will hit the player-character,
        # but not the enemy-character (or other enemies)
        mask = BitMask32()
        mask.setBit(1)

        segmentNode.setFromCollideMask(mask)

        mask = BitMask32()

        segmentNode.setIntoCollideMask(mask)

        self.attackSegmentNodePath = render.attachNewNode(segmentNode)
        self.segmentQueue = CollisionHandlerQueue()

        base.cTrav.addCollider(self.attackSegmentNodePath, self.segmentQueue)

        # How much damage the enemy's attack does
        # That is, this results in the player-character's
        # health being reduced by one.
        self.attackDamage = -1

        # The delay between the start of an attack,
        # and the attack (potentially) landing
        self.attackDelay = 0.3
        self.attackDelayTimer = 0
        # How long to wait between attacks
        self.attackWaitTimer = 0

    def runLogic(self, player, dt):
        # if the spawn animation is playing, we skip the other behaviour in runLogic
        spawnControl = self.actor.getAnimControl("spawn")
        if spawnControl is not None and spawnControl.isPlaying():
            return
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
            attackControl = self.actor.getAnimControl("attack")
            if not attackControl.isPlaying():
                self.walking = True
                vectorToPlayer.setZ(0)
                vectorToPlayer.normalize()
                self.velocity += vectorToPlayer*self.acceleration*dt
                self.attackWaitTimer = 0.2
                self.attackDelayTimer = 0
        else:
            self.walking = False
            self.velocity.set(0, 0, 0)

            # If we're waiting for an attack to land...
            if self.attackDelayTimer > 0:
                self.attackDelayTimer -= dt
                # If the time has come for the attack to land...
                if self.attackDelayTimer <= 0:
                    # Check for a hit..
                    if self.segmentQueue.getNumEntries() > 0:
                        self.segmentQueue.sortEntries()
                        segmentHit = self.segmentQueue.getEntry(0)

                        hitNodePath = segmentHit.getIntoNodePath()
                        if hitNodePath.hasPythonTag("owner"):
                            # Apply damage!
                            hitObject = hitNodePath.getPythonTag("owner")
                            hitObject.alterHealth(self.attackDamage)
                            self.attackWaitTimer = 1.0

            # If we're instead waiting to be allowed to attack...
            elif self.attackWaitTimer > 0:
                self.attackWaitTimer -= dt
                # If the wait has ended...
                if self.attackWaitTimer <= 0:
                    # Start an attack!
                    # (And set the wait-timer to a random amount,
                    #  to vary things a little bit.)
                    self.attackWaitTimer = random.uniform(0.5, 0.7)
                    self.attackDelayTimer = self.attackDelay
                    self.actor.play("attack")
                    self.attackSound.play()

        self.actor.setH(heading)

        # Set the segment's start- and end- points.
        # "getQuat" returns a quaternion--a representation
        # of orientation or rotation--that represents the
        # NodePath's orientation. This is useful here,
        # because Panda's quaternion class has methods to get
        # forward, right, and up vectors for that orientation.
        # Thus, what we're doing is making the segment point "forwards".
        self.attackSegment.setPointA(self.actor.getPos())
        self.attackSegment.setPointB(self.actor.getPos() + self.actor.getQuat().getForward() * self.attackDistance)

    def alterHealth(self, dHealth):
        Enemy.alterHealth(self, dHealth)
        self.updateHealthVisual()

    def updateHealthVisual(self):
        perc = self.health / self.maxHealth
        if perc < 0:
            perc = 0
        # The parameters here are red, green, blue, and alpha
        self.actor.setColorScale(perc, perc, perc, 1)

    def cleanup(self):
        base.cTrav.removeCollider(self.attackSegmentNodePath)
        self.attackSegmentNodePath.removeNode()

        GameObject.cleanup(self)
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

        self.impactSound = loader.loadSfx("music/trapHitsSomething.ogg")
        self.stopSound = loader.loadSfx("music/trapStop.ogg")
        self.movementSound = loader.loadSfx("music/trapSlide.ogg")
        self.movementSound.setLoop(True)

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
                self.movementSound.play()

    def alterHealth(self, dHealth):
        pass

    def cleanup(self):
        self.movementSound.stop()

        Enemy.cleanup(self)