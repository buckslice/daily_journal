import os
import sys
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import QSizePolicy

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import random
import functools

configPath = 'config.txt'

class JournalWindow(QtWidgets.QMainWindow):
    def __init__(self, *args):
        QtWidgets.QMainWindow.__init__(self, *args)

        # init variables
        self.calendar = None
        self.curJournalDate = QtCore.QDate.currentDate()

        self.loadConfig()

        self.centralWidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.centralWidget)

        self.layout = QtWidgets.QVBoxLayout(self.centralWidget)

        self.setWindowTitle("Mary's Journals")
        self.setWindowFlags(QtCore.Qt.Window)
        self.resize(600,600)

        # setup menu
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('File')

        quitAction = QtWidgets.QAction('Save and Quit', self)
        quitAction.setShortcut('Ctrl+W') # Q wont work for some reason?
        quitAction.triggered.connect(self.closeApp)
        fileMenu.addAction(quitAction)

        journalAction = QtWidgets.QAction('Journal', self)
        journalAction.triggered.connect(self.openJournalFrame)
        menuBar.addAction(journalAction)

        analysisAction = QtWidgets.QAction('Analysis', self)
        analysisAction.triggered.connect(self.openAnalysisFrame)
        menuBar.addAction(analysisAction)

        self.optionsMenu = menuBar.addMenu('Options')

        menuBar.addMenu(self.optionsMenu)

        # delayed a bit so window has chance to open and draw
        self.journals = {} # dict from QDate to string, should also store flag for if it needs analysis later too
        self.metaDataByDate = {} # QDate to metadata list for each doc
        self.metaData = {} # metadata string to list of date and value tuples
        # qdate, to string of whole doc, list of metadata, and flag for metadata or maybe anotehr metadata dict.yaaaa!
        QtCore.QTimer.singleShot(500, self.loadJournals)


    def openSaveDialog(self):
        options = QtWidgets.QFileDialog.DontResolveSymlinks | QtWidgets.QFileDialog.ShowDirsOnly
        self.opts['saveLocation'] = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select the save folder for your journals', '', options)

    # loads all the journals into memory
    def loadJournals(self):
        # make sure save location is correctly specified and prompt if not
        notInOpts = 'saveLocation' not in self.opts 
        if notInOpts or not os.path.exists(self.opts['saveLocation']):
            msg = QtWidgets.QMessageBox()
            msg.setWindowTitle('Journal Folder not found!')
            if notInOpts:
                msg.setText('Please select where you want to save your journals.')
                msg.setIcon(QtWidgets.QMessageBox.Information)
            else:
                msg.setText("Can't find journal folder! Did it move?")
                msg.setIcon(QtWidgets.QMessageBox.Critical)

            msg.exec_()

            self.opts['saveLocation'] = ''
            while not os.path.exists(self.opts['saveLocation']):
                self.openSaveDialog()


        print(f'loading journals from folder at: {self.opts["saveLocation"]}')

        # load all files in that folder recursively
        # check for correct date by name (todo: or by creation date)
        files = self.getFilePaths(self.opts['saveLocation'])
        for file in files:
            n = os.path.split(file)[1]
            n = os.path.splitext(n)[0]
            parts = n.split('-')
            if len(parts) == 3:
                print(f'{n} correctly formatted')
                date = QtCore.QDate.fromString(''.join(parts), 'yyyyMMdd')
                with open(file,'r',errors="ignore") as f:
                    words = f.read()#.replace('\n',' ')

                if date in self.journals:
                    print('this is weird')
                    self.journals[date] = f'{self.journals[date]}\n{words}'
                else:
                    self.journals[date] = words
                
            else:
                print(f'{n} incorrectly formatted file name. should be yyyy-MM-dd')

        self.openJournalFrame()

    #finds abspath of all text files in rootDir (and subdirectories)
    def getFilePaths(self, rootDir='.'): # default to local dir
        files = []
        for dirpath, dirnames, filenames in os.walk(rootDir):
            for s in filenames:
                if s.endswith('.txt'):
                    files.append(os.path.join(os.path.abspath(dirpath),s))              
        return files
        
    def saveCurrentJournal(self):
        if not self.editor:
            return

        name = self.curJournalDate.toString('yyyy-MM-dd')
        fileName = os.path.join(self.opts['saveLocation'],f'{name}.txt')
        words = str(self.editor.toPlainText())
        if not words: # if editor is empty
            # delete journal file if it exists
            if os.path.exists(fileName):
                print(f'{name} is now empty, removing')
                os.remove(fileName)
            else: # just warn that no new journal is saved
                print(f'{name} empty journal, not saving')

            # remove from memory too
            if self.curJournalDate in self.journals:
                del self.journals[self.curJournalDate]
            return

        # update current entry in memory
        self.journals[self.curJournalDate] = words
        # save to journal folder
        with open(fileName, 'w') as file:
            print(f'{name} saving journal')
            file.write(words)

        # remove metaData entry so it gets regenerated next time
        if self.curJournalDate in self.metaDataByDate:
            del self.metaDataByDate[self.curJournalDate]


    def loadConfig(self):
        self.opts = {} # make sure values are always lists (makes things simpler)

        # setup defaults here
        self.opts['font'] = ['Helvetica', '14']
        self.opts['bgColor'] = ['255','255','255']
        self.opts['fgColor'] = ['0','0','0']
        self.opts['cartoonMode'] = ['False']

        if os.path.isfile(configPath):
            with open(configPath, 'r') as file:
                lines = file.readlines()
            lines = [line.strip() for line in lines]
            
            for line in lines:
                if line:
                    splits = line.split(':',1)
                    if len(splits) == 2:
                        ss = splits[1].split(',')
                        self.opts[splits[0]] = ss[0] if len(ss) == 1 else ss
                    else:
                        print('problem with the config file...')

            #print(self.opts)


    def saveConfig(self):
        with open(configPath, 'w') as file:
            for k,v in self.opts.items():
                if isinstance(v, list):
                    file.write(f'{k}:{",".join(str(x) for x in v)}\n')
                else:
                    file.write(f'{k}:{v}\n')

    def openCalendar(self):
        self.calendar = CalendarDateSelect(self, [d for d,w in self.journals.items()])
        self.calendar.show()

    def updateDate(self, date=None):
        if date:
            self.saveCurrentJournal()
            self.curJournalDate = date

        if self.curJournalDate in self.journals:
            self.editor.setPlainText(self.journals[self.curJournalDate])
        else:
            self.editor.setPlainText('')
        self.dateButton.setText(self.curJournalDate.toString('MMMM d, yyyy'))

        # calculate label string that tells you relation from journal to today
        dayDiff = QtCore.QDate.currentDate().daysTo(self.curJournalDate)
        dayStr = 'days' if abs(dayDiff) > 1 else 'day'
        if dayDiff == 0:
            ageStr = ' today'
        elif dayDiff < 0:
            ageStr = f' {-dayDiff} {dayStr} ago'
        elif dayDiff > 0:
            ageStr = f' {dayDiff} {dayStr} in the future?'
        self.ageLabel.setText(ageStr)

    def openJournalFrame(self):
        self.optionsMenu.clear()

        self.clearLayout(self.layout)

        self.editor = MyPlainTextEdit()

        # action for choosing new font
        fontAction = QtWidgets.QAction('Set Font', self)
        fontAction.triggered.connect(self.openFontWindow)
        self.optionsMenu.addAction(fontAction)

        # actions for changing editor colors
        self.bgColorAction = QtWidgets.QAction('Set BG', self)
        self.bgColorAction.triggered.connect(functools.partial(self.setEditorColor, True, True))
        self.optionsMenu.addAction(self.bgColorAction)
        self.fgColorAction = QtWidgets.QAction('Set FG', self)
        self.fgColorAction.triggered.connect(functools.partial(self.setEditorColor, False, True))
        self.optionsMenu.addAction(self.fgColorAction)

        hf = QtGui.QFont('Helvetica', 14)
        jlayout = QtWidgets.QVBoxLayout()
        hlayout = QtWidgets.QHBoxLayout()
        self.dateButton = QtWidgets.QPushButton('', font=hf)
        self.dateButton.clicked.connect(self.openCalendar)
        hlayout.addWidget(self.dateButton)
        self.ageLabel = QtWidgets.QLabel('today', font=hf)
        hlayout.addWidget(self.ageLabel)
        hlayout.addStretch()

        jlayout.addLayout(hlayout)
        jlayout.addWidget(self.editor)

        self.layout.addLayout(jlayout)

        self.loadEditorSettings()
        self.updateDate()

    def openAnalysisFrame(self):
        self.saveCurrentJournal()
        self.editor = None # kinda filth but whatever
        self.optionsMenu.clear()
        self.clearLayout(self.layout)
        
        self.cartoonAction = QtWidgets.QAction('Cartoon mode', self)
        self.cartoonAction.setCheckable(True)
        self.cartoonAction.setChecked(self.getOpt('cartoonMode'))
        self.optionsMenu.addAction(self.cartoonAction)

        # a figure instance to plot on
        self.figure = Figure()

        self.figure.set_tight_layout(True)
        
        self.canvas = FigureCanvas(self.figure)

        self.navToolBar = NavigationToolbar(self.canvas, self)

        # set the layout
        alayout = QtWidgets.QVBoxLayout()

        topLayout = QtWidgets.QHBoxLayout()
        plotButton = QtWidgets.QPushButton('Plot')
        plotButton.clicked.connect(self.plotWithOptions)
        topLayout.addWidget(plotButton)

        self.ccb = CheckableComboBox()
        #ccb.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum))
        #ccb.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        #ccb.adjustSize()
        #ccb.resize(200,30)
        self.ccb.setMinimumSize(100,20)

        topLayout.addWidget(self.ccb)

        topLayout.addStretch()
        alayout.addLayout(topLayout)

        alayout.addWidget(self.navToolBar)
        alayout.addWidget(self.canvas)

        self.layout.addLayout(alayout)

        # make sure metadata is up to date
        self.updateMetaDataByDate()


    def findMetaData(self, document):
        data = [] # list of tuples as (TAG, value)
        for line in document.split('\n'):
            t = line.split(':')
            # will ignore things after a second colon
            if len(t) >= 2 and t[0].isupper():
                data.append((t[0],t[1]))
        return data

    # rebuilds dictionary of metadata to list of tuples of date and values
    def rebuildMetaData(self):
        self.metaData = {}
        for date, data in self.metaDataByDate.items():
            for tag,val in data:
                if tag not in self.metaData:
                    self.metaData[tag] = [(date,val)]
                else:
                    self.metaData[tag].append((date,val))

        # update combo box with list of tags
        self.ccb.clear()
        tags = []
        for tag, data in self.metaData.items():
            tags.append(tag)
        tags.sort()
        # setup everything as unchecked
        for i,tag in enumerate(tags):
            self.ccb.addItem(tag)
            item = self.ccb.model().item(i, 0)
            item.setCheckState(QtCore.Qt.Unchecked)

    def updateMetaDataByDate(self):
        newCount = 0
        for date,doc in self.journals.items():
            if date not in self.metaDataByDate:
                newCount += 1
                data = self.findMetaData(doc)
                self.metaDataByDate[date] = data
        if newCount > 0:
            self.rebuildMetaData()
        print(f'{newCount} new metadatas')


    def plotWithOptions(self):
        isChecked = self.cartoonAction.isChecked()
        self.opts['cartoonMode'] = f'{isChecked}'
        if isChecked:
            with plt.xkcd():
                self.plot()
        else:
            self.plot()

    # checks if each value in list can be cast as a number
    def isPlottable(self, tagList):
        for t in tagList:
            try:
                float(t[1]) # second part of tuple is value
                continue
            except ValueError:
                return False
        return True

    # plot each tag
    def plot(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        # give non abbreviated date when hovering
        ax.fmt_xdata = mdates.DateFormatter('%Y-%m-%d')

        # find all checked tags in the combo box
        tags = []
        for i in range(self.ccb.count()):
            item = self.ccb.model().item(i,0)
            if item.checkState() == QtCore.Qt.Checked:
                tag = self.ccb.itemText(i)
                tags.append(tag)

        for tag in tags:
            # make sure tag has metaData
            if tag not in self.metaData:
                print(f"Error: tag '{tag}' not found!")
                continue
            tagList = self.metaData[tag]
            # make sure tag is plottable
            if not self.isPlottable(tagList):
                print(f"Error: tag '{tag}' contains non numeric values, can't plot")
                continue

            tagList.sort() #sorts by date

            # separate tuples into x and y lists
            xd = [QtCore.QDateTime(t[0]).toPyDateTime() for t in tagList]                
            yd = [float(t[1]) for t in tagList]      

            ax.plot(xd, yd, '-o', label=tag)

        ax.set_xlabel('Date')

        # testing out some other plot options
        #self.figure.autofmt_xdate()
        #self.figure.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        #self.figure.legend('bottom left')
        #ax.set_title('hello there i am a test')
        #ypad = 1.2 if self.getOpt('cartoonMode') else 1.1
        #ax.legend(loc='upper center', bbox_to_anchor=(0.5, ypad), ncol=4)
        
        ax.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3, ncol=4, borderaxespad=0.) #mode='expand'
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=25)#, ha='right')
        self.canvas.draw()

    # deserialize option from its string form and return correct type object
    def getOpt(self, opt):
        od = self.opts[opt]
        if opt == 'font':
            return QtGui.QFont(od[0], int(od[1]))
        elif opt == 'bgColor' or opt == 'fgColor':
            c = [int(col) for col in od]
            return QtGui.QColor(c[0],c[1],c[2])
        elif opt == 'cartoonMode':
            return od == 'True'
        else:
            print(f'unknown opt: {opt}!')

    # opens a font selection dialog
    def openFontWindow(self):
        font,valid = QtWidgets.QFontDialog.getFont(self.getOpt('font'))
        if valid:
            self.editor.setFont(font)
            self.opts['font'] = [font.family(), font.pointSize()]

    def loadEditorSettings(self):
        self.editor.setFont(self.getOpt('font'))
        self.setEditorColor(True,False)
        self.setEditorColor(False,False)

    def setEditorColor(self, isBg, prompt):
        optStr = 'bgColor' if isBg else 'fgColor'
        color = self.getOpt(optStr)
        # if prompt then get a new color from a dialog
        if prompt:
            promptStr = f'Select {"background color" if isBg else "foreground color"}'
            color = QtWidgets.QColorDialog.getColor(color, self.parentWidget(), promptStr)
            if not color.isValid():
                return
        # set an icon with the color next to the menu action
        pixmap = QtGui.QPixmap(QtCore.QSize(16, 16))
        pixmap.fill(color)
        action = self.bgColorAction if isBg else self.fgColorAction
        action.setIcon(QtGui.QIcon(pixmap))
        # apply the color to the editor
        self.opts[optStr] = [color.red(), color.green(), color.blue()]
        vp = self.editor.viewport()
        p = vp.palette()
        p.setColor((vp.backgroundRole() if isBg else vp.foregroundRole()), color)
        vp.setPalette(p)

    # clears all widgets and layouts from the given layout
    def clearLayout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.layout():
                self.clearLayout(child.layout())
            elif child.widget():
                child.widget().deleteLater()

    def closeApp(self):
        self.close() # so close event is triggered

    # triggered when app is closed, this saves everything
    def closeEvent(self, e):
        if self.calendar:
            self.calendar.close()
        self.saveCurrentJournal()
        self.saveConfig()
        print('goodbye!!!')


