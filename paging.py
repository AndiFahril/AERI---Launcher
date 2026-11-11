from PySide6.QtCore import Qt,Signal,QPoint,QPropertyAnimation,QParallelAnimationGroup,QEasingCurve
from PySide6.QtWidgets import QWidget,QGridLayout,QLayout

class AppPage(QWidget):
    COLUMNS=4
    ROWS=3
    CARD_HEIGHT=120
    GAP=14
    SIDE_MARGIN=2
    def __init__(self):
        super().__init__();self.setObjectName('appPage')
        self.grid=QGridLayout(self);self.grid.setContentsMargins(self.SIDE_MARGIN,0,self.SIDE_MARGIN,0);self.grid.setHorizontalSpacing(self.GAP);self.grid.setVerticalSpacing(self.GAP)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.grid.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        for row in range(self.ROWS):self.grid.setRowMinimumHeight(row,self.CARD_HEIGHT)
    def resizeEvent(self,event):
        super().resizeEvent(event);self.equalize_columns()
    def equalize_columns(self):
        width=max(0,self.width()-(self.SIDE_MARGIN*2)-(self.GAP*(self.COLUMNS-1)))
        base,remainder=divmod(width,self.COLUMNS)
        # Avoid fractional geometry: the few spare pixels are assigned left to right.
        widths=[base+(1 if col<remainder else 0) for col in range(self.COLUMNS)]
        for col,value in enumerate(widths):self.grid.setColumnMinimumWidth(col,value)
        for index in range(self.grid.count()):
            row,col,rows,cols=self.grid.getItemPosition(index);widget=self.grid.itemAt(index).widget()
            if widget is not None and cols==1:widget.setFixedWidth(widths[col])

class SlidePages(QWidget):
    changed=Signal(int)
    swipe=Signal(int)
    def __init__(self):
        super().__init__()
        self.setObjectName('pageHost');self.setMinimumHeight(388)
        self.pages=[];self.current_index=0;self.animation=None;self.origin=None
    def replace(self,pages):
        self.finish()
        for page in self.pages:page.hide();page.deleteLater()
        self.pages=pages;self.current_index=0
        for index,page in enumerate(pages):
            page.setParent(self);page.setGeometry(self.rect());page.setVisible(index==0)
        self.changed.emit(0)
    def finish(self):
        if self.animation is not None:
            self.animation.stop();self.animation.deleteLater();self.animation=None
        for index,page in enumerate(self.pages):
            page.setGeometry(self.rect());page.setVisible(index==self.current_index)
    def go(self,index,animate=True):
        if self.animation is not None or not 0<=index<len(self.pages) or index==self.current_index:return False
        previous=self.current_index;self.current_index=index
        if not animate:
            self.finish();self.changed.emit(index);return True
        width=self.width();direction=1 if index>previous else -1
        old,new=self.pages[previous],self.pages[index]
        old.setGeometry(self.rect());new.setGeometry(self.rect());new.move(direction*width,0)
        old.show();new.show();new.raise_()
        group=QParallelAnimationGroup(self)
        for page,start,end in ((old,QPoint(0,0),QPoint(-direction*width,0)),
                               (new,QPoint(direction*width,0),QPoint(0,0))):
            animation=QPropertyAnimation(page,b'pos',group);animation.setDuration(220)
            animation.setStartValue(start);animation.setEndValue(end)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic);group.addAnimation(animation)
        self.animation=group
        group.finished.connect(self.finish);group.start();self.changed.emit(index);return True
    def resizeEvent(self,event):
        super().resizeEvent(event);self.finish()
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self.origin=event.position().toPoint()
    def mouseReleaseEvent(self,event):
        if self.origin is not None:
            delta=event.position().toPoint()-self.origin;self.origin=None
            if abs(delta.x())>=60 and abs(delta.x())>abs(delta.y()):self.swipe.emit(1 if delta.x()<0 else -1)
