#!/usr/bin/env python3

import sys
import os
import random

from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox, QFileDialog, QLabel, QPushButton, \
                            QLineEdit, QHBoxLayout, QVBoxLayout, QGridLayout, QCheckBox, QAction, QProgressBar
from PyQt5.QtGui import QIcon
from PyQt5.Qt import Qt
from PyQt5.QtCore import QThread, pyqtSignal

from PIL import Image
from PIL import ImageChops
from PIL import ImageEnhance

__author__ = "Ty Phillips"
__copyright__ = "Copyright 2018"
__version__ = "0.1 Beta"

class DoubleX(QWidget):
	"""Main widget for Double Exposure Creator."""
	def __init__(self):
		super().__init__()

		self.initUI()

	def initUI(self):

		self.setWindowTitle("Double Exposure Creator " + __version__)
		#self.setWindowIcon(QIcon('doublex.png'))

		self.lblDir1 = QLabel()
		self.lblDir2 = QLabel()
		self.lblOutDir = QLabel()
		self.lblDir1.setText("Directory 1")
		self.lblDir2.setText("Directory 2")
		self.lblOutDir.setText("Output Directory")

		self.txtDir1 = QLineEdit()
		self.txtDir2 = QLineEdit()
		self.txtOutDir = QLineEdit()
		self.txtDir1.setFixedWidth(500)
		self.txtDir2.setFixedWidth(500)
		self.txtOutDir.setFixedWidth(500)

		self.btnBrowse1 = QPushButton("Browse")
		self.btnBrowse2 = QPushButton("Browse")
		self.btnBrowse3 = QPushButton("Browse")
		self.btnBrowse1.setObjectName('Browse1')
		self.btnBrowse2.setObjectName('Browse2')
		self.btnBrowse3.setObjectName('Browse3')

		self.progress = QProgressBar()
		self.progress.setGeometry(0, 0, 300, 25)
		self.progress.setMaximum(100)

		self.chkResize = QCheckBox("Resize")
		self.chkConvertGS = QCheckBox("Convert to greyscale")

		self.btnExecute = QPushButton("Execute")
		self.btnExit = QPushButton("Exit")

		self.txtDir1.textChanged.connect(self.refreshControls)
		self.txtOutDir.textChanged.connect(self.refreshControls)
		self.btnBrowse1.clicked.connect(self.browseClicked)
		self.btnBrowse2.clicked.connect(self.browseClicked)
		self.btnBrowse3.clicked.connect(self.browseClicked)
		self.btnExecute.clicked.connect(self.createImages)
		self.btnExit.clicked.connect(self.exitProgram)

		self.refreshControls()

		# Upper layout box
		ubox = QGridLayout()
		ubox.addWidget(self.lblDir1, 0, 0)
		ubox.addWidget(self.txtDir1, 0, 1)
		ubox.addWidget(self.btnBrowse1, 0, 2)
		ubox.addWidget(self.lblDir2, 1, 0)
		ubox.addWidget(self.txtDir2, 1, 1)
		ubox.addWidget(self.btnBrowse2, 1, 2)
		ubox.addWidget(self.lblOutDir, 2, 0)
		ubox.addWidget(self.txtOutDir, 2, 1)
		ubox.addWidget(self.btnBrowse3, 2, 2)

		# Normalize column widths
		ubox.setColumnStretch(1, 10)

		# Lower layout box
		lbox = QHBoxLayout()
		lbox.addWidget(self.chkResize)
		lbox.addWidget(self.chkConvertGS)
		lbox.addWidget(self.btnExecute)
		lbox.addWidget(self.btnExit)

		box = QVBoxLayout()
		box.addLayout(ubox)
		box.addWidget(self.progress)
		box.addLayout(lbox)
		self.setLayout(box)
		self.show()

	def refreshControls(self):
		"""Update UI controls based on current UI state."""
		if os.path.exists(self.txtDir1.text()) and os.path.exists(self.txtOutDir.text()):
			self.btnExecute.setEnabled(True)
		else:
			self.btnExecute.setEnabled(False)

	def browseClicked(self):
		"""Populate appropriate directories, depending on which Browse button was clicked."""
		whoClicked = self.sender().objectName()

		if whoClicked == 'Browse1':
			self.txtDir1.setText(QFileDialog.getExistingDirectory(self, "Select Directory"))
		elif whoClicked == 'Browse2':
			self.txtDir2.setText(QFileDialog.getExistingDirectory(self, "Select Directory"))
		elif whoClicked == 'Browse3':
			self.txtOutDir.setText(QFileDialog.getExistingDirectory(self, "Select Directory"))
		else:
			pass

	def createImages(self):
		"""Create the actual double exposed images based on the specified folders."""
		# First generate a list of random image pairs
		filepairs = self.generateImagePairs()
		self.thread = ImageCombine(filepairs, self.txtOutDir.text(), self.chkResize.isChecked(), self.chkConvertGS.isChecked())
		self.thread.start()
		self.thread.progress.connect(self.updateProgress)
		self.thread.finished.connect(self.actionCompleted)

	def updateProgress(self, value):
		self.progress.setValue(value)

	def actionCompleted(self):
		QMessageBox.information(self, "Message", "Action completed")
		self.progress.reset()

	def generateImagePairs(self):
		"""First generate a list of random image pairs."""
		filelist1 = []
		filelist2 = []

		for filename in os.listdir(self.txtDir1.text()):
			if filename.upper().endswith(".JPG") or filename.upper().endswith(".JPEG"):
				filelist1.append(os.path.join(self.txtDir1.text(), filename))

		for filename in os.listdir(self.txtDir2.text()):
			if filename.upper().endswith(".JPG") or filename.upper().endswith(".JPEG"):
				filelist2.append(os.path.join(self.txtDir2.text(), filename))

		# First filelist should be shorter or the same length as the second list
		#   Swap lists if first one is longer
		if len(filelist1) > len(filelist2):
			tmplist = filelist2
			filelist2 = filelist1
			filelist1 = tmplist

		filepairs = []

		# Create list of file pairs, with each pair itself a list
		for i in range(len(filelist1)):
			file1 = filelist1.pop(random.randint(0, len(filelist1)-1))	# Remove a random file from the list
			file2 = filelist2.pop(random.randint(0, len(filelist2)-1))	# Pair it with a random file from the second list
			filepairs.append([file1, file2])

		return filepairs

	def exitProgram(self):
		sys.exit()


