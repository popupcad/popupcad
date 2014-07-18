# -*- coding: utf-8 -*-
"""
Written by Daniel M. Aukes.
Email: danaukes<at>seas.harvard.edu.
Please see LICENSE.txt for full license.
"""
import sys
import PySide.QtGui as qg
import PySide.QtCore as qc
import popupcad
from popupcad.graphics2d.interactivevertex import InteractiveVertex
from popupcad.graphics2d.interactiveedge import InteractiveEdge
from popupcad.graphics2d.interactive import Interactive, InteractiveLine
from popupcad.graphics2d.static import Static,StaticLine
#from popupcad.graphics2d.proto import ProtoLine,ProtoPath,ProtoCircle,ProtoPoly,ProtoRect,ProtoRect2Point
from popupcad.graphics2d.proto import ProtoLine,ProtoPath,ProtoCircle,ProtoPoly,ProtoRect2Point
from popupcad.graphics2d.graphicsscene import GraphicsScene
from popupcad.graphics2d.graphicsview import GraphicsView
import popupcad.constraints as constraints
from popupcad.filetypes import Sketch
from popupcad.widgets.listeditor import ListEditor,ListSelector
from popupcad.supportfiles import Icon
import numpy
from popupcad.widgets.widgetcommon import WidgetCommon
from popupcad.filetypes.undoredo import UndoRedo
from popupcad.widgets.dragndroptree import DraggableTreeWidget
from popupcad.manufacturing.nulloperation import NullOp
from popupcad.graphics2d.text import TextItem

class Sketcher(qg.QMainWindow,WidgetCommon):
    showprop = qc.Signal(object)
    
    def __init__(self,parent,sketch,design = None,ii = None,jj = 0,kk = 0,isOperation = False,selectedlayers = None,accept_method = None,selectops = False,oplimit = None):
        
        qg.QMainWindow.__init__(self,parent)
        self.design = design
        self.isOperation = isOperation
        self.accept_method = accept_method
        self.selectops = selectops
        
        if selectedlayers == None:
            if design != None:
                selectedlayers = self.design.layerdef().layers
            
        if self.design == None:
            self.operations = [NullOp()]
        else:
            if oplimit==None:
                self.operations = [NullOp()]+self.design.operations[:]
            else:
                self.operations = [NullOp()]+self.design.operations[:oplimit]

        self.setupLayout()   
        
        if self.selectops:
            self.optree.linklist(self.operations)
        self.loadsketch(sketch)
        
        self.createActions()        
        
        if self.selectops:
            if ii!=None:
                ii = ii+1
            else:
                ii = 0
            self.optree.setCurrentIndeces(ii,jj)
        
        if self.isOperation:
            self.selectlayers(selectedlayers)
            self.operationtypeselector.setCurrentIndex(kk)

        self.load_references()

        self.connectSignals()
    def connectSignals(self):
        self.setWindowModality(qc.Qt.WindowModality.ApplicationModal)
        self.setAttribute(qc.Qt.WA_DeleteOnClose)
        self.scene.itemclicked.connect(self.loadpropwindow)
        self.showprop.connect(self.loadpropwindow)
        self.graphicsview.zoomToFit()
        self.scene.newpolygon.connect(self.undoredo.savesnapshot)
        self.scene.savesnapshot.connect(self.undoredo.savesnapshot)
        self.constraint_editor.signal_edit.connect(self.editItem)