# slightly modified version of normal widget to have tabs insert 4 spaces instead
class MyPlainTextEdit(QtWidgets.QPlainTextEdit):
    def __init__(self, *args):
        QtWidgets.QPlainTextEdit.__init__(self, *args)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Tab:
            self.insertPlainText('    ')
            event.accept()
        else:
            QtWidgets.QPlainTextEdit.keyPressEvent(self, event)

# little popup window with calendar and button to open the journal at selected date
# also highlights dates that have journal entries
class CalendarDateSelect(QtWidgets.QFrame):
    def __init__(self, window, journalDates, *args):
        QtWidgets.QFrame.__init__(self, *args)

        self.setWindowTitle('Select Journal Date')

        self.layout = QtWidgets.QVBoxLayout(self)
        self.cal = QtWidgets.QCalendarWidget()

        form = QtGui.QTextCharFormat()
        form.setBackground(QtGui.QColor(0,255,0))
        for date in journalDates:
            self.cal.setDateTextFormat(date, form)

        self.layout.addWidget(self.cal)

        self.doneButton = QtWidgets.QPushButton('Open Journal')
        self.doneButton.clicked.connect(self.returnDate)
        self.layout.addWidget(self.doneButton)

        self.window = window

        g = self.window.geometry()
        self.move(g.x() + 100, g.y() + 100)

    def returnDate(self):
        self.window.updateDate(self.cal.selectedDate())
        self.close()

# combo box where you can select multiple options at once
class CheckableComboBox(QtWidgets.QComboBox):
    def __init__(self):
        super(CheckableComboBox, self).__init__()
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QtGui.QStandardItemModel(self))

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.checkState() == QtCore.Qt.Checked:
            item.setCheckState(QtCore.Qt.Unchecked)
        else:
            item.setCheckState(QtCore.Qt.Checked)

# ColorButton from formlayout.py in matplotlib was cool
# spellcheck ? https://stackoverflow.com/questions/8722061/pyqt-how-to-turn-on-off-spellchecking

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    main = JournalWindow()
    main.show()

    sys.exit(app.exec_())