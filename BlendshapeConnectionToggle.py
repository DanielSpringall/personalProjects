"""
blendshapeConnectionToggle is used to disconnect then re-connect incoming connections to a blendshape node. This helps
in bypassing the issue of editing a shape in a combination target. Because the connection on the blendshape node is
stored as a string, this also allows for quickly swapping a driver for a target by disconnecting the connections,
renaming the target, and then re connecting any connections
To run:
import blendshapeConnectionToggle; blendshapeConnectionToggle.ToggleBlendShapeConnection_UI()
-------------------------
MIT License
Copyright (c) 2018 Daniel Springall
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import maya.cmds as cmds


class ToggleBlendShapeConnection_UI:
    def __init__(self):
        # Create the window
        if cmds.window("blendShapeConnectionToggle_UI", exists=True):
            cmds.deleteUI("blendShapeConnectionToggle_UI")
        self.window = cmds.window("blendShapeConnectionToggle_UI", t="bsConnection Toggle", sizeable=False,
                                  wh=(300, 155))

        # Get scene data
        self.parentNode = "blendShapeConnection_data"
        self.sceneBlendShapes = sorted(getSceneBlendShapeNodes())

        # Create script job
        self.scriptJob_number = cmds.scriptJob(event=["SelectionChanged", self.updateBlendShapeMenuFromSelection],
                                               parent=self.window)

        # UI Elements
        self.blendShape_optionMenu = None
        self.disconnectCorrectives_checkBox = None
        self.ignoreMissingAttributesOnConnection_checkBox = None
        self.toggleBlendShape_btn = None

        # Create and show the UI
        self.initUI()
        self.updateBlendShapeMenuFromSelection()
        self.updateActionButton()
        cmds.showWindow(self.window)

    def initUI(self):
        parentLayout = cmds.columnLayout(columnAttach=("both", 20), rowSpacing=10, cal="center", adj=True)

        cmds.separator(style="none", h=10)
        self.blendShape_optionMenu = cmds.optionMenu(label="BlendShape: ", cc=self.updateActionButton)
        if self.sceneBlendShapes:
            for blendShape in self.sceneBlendShapes:
                cmds.menuItem(label=blendShape, parent=self.blendShape_optionMenu)
        else:
            cmds.menuItem(label="No Scene BlendShapes", parent=self.blendShape_optionMenu)
            cmds.optionMenu(self.blendShape_optionMenu, e=True, en=False)

        cmds.rowLayout(nc=2)
        cmds.separator(w=5, st="none")
        cmds.columnLayout()
        self.disconnectCorrectives_checkBox = cmds.checkBox(label="Disconnect corrective drivers", value=True)
        self.ignoreMissingAttributesOnConnection_checkBox = cmds.checkBox(
            label="Ignore missing attributes on connection", value=False)

        cmds.setParent(parentLayout)
        cmds.rowLayout(nc=2)
        self.toggleBlendShape_btn = cmds.button(label="Disconnect", h=30, w=125)
        cmds.button(label="Close", command="cmds.deleteUI(\"blendShapeConnectionToggle_UI\")", h=30, w=125)

    def getBlendShapeNodeFromOptionMenu(self):
        return cmds.optionMenu(self.blendShape_optionMenu, q=True, value=True)

    def updateBlendShapeMenuFromSelection(self):
        """ Update the selected item in the blendShape optionMenu based on selection, will select either a meshes
        blendShape node, or if a dataNode is selected it will select it's corresponding blendShape node as well
        """
        blendShapeNode = self.getBlendShapeNodeFromSelection()
        if not blendShapeNode:
            return

        # No point updating if it's the same as what's selected
        if blendShapeNode == self.getBlendShapeNodeFromOptionMenu():
            return

        index = self.sceneBlendShapes.index(blendShapeNode) + 1  # optionMenu input is 1 based index
        cmds.optionMenu(self.blendShape_optionMenu, e=True, select=index)

        self.updateActionButton()

    def updateActionButton(self, *args, **kwargs):
        """ Update the Reconnect/Disconnect button based on what selection is given in the optionMenu
        """
        selectedBlendShape = self.getBlendShapeNodeFromOptionMenu()
        if not selectedBlendShape:
            return

        blendShapeDataNodes = getBlendShapeDataNodes()
        if blendShapeDataNodes:
            if "connectionData_{}".format(selectedBlendShape) in blendShapeDataNodes:
                cmds.button(self.toggleBlendShape_btn, e=True, label="Reconnect", c=self.reconnectBlendShapeConnections)
                cmds.checkBox(self.disconnectCorrectives_checkBox, e=True, en=False)
                cmds.checkBox(self.ignoreMissingAttributesOnConnection_checkBox, e=True, en=True)
                return
        cmds.button(self.toggleBlendShape_btn, e=True, label="Disconnect", c=self.disconnectBlendShapeConnections)
        cmds.checkBox(self.disconnectCorrectives_checkBox, e=True, en=True)
        cmds.checkBox(self.ignoreMissingAttributesOnConnection_checkBox, e=True, en=False)

    @staticmethod
    def getBlendShapeNodeFromSelection():
        """ Get the a blendShape node based on selection, either from a mesh, or a dataNode holding a blendShape nodes
        connections
        """
        selection = cmds.ls(sl=True)
        if len(selection) != 1:
            return None

        # Check to see if it's a blendShape node
        if cmds.nodeType(selection[0]) == "blendShape":
            return selection[0]

        # Check to see if it's a dataNode
        if cmds.nodeType(selection[0]) == "transform":
            if selection[0].startswith("connectionData_"):
                return selection[0].replace("connectionData_", "")

        # Check to see if it's a mesh with a blendShape
        shapeNode = getShapeNode(selection[0])
        if not shapeNode:
            return None
        history = cmds.listHistory(shapeNode) or []
        for node in history:
            if cmds.nodeType(node) == "blendShape":
                return node
        return None

    # Scene actions
    def disconnectBlendShapeConnections(self, *args, **kwargs):
        blendShape = self.getBlendShapeNodeFromOptionMenu()
        if not blendShape or blendShape == "No Scene BlendShapes":
            print "No blendShape selected to disconnect"
            return

        self.createBlendShapeDataParentNode()
        dataNodeName = "connectionData_{}".format(blendShape)
        if cmds.checkBox(self.disconnectCorrectives_checkBox, q=True, v=True):
            skipNodeTypes = ["combinationShape"]
        else:
            skipNodeTypes = None
        success = disconnectNodeConnections(blendShape, dataNodeName, parent=self.parentNode,
                                            skipNodeTypes=skipNodeTypes)
        if success:
            self.updateActionButton()
        else:
            self.removeBlendShapeDataParentNode()

    def reconnectBlendShapeConnections(self, *args, **kwargs):
        blendShape = self.getBlendShapeNodeFromOptionMenu()
        if not blendShape or blendShape == "No Scene BlendShapes":
            print "No blendShape selected to reconnect"
            return

        ignoreMissingAttributes = cmds.checkBox(self.ignoreMissingAttributesOnConnection_checkBox, q=True, v=True)
        dataNodeName = "connectionData_{}".format(blendShape)
        success = reconnectNodeConnections(blendShape, dataNode=dataNodeName,
                                           ignoreMissingAttributes=ignoreMissingAttributes)
        if success:
            self.updateActionButton()
            self.removeBlendShapeDataParentNode()

    def createBlendShapeDataParentNode(self):
        """ Creates the blendShape data parent node, if it doesn't exist in the scene, creates it
        """
        if not cmds.objExists(self.parentNode):
            cmds.group(n=self.parentNode, em=True)
            cmds.lockNode(self.parentNode, lock=True)

    def removeBlendShapeDataParentNode(self):
        """ If the parent node has no child nodes, remove the blendShape data parent node from the scene
        """
        if not cmds.listRelatives(self.parentNode):
            cmds.lockNode(self.parentNode, lock=False)
            cmds.delete(self.parentNode)


def getSceneBlendShapeNodes():
    """ Gets all the blendShape nodes in the scene
    :return: list[string], all the blendShape nodes in the scene, or None of none exist
    """
    return cmds.ls(type="blendShape")


def getBlendShapeDataNodes():
    """ Get a list of nodes in the scene that contain blendShape connection info
    :return: list[string], name of the blendShape data nodes, or None if none exist
    """
    parentNode = "blendShapeConnection_data"
    if not cmds.objExists(parentNode):
        return []
    return cmds.listRelatives(parentNode)


def getShapeNode(node):
    """ Get a transform nodes child shape node
    :param node: string, name of the transform node to check for a shape node from
    :return: string, shape nodes name, or None
    """
    if cmds.nodeType(node) == "transform":
        shapes = cmds.listRelatives(node, shapes=True, path=True, noIntermediate=True)
        if shapes:
            return shapes[0]
    elif cmds.nodeType(node) in ["mesh", "nurbsCurve", "nurbsSurface"]:
        return node
    return None


def disconnectNodeConnections(sourceNode, dataNodeName, parent=None, skipNodeTypes=None):
    """ Disconnect a given nodes incoming connections and temporarily store them on another node in the scene
    :param sourceNode: string, name of the node to disconnect connections from
    :param dataNodeName: string, name to give the node that will store temporarily store the connections
    :param parent: string, name of the node to parent the dataNode to
    :param skipNodeTypes: list[string], types of nodes to skip from being disconnected
    :return: bool, True if disconnection was successful, False otherwise
    """
    targets = cmds.listAttr("{}.w".format(sourceNode), m=True)
    if not targets:
        cmds.warning("No targets on the blendShape node to disconnect")
        return False

    dataNode = cmds.group(n=dataNodeName, em=True)

    connectionList = []
    try:
        for target in targets:
            connections = cmds.listConnections("{}.{}".format(sourceNode, target), s=True, d=False, p=True)
            if not connections:
                continue

            connection = connections[0]
            if skipNodeTypes:
                if cmds.nodeType(connection.rsplit(".", 1)[0]) in skipNodeTypes:
                    continue

            # Add the attribute to the data node and connect it
            cmds.addAttr(dataNode, ln=target)
            cmds.connectAttr(connection, "{}.{}".format(dataNode, target))
            # Store the attribute connection so that we can undo any connections if something goes wrong
            cmds.disconnectAttr(connection, "{}.{}".format(sourceNode, target))
            connectionList.append([connection, "{}.{}".format(sourceNode, target)])
    except RuntimeError as e:
        # In the event of an runtime error, reset the blendShape node back to normal
        if connectionList:
            for source, destination in connectionList:
                cmds.connectAttr(source, destination, f=True)
        cmds.delete(dataNode)
        cmds.warning("Failed to disconnect connections for {}".format(sourceNode))
        print e
        return False

    # If we didn't find any connections delete the dataNode
    if not connectionList:
        cmds.warning("No connections found for {}".format(sourceNode))
        cmds.delete(dataNode)
        return False

    # Parent and lock the node
    if parent:
        cmds.parent(dataNode, parent)
    cmds.lockNode(dataNode, lock=True)
    return True


def reconnectNodeConnections(destinationNode, dataNode, ignoreMissingAttributes=False):
    """ Reconnect connections stored on a dataNode back to a blendShape node
    :param destinationNode: string, name of the node to reconnect the connections to
    :param dataNode: string, name of the node storing the connections
    :param ignoreMissingAttributes: bool, whether or not missing connections on the destinationNode are ignored
    :return: bool, True if reconnection was successful, False otherwise
    """
    connections = cmds.listConnections(dataNode, s=True, d=False, c=True, p=True)
    if not connections:
        raise RuntimeError("No connections exist on {} to reconnect to {}".format(dataNode, destinationNode))

    connectionList = []
    missingAttributeList = []
    try:
        for i in xrange(0, len(connections), 2):
            source = connections[i+1]
            destination = connections[i]
            attribute = destination.rsplit(".", 1)[1]
            newDestination = "{}.{}".format(destinationNode, attribute)

            if not cmds.attributeQuery(attribute, node=destinationNode, ex=True):
                missingAttributeList.append(attribute)
                continue
            cmds.connectAttr(source, newDestination)
            connectionList.append([source, newDestination])
    except RuntimeError as e:
        # In the event of an runtime error, reset the dataNode back to normal
        if connectionList:
            for source, destination in connectionList:
                cmds.connectAttr(source, destination, f=True)
        cmds.warning("Failed to reconnect blendShape connections for {}".format(destinationNode))
        print e
        return False

    # If we couldn't find all the connections, reconnect everything and inform the user of the missing attributes
    if not ignoreMissingAttributes and missingAttributeList:
        cmds.warning("Failed to find the following attributes on the {}".format(destinationNode))
        for attribute in missingAttributeList:
            print attribute
        # Disconnect any of the connections made
        for source, destination in connectionList:
            cmds.disconnectAttr(source, destination)
        return False

    cmds.lockNode(dataNode, lock=False)
    cmds.delete(dataNode)
    return True