#        self.constraint_editor.itemdeleted.connect(self.refreshconstraints)
        self.constraint_editor.itemPressed.connect(self.showconstraint_item)
        if self.selectops:
            self.optree.currentRowChanged.connect(self.load_references)
        
    def setupLayout(self):
        if self.isOperation:
            self.operationtypeselector = qg.QComboBox()
            self.operationtypeselector.addItems(['union','intersection','difference','symmetric_difference'])
            self.operationtypedock = qg.QDockWidget()
            self.operationtypedock.setWidget(self.operationtypeselector)
            self.operationtypedock.setAllowedAreas(qc.Qt.AllDockWidgetAreas)
            self.operationtypedock.setWindowTitle('Operation Types')

        self.constraint_editor = ListEditor()
        if self.selectops:
            self.optree = DraggableTreeWidget()
        self.propertieswindow = qg.QWidget()
        
        if self.isOperation:
            self.layerlistwidget = ListSelector()

            if self.design !=None:
                layers = self.design.layerdef().layers
            else:
                layers = []
            self.layerlistwidget.linklist(layers)
            

        ok_button = qg.QPushButton('&Ok',self)
        cancel_button= qg.QPushButton('&Cancel',self)
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        sublayout= qg.QHBoxLayout()
        sublayout.addStretch(1)
        sublayout.addWidget(ok_button)
        sublayout.addWidget(cancel_button)
        sublayout.addStretch(1)

        self.scene = GraphicsScene()
        self.graphicsview = GraphicsView(self.scene)
        
        centrallayout = qg.QVBoxLayout()
        centrallayout.addWidget(self.graphicsview)
        centrallayout.addLayout(sublayout)
        centralwidget = qg.QWidget()
        centralwidget.setLayout(centrallayout)

        if self.selectops:
            self.optreedock = qg.QDockWidget()
            self.optreedock.setWidget(self.optree)
            self.optreedock.setAllowedAreas(qc.Qt.AllDockWidgetAreas)
            self.optreedock.setWindowTitle('Operatons')

        self.constraintdock = qg.QDockWidget()
        self.constraintdock.setWidget(self.constraint_editor)
        self.constraintdock.setAllowedAreas(qc.Qt.AllDockWidgetAreas)
        self.constraintdock.setWindowTitle('Constraints')
        self.constraintdock.setMinimumHeight(200)

        self.propdock = qg.QDockWidget()
        self.propdock.setWidget(self.propertieswindow)
        self.propdock.setAllowedAreas(qc.Qt.AllDockWidgetAreas)
        self.propdock.setWindowTitle('Properties')
        self.propdock.setMinimumHeight(200)

        if self.isOperation:
            self.layerdock = qg.QDockWidget()
            self.layerdock.setWidget(self.layerlistwidget)
            self.layerdock.setAllowedAreas(qc.Qt.AllDockWidgetAreas)
            self.layerdock.setWindowTitle('Layers')
        
            self.addDockWidget(qc.Qt.LeftDockWidgetArea,self.operationtypedock)

        if self.selectops:
            self.addDockWidget(qc.Qt.LeftDockWidgetArea,self.optreedock)
        self.addDockWidget(qc.Qt.RightDockWidgetArea,self.constraintdock)
        self.addDockWidget(qc.Qt.RightDockWidgetArea,self.propdock)

        if self.isOperation:
            self.addDockWidget(qc.Qt.LeftDockWidgetArea,self.layerdock)

        self.setCentralWidget(centralwidget)        
        self.setWindowTitle('Sketcher')
        self.resize(1024,576)
        dxy = qg.QApplication.desktop().screen().rect().center() - self.rect().center()
        self.move(dxy)
        
    def showconstraint_item(self,obj1):
#        print 'vertex_ids:',obj1.customdata.vertex_ids
        self.showprop.emit(obj1.customdata)
        self.scene.clearSelection()
        vertices = [item for item in self.scene.items() if isinstance(item,InteractiveVertex)]
        for v in vertices:
#            print v.symbolic.id
            if v.symbolic.id in obj1.customdata.vertex_ids:
#                print 'found:',v.symbolic.id
                v.setSelected(True)
        pass
        edges = [item for item in self.scene.items() if isinstance(item,InteractiveEdge)]
        for edge in edges:
            a = [edge.handle1,edge.handle2]
            b = [item.symbolic.id for item in a]
            c= set(b)
            if any([len(c.intersection(segment))==2 for segment in obj1.customdata.segment_ids]):
                edge.setSelected(True)

    def regen_id(self):
        self.sketch.regen_id()

    def editItem(self,constraint):
        self.undoredo.savesnapshot()
        constraint.edit()
        self.refreshconstraints()
        
    def refreshconstraints(self):
        self.undoredo.savesnapshot()
        parents = [parent for parent in self.scene.items() if ((isinstance(parent,Interactive)))]
        interactivevertices = [item for parent in parents for item in parent.handles()]


