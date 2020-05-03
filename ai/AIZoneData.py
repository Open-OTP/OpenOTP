from panda3d.core import NodePath, CollisionTraverser
from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.task import Task
from typing import Dict, List, Tuple


from . import OTPGlobals


class AIZoneData:
    notify = directNotify.newCategory('AIZoneData')

    def __init__(self, air, parentId, zoneId):
        self._air = air
        self._parentId = parentId
        self._zoneId = zoneId
        self._data = self._air.zoneDataStore.getDataForZone(self._parentId, self._zoneId)

    def destroy(self):
        del self._data
        self._air.zoneDataStore.releaseDataForZone(self._parentId, self._zoneId)
        del self._zoneId
        del self._parentId
        del self._air

    def __getattr__(self, attr):
        return getattr(self._data, attr)


class AIZoneDataObj:
    DefaultCTravName = 'default'

    __slots__ = '_parentId', '_zoneId', 'refCount', '_collTravs', '_collTravsStarted', '_render', '_nonCollidableParent', '_parentMgr'

    def __init__(self, parentId, zoneId):
        self._parentId = parentId
        self._zoneId = zoneId
        self.refCount = 0
        self._collTravs = {}
        self._collTravsStarted = set()
        self._render = None
        self._nonCollidableParent = None
        self._parentMgr = None

    def destroy(self):
        for name in list(self._collTravsStarted):
            self.stopCollTrav(cTravName=name)

        self._collTravsStarted.clear()
        self._collTravs.clear()
        if self._nonCollidableParent:
            self._nonCollidableParent.removeNode()
        if self._render:
            self._render.removeNode()
        if self._parentMgr:
            self._parentMgr.destroy()
            del self._parentMgr

    @property
    def location(self):
        return self._parentId, self._zoneId

    def __str__(self):
        output = str(self._collTravs)
        output += '\n'
        totalColliders = 0
        totalTraversers = 0
        for currCollTrav in self._collTravs.values():
            totalTraversers += 1
            totalColliders += currCollTrav.getNumColliders()

        output += 'Num traversers: %s  Num total colliders: %s' % (totalTraversers, totalColliders)
        return output

    @property
    def render(self):
        if not self._render:
            self._render = NodePath('render-%s-%s' % self.location)
        return self._render

    @property
    def nonCollidableParent(self):
        if not self._nonCollidableParent:
            self._nonCollidableParent = self.render.attachNewNode('nonCollidables')
        return self._nonCollidableParent

    @property
    def parentMgr(self):
        if not self._parentMgr:
            self._parentMgr = ParentMgr()
            self._parentMgr.registerParent(OTPGlobals.SPHidden, simbase.hidden)
            self._parentMgr.registerParent(OTPGlobals.SPRender, self.render)
        return self._parentMgr

    def hasCollTrav(self, name=None):
        if name is None:
            name = AIZoneDataObj.DefaultCTravName
        return name in self._collTravs

    def getCollTrav(self, name=None):
        if name is None:
            name = AIZoneDataObj.DefaultCTravName
        if name not in self._collTravs:
            self._collTravs[name] = CollisionTraverser('cTrav-%s-%s-%s' % (name, self._parentId, self._zoneId))
        return self._collTravs[name]

    def removeCollTrav(self, name):
        if name in self._collTravs:
            del self._collTravs[name]

    def _getCTravTaskName(self, name=None):
        if name is None:
            name = AIZoneDataObj.DefaultCTravName
        return 'collTrav-%s-%s-%s' % (name, self._parentId, self._zoneId)

    def _doCollisions(self, task=None, topNode=None, cTravName=None):
        render = self.render
        curTime = globalClock.getFrameTime()
        render.setTag('lastTraverseTime', str(curTime))
        if topNode:
            topNode = render
        if cTravName is None:
            cTravName = AIZoneDataObj.DefaultCTravName
        collTrav = self._collTravs[cTravName]
        messenger.send('preColl-' + collTrav.getName())
        collTrav.traverse(topNode)
        messenger.send('postColl-' + collTrav.getName())
        return Task.cont

    def doCollTrav(self, topNode=None, cTravName=None):
        self.getCollTrav(cTravName)
        self._doCollisions(topNode=topNode, cTravName=cTravName)

    def startCollTrav(self, respectPrevTransform=1, cTravName=None):
        if cTravName is None:
            cTravName = AIZoneDataObj.DefaultCTravName
        if cTravName not in self._collTravsStarted:
            self.getCollTrav(name=cTravName)
            taskMgr.add(self._doCollisions, self._getCTravTaskName(name=cTravName),
                        priority=OTPGlobals.AICollisionPriority, extraArgs=[self._zoneId])
            self._collTravsStarted.add(cTravName)
        self.setRespectPrevTransform(respectPrevTransform, cTravName=cTravName)
        return

    def stopCollTrav(self, cTravName=None):
        if cTravName is None:
            cTravName = AIZoneDataObj.DefaultCTravName
        if cTravName in self._collTravsStarted:
            taskMgr.remove(self._getCTravTaskName(name=cTravName))
            self._collTravsStarted.remove(cTravName)
        return

    def setRespectPrevTransform(self, flag, cTravName=None):
        if cTravName is None:
            cTravName = AIZoneDataObj.DefaultCTravName
        self._collTravs[cTravName].setRespectPrevTransform(flag)
        return

    def getRespectPrevTransform(self, cTravName=None):
        if cTravName is None:
            cTravName = AIZoneDataObj.DefaultCTravName
        return self._collTravs[cTravName].getRespectPrevTransform()