class ImageCombine(QThread):
	"""Thread object for combining image pairs."""
	progress = pyqtSignal(int)

	def __init__(self, filepairs, outdir, resize=False, convertGS=False):
		QThread.__init__(self)	#TODO replace this with super()
		self.filepairs = filepairs
		self.outdir = outdir
		self.resize = resize
		self.convertGS = convertGS

	def run(self):
		"""Create the combination images."""
		for index, pair in enumerate(self.filepairs):
			if self.convertGS:
				img1 = Image.open(pair[0]).convert('L')
				img2 = Image.open(pair[1]).convert('L')
			else:
				img1 = Image.open(pair[0])
				img2 = Image.open(pair[1])

			if self.resize:
				# Resize to 20% of longest dimension of smaller
				newsize = min(max(img1.size), max(img2.size))
				newsize /= 5
				img1.thumbnail((newsize, newsize), Image.ANTIALIAS)
				img2.thumbnail((newsize, newsize), Image.ANTIALIAS)
				
			enhancer1 = ImageEnhance.Brightness(img1)
			enhancer2 = ImageEnhance.Brightness(img2)

			# Output filename format "file1_file2.JPG" where 'file1' and 'file2' are the file name, sans extension
			outfname = os.path.splitext(os.path.basename(pair[0]))[0]
			outfname += "_"
			outfname += os.path.basename(pair[1])

			img3 = ImageChops.add(enhancer1.enhance(0.5), enhancer2.enhance(0.5))

			img3.save(os.path.join(self.outdir, outfname))

			# Send calculated progress to progress bar
			self.progress.emit((index+1) * 100 / len(self.filepairs))


if __name__ == '__main__':
	app = QApplication(sys.argv)
	win = DoubleX()
	sys.exit(app.exec())