#        allvisiblevertices = [item for item in self.scene.items() if isinstance(item,InteractiveVertex)]

        interactivevertices = [item for parent in parents for item in parent.handles()]

        controllinevertices = [item for parent in self.scene.controllines for item in [parent.handle1,parent.handle2]]
        
        vertices = list(set(interactivevertices+self.scene.controlpoints + controllinevertices))
        
        symbolicvertices = [vertex.symbolic for vertex in vertices]
        self.sketch.constraintsystem.process(symbolicvertices)
        [vertex.updatefromsymbolic() for vertex in vertices]            
        [parent.updateshape() for parent in parents]
            
        self.constraint_editor.refresh()

    def createActions(self):
        self.fileactions = []
        self.fileactions.append({'text':"&New",'kwargs':{'triggered':self.newfile,'shortcut':qg.QKeySequence.New,'icon':Icon('new')}})
        self.fileactions.append({'text':"&Open...",'kwargs':{'triggered':self.open,'shortcut':qg.QKeySequence.Open,'icon':Icon('open')}})
        self.fileactions.append({'text':"Import...",'kwargs':{'triggered':self.solidworksimport,'icon':Icon('import')}})      
        self.fileactions.append({'text':"&Save",'kwargs':{'triggered':self.save,'shortcut':qg.QKeySequence.Save,'icon':Icon('save')}})
        self.fileactions.append({'text':"Save &As...",'kwargs':{'triggered':self.saveAs,'shortcut':qg.QKeySequence.SaveAs,'icon':Icon('saveas')}})      
        self.fileactions.append({'text':"Regen ID",'kwargs':{'triggered':self.regen_id}})      

        self.editactions = []
        self.editactions.append({'text':'Undo','kwargs':{'triggered':self.undoredo.undo,'shortcut':qg.QKeySequence.Undo,'icon':Icon('undo')}})      
        self.editactions.append({'text':'Redo','kwargs':{'triggered':self.undoredo.redo,'shortcut':qg.QKeySequence.Redo,'icon':Icon('redo')}})      
        self.editactions.append(None)      
        self.editactions.append({'text':'Cut','kwargs':{'triggered':self.cut_to_clipboard,'shortcut':qg.QKeySequence.Cut}})      
        self.editactions.append({'text':'Copy','kwargs':{'triggered':self.copy_to_clipboard,'shortcut':qg.QKeySequence.Copy}})      
        self.editactions.append({'text':'Paste','kwargs':{'triggered':self.paste_from_clipboard,'shortcut':qg.QKeySequence.Paste}})      