class AIZoneDataStore:
    def __init__(self):
        self._zone2data: Dict[Tuple[int, int], AIZoneDataObj] = {}

    def destroy(self):
        for zone, data in self._zone2data.items():
            data.destroy()

        del self._zone2data

    def hasDataForZone(self, parentId, zoneId) -> bool:
        key = (parentId, zoneId)
        return key in self._zone2data

    def getDataForZone(self, parentId, zoneId) -> AIZoneDataObj:
        key = (parentId, zoneId)
        if key not in self._zone2data:
            self._zone2data[key] = AIZoneDataObj(parentId, zoneId)
        data = self._zone2data[key]
        data.refCount += 1
        return data

    def releaseDataForZone(self, parentId, zoneId):
        key = (parentId, zoneId)
        data = self._zone2data[key]
        data.refCount -= 1
        if data.refCount == 0:
            del self._zone2data[key]
            data.destroy()


class ParentMgr:
    """ParentMgr holds a table of nodes that avatars may be parented to
    in a distributed manner. All clients within a particular zone maintain
    identical tables of these nodes, and the nodes are referenced by 'tokens'
    which the clients can pass to each other to communicate distributed
    reparenting information.
    The functionality of ParentMgr used to be implemented with a simple
    token->node dictionary. As distributed 'parent' objects were manifested,
    they would add themselves to the dictionary. Problems occured when
    distributed avatars were manifested before the objects to which they
    were parented to.
    Since the order of object manifestation depends on the order of the
    classes in the DC file, we could maintain an ordering of DC definitions
    that ensures that the necessary objects are manifested before avatars.
    However, it's easy enough to keep a list of pending reparents and thus
    support the general case without requiring any strict ordering in the DC.
    """

    __slots__ = 'nodes', 'pendingParents', 'pendingRequests'

    def __init__(self):
        self.nodes: Dict[str, NodePath] = {}
        self.pendingParents: Dict[str, List[NodePath]] = {}
        self.pendingRequests: Dict[NodePath, str] = {}

    def destroy(self):
        self.nodes.clear()
        self.pendingParents.clear()
        self.pendingRequests.clear()

    def registerParent(self, token: str, parent: NodePath):
        self.nodes[token] = parent

        if token in self.pendingParents:
            _, children = self.pendingParents.popitem()
            for child in children:
                child.reparentTo(parent)

    def unregisterParent(self, token: str):
        try:
            del self.nodes[token]
        except KeyError:
            pass

    def _delPendingRequest(self, child: NodePath):
        if child in self.pendingRequests:
            token = self.pendingRequests.pop(child)
            self.pendingParents[token].remove(child)

    def requestReparent(self, child: NodePath, parentToken: str):
        self._delPendingRequest(child)
        if parentToken in self.nodes:
            child.wrtReparentTo(self.nodes[parentToken])
        else:
            self.pendingParents.setdefault(parentToken, []).append(child)
            child.reparentTo(hidden)