#        self.editactions.append({'text':'Delete','kwargs':{'triggered':self.delete_selected_items,'shortcut':qg.QKeySequence.Delete}})      
        self.editactions.append(None)      
        self.editactions.append({'text':'Group','kwargs':{'triggered':self.group,'shortcut':qc.Qt.CTRL+qc.Qt.Key_G}})      
        self.editactions.append({'text':'Unroup','kwargs':{'triggered':self.ungroup,'shortcut':qc.Qt.CTRL+qc.Qt.Key_U}})      

        self.viewactions = []
        self.viewactions.append({'text':'Operations','kwargs':{'triggered':lambda:self.showhide(self.optreedock)}})
        self.viewactions.append({'text':'Constraints','kwargs':{'triggered':lambda:self.showhide(self.constraintdock)}})
        self.viewactions.append({'text':'Properties','kwargs':{'triggered':lambda:self.showhide(self.propdock)}})
        if self.isOperation:
            self.viewactions.append({'text':'Layers','kwargs':{'triggered':lambda:self.showhide(self.layerdock)}})
            self.viewactions.append({'text':'Operation Types','kwargs':{'triggered':lambda:self.showhide(self.operationtypedock)}})
        self.viewactions.append({'text':'select','kwargs':{'triggered':self.graphicsview.rubberband,'shortcut': qc.Qt.CTRL+qc.Qt.SHIFT+qc.Qt.Key_S,'icon':Icon('select')}})
        self.viewactions.append({'text':'pan','kwargs':{'triggered':self.graphicsview.scrollhand,'shortcut': qc.Qt.CTRL+qc.Qt.SHIFT+qc.Qt.Key_P,'icon':Icon('pan')}})
        self.viewactions.append(None)
        self.viewactions.append({'text':'Zoom Fit','kwargs':{'triggered':self.graphicsview.zoomToFit,'shortcut':qc.Qt.CTRL+qc.Qt.Key_F}})
        self.viewactions.append({'text':'Screenshot','kwargs':{'triggered':self.scene.screenShot,'shortcut': qc.Qt.CTRL+qc.Qt.Key_R}})
        
        self.drawingactions = []
        self.drawingactions.append({'text':'polyline','kwargs':{'triggered':lambda:self.addproto(ProtoPath),'icon':Icon('polyline')}})
        self.drawingactions.append({'text':'line','kwargs':{'triggered':lambda:self.addproto(ProtoLine),'icon':Icon('line')}})
        self.drawingactions.append({'text':'poly','kwargs':{'triggered':lambda:self.addproto(ProtoPoly),'icon':Icon('polygon')}})
        self.drawingactions.append({'text':'rect','kwargs':{'triggered':lambda:self.addproto(ProtoRect2Point),'icon':Icon('rectangle')}})
        self.drawingactions.append({'text':'circle','kwargs':{'triggered':lambda:self.addproto(ProtoCircle),'icon':Icon('circle')}})
        self.drawingactions.append({'text':'text','kwargs':{'triggered':lambda:self.addproto(TextItem)}})
        self.drawingactions.append(None)
        self.drawingactions.append({'text':'joinedges','kwargs':{'triggered':self.joinedges,'icon':Icon('joinedges')}})
        self.drawingactions.append({'text':'autobridge','kwargs':{'triggered':self.autobridge,'icon':Icon('autobridge')}})

        self.constraintactions = []
        self.constraintactions.append({'text':'Constraints On','kwargs':{'triggered':self.scene.showvertices,'icon':Icon('showconstraints')}})
        self.constraintactions.append(None)
        self.constraintactions.append({'text':'Horizontal','kwargs':{'triggered':lambda:self.add_constraint(constraints.horizontal),'icon':Icon('horizontal')}})
        self.constraintactions.append({'text':'Vertical','kwargs':{'triggered':lambda:self.add_constraint(constraints.vertical),'icon':Icon('vertical')}})
        self.constraintactions.append({'text':'Coincident','kwargs':{'triggered':lambda:self.add_constraint(constraints.coincident)}})
        self.constraintactions.append({'text':'Distance','kwargs':{'triggered':lambda:self.add_constraint(constraints.distance),'icon':Icon('distance')}})
        self.constraintactions.append({'text':'DistanceX','kwargs':{'triggered':lambda:self.add_constraint(constraints.distancex),'icon':Icon('distancex')}})
        self.constraintactions.append({'text':'DistanceY','kwargs':{'triggered':lambda:self.add_constraint(constraints.distancey),'icon':Icon('distancey')}})
        self.constraintactions.append({'text':'Angle','kwargs':{'triggered':lambda:self.add_constraint(constraints.angle),'icon':Icon('angle')}})
        self.constraintactions.append({'text':'Parallel','kwargs':{'triggered':lambda:self.add_constraint(constraints.parallel),'icon':Icon('parallel')}})
        self.constraintactions.append({'text':'Perpendicular','kwargs':{'triggered':lambda:self.add_constraint(constraints.perpendicular),'icon':Icon('perpendicular')}})
        self.constraintactions.append({'text':'Equal','kwargs':{'triggered':lambda:self.add_constraint(constraints.equal),'icon':Icon('equal')}})
        self.constraintactions.append({'text':'PointLine','kwargs':{'triggered':lambda:self.add_constraint(constraints.PointLine),'icon':Icon('pointline')}})
        self.constraintactions.append({'text':'Update','kwargs':{'triggered':self.refreshconstraints,'icon':Icon('refresh')}})

        self.menu_file = self.buildMenu(self.fileactions,name='File')
        self.menu_edit = self.buildMenu(self.editactions,name='Edit')
        self.menu_drawing = self.buildMenu(self.drawingactions,name='Drawing')
        self.menu_constraints = self.buildMenu(self.constraintactions,name='Constraints')
        self.menu_view = self.buildMenu(self.viewactions,name='View')

        self.toolbar_drawing = self.buildToolbar(self.drawingactions,name='Drawing',size=36,area=qc.Qt.ToolBarArea.TopToolBarArea)
        self.toolbar_constraints = self.buildToolbar(self.constraintactions,name='Constraints',size=36,area=qc.Qt.ToolBarArea.TopToolBarArea)

    def keyPressEvent(self,event):
        if event.key() == qc.Qt.Key_Delete:
            self.undoredo.savesnapshot()
        super(GraphicsScene,self).keyPressEvent(event)
        
    def cut_to_clipboard(self):
        self.undoredo.savesnapshot()
        self.scene.cut_to_clipboard()
    def copy_to_clipboard(self):
        self.undoredo.savesnapshot()
        self.scene.copy_to_clipboard()
    def paste_from_clipboard(self):
        self.undoredo.savesnapshot()
        self.scene.paste_from_clipboard()
#    def delete_selected_items(self):
#        self.undoredo.savesnapshot()
#        self.scene.delete_selected_items()
    def selectlayers(self,layers):
        if self.isOperation:
            self.layerlistwidget.selectItems(layers)

    def add_constraint(self,constraintclass):
        self.undoredo.savesnapshot()
        items = []
        for item in self.scene.selectedItems():
            if isinstance(item,InteractiveVertex):
                items.append(item.symbolic)
            elif isinstance(item,InteractiveEdge):
                items.append(item.symbolic())
            elif isinstance(item,InteractiveLine):
                items.append(item.selectableedges[0].symbolic())
            elif isinstance(item,StaticLine):
                items.append(item.selectableedges[0].symbolic())
                                         
        constraint = constraintclass.new(self,*items)
        if constraint !=None:
            self.sketch.constraintsystem.add_constraint(constraint)
            self.refreshconstraints()

    def loadsketch(self,sketch):
        self.sketch = sketch.copy()
        self.scene.deleteall()
        for item in self.sketch.operationgeometry:
            newitem = item.outputinteractive()
            self.scene.addItem(newitem)
            newitem.refreshview()

        self.constraint_editor.linklist(self.sketch.constraintsystem.constraints)
        self.undoredo = UndoRedo(self.get_current_sketch,self.loadsketch)

    def buildsketch(self):
        self.sketch.cleargeometries()
        geometries = [item.generic for item in self.scene.items() if isinstance(item,Interactive) if item.generic.isValid()]
        self.sketch.addoperationgeometries(geometries)
        if self.isOperation:        
            self.layers = [self.layerlistwidget.list[item.row()] for  item in self.layerlistwidget.selectedIndexes()]

    def get_current_sketch(self):
        self.buildsketch()
        return self.sketch
        
    def newfile(self):
        sketch = popupcad.filetypes.Sketch()
        self.loadsketch(sketch)
        self.undoredo.restartundoqueue()

    def solidworksimport(self):
        from popupcad.filetypes.solidworksimport import Assembly
        a = Assembly.open()
        sketch = a.build_face_sketch()
        self.loadsketch(sketch)

#    def solidworksimport2(self):
#        from popupcad.filetypes.solidworksimport import Assembly
#        a = Assembly.open()
#        sketch = a.build_line_sketch()
#        self.loadsketch(sketch)
        
    def open(self):
        sketch = popupcad.filetypes.Sketch.open()
        if not sketch==None:
            self.loadsketch(sketch)

    def save(self):
        self.buildsketch()
        self.sketch.save()
        
    def saveAs(self):
        self.buildsketch()
        self.sketch.saveAs()

    def addproto(self,proto):
        self.graphicsview.turn_off_drag()
        self.scene.addpolygon(proto)

    def joinedges(self):
        selecteditems = self.scene.selectedItems()
        vertices = [item for item in selecteditems if isinstance(item,InteractiveVertex)]
        edges = [item for item in selecteditems if isinstance(item,InteractiveEdge)]
        [vertices.extend([edge.handle1,edge.handle2]) for edge in edges]
        vertices2=[]
        for vertex in vertices:
            scenepos = vertex.scenePos()
            vertices2.append((scenepos.x(),scenepos.y()))
        vertices2 = numpy.array(vertices2)        
        poly = popupcad.algorithms.autobridge.joinedges(vertices2)
        self.scene.addItem(poly.outputinteractive())

    def autobridge(self):
        interactives = [item for item in self.scene.items() if isinstance(item,Interactive)]
#        statics = [item for item in self.scene.items() if isinstance(item,Static)]
        
        handles = []
        [handles.extend(item.handles()) for item in interactives]
        handles.extend(self.scene.controlpoints)        
        vertices = []
        for handle in handles:
            scenepos = handle.scenePos()
            vertices.append((scenepos.x(),scenepos.y()))
        polys = popupcad.algorithms.autobridge.autobridge(vertices)
        [self.scene.addItem(poly.outputinteractive()) for poly in polys]     

    def showconstraint(self,row):
        item = self.constraint_editor.item(row)
        self.showconstraint_item(item)

    def accept(self):
#        print self.acceptdata()
        if self.accept_method!=None:
            self.accept_method(*self.acceptdata())
        self.close()

    def reject(self):
        self.close()

    def keyPressEvent(self,event):
        if not self.keypressfiltering(event):
            super(Sketcher,self).keyPressEvent(event)
    
    def loadpropwindow(self,obj):
        widget = obj.properties()
        self.propdock.setWidget(widget)        
        
    def acceptdata(self):
        self.buildsketch()
        if self.selectops:
            ii,jj = self.optree.currentIndeces()
            ii -= 1
            if ii==-1:
                ii=None
            if self.isOperation:
                kk = self.operationtypeselector.currentIndex()
                layer_links = [item.id for item in self.layers]
                return self.sketch,ii,jj,layer_links,kk
            else:
                return self.sketch,ii,jj
        else:
            return self.sketch,

    def keypressfiltering(self,event):
        if event.key() == qc.Qt.Key_Escape:
            return True
        elif event.key() == qc.Qt.Key_Enter:
            return True
        elif event.key() == qc.Qt.Key_Return:
            return True
        else:
            return False

    def load_references(self):
        if self.selectops:
            self.scene.removerefgeoms()
            self.scene.controlpoints = []
            self.scene.controllines = []
            ii,jj = self.optree.currentIndeces()
            
            if ii>0:
                ii-=1
                
                if self.design !=None:
                    try:
                        operationgeometries = self.design.operations[ii].output[jj].generic_geometry_2d()
                        for layer in self.design.layerdef().layers:
                            operationgeometry = operationgeometries[layer]
                            for item in operationgeometry:
                                newitem = item.outputstatic(color = layer.color)
                                self.scene.addItem(newitem)        
                    except AttributeError:
                        pass        
                    self.scene.controllines = self.design.loadcontrollines(ii,jj)
                    self.scene.controlpoints= self.design.loadcontrolpoints(ii,jj)
        
    def group(self):
        from popupcad.graphics2d.grouper import Grouper
        o = Grouper()        
        o.addchildren(self.scene.selectedItems())
        self.scene.addItem(o)
        

    def ungroup(self):
        from popupcad.graphics2d.grouper import Grouper
        for item in self.scene.selectedItems():
            if isinstance(item,Grouper):
                item.removegroupeditems()
                item.softdelete()
            
if __name__ == "__main__":
    app = qg.QApplication(sys.argv)
    mw = Sketcher(None,Sketch())
    mw.show()
    mw.raise_()
    sys.exit(app.exec_())        