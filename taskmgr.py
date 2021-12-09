#!/usr/bin/python3

#TaskManager2
#v0.5
#License -- GPL v3
#(c) Anirban Banerjee 2021

import wx
import os
from os import path
import sys
import traceback
import re
import time
import wx.adv
import threading

_daysInMonths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
_months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
			'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
			'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
_WMYs = {'Days': 'd', 'Weeks': 'w', 'Months': 'm', 'Years': 'y'}
_my = ['m', 'y']
_wmy = ['d', 'w', 'm', 'y']
_days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
_weekdays = { 'Sunday': 'sun', 'Monday': 'mon', 'Tuesday': 'tue', 'Wednesday': 'wed', 
				'Thursday': 'thu', 'Friday': 'fri', 'Saturday': 'sat'}
_wds = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'day']
_WMY = {'Day': 'd', 'Week': 'w', 'Month': 'm', 'Year': 'y'}
_recurSpanUnitList = ['Days', 'Weeks', 'Months', 'Years']
_priorityList = ['None', '(A)', '(B)', '(C)', '(D)', '(E)', '(F)']
_recurrenceTypeList = ['None', 'Span', 'Day', 'Last day']
_recurDayUnitList = ['Month', 'Year']
_recurDayList = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Day']
		
_DEBUG_ENABLE = 3

def _DEBUG2 (*args):
	if _DEBUG_ENABLE == 2:
		print (*args)

def _DEBUG1 (*args):
	if _DEBUG_ENABLE == 1:
		print (*args)

def _DEBUG (*args):
	if _DEBUG_ENABLE < 1:
		print (*args)

def _getZoneHour():
	return abs(time.timezone/3600)

def _makeDateForTodo (asctime):
	#print ("_makeDateForTodo: asctime = ", asctime)
	match = re.match(r'^...\s(...)\s+([0-9]{1,})\s\S+\s([0-9]{4})', asctime) #'Tue Nov  2 20:01:51 2021'
	dd = mm = yyyy = ''
	if match:
		#print (match.group(1), " ", match.group(2), " ", match.group(3))
		dd = match.group(2)
		mm = str(_months.index(match.group(1).lower()) + 1)
		if len(mm) == 1:
			mm = '0'+mm
		if len(dd) == 1:
			dd = '0'+dd
		yyyy = match.group(3)
		return yyyy+'-'+mm+'-'+dd
	else:
		return None

def _makeDateForSystem (dd, mm, yyyy, zoneHour):
	day = _days[_day(dd, mm, yyyy, zoneHour)]
	month = _MONTHS[mm-1]
	date = str(dd)
	if dd < 10:
		date = ' ' + date
	return f'{day} {month} {date} 00:00:00 ' + str(yyyy)

def _timeScaleAtMidnight (todoDate, zoneHour=5.5):
	#timescale at midnight
	#https://stjarnhimlen.se/comp/ppcomp.html#3
	#The time scale in these formulae are counted in days. 
	#Hours, minutes, seconds are expressed as fractions of a day. 
	#Day 0.0 occurs at 2000 Jan 0.0 UT (or 1999 Dec 31, 24:00 UT). 
	#This "day number" d is computed as follows (y=year, m=month, D=date, 
	#UT=UT in hours+decimals):

	#d = 367*yyyy \
	#	- 7 * ( yyyy + (mm+9)/12 ) / 4 \
	#	- 3 * ( ( yyyy + (mm-9)/7 ) / 100 + 1 ) / 4 \
	#	+ 275*mm/9 + dd - 730515

	match = re.match(r'^([0-9]{4})\-([0-9]{1,2})\-([0-9]{1,2})', todoDate)
	if match == None:
		return None

	d = int(match.group(3))
	m = int(match.group(2))
	y = int(match.group(1))

	d = 367*y \
		- 7 * ( y + (m+9)//12 ) // 4 \
		- 3 * ( ( y + (m-9)//7 ) // 100 + 1 ) // 4 \
		+ 275*m//9 + d - 730515
	
	return d - zoneHour/24.0 #add 2451543.5 to get Julian Date

def _day (todoDate, zoneHour=5.5):
	d = _timeScaleAtMidnight(todoDate, zoneHour)
	d += (zoneHour/24.0)
	index = int((d+5)%7)
	return index

def _dateDifference (tdA, tdB):
	_DEBUG ("_dateDifference ~~~ tdA = ", tdA, "~~~ tdB = ", tdB)
	if tdA == '' or tdB == '':
		return None
	#returns time scale tdA - time scale tdB
	return _timeScaleAtMidnight(tdA) - _timeScaleAtMidnight(tdB)

def _firstTodoDateIsEarlier (tdA, tdB):
	_DEBUG ("_firstTodoDateIsEarlier ~~~ tdA = ", tdA, "~~~ tdB = ", tdB)
	if tdA == '' or tdB == '':
		return True
	#returns True is tdA is earlier than tdB
	return _dateDifference (tdA, tdB) < 0

def _isLeapYear (year):
	if year % 400 == 0:
		return True
	elif year % 100 == 0:
		return False
	elif year % 4 == 0:
		return True
	else:
		return False

def _resolveRecurrenceType2 (todoDate, 
				recurrenceType2Nth = '', 
				recurrenceType2Day = '', 
				recurrenceType2Unit = ''):

	_DEBUG ("******* _resolveRecurrenceType2: ", todoDate, recurrenceType2Nth, recurrenceType2Day, recurrenceType2Unit)
	nextDate = todoDate
	match = re.match(r'^([0-9]{4})\-([0-9]{1,2})\-([0-9]{1,2})', todoDate)
	if match:
		yyyy = match.group(1)
		mm = match.group(2)
		dd = match.group(3)

	if recurrenceType2Unit == 'm':
		#what was the day for the first of the todoDate month
		#print (" date of first day = ", yyyy+'-'+mm+'-01')
		firstDayIndex = _day(yyyy+'-'+mm+'-01', _getZoneHour())
		#print (" %%% todoDate = ", todoDate)
		
		if recurrenceType2Day == 'day':
			nthDay = 1
			dateOf1stOccurrence = int(recurrenceType2Nth)
		else:
			whichDayIndex = _wds.index(recurrenceType2Day)

			diff = whichDayIndex - firstDayIndex
			if diff < 0:
				diff += 7

			dateOf1stOccurrence = 1 + diff
			daysInMonth = _daysInMonths[int(mm)-1] 

			#print (" %%% whichDayIndex = ", whichDayIndex)
			#print (" %%% firstDayIndex = ", firstDayIndex)
			#print (" %%% diff = ", diff)
			#print (" %%% daysInMonth = ", daysInMonth)
			#print (" %%% todoDate = ", todoDate, " Day 1 falls on ", _wds[firstDayIndex])
			#print (" %%% dateOf1stOccurrence = ", dateOf1stOccurrence, " we are looking for ", recurrenceType2Nth, "th ", recurrenceType2Day)

		if recurrenceType2Nth in 'lL':
			nthDay = 4
			if daysInMonth == 29:
				#the day of 1st of this month will repeat 5 times
				if whichDayIndex == firstDayIndex:
					nthDay = 5
			elif daysInMonth == 30:
				#the day of 1st and 2nd of this month will repeat 5 times
				if whichDayIndex in (firstDayIndex, firstDayIndex+1):
					nthDay = 5
			elif daysInMonth == 31:
				#the day of 1st, 2nd and 3rd of this month will repeat 5 times
				if whichDayIndex in (firstDayIndex, firstDayIndex+1, firstDayIndex+2):
					nthDay = 5
			else:
				# 28 days. All days of the week will occur 4 times
				nthDay = 4
		elif recurrenceType2Day != 'day':
			#print ("#### recurrenceType2Nth = ", recurrenceType2Nth)
			nthDay = int(recurrenceType2Nth)

		date = (nthDay - 1) * 7 + dateOf1stOccurrence
		nextDate = yyyy+'-'+mm+'-'+(str(date) if date > 9 else '0'+str(date))
		#print ("_resolveRecurrenceType2 %%% A. nextDate = ", nextDate)

	elif recurrenceType2Unit == 'y':
		_DEBUG (" %%% recurrenceType2Unit = ", recurrenceType2Unit)
		_DEBUG (" date of first day of the year = ", yyyy+'-01-01')
		firstDayIndex = _day(yyyy+'-01-01', _getZoneHour())
		
		whichDayIndex = _wds.index(recurrenceType2Day)

		diff = whichDayIndex - firstDayIndex
		if diff < 0:
			diff += 7

		dateOf1stOccurrence = 1 + diff
		daysInMonth = _daysInMonths[int(mm)-1] 

		if recurrenceType2Nth in 'lL':
			nthDay = 52
			if _isLeapYear (int(yyyy)):
				#in a leap year, 365th and 366th days will have 53 occurrences
				if whichDayIndex in (firstDayIndex, firstDayIndex+1):
					nthDay = 53
			else:
				if whichDayIndex == firstDayIndex:
					nthDay = 53
				else:
					nthDay = 52
		else:
			_DEBUG ("#### recurrenceType2Nth = ", recurrenceType2Nth)
			nthDay = int(recurrenceType2Nth)

		date = (nthDay - 1) * 7 + dateOf1stOccurrence
		month = 0
		for e in _daysInMonths:
			if date <= e:
				break
			date -= e
			month += 1

		month += 1 #January is 1
		nextDate = yyyy+'-'+(str(month) if month > 9 else '0'+str(month))+'-'+(str(date) if date > 9 else '0'+str(date))
		if todoDate != '':
			if _firstTodoDateIsEarlier(nextDate, todoDate):
				nextDate = str(int(yyyy)+1)+'-'+(str(month) if month > 9 else '0'+str(month))+'-'+(str(date) if date > 9 else '0'+str(date))
				
		_DEBUG ("_resolveRecurrenceType2 %%% B. nextDate = ", nextDate)

	_DEBUG ("_resolveRecurrenceType2 %%% returning with nextDate = ", nextDate)
	#print()
	#print()
	return nextDate

def _nextDate(todoDate, recurrenceCount = '', 
				recurrenceUnit = '',
				recurrenceType2Nth = '', 
				recurrenceType2Day = '', 
				recurrenceType2Unit = ''):

	_DEBUG1 ("\n======NEXT DATE======\n")
	nextDate = todoDate
	match = re.match(r'^([0-9]{4})\-([0-9]{1,2})\-([0-9]{1,2})', todoDate)
	if match:
		yyyy = match.group(1)
		mm = match.group(2)
		dd = match.group(3)

	#print ("recurrenceUnit = ", recurrenceUnit)
	if recurrenceUnit == 'm':
		newmm = (int(mm) - 1 + int(recurrenceCount))
		yyyyInt = int(yyyy) + newmm//12
		newmm = newmm % 12 + 1
		newmmStr = str(newmm)
		if newmm < 10:
			newmmStr = '0' + newmmStr
		yyyy = str(yyyyInt)
		ddInt = int(dd)
		if not _isLeapYear (yyyyInt) and newmm == 2 and ddInt >= 29:
			dd = '28'
		elif ddInt > _daysInMonths[newmm - 1]:
			dd = str(_daysInMonths[newmm - 1])
		if len(dd) == 1:
			dd = '0'+dd
		#print ("newmm = ", newmm)
		#print ("yyyyInt = ", yyyyInt)
		nextDate = yyyy+'-'+newmmStr+'-'+dd
	elif recurrenceUnit == 'd':
		i = int(mm) - 1
		newdd = (int(dd) + int(recurrenceCount))
		cumuDays = 0
		monthCount = 0
		_daysInMonthsLocal = []
		y = int(yyyy)
		for e in _daysInMonths:
			_daysInMonthsLocal.append(e)
		if i >= 2:
			#current month is March or later, will spill into next year's Feb
			#find out if next year is leap
			if _isLeapYear (y+1):
				_daysInMonthsLocal[1] = 29
		else:
			#current month is Jan or Feb, find out if current year is leap
			if _isLeapYear (y):
				_daysInMonthsLocal[1] = 29
		for e in (_daysInMonthsLocal[i:] + _daysInMonthsLocal[0:i]):
			newdd -= e
			if newdd <= 0:
				newdd += e
				break 
			monthCount += 1
		dd = str(newdd)
		if i+monthCount >= 12:
			yyyy = str(y+1)

		monthCount = ((i+monthCount) % 12) + 1
		nextDate = yyyy+'-'+(str(monthCount) if monthCount > 9 else '0'+str(monthCount))+'-'+dd

	elif recurrenceUnit == 'y':
		recurrenceCountInt = int(recurrenceCount)
		newyyyy = int(yyyy) + recurrenceCountInt
		if int(mm) == 2 and dd == '29':
			if not _isLeapYear(newyyyy):
				#current date is on a leap year and
				#recurrence occurs on a non-leap year 
				dd = '28'
		nextDate = str(newyyyy)+'-'+mm+'-'+dd

	elif recurrenceType2Unit == 'm':
		#set todoDate to first of next month and
		#resolve date
		if int(mm) + 1 > 12:
			mm = '01'
			yyyy = str(int(yyyy) + 1)
		
		nextDate = _resolveRecurrenceType2 (yyyy+'-'+mm+'-01', recurrenceType2Nth, 
					recurrenceType2Day, recurrenceType2Unit)

	elif recurrenceType2Unit == 'y':
		#set todoDate to first of January of next year and
		#resolve date
		yyyy = str(int(yyyy) + 1)
		
		nextDate = _resolveRecurrenceType2 (yyyy+'-01-01', recurrenceType2Nth, 
					recurrenceType2Day, recurrenceType2Unit)

	#print ("_nextDate %%% returning with nextDate = ", nextDate)
	#print ("===========")
	return nextDate

def _validate (date):
	dd = mm = yyyy = 0
	match = re.match(r'^([0-9]{4})\-([0-9]{1,2})\-([0-9]{1,2})', date)
	if date == '':
		#null date
		return True
	
	if match:
		yyyy = int(match.group(1))
		mm = int(match.group(2))
		dd = int(match.group(3))
	if mm < 1 or mm > 12:
		#print (date, " failed A !! mm = ", mm)
		return False
	
	if dd > _daysInMonths[mm-1]:
		if _isLeapYear (yyyy) and mm == 2:
			if dd > 29:
				return False
				#print (date, " failed B !!")
		else:
			return False
			#print (date, " failed C !!")


	return True

class todo ():

	def __init__(self, todoFile="./todo.txt"):
		self.fileError = False
		self.todoFile = todoFile
		self.todoTasksTask = {}
		self.todoTasksDueDate = {}
		self.comments = []
		#print ("todo: init - self.todofile = ", self.todoFile)

		try:
			f = open(self.todoFile, mode='r', encoding='utf-8')
		except FileNotFoundError:
			print ("File ", self.todoFile, " not found.")
			self.fileError = True
			return

		for line in f:
			#print (line)
			line = line.strip('\n')
			line = line.strip()
			hasError = False
			completed = False
			allCompleted = False
			task = ''
			dueDate = ''
			priority = ''
			creationDate = ''
			completionDate = ''
			recurrenceCount = ''
			recurrenceUnit = ''
			recurrenceType2Nth = ''
			recurrenceType2Day = ''
			recurrenceType2Unit = ''
			projects = []
			contexts = []
			if line.find('x ') == 0:
				completed = True
				line = line[2:]
			elif line.find('#x ') == 0:
				allCompleted = True
				line = line[3:]
			elif line.find('#') == 0:
				self.comments.append(line)
				continue
			elif line.strip() == '':
				continue
			#print ("At end of parsing #: line = ", line)
		
			#extract all contexts starting with ' +'
			line += ' ' #the regex won't work without the extra space at end
			if line.find (' @') >= 0:
				match = re.match(r'(.*?) @(.*?)\s(.*)', line)
				while (match):
					contexts.append(match.group(2))
					line = match.group(1) + ' ' + match.group(3)
					#print ("Now line is ", line, " - contexts is ", contexts)
					match = re.match(r'(.*?) @(.*?)\s(.*)', line)

			#print ("At end of contexts: line = ", line)

			#extract all projects starting with ' +'
			line = line.strip() + ' '  #the regex won't work without the extra space at end
			#print ("At start of projects: line = ", line)
			if line.find (' +') >= 0:
				match = re.match(r'(.*?) \+(\S+?)\s(.*)', line)
				while (match):
					projects.append(match.group(2))
					line = match.group(1) + ' ' + match.group(3)
					#print ("Now line is ", line, " - projects is ", projects)
					match = re.match(r'(.*?) \+(\S+?)\s(.*)', line)

			#print ("At end of projects: line = ", line)
			#print ("At end of contexts: contexts = ", contexts)
			#print ("At end of projects: projects = ", projects)

			line = line.strip()
			match = re.match(r'^.*due:([0-9]{4})\-([0-9]{1,2})\-([0-9]{1,2}).*', line)
			if match:
				#redo after 0-extending months and days
				yyyy = match.group(1)
				mm = match.group(2)
				dd = match.group(3)
				if len(mm) == 1:
					mm = '0'+mm
				if len(dd) == 1:
					dd = '0'+dd
				dueDate = yyyy + '-' + mm + '-' + dd
		
			match = re.match(r'^.*rec:([0-9]{,})([d|w|m|y])', line)
			if match:
				recurrenceCount = match.group(1)
				if recurrenceCount == '': #'rec:m' is same as 'rec:1m'
					recurrenceCount = '1'
				recurrenceUnit = match.group(2)
				#print ("recurrenceCount match found for line ", line)
				if recurrenceUnit == 'd':
					if int(recurrenceCount) > 365:
						hasError = True
		
			match = re.match(r'^.*rec:([0-9|l|L]{1,3})\-(mon|tue|wed|thu|fri|sat|sun|day)\-(m|y)', line)
			if match:
				recurrenceType2Nth = match.group(1)
				recurrenceType2Day = match.group(2)
				recurrenceType2Unit = match.group(3)

				#recurrence Type 1 will be removed
				recurrenceCount = ''
				recurrenceUnit = ''
				#print ("recurrenceType2 match found for line ", line)
				#print (recurrenceType2Nth, recurrenceType2Day, recurrenceType2Unit)
		
			if completed == True or allCompleted == True:
				match = re.match(r'^(\([A-Z]\))?\s+([0-9]{4}\-[0-9]{1,2}\-[0-9]{1,2})?\s+([0-9]{4}\-[0-9]{1,2}\-[0-9]{1,2})?\s(.*)', line)
				if match:
					priority = match.group(1)
					completionDate = match.group(2)
					if priority == None:
						priority = ''
					creationDate = match.group(3)
					line = match.group(4)
					#print ("A. completed = ", completed, " priority matched is ", priority, " for line ", line, "creationDate = ", creationDate)
				else:
					match = re.match(r'^([0-9]{4}\-[0-9]{1,2}\-[0-9]{1,})?\s?([0-9]{4}\-[0-9]{1,2}\-[0-9]{1,2})?\s(.*)', line)
					if match:
						completionDate = match.group(1)
						creationDate = match.group(2)
						line = match.group(3)
					if creationDate == None:
						#is completion date is provided, creation date is must
						creationDate = ''
					#print ("B. completed = ", completed, " priority matched is ", priority, " for line ", line, "creationDate = ", creationDate, "completionDate = ", completionDate)
			else:
				match = re.match(r'^(\([A-Z]\))?\s*([0-9]{4}\-[0-9]{1,}\-[0-9]{1,})?\s*(.*)', line)
				if match:
					if match.group(1):
						priority = match.group(1)
					creationDate = match.group(2)
					if creationDate == None:
						creationDate = ''
					line = match.group(3)
					#print ("X. completed = ", completed, " priority matched is ", priority, " for line ", line, "creationDate = ", creationDate)
				else:
					match = re.match(r'^([0-9]{4}\-[0-9]{1,}\-[0-9]{1,})?\s*(.*)', line)
					if match:
						creationDate = match.group(1)
						line = match.group(2)
					
						#print ("Y. completed = ", completed, " priority matched is ", priority, " for line ", line, "creationDate = ", creationDate)

		
			#print ("=========\t\tnow line is ", line)
			match = re.match (r'(.*)\s+(due:|rec:)', line)
			#print ("Now matching due:|rec:")
			if match:
				#print ("-- due:|rec: match found")
				task = match.group(1)
				#might have matched /Task due:## rec:##/ or /Task due:##/ or /Task rec:##/
				#remove due:##
				match = re.match (r'(.*)\s+due:', task)
				if match:
					task = match.group(1)
			else:
				match = re.match (r'(.*)\s+(rec:|due:)', line)
				#print ("Now matching (rec:|due:)")
				if match:
					#print (" -- rec:|due: match found")
					task = match.group(1)
					match = re.match (r'(.*)\s+rec:', task)
					if match:
						task = match.group(1)
				else:
					#print ("matching creation date followed by task")
					match = re.match(r'^([0-9]{4}\-[0-9]{1,}\-[0-9]{1,})?\s+(.*)', line)
					if match:
						task = match.group(2)
					else:
						task = line
		
			match = re.match(r'^([0-9]{4})\-([0-9]{1,})\-([0-9]{1,})', completionDate)
			if match:
				yyyy, mm, dd = match.group(1), match.group(2), match.group(3)
				if len(mm) == 1:
					mm = '0'+mm
				if len(dd) == 1:
					dd = '0'+dd
				completionDate = yyyy + '-' + mm + '-' + dd

			#print ("Z. completed = ", completed, " priority matched is ", priority, " for line ", line, "creationDate = ", creationDate)
			match = re.match(r'^([0-9]{4})\-([0-9]{1,})\-([0-9]{1,})', creationDate)
			if match:
				yyyy, mm, dd = match.group(1), match.group(2), match.group(3)
				if len(mm) == 1:
					mm = '0'+mm
				if len(dd) == 1:
					dd = '0'+dd
				creationDate = yyyy + '-' + mm + '-' + dd

			if	completionDate != '' and (completed == False and allCompleted == False):
				#print ("completion error")
				hasError = True
				_DEBUG ("X. completion error with task = ", task)

		
			#print ("dueDate ", dueDate, " is good ", _validate(dueDate))
			#print ("completionDate ", completionDate, " is good ", _validate(completionDate))
			#print ("creationDate ", creationDate, " is good ", _validate(creationDate))
			if not _validate(dueDate) or not _validate(completionDate) or not _validate(creationDate):
				hasError = True
				_DEBUG ("Y. task validate error with task = ", task)
			#print ("creationDate ", creationDate, " validation returned ", _validate(creationDate))

			match = re.match(r'^([0-9]{4}\-[0-9]{1,}\-[0-9]{1,})', task)
			if match:
				_DEBUG ("Z. task check error with task = ", task)
				hasError = True
			
			duplicateEvent = False
			if task in self.todoTasksTask.keys():
				#duplicate events are not allowed
				#the previous task dict will be overwritten
				duplicateEvent = True

			if dueDate in self.todoTasksDueDate.keys() and duplicateEvent == False:
				#if the task is not a duplicate, the due date can still be duplicate
				#so, uniquify the due date
				dueDate += ' ' #append a space
				while dueDate in self.todoTasksDueDate.keys():
					dueDate += ' '

			self.todoTasksDueDate[dueDate] = task
			self.todoTasksTask[task] = (dueDate, hasError, completed, completionDate, allCompleted, priority, creationDate,
										recurrenceCount, recurrenceUnit, recurrenceType2Nth, recurrenceType2Day, recurrenceType2Unit,
										contexts, projects)

			#print ("class todo: task = ", task, " length = ", len(task))
			#print ("\thasError = ", hasError)
			#print ("\tcompleted =", completed)
			#print ("\tcompletionDate =", completionDate)
			#print ("\tpriority = ", priority)
			#print ("\tcreationDate =", creationDate)
			#print ("\tdueDate  =", dueDate)
			#print ("\trecurrenceCount =", recurrenceCount)
			#print ("\trecurrenceUnit =", recurrenceUnit)
			#print ("\trecurrenceType2Nth =", recurrenceType2Nth)
			#print ("\trecurrenceType2Day =", recurrenceType2Day)
			#print ("\trecurrenceType2Unit  =", recurrenceType2Unit)
		
		#print ("\n==================================================\n")
		f.close()
		#for dueDate in sorted(self.todoTasksDueDate.keys()):
			#print ("#### task is ", self.todoTasksDueDate[dueDate])
		#print ("\n################n")
		self.fileError = False

	def getTodoTasks(self):
		return self.todoTasksTask, self.todoTasksDueDate, self.comments

	def updateTodoTxt (self):
		pass

def handleGUIException(excType, excValue, excTraceback):
	try:
		logError = False
		with open ('TaskManager.log', 'w') as f:
			f.write (''.join(traceback.format_exception(excType, excValue, excTraceback)))
			f.close()
	except:
		logError = True

	errMsg = 'Fatal error seen, TaskManager will close.'
	if logError == True:
		errMsg += '\nError log file could not be created.'
	else:
		errMsg += '\nSend TaskManager.log to <anirbax@gmail.com>.'
	print (''.join(traceback.format_exception(excType, excValue, excTraceback)))
	dlg = wx.MessageDialog(None, errMsg, 'Fatal Error', wx.OK | wx.ICON_ERROR)
	dlg.ShowModal()
	dlg.Destroy()
	sys.exit()

sys.excepthook = handleGUIException

class completeTaskDialog (wx.Dialog):
	def __init__(self, parent, todoTasksSelectedListLen, completed=False, allCompleted=False, recurringTask=False):
		self.parent = parent
		self.todoTasksSelectedListLen = todoTasksSelectedListLen
		wx.Dialog.__init__(self, parent, title="Task Completion", size=(500,200))
		l = 'task' if todoTasksSelectedListLen == 1 else 'all ' + str(todoTasksSelectedListLen) + ' selected tasks'
		self.markComplete = wx.CheckBox(self, label='Mark ' + l + ' complete', size=(-1, 20))
		self.markAllComplete = wx.CheckBox(self, label='Mark all occurrences of ' + l + ' complete', size=(-1, 20))
		self.markComplete.SetValue(completed)
		self.markAllComplete.SetValue(allCompleted)
		self.okButton = wx.Button(self, -1, "Ok")
		self.cancelButton = wx.Button(self, -1, "Cancel")
		self.okButton.Bind (wx.EVT_BUTTON, self.okButtonHandler)
		self.cancelButton.Bind (wx.EVT_BUTTON, self.cancelButtonHandler)

		sizerTop = wx.BoxSizer(wx.VERTICAL)
		if not recurringTask:
			sizerTop.AddSpacer(20)
		sizerTop.AddSpacer(20)
		sizerTop.Add(self.markComplete, flag=wx.CENTER)
		sizerTop.AddSpacer(20)
		sizerTop.Add(self.markAllComplete, flag=wx.CENTER)
		sizerBottom = wx.BoxSizer(wx.HORIZONTAL)
		sizerBottom.AddSpacer(120)
		sizerBottom.Add(self.cancelButton)
		sizerBottom.AddSpacer(80)
		sizerBottom.Add(self.okButton)
		sizerTop.AddSpacer(30)
		sizerTop.Add(sizerBottom)

		self.SetSizer(sizerTop)

		if recurringTask:
			self.markAllComplete.Show()
		else:
			self.markAllComplete.Hide()

	def okButtonHandler(self, event=None):
		#print ("Task Completer Dialog: ", self.todoTasksSelectedListLen, "tasks")
		self.parent.completeTask = self.markComplete.IsChecked()
		self.parent.completeAllTasks = self.markAllComplete.IsChecked()
		self.exit(event=None)

	def cancelButtonHandler(self, event=None):
		self.parent.completeTask = False
		self.parent.completeAllTasks = False
		self.exit(event=None)

	def exit(self, event=None):
		self.parent.fileSave()
		self.Destroy()

class editTaskDialog (wx.Dialog):

	def __init__(self, parent, todoTasksTask = '', todoTasksDetails = ()):
		self.parent = parent
		self.editMode = (todoTasksTask != '')
		self.creationDate = ''
		self.todoTasksTaskForEdit = todoTasksTask

		wx.Dialog.__init__(self, parent, title="Task Editor", size=(840,525))
		self.Bind(wx.EVT_CLOSE, self.exit)

		mainSizer = wx.GridBagSizer(vgap=10, hgap=10)

		taskLabel = wx.StaticText(self, label="Task", style=wx.ALIGN_RIGHT)
		self.taskText = wx.TextCtrl(self, size=(762, -1))
		self.taskText.SetHint("Set task details here.")

		projectLabel = wx.StaticText(self, label="Project")
		self.projectText = wx.TextCtrl(self, size=(740,-1))
		self.projectText.SetHint("Project that this task is part of.")

		contextLabel = wx.StaticText(self, label="Context")
		self.contextText = wx.TextCtrl(self, size=(735,-1))
		self.contextText.SetHint("Contexts/tags associated with this task.")

		priorityLabel = wx.StaticText(self, label="Priority")
		self.priorityText = wx.ComboBox(self, -1, 'None', choices=_priorityList, style=wx.CB_READONLY)

		self.noDueDateCheckBox = wx.CheckBox(self, label='No Due Date', size=(-1, 20))
		self.noDueDateCheckBox.Bind(wx.EVT_CHECKBOX, self.noDueDateCheckBoxHandler)		
		self.noDueDateCheckBox.SetValue(False)

		self.dueDatePickerLabel = wx.StaticText(self, label="Due Date")
		self.datePicker = wx.adv.DatePickerCtrl(self, size=(150,-1),
								style = wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY | wx.adv.DP_ALLOWNONE)

		recurrenceRadioBoxLabel = wx.StaticText(self, label="Recurrence Type")
		self.recurrenceRadioBox = wx.RadioBox(self, label='', choices=_recurrenceTypeList, style=wx.NO_BORDER)
		self.recurrenceRadioBox.Bind(wx.EVT_RADIOBOX,self.recurrenceRadioBoxHandler)

		self.recurDetailsLabel = wx.StaticText(self, label='Occurs on the')
		self.recurDetailsLabel.Disable()

		recurDetailsSizerA = wx.BoxSizer(wx.HORIZONTAL)
		self.recurSpanText = wx.StaticText(self, label='Occurs Every ')
		self.recurSpanCount = wx.TextCtrl(self, value='1', size=(40, -1))
		self.recurSpanUnit = wx.ComboBox(self, -1, 'Months', choices=_recurSpanUnitList, style=wx.CB_READONLY)
		self.recurSpanText.Disable()
		self.recurSpanCount.Disable()
		self.recurSpanUnit.Disable()
		recurDetailsSizerA.Add(self.recurSpanText, flag=wx.ALIGN_CENTER_VERTICAL)
		recurDetailsSizerA.Add(self.recurSpanCount)
		recurDetailsSizerA.Add(self.recurSpanUnit)

		recurDetailsSizerB = wx.BoxSizer(wx.HORIZONTAL)
		self.recurLastDayText = wx.StaticText(self, label='Last')
		self.recurDayNumber = wx.TextCtrl(self, value='1', size=(40, -1))
		self.recurDayNumber.Bind (wx.EVT_KEY_UP, self.recurDayNumberHandler)
		self.recurDayNumAdjectiveText = wx.StaticText(self, label='st')
		self.recurDay = wx.ComboBox(self, -1, 'Sunday', choices=_recurDayList, style=wx.CB_READONLY)
		self.recurDayText = wx.StaticText(self, label='of every')
		self.recurDayUnit = wx.ComboBox(self, -1, 'Month', choices=_recurDayUnitList, style=wx.CB_READONLY)
		self.recurDayNumber.Disable()
		self.recurDayNumAdjectiveText.Disable()
		self.recurDay.Disable()
		self.recurDayText.Disable()
		self.recurDayUnit.Disable()
		recurDetailsSizerB.Add(self.recurLastDayText, flag=wx.ALIGN_CENTER_VERTICAL)
		recurDetailsSizerB.Add(self.recurDayNumber)
		recurDetailsSizerB.Add(self.recurDayNumAdjectiveText, flag=wx.ALIGN_CENTER_VERTICAL)
		recurDetailsSizerB.AddSpacer(10)
		recurDetailsSizerB.Add(self.recurDay)
		recurDetailsSizerB.AddSpacer(10)
		recurDetailsSizerB.Add(self.recurDayText, flag=wx.ALIGN_CENTER_VERTICAL)
		recurDetailsSizerB.AddSpacer(10)
		recurDetailsSizerB.Add(self.recurDayUnit)
		self.recurLastDayText.Hide()

		recurDetailsSizerC = wx.BoxSizer(wx.VERTICAL)
		self.completeCheckBox = wx.CheckBox(self, label='This occurrence is complete', size=(-1, 20))
		self.allCompleteCheckBox = wx.CheckBox(self, label='All occurrences are complete', size=(-1, 20))
		self.allCompleteCheckBox.Bind(wx.EVT_CHECKBOX, self.allCompleteCheckBoxHandler)		
		if todoTasksTask != '':
			recurDetailsSizerC.Add(self.completeCheckBox)
			recurDetailsSizerC.AddSpacer(10)
			recurDetailsSizerC.Add(self.allCompleteCheckBox)
			recurDetailsSizerC.AddSpacer(20)
		else:
			recurDetailsSizerC.AddSpacer(70)

		if todoTasksTask == '':
			self.completeCheckBox.Hide()
			self.allCompleteCheckBox.Hide()

		self.okButton = wx.Button(self, -1, "Ok")
		self.cancelButton = wx.Button(self, -1, "Cancel")
		self.okButton.Bind (wx.EVT_BUTTON, self.okButtonHandler)
		self.cancelButton.Bind (wx.EVT_BUTTON, self.cancelButtonHandler)

		taskSizer = wx.BoxSizer(wx.HORIZONTAL)
		taskSizer.Add(taskLabel, flag=wx.ALIGN_CENTER_VERTICAL)
		taskSizer.AddSpacer(5)
		taskSizer.Add(self.taskText)
		mainSizer.Add(taskSizer, pos=(1, 0), span=(1,9), flag=wx.LEFT|wx.RIGHT, border=15)

		projectSizer = wx.BoxSizer(wx.HORIZONTAL)
		projectSizer.Add(projectLabel, flag=wx.ALIGN_CENTER_VERTICAL)
		projectSizer.AddSpacer(5)
		projectSizer.Add(self.projectText)
		mainSizer.Add(projectSizer, pos=(2,0), flag=wx.LEFT, border=15)

		contextSizer = wx.BoxSizer(wx.HORIZONTAL)
		contextSizer.Add(contextLabel, flag=wx.ALIGN_CENTER_VERTICAL)
		contextSizer.AddSpacer(5)
		contextSizer.Add(self.contextText)
		mainSizer.Add(contextSizer, pos=(3,0), flag=wx.LEFT, border=15)

		leftMiddleSizer = wx.BoxSizer(wx.VERTICAL)
		rightMiddleSizer = wx.BoxSizer(wx.VERTICAL)
		middleSizer = wx.BoxSizer(wx.HORIZONTAL)
		bottomSizer = wx.BoxSizer(wx.HORIZONTAL)

		prioritySizer = wx.BoxSizer(wx.HORIZONTAL)
		prioritySizer.Add(priorityLabel, flag=wx.ALIGN_CENTER_VERTICAL)
		prioritySizer.AddSpacer(25)
		prioritySizer.Add(self.priorityText)
		
		noDueDateCheckBoxSizer = wx.BoxSizer(wx.HORIZONTAL)
		noDueDateCheckBoxSizer.Add(self.noDueDateCheckBox)

		dueDateSizer = wx.BoxSizer(wx.HORIZONTAL)
		dueDateSizer.Add(self.dueDatePickerLabel, flag=wx.ALIGN_CENTER_VERTICAL)
		dueDateSizer.AddSpacer(10)
		dueDateSizer.Add(self.datePicker)
		leftMiddleSizer.AddSpacer(15)
		leftMiddleSizer.Add(noDueDateCheckBoxSizer)
		leftMiddleSizer.AddSpacer(25)
		leftMiddleSizer.Add(dueDateSizer)
		leftMiddleSizer.AddSpacer(5)

		recurrenceTypeSizer = wx.BoxSizer(wx.HORIZONTAL)
		recurrenceTypeSizer.Add(recurrenceRadioBoxLabel, flag=wx.ALIGN_CENTER_VERTICAL)
		recurrenceTypeSizer.AddSpacer(5)
		recurrenceTypeSizer.Add(self.recurrenceRadioBox)
		leftMiddleSizer.Add(recurrenceTypeSizer)

		rightMiddleSizer.AddSpacer(15)
		rightMiddleSizer.Add(prioritySizer)
		rightMiddleSizer.AddSpacer(15)
		rightMiddleSizer.Add(recurDetailsSizerA)
		rightMiddleSizer.AddSpacer(15)
		rightMiddleSizer.Add(self.recurDetailsLabel, flag=wx.ALIGN_LEFT)
		rightMiddleSizer.AddSpacer(10)
		rightMiddleSizer.Add(recurDetailsSizerB)
		rightMiddleSizer.AddSpacer(10)
		rightMiddleSizer.Add(recurDetailsSizerC)

		middleSizer.AddSpacer(40)
		middleSizer.Add(leftMiddleSizer)
		middleSizer.AddSpacer(90)
		middleSizer.Add(rightMiddleSizer)

		mainSizer.Add(middleSizer, pos=(4, 0), flag=wx.LEFT, border=35)

		bottomSizer.AddSpacer(200)
		bottomSizer.Add(self.cancelButton)
		bottomSizer.AddSpacer(220)
		bottomSizer.Add(self.okButton)

		mainSizer.Add(bottomSizer, pos=(5, 0), flag=wx.BOTTOM|wx.LEFT, border=0)

		if todoTasksTask != '':
			(dueDate, hasError, completed, completionDate, allCompleted, 
			priority, self.creationDate,
			recurrenceCount, recurrenceUnit, 
			recurrenceType2Nth, recurrenceType2Day, 
			recurrenceType2Unit, contexts, projects) = todoTasksDetails
			_DEBUG (" EDIT TASKS %% edit tasks dialog - hasError", hasError)
			_DEBUG ("%% edit tasks dialog - completed", completed)
			_DEBUG ("%% edit tasks dialog - allCompleted", allCompleted)
			#print ("%% edit tasks dialog - recurrenceCount", recurrenceCount)
			#print ("%% edit tasks dialog - recurrenceCount == ''", recurrenceCount=='')
			#print ("%% edit tasks dialog - recurrenceType2Nth", recurrenceType2Nth)
			#print ("%% edit tasks dialog - recurrenceType2Unit", recurrenceType2Unit)
			if hasError == False:
				self.taskText.WriteText(todoTasksTask)

				for e in contexts:
					self.contextText.AppendText('@'+e+' ')

				for e in projects:
					self.projectText.AppendText('+'+e+' ')

				if priority in _priorityList:
					self.priorityText.SetSelection(_priorityList.index(priority))
				else:
					self.priorityText.SetSelection(0)

				if dueDate.strip() != '': 
					dList = dueDate.split('-')
					if dList[0] != '': 
						self.noDueDateCheckBox.SetValue(False)
						self.datePicker.SetValue(wx.DateTime(int(dList[2]), int(dList[1])-1, int(dList[0])))
				else:
					self.noDueDateCheckBox.SetValue(True)
					self.datePicker.Disable()

				if recurrenceCount != '' and recurrenceType2Nth == '':
					self.recurrenceRadioBox.SetSelection(1)
				elif recurrenceCount == '' and recurrenceType2Nth != '':
					if recurrenceType2Nth in 'lL':
						self.recurrenceRadioBox.SetSelection(3)
					else:
						self.recurrenceRadioBox.SetSelection(2)
				else:
					self.recurrenceRadioBox.SetSelection(0)

				self.recurrenceRadioBoxHandler()
				if recurrenceCount != '' and recurrenceType2Nth == '':
					self.recurSpanCount.Clear()
					self.recurSpanCount.WriteText(recurrenceCount)
					#print ("recurSpanUnit is set to ", _wmy.index(recurrenceUnit))
					self.recurSpanUnit.SetSelection(_wmy.index(recurrenceUnit))
				elif recurrenceCount == '' and recurrenceType2Nth != '':
					if recurrenceType2Nth not in 'lL':
						self.recurDayNumber.Clear()
						self.recurDayNumber.WriteText(recurrenceType2Nth)
						self.recurDayNumberHandler()
					self.recurDay.SetSelection(_wds.index(recurrenceType2Day))
					self.recurDayUnit.SetSelection(_my.index(recurrenceType2Unit))
					#print ("self.recurDayUnit.GetStringSelection()=", self.recurDayUnit.GetStringSelection())
					#print ("self.recurDayUnit.GetSelection()=", self.recurDayUnit.GetSelection())
					#print ("self.recurDayUnit.GetCurrentSelection()=", self.recurDayUnit.GetCurrentSelection())

				if completed:
					#print ("%% AA. edit tasks dialog - completed", completed)
					#print ("%% AA. edit tasks dialog - allCompleted", allCompleted)
					self.allCompleteCheckBox.SetValue(False)
					self.completeCheckBox.SetValue(True)

				if recurrenceCount == '' and recurrenceType2Nth == '':
					self.allCompleteCheckBox.Hide()
				elif allCompleted:
					self.allCompleteCheckBox.SetValue(True)
					self.completeCheckBox.SetValue(True)
					self.completeCheckBox.Disable()

		self.SetSizer(mainSizer)

	def allCompleteCheckBoxHandler(self, event=None):
		if self.allCompleteCheckBox.IsChecked():
			self.completeCheckBox.SetValue(True)
			self.completeCheckBox.Disable()
		else:
			self.completeCheckBox.Enable()
			
	def noDueDateCheckBoxHandler(self, event=None):
		recurrenceRadioBoxSelection = self.recurrenceRadioBox.GetSelection()
		if self.noDueDateCheckBox.IsChecked() or recurrenceRadioBoxSelection > 1:
			self.datePicker.Disable()
		else:
			self.datePicker.Enable()

	def validateUserInputs(self, editMode=False):
		errorInUserInputs = False
		task = self.taskText.GetLineText(0).strip()
		#print ("validateUserInputs: task is ", task)
		#print ("self.parent.todoTasksTask keys ", self.parent.todoTasksTask.keys())
		if task == '':
			errMsg = "Task field cannot be empty"
			errorInUserInputs = True

		if task in self.parent.todoTasksTask.keys() and editMode == False:
			#new task being 
			#print (task, "exists in ", self.parent.todoTasksTask.keys())
			errMsg = "Task already exists!"
			errorInUserInputs = True

		recurrenceSelection = self.recurrenceRadioBox.GetSelection()
		if recurrenceSelection == 1:
			try:
				count = int(self.recurSpanCount.GetLineText(0))
			except:
				count = -1
			if count < 1:
				errMsg = "Bad recurrence span."
				errorInUserInputs = True
		elif recurrenceSelection == 2:
			try:
				count = int(self.recurDayNumber.GetLineText(0))
			except:
				count = -1
			#print ("count = ", count, "self.recurDayNumber.GetLineText(0) = ", self.recurDayNumber.GetLineText(0))
			if (count < 1 or count > 4) and self.recurDay.GetStringSelection() != 'Day' and self.recurDayUnit.GetStringSelection() == 'Month' or\
					(count < 1 or count > 31) and self.recurDay.GetStringSelection() == 'Day' and self.recurDayUnit.GetStringSelection() == 'Month' or\
					(count < 1 or count > 52)  and self.recurDayUnit.GetStringSelection() == 'Year':
				errMsg = "Bad day!"
				errorInUserInputs = True

		if errorInUserInputs == True:
			dlg = wx.MessageDialog(None, errMsg, 'Error', wx.OK | wx.ICON_ERROR)
			dlg.ShowModal()
			dlg.Destroy()
		return not errorInUserInputs

	def recurDayNumberHandler(self, event=None):
		recurDayNum = self.recurDayNumber.GetLineText(0)
		#print ("recurDayNum = ", recurDayNum)
		if recurDayNum == '':
			self.recurDayNumAdjectiveText.SetLabel('')
		elif recurDayNum[-2:-1] == '1':
			self.recurDayNumAdjectiveText.SetLabel('th')
		elif recurDayNum[-1:] == '1':
			self.recurDayNumAdjectiveText.SetLabel('st')
		elif recurDayNum[-1:] == '2':
			self.recurDayNumAdjectiveText.SetLabel('nd')
		elif recurDayNum[-1:] == '3':
			self.recurDayNumAdjectiveText.SetLabel('rd')
		else:
			self.recurDayNumAdjectiveText.SetLabel('th')

	def getTags(self):
		projects = []
		contexts = []

		projectText = self.projectText.GetLineText(0).replace(',', ' ')
		projectText = projectText.replace('+', ' ')
		l = filter(lambda x: x != '', projectText.split(' '))
		for e in l:
			projects.append(e)
		contextText = self.contextText.GetLineText(0).replace(',', ' ')
		contextText = contextText.replace('@', ' ')
		l = filter(lambda x: x != '', contextText.split(' '))
		for e in l:
			contexts.append(e)

		#print ("getTags: A. contexts, projects=", contexts, projects)

		return contexts, projects

	def okButtonHandler(self, event=None):
		self.parent.newtodoTasksTask = {}
		self.parent.newTodoTasksDueDate = {}
		goodValidation = self.validateUserInputs(self.editMode)
		contexts, projects = self.getTags()

		if goodValidation == True: #no error seen
			today = _makeDateForTodo(time.asctime())
			#print ("self.recurSpanUnit.GetStringSelection()=", self.recurSpanUnit.GetStringSelection())
			#print ("self.recurDay.GetStringSelection()=", self.recurDay.GetStringSelection())
			#print ("self.recurDayUnit.GetStringSelection()=", self.recurDayUnit.GetStringSelection())

			recurrenceCount = recurrenceUnit = recurrenceType2Nth = recurrenceType2Day = recurrenceType2Unit = ''
			recurrenceSelection = self.recurrenceRadioBox.GetSelection()
			if  recurrenceSelection == 1:
				recurrenceCount = self.recurSpanCount.GetLineText(0).strip()
				recurrenceUnit = _WMYs[self.recurSpanUnit.GetStringSelection()]
			elif recurrenceSelection > 1:
				recurrenceType2Nth = self.recurDayNumber.GetLineText(0).strip()
				recurrenceType2Day = _weekdays[self.recurDay.GetStringSelection()]
				#print ("^^^^^^^ self.recurDayUnit.GetStringSelection() = ", self.recurDayUnit.GetStringSelection())
				recurrenceType2Unit = _WMY[self.recurDayUnit.GetStringSelection()]
			if recurrenceSelection == 3:
				recurrenceType2Nth = 'L'
			task = self.taskText.GetLineText(0).strip()

			priority = self.priorityText.GetStringSelection()
			if priority == 'None':
				priority = ''

			completed = allCompleted = False
			if self.completeCheckBox.IsChecked():
				completed = True
			if self.allCompleteCheckBox.IsChecked():
				completed = True
				allCompleted = True

			completionDate = today if (completed or allCompleted) else ''
			creationDate = self.creationDate if self.editMode else today
			if self.noDueDateCheckBox.IsChecked():
				dueDate = ''
			else:
				dueDate = _makeDateForTodo(str(self.datePicker.GetValue()))
			self.parent.newtodoTasksTask[task] = (dueDate, False, completed, completionDate, allCompleted, priority, creationDate,
				recurrenceCount, recurrenceUnit,
				recurrenceType2Nth, recurrenceType2Day, recurrenceType2Unit, contexts, projects)
				#(dueDate, hasError, completed, completionDate, allCompleted, priority, creationDate,
				#recurrenceCount, recurrenceUnit, 
				#recurrenceType2Nth, recurrenceType2Day, recurrenceType2Unit, contexts, projects)
			#print ("type of datetime is ", type(self.datePicker.GetValue()))
			self.parent.newTodoTasksDueDate[dueDate] = task
			#print ("dueDate =", dueDate)
			self.exit(event=None)

	def cancelButtonHandler(self, event=None):
		self.parent.newtodoTasksTask = {}
		self.parent.newTodoTasksDueDate = {}
		self.exit(event=None)

	def recurrenceRadioBoxHandler(self, event=None):
		selection = self.recurrenceRadioBox.GetSelection()
		#print ("recurrence type is #", selection)
		self.dueDatePickerLabel.Enable()
		if not self.noDueDateCheckBox.IsChecked():
			self.datePicker.Enable()
		self.recurDayNumber.Show()
		self.recurLastDayText.Hide()
		self.recurDayNumAdjectiveText.Hide()
		if selection == 0:
			self.recurDetailsLabel.Disable()
			self.recurSpanText.Disable()
			self.recurSpanCount.Disable()
			self.recurSpanUnit.Disable()
			self.recurDayNumber.Disable()
			self.recurDay.Disable()
			self.recurDayText.Disable()
			self.recurDayUnit.Disable()
			self.allCompleteCheckBox.Hide()
		elif selection == 1:
			self.recurDetailsLabel.Enable()
			self.recurSpanText.Enable()
			self.recurSpanCount.Enable()
			self.recurSpanUnit.Enable()
			self.recurDayNumber.Disable()
			self.recurDay.Disable()
			self.recurDayText.Disable()
			self.recurDayUnit.Disable()
			self.allCompleteCheckBox.Show()
			self.allCompleteCheckBox.Enable()
		elif selection == 2:
			self.dueDatePickerLabel.Disable()
			self.datePicker.Disable()
			self.recurDetailsLabel.Enable()
			self.recurSpanText.Disable()
			self.recurSpanCount.Disable()
			self.recurSpanUnit.Disable()
			self.recurDayNumber.Enable()
			self.recurDay.Enable()
			self.recurDayNumAdjectiveText.Show()
			self.recurDayNumAdjectiveText.Enable()
			self.recurDayText.Enable()
			self.recurDayUnit.Enable()
			self.allCompleteCheckBox.Show()
			self.allCompleteCheckBox.Enable()
		elif selection == 3:
			self.dueDatePickerLabel.Disable()
			self.datePicker.Disable()
			self.recurDetailsLabel.Enable()
			self.recurSpanText.Disable()
			self.recurSpanCount.Disable()
			self.recurSpanUnit.Disable()
			self.recurLastDayText.Show()
			self.recurLastDayText.Enable()
			self.recurDayNumber.Hide()
			self.recurDayNumAdjectiveText.Hide()
			self.recurDay.Enable()
			self.recurDayText.Enable()
			self.recurDayUnit.Enable()
			self.allCompleteCheckBox.Show()
			self.allCompleteCheckBox.Enable()
		self.Layout()

	def exit(self, event=None):
		self.parent.fileSave()
		self.Destroy()

class taskManager(wx.Frame):

	def setTodoTasks (self):
		self.todoTasksTask, self.todoTasksDueDate, self.todoFileComments = self.todo.getTodoTasks()
 
	def __init__(self, title, todoFile):
		mainFrame = wx.Frame.__init__(self, None, size=(1250, 600), title=title)
		self.Bind(wx.EVT_CLOSE, self.fileQuit, mainFrame)

		#default values
		self.fileName = ''
		self.dirName = ''
		self.title = title
		self.searchString = ''
		self.taskContentsDirty = False
		self.completeTask = False
		self.completeAllTasks = False
		self.newtodoTasksTask = {}
		self.newTodoTasksDueDate = {}
		self.todoTasksTask, self.todoTasksDueDate = {}, {}
		self.selectedTask = ''
		self.selectedProjects = []
		self.selectedContexts = []
		self.todoFileComments = []
		self.todoFile = todoFile
		self.showButtons = True

		# Setting up the menu.
		self.fileMenu = wx.Menu()
		self.editMenu = wx.Menu()
		self.optionsMenu = wx.Menu()
		self.helpMenu = wx.Menu()
		self.menuNewTask = self.fileMenu.Append(-1, "New Task", "Create new task")
		self.menuEditTask = self.fileMenu.Append(-1, "Edit Task", "Edit an existing task")
		self.menuDeleteTask = self.fileMenu.Append(-1, "Delete Task", "Delete task")
		self.fileMenu.AppendSeparator()
		self.menuOpen = self.fileMenu.Append(-1, "Open todo.txt...\tCtrl+O", "Locate todo.txt")
		self.menuSave = self.fileMenu.Append(-1, "&Save...\tCtrl+S", "Save the current file to disk")
		self.fileMenu.AppendSeparator()
		self.menuExit = self.fileMenu.Append(-1,"&Quit\tCtrl+Q","Exit TaskManager")
		self.menuQuickButtons = self.editMenu.Append(-1,"Hide Quick Buttons \tCtrl+F"," Show/Hide search and searchTasks")
		self.menuClearSearch = self.editMenu.Append(-1,"Clear Search"," Clear Search")
		self.menuFont = self.optionsMenu.Append(wx.ID_SELECT_FONT,"&Font...\tCtrl+T"," Change Font")
		self.menuAbout = self.helpMenu.Append(wx.ID_ABOUT, "&About", "Information about TaskManager")

		#Create the menubar.
		self.menuBar = wx.MenuBar()
		self.menuBar.Append(self.fileMenu,"&File")
		self.menuBar.Append(self.editMenu,"&Edit")
		self.menuBar.Append(self.optionsMenu,"&Options") 
		self.menuBar.Append(self.helpMenu,"&Help") 
		self.SetMenuBar(self.menuBar)  # Adding the MenuBar to the Frame content.
		#Menu events
		self.Bind(wx.EVT_MENU, self.newTaskButtonHandler, self.menuNewTask)
		self.Bind(wx.EVT_MENU, self.editTaskButtonHandler, self.menuEditTask)
		self.Bind(wx.EVT_MENU, self.menuDeleteTaskHandler, self.menuDeleteTask)
		self.Bind(wx.EVT_MENU, self.fileOpen, self.menuOpen)
		self.Bind(wx.EVT_MENU, self.fileSave, self.menuSave)
		self.Bind(wx.EVT_MENU, self.fileQuit, self.menuExit)
		self.Bind(wx.EVT_MENU, self.fontSelect, self.menuFont)
		self.Bind(wx.EVT_MENU, self.showButtonsHandler, self.menuQuickButtons)
		self.Bind(wx.EVT_MENU, self.clearSearchHandler, self.menuClearSearch)
		self.Bind(wx.EVT_MENU, self.helpAbout, self.menuAbout)
		#sizers
		self.sizer = wx.BoxSizer(wx.VERTICAL) #contains vertically stacked sizerTweedleDum and sizerTweedleDee
		self.sizerTweedleDum = wx.BoxSizer(wx.HORIZONTAL) #contains horizontally stacked sizers Left, Middle and Right
		self.sizerLeft = wx.BoxSizer(wx.VERTICAL) #contains task label and tasks
		self.sizerRight = wx.BoxSizer(wx.VERTICAL) #contains contexts and projects
		self.sizerTweedleDee = wx.BoxSizer(wx.HORIZONTAL)
		self.taskList = wx.ListCtrl(self, name="taskList", style=wx.LC_REPORT)
		self.taskList.Bind(wx.EVT_LIST_ITEM_SELECTED, self.taskSelectedHandler)
		self.taskList.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.itemDeselectedHandler)
		self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.rightClickHandler)
		self.taskList.InsertColumn(0, "Due Date", wx.LIST_FORMAT_CENTRE)
		self.taskList.InsertColumn(1, "Tasks", wx.LIST_FORMAT_CENTRE)
		self.taskList.InsertColumn(2, "Priority", wx.LIST_FORMAT_CENTRE)
		self.taskList.InsertColumn(3, "Completion Status", wx.LIST_FORMAT_CENTRE)
		self.taskList.InsertColumn(4, "Next Due", wx.LIST_FORMAT_CENTRE)
		self.projectList = wx.ListBox(self, name="projectList", style=wx.LB_MULTIPLE)
		self.projectList.Bind(wx.EVT_LISTBOX, self.projectListBoxHandler)		
		self.projectLabel = wx.StaticText(self, label="Project Tags")
		#self.projectLabel.SetFont(wx.Font(14, family=wx.FONTFAMILY_DEFAULT, style = 0, weight = 90, 
		#			  underline = False, faceName ="", encoding = wx.FONTENCODING_DEFAULT))
		self.contextList = wx.ListBox (self, name="contextList", style=wx.LB_MULTIPLE)
		self.contextList.Bind(wx.EVT_LISTBOX, self.contextListBoxHandler)		
		self.contextLabel = wx.StaticText(self, label="Context Tags")
		#self.contextLabel.SetFont(wx.Font(14, family=wx.FONTFAMILY_DEFAULT, style = 0, weight = 90, 
		#			  underline = False, faceName ="", encoding = wx.FONTENCODING_DEFAULT))
		self.newTaskButton = wx.Button(self, -1, "New Task", style=wx.RAISED_BORDER)
		self.newTaskButton.Bind (wx.EVT_BUTTON, self.newTaskButtonHandler)
		self.editTaskButton = wx.Button(self, -1, "Edit Task", style=wx.RAISED_BORDER)
		self.editTaskButton.Bind (wx.EVT_BUTTON, self.editTaskButtonHandler)
		self.completeTaskButton = wx.Button(self, -1, "Complete Task", style=wx.BORDER_DEFAULT)
		self.completeTaskButton.Bind (wx.EVT_BUTTON, self.completeTaskButtonHandler)
		self.searchTaskBarClearButton = wx.Button(self, -1, ">", style=wx.BU_EXACTFIT)#+wx.RAISED_BORDER)
		self.searchTasksBar = wx.TextCtrl (self, name="searchTasksBar", style=wx.TE_NOHIDESEL+wx.TE_RICH+wx.RAISED_BORDER)
		self.searchTaskBarClearButton.Bind (wx.EVT_BUTTON, self.clearSearchHandler)
		self.searchTasksBar.Bind (wx.EVT_KEY_UP, self.searchBarHandler)
		self.searchTasksBar.SetHint("Type task to search...")
		self.clearTagsButton = wx.Button(self, -1, "Clear Tags")#+wx.RAISED_BORDER)
		self.clearTagsButton.Bind (wx.EVT_BUTTON, self.clearTagsButtonHandler)
		self.showCompletedTasksCheckBox = wx.CheckBox(self, label="Show Completed Tasks", size=(-1, 27))
		self.showCompletedTasksCheckBox.Bind(wx.EVT_CHECKBOX, self.showCompletedTasksCheckBoxHandler)		
		self.showCompletedTasksCheckBox.SetValue(False)
		self.sizerLeft.Add(self.taskList, 200, wx.EXPAND)
		self.sizerRight.Add(self.projectList, 100, wx.EXPAND)
		self.sizerRight.Add(self.projectLabel, 1, wx.ALIGN_CENTER)
		self.sizerRight.Add(self.contextList, 100, wx.EXPAND)
		self.sizerRight.Add(self.contextLabel, 1, wx.ALIGN_CENTER)
		self.sizerTweedleDum.Add(self.sizerLeft, 40, wx.EXPAND+wx.TOP)
		self.sizerTweedleDum.Add(self.sizerRight, 10, wx.EXPAND+wx.TOP)
		self.sizerTweedleDee.AddSpacer(10)
		self.sizerTweedleDee.Add(self.newTaskButton, 0)
		self.sizerTweedleDee.AddSpacer(10)
		self.sizerTweedleDee.Add(self.editTaskButton, 0)
		self.sizerTweedleDee.AddSpacer(10)
		self.sizerTweedleDee.Add(self.showCompletedTasksCheckBox, 1, wx.ALIGN_CENTER)
		self.sizerTweedleDee.AddSpacer(20)
		self.sizerTweedleDee.Add(self.completeTaskButton, 0)
		self.sizerTweedleDee.AddSpacer(20)
		self.sizerTweedleDee.Add(self.searchTaskBarClearButton, 0, wx.ALIGN_CENTER)
		self.sizerTweedleDee.Add(self.searchTasksBar, 100, wx.EXPAND)
		self.sizerTweedleDee.AddSpacer(20)
		self.sizerTweedleDee.Add(self.clearTagsButton, 0)
		self.sizerTweedleDee.AddSpacer(10)
		self.sizer.AddSpacer(13)
		self.sizer.Add(self.sizerTweedleDee, 1, wx.EXPAND+wx.BOTTOM)
		self.sizer.Add(self.sizerTweedleDum, 100, wx.EXPAND+wx.TOP, border=12)
		self.fontInformation = self.taskList.GetFont()
		self.sizer.Layout()
		self.sizer.Show(self.sizerTweedleDee)
		self.sizer.Show(self.sizerTweedleDum)
		#Layout sizers
		self.SetSizeHints(1250,400)
		self.SetSizer(self.sizer)
		#status bar
		self.statusbar = self.CreateStatusBar(1) # A Statusbar in the bottom of the window

		self.setupTimer()

	def setupTimer (self):
		asctime = time.asctime()
		match = re.match(r'^(.*?)\s(.*?)\s+(.*?)([0-9]{2}:[0-9]{2}:[0-9]{2})\s([0-9]{4})$', asctime) #'Tue Nov  2 20:01:51 2021'
		if match:
			nowSeconds = time.mktime(time.strptime(match.group(5)+'-'+match.group(2)+'-'+match.group(3)+' '+match.group(4), "%Y-%b-%d %H:%M:%S"))
			midnightSeconds = time.mktime(time.strptime(match.group(5)+'-'+match.group(2)+'-'+match.group(3)+' 23:59:59', "%Y-%b-%d %H:%M:%S"))
			threading.Timer(midnightSeconds - nowSeconds + 10, self.setupTimer).start() #9 seconds into the new day
			#print ("nowSeconds = ", nowSeconds, "midnightSeconds = ", midnightSeconds)
		self.openTodoFileAndSetStatus(self.todoFile)
		

	def openTodoFileAndSetStatus (self, fullFileName=''):
		#print ("openTodoFileAndSetStatus: calling todoFileOpen with ", fullFileName)
		todoError = self.todoFileOpen(fullFileName)

		if (todoError == True):
			self.statusMessage = "No todo.txt file loaded" 
		else:
			self.statusMessage = "Loaded "+self.todoFile

		self.statusbar.SetStatusWidths([-1])
		self.statusbar.SetStatusText(self.statusMessage, 0)

		#print ("INIT: self.todoFile is ", self.todoFile)

	def clearTagsButtonHandler (self, event=None):
		self.selectedProjects = []
		self.selectedContexts = []
		for e in range(0, self.projectList.GetCount()):
			self.projectList.Deselect(e)

		for e in range(0, self.contextList.GetCount()):
			self.contextList.Deselect(e)
		self.populateTasks(skipTagsRedraw=True)

	def populateTasks (self, skipTagsRedraw=False):
		#print (self.todoTasksTask)
		self.taskList.DeleteAllItems()
		if skipTagsRedraw == False:
			#while (self.projectList.GetCount()):
			#	self.projectList.Delete(self.projectList.GetTopItem())
			while (self.projectList.GetTopItem() >= 0):
				self.projectList.Delete(self.projectList.GetTopItem())
			#while (self.contextList.GetCount()):
			#	self.contextList.Delete(self.contextList.GetTopItem())
			while (self.contextList.GetTopItem() >= 0):
				self.contextList.Delete(self.contextList.GetTopItem())

		sortedDueDateTasks = {}
		
		#print ("populateTasks: todoTasksDueDate dict is : ", self.todoTasksDueDate)
		for key in self.todoTasksDueDate.keys():
			_DEBUG1(" dueDate keys: ", key)
			task = self.todoTasksDueDate[key]
			(dueDate, hasError, completed, completionDate, allCompleted,
				priority, creationDate,
				recurrenceCount, recurrenceUnit, 
				recurrenceType2Nth, recurrenceType2Day, 
				recurrenceType2Unit, contexts, projects) = self.todoTasksTask[task]

			recurringTask = recurrenceCount != '' or recurrenceType2Nth != ''
			#print ("\n %%% Task: ", task, " hasError = ", hasError, 
			#	" showCompletedTasksCheckBox - check is ", self.showCompletedTasksCheckBox.IsChecked())
			if hasError == False and (self.showCompletedTasksCheckBox.IsChecked() or\
				not ((completed and not recurringTask) or allCompleted)):
				#print ("%%% getitem count = ", self.taskList.GetItemCount())
				#print ("index is now ", index)
				showTask = True
				if skipTagsRedraw == True and (self.selectedProjects != [] or self.selectedContexts != []):
					showTask = False
					for e in self.selectedProjects:
						if e in projects:
							showTask = True
							break

					for e in self.selectedContexts:
						if e in contexts:
							showTask = True
							break

				if showTask == True:
					#print ("showTask = ", showTask)
					howSoonIsSoon = 7
					dueDate = dueDate.strip()
					nextDueDate = '?'
					completionStatus = '#'
					isRecurring = recurrenceCount != '' or recurrenceType2Nth != ''
					todayIsPastDueDate = False
					dueDateComingSoon = False
					hasDueDate = False
					dueDateIsToday = False
					dueDateIsTomorrow = False

					#print (" === recurrenceCount = ", recurrenceCount)
					today = _makeDateForTodo(time.asctime())
					if recurrenceType2Nth != '':
						#task occurs on nth x-day of every month/year
						#replace dueDate with calculated day

						#use original due date or today's date, whichever is later
						#for calculation
						_DEBUG (" === found Recurring task Type 2 - dueDate = ", dueDate, "ord dueDate = EMPTY", dueDate == '')
						if dueDate == '':
							dueDate = today
						elif _firstTodoDateIsEarlier(dueDate, today):
							dueDate = today
						
						dueDate = _resolveRecurrenceType2 (dueDate,
									recurrenceType2Nth, 
									recurrenceType2Day, 
									recurrenceType2Unit)
						_DEBUG (" === found Recurring Type 2 task - dueDate now set to ", dueDate)
					elif recurrenceCount != '' and dueDate == '':
						dueDate = _nextDate(creationDate, recurrenceCount, recurrenceUnit)
					elif recurrenceCount != '':
						dueDateIsPast = _firstTodoDateIsEarlier(dueDate, today)
						_DEBUG (" === found Recurring Type 1 with dueDate = ", dueDate)
						#if due date is past
						#iterate until due date is on or later than today
						iterCount = 0
						if dueDateIsPast:
							while (dueDateIsPast and iterCount < 1000):
								dueDate = _nextDate(dueDate, recurrenceCount, recurrenceUnit, 
									recurrenceType2Nth, recurrenceType2Day, recurrenceType2Unit)
								dueDateIsPast = _firstTodoDateIsEarlier(dueDate, today)
								iterCount += 1

					hasDueDate = dueDate != ''

					if hasDueDate:
						_DEBUG ("=== hasDueDate ~~~ dueDate = ", dueDate)
						todayIsPastDueDate = _firstTodoDateIsEarlier(dueDate, today) 
						_DEBUG ("=== todayIsPastDueDate ~~~ = ", todayIsPastDueDate)
						if recurrenceUnit == 'm' or recurrenceType2Unit == 'm': 
							howSoonIsSoon = 14
						elif recurrenceUnit == 'y' or recurrenceType2Unit == 'y': 
							howSoonIsSoon = 30
						elif recurrenceUnit == 'w' or recurrenceType2Unit == 'w': 
							howSoonIsSoon = 3
						diff = _dateDifference(dueDate, _makeDateForTodo(time.asctime()))
						_DEBUG2 (" A. ### date diff = ", diff)
						dueDateComingSoon = (diff <= howSoonIsSoon) and not todayIsPastDueDate
						_DEBUG2 (" A. ### dueDateComingSoon = ", dueDateComingSoon)

					dueDateIsToday = (_dateDifference(dueDate, _makeDateForTodo(time.asctime())) == 0) 
					dueDateIsTomorrow = (_dateDifference(dueDate, _makeDateForTodo(time.asctime())) == 1) 

					_DEBUG ("---B--", task, "---B--")
					_DEBUG ("dueDate = ", dueDate, "nextDueDate = ", nextDueDate, "isRecurring = ", isRecurring, "hasDueDate = ", hasDueDate)
					_DEBUG ("todayIsPastDueDate = ", todayIsPastDueDate, "dueDateComingSoon = ", dueDateComingSoon)

					if not hasDueDate and not isRecurring:
						if not completed:
							completionStatus = 'Active'
							#print ('%%%% Active')
							nextDueDate = '-'
						else:
							completionStatus = 'Done'
							nextDueDate = '-'
					elif isRecurring:
						if allCompleted:
							completionStatus = 'Done'
							#print ('%%%% 4 Done')
							#dueDate = '-'
							nextDueDate = '-'
						elif not completed and not allCompleted and (dueDateIsToday or dueDateIsTomorrow):
							if dueDateIsToday:
								completionStatus = 'TODAY'
							elif dueDateIsTomorrow:
								completionStatus = 'TOMORROW'
							nextDueDate = dueDate
						elif completed and not allCompleted:
							if todayIsPastDueDate:
								dueDate = _nextDate(dueDate, recurrenceCount, recurrenceUnit, 
									recurrenceType2Nth, recurrenceType2Day, recurrenceType2Unit)
							nextDueDate = _nextDate(dueDate, recurrenceCount, recurrenceUnit, 
								recurrenceType2Nth, recurrenceType2Day, recurrenceType2Unit)
							diff = _dateDifference(dueDate, _makeDateForTodo(time.asctime()))
							dueDateComingSoon = (diff <= howSoonIsSoon) and not todayIsPastDueDate
							_DEBUG2 ("AAA. task = ", task)
							_DEBUG2 ("AAA. dueDate = ", dueDate, "nextDueDate = ", nextDueDate)
							_DEBUG2 ("AAA. diff = ", diff, "dueDateComingSoon = ", dueDateComingSoon)
							if dueDateComingSoon:
								completionStatus = 'Coming up'
							else:
								completionStatus = 'Scheduled'
						elif not completed and not allCompleted and todayIsPastDueDate:
							completionStatus = 'Missed last'
							#print ('%%%% Missed last')
							nextDueDate = _nextDate(dueDate, recurrenceCount, recurrenceUnit, 
								recurrenceType2Nth, recurrenceType2Day, recurrenceType2Unit)
						elif not allCompleted:
							nextDueDate = _nextDate(dueDate, recurrenceCount, recurrenceUnit, 
								recurrenceType2Nth, recurrenceType2Day, recurrenceType2Unit)
							diff = _dateDifference(dueDate, _makeDateForTodo(time.asctime()))
							dueDateComingSoon = (diff <= howSoonIsSoon) and not todayIsPastDueDate
							_DEBUG2 ("X. task = ", task)
							_DEBUG2 ("X. dueDate = ", dueDate, "nextDueDate = ", nextDueDate, "isRecurring = ", isRecurring, "hasDueDate = ", hasDueDate)
							if dueDateComingSoon:
								completionStatus = 'Coming up'
							else:
								completionStatus = 'Scheduled'
							#print ('%%%% 1 Scheduled')
					else: #non-recurring and has due date
						if not completed and not allCompleted and (dueDateIsToday or dueDateIsTomorrow):
							if dueDateIsToday:
								completionStatus = 'TODAY'
							elif dueDateIsTomorrow:
								completionStatus = 'TOMORROW'
							nextDueDate = dueDate
						elif completed:
							completionStatus = 'Done'
							#print ('%%%% 1 Done')
							nextDueDate = '-'
						elif not completed and todayIsPastDueDate:
							completionStatus = 'OVERDUE'
							#print ('%%%% Overdue')
							nextDueDate = _makeDateForTodo(time.asctime())
						elif not completed and not todayIsPastDueDate and not dueDateComingSoon:
							completionStatus = 'To do'
							#print ('%%%% 2 To do')
							nextDueDate = dueDate
						elif not completed and not dueDateComingSoon and not todayIsPastDueDate:
							completionStatus = 'To do'
							#print ('%%%% 3 To do')
							nextDueDate = _nextDate(dueDate, recurrenceCount, recurrenceUnit, 
								recurrenceType2Nth, recurrenceType2Day, recurrenceType2Unit)
						elif not completed and dueDateComingSoon and not todayIsPastDueDate:
							completionStatus = 'Coming up'
							_DEBUG ('%%%% 2 Coming up')
							nextDueDate = _nextDate(dueDate, recurrenceCount, recurrenceUnit, 
								recurrenceType2Nth, recurrenceType2Day, recurrenceType2Unit)
					_DEBUG (ord(dueDate[0]) if len(dueDate) == 1 else "len dueDate is not 1")
					_DEBUG1 ("Final -- dueDate = ", dueDate, "nextDueDate = ", nextDueDate, "isRecurring = ", isRecurring, "hasDueDate = ", hasDueDate, "completionStatus = ", completionStatus)
						
					while dueDate in sortedDueDateTasks.keys():
						#uniquify again
						dueDate += ' '

					sortedDueDateTasks[dueDate] = (task.strip(), priority, completionStatus, nextDueDate)

				#endif showTask == True:

				if skipTagsRedraw == False:
					for e in projects:
						if self.projectList.FindString('+'+e) == wx.NOT_FOUND:
							self.projectList.InsertItems(['+'+e], self.projectList.GetCount())

					for e in contexts:
						if self.contextList.FindString('@'+e) == wx.NOT_FOUND:
							self.contextList.InsertItems(['@'+e], self.contextList.GetCount())

				#print ("populateTasks: contexts = ", contexts)
				#print ("populateTasks: projects = ", projects)

			#endif hasError == False and ...

		#endfor key in ...

		index = 0
		task = ''
		for key in sorted(sortedDueDateTasks.keys()):
			#_DEBUG1("sortedDueDateTasks key = ", key)
			(task, priority, completionStatus, nextDueDate) = sortedDueDateTasks[key]
			#print ("self.searchString = ", self.searchString)
			searchSubStringList = self.searchString.split()
			searchStringMatch = False
			for searchSubString in searchSubStringList:
				if task.find(searchSubString) >= 0:
					searchStringMatch = True
					break
			#print ("\n %%% Task: ", task, " searchStringMatch = ", searchStringMatch)
			if searchStringMatch or self.searchString == '':
				self.taskList.InsertItem(index, key.strip())
				self.taskList.SetItem(index, 1, task)
				self.taskList.SetItem(index, 2, priority)
				self.taskList.SetItem(index, 3, completionStatus)
				self.taskList.SetItem(index, 4, nextDueDate)
				if not index % 2:
					self.taskList.SetItemBackgroundColour(index, "light yellow")
				index += 1

			self.taskList.SetColumnWidth(0, -2)
			self.taskList.SetColumnWidth(1, -1 if len(task.strip()) > 100 else 600)
			self.taskList.SetColumnWidth(2, -2)
			self.taskList.SetColumnWidth(3, -2)
			self.taskList.SetColumnWidth(4, -2)
		
		self.Show()

	def showCompletedTasksCheckBoxHandler (self, event=None):
		self.populateTasks()

	def projectListBoxHandler (self, event=None):
		self.selectedProjects = []
		ss = self.projectList.GetSelections()
		#print ("projectList seletion indices - ", ss)
		for s in ss:
			project = self.projectList.GetString(s)
			self.selectedProjects.append(project[1:])
			#print ("selected project - ", project[1:])

		#print ("selectedProjects - ", self.selectedProjects)
		self.populateTasks(skipTagsRedraw=True)

	def contextListBoxHandler (self, event=None):
		self.selectedContexts = []
		ss = self.contextList.GetSelections()
		#print ("contextList seletion indices - ", ss)
		for s in ss:
			context = self.contextList.GetString(s)
			self.selectedContexts.append(context[1:])
			#print ("selected context - ", context[1:])
		#print ("selectedContexts - ", self.selectedContexts)
		self.populateTasks(skipTagsRedraw=True)

	def taskSelectedHandler (self, event=None):
		index = event.GetIndex()
		#print ("selected task index is ", index)
		#this is the last selected task - used for editing the task
		self.selectedTask = self.taskList.GetItemText(index, 1)
		selectedTasksList = []
		index = -1
		while True:
			index = self.taskList.GetNextItem(index,
								wx.LIST_NEXT_ALL,
								wx.LIST_STATE_SELECTED)
			if index == -1:
				break
			else:
				selectedTasksList.append(self.taskList.GetItemText(index, 1))
		#print ("completeTaskButtonHandler: selected task list: ", selectedTasksList)
		for e in range(0, self.projectList.GetCount()):
			self.projectList.Deselect(e)

		for e in range(0, self.contextList.GetCount()):
			self.contextList.Deselect(e)

		if selectedTasksList != []:
			contexts = []
			projects = []
			for e in selectedTasksList:
				*others, c, p = self.todoTasksTask[e]
				contexts += c
				projects += p
		else:
			return
		#print(selectedTasksList)
		#print ("selected projects ", projects)
		#print ("selected contexts ", contexts)
		for e in projects:
			self.projectList.SetSelection(self.projectList.FindString('+'+e))

		for e in contexts:
			self.contextList.SetSelection(self.contextList.FindString('@'+e))

	def itemDeselectedHandler (self, event=None):
		#print ("deselected task index is ", event.GetIndex())
		self.selectedTask = ''
		self.taskSelectedHandler(event)

	def clearSearchHandler (self, event=None):
		self.searchTasksBar.Clear()
		self.searchString = ''
		#print ("clearSearchHandler calling populateTasks", )
		self.populateTasks()
		#print ("clearSearchHandler returned from populateTasks")

	def showButtonsHandler (self, event=None):
		if self.showButtons == False:
			self.sizer.Show(self.sizerTweedleDee)
			self.menuQuickButtons.SetItemLabel ("Hide Quick Buttons")
			self.searchTasksBar.SetFocus()
		else:
			self.sizer.Hide(self.sizerTweedleDee)
			self.menuQuickButtons.SetItemLabel ("Show Quick Buttons")
			self.taskList.SetFocus()

		self.showButtons = not self.showButtons
		self.sizer.Layout()

	def searchBarHandler (self, event=None):
		string = self.searchTasksBar.GetValue()
		if (string != self.searchString):
			self.searchString = string
		self.populateTasks()
		event.Skip()

	def completeTaskButtonHandler (self, event=None):
		#e = self.taskList.GetSelectedItemCount()
		#if e != -1:
		#	print ("completeTaskButtonHandler:  selected item count = ", e)
		#else:
		#	print ("Nothing selected")

		selectedTasksList = []
		index = -1
		while True:
			index = self.taskList.GetNextItem(index,
								wx.LIST_NEXT_ALL,
								wx.LIST_STATE_SELECTED)
			if index == -1:
				break
			else:
				selectedTasksList.append(self.taskList.GetItemText(index, 1))
		#print ("completeTaskButtonHandler: selected task list: ", selectedTasksList)
		if selectedTasksList != []:
			completedAny = False
			allCompletedAny = False
			recurringTaskAny = False
			for task in selectedTasksList:
				#print ("Before - self.todoTasksTask[task]: ", self.todoTasksTask[task])
				(dueDate, hasError, completed, completionDate, allCompleted, 
				priority, self.creationDate,
				recurrenceCount, recurrenceUnit, 
				recurrenceType2Nth, recurrenceType2Day, 
				recurrenceType2Unit, contexts, projects) = self.todoTasksTask[task]
				
				if completed:
					completedAny = True
				if allCompleted:
					allCompletedAny = True
				if recurrenceCount != '' or recurrenceType2Nth != '':
					recurringTaskAny = True

			completeSelectedTaskDialog = completeTaskDialog (self, len(selectedTasksList), 
													completedAny, allCompletedAny, recurringTaskAny)
			completeSelectedTaskDialog.ShowModal()
			#print ("Returned from completeTaskButtonHandler: ")
			#print ("self.completeTask = ", self.completeTask)
			#print ("self.completeAllTasks = ", self.completeAllTasks)
			for task in selectedTasksList:
				(dueDate, hasError, completed, completionDate, allCompleted, 
				priority, self.creationDate,
				recurrenceCount, recurrenceUnit, 
				recurrenceType2Nth, recurrenceType2Day, 
				recurrenceType2Unit, contexts, projects) = self.todoTasksTask[task]

				if self.completeAllTasks:
					self.completeTask = True

				today = _makeDateForTodo(time.asctime())
				if self.creationDate == '' and self.completeTask == True:
					self.creationDate = today

				if completionDate == '':
					completionDate = today


				#print ("self.completeTask = ", self.completeTask)
				#print ("self.completeAllTasks = ", self.completeAllTasks)
				self.todoTasksTask[task] = (dueDate, hasError, self.completeTask, completionDate, self.completeAllTasks, 
											priority, self.creationDate,
											recurrenceCount, recurrenceUnit, 
											recurrenceType2Nth, recurrenceType2Day, 
											recurrenceType2Unit, contexts, projects)
				self.taskContentsDirty = True
				#print ("After - self.todoTasksTask[task]: ", self.todoTasksTask[task])
		else:
			dlg = wx.MessageDialog(None, 'Please select a task to mark as complete', 'Task Completion', wx.OK )
			dlg.ShowModal()
			dlg.Destroy()

		self.populateTasks()
	
	def updateStatus (self, string=''):
		self.statusbar.SetStatusText(string)
		self.statusbar.SetStatusText(self.statusMessage, 1)

	def setTaskManagerTitle(self, mod=''):
		if self.fileName != '':
			self.title = "Task Manager  - "+self.todoFile
		else:
			self.title = "Task Manager"

		self.SetTitle(self.title + mod)

	def helpAbout (self,e):
		# Create a message dialog box
		dlg = wx.MessageDialog(self, " TaskManager v2021-11-08 (c) 2021 Anirban Banerjee\n <anirbax@gmail.com>", "About TaskManager", wx.OK)
		dlg.ShowModal() # Shows it
		dlg.Destroy() # finally destroy it when finished.

	def todoFileOpen(self, fullFileName=''):
		#print ("0. taskManager: init - self.todoFile = ", self.todoFile)

		if fullFileName != '':
			self.todoFile = os.path.expanduser(fullFileName)
		elif os.path.isfile(os.path.expanduser('./todo.txt')):
			self.todoFile = os.path.expanduser('./todo.txt')
		elif os.path.isfile(os.path.expanduser('~/todo.txt')):
			self.todoFile = os.path.expanduser('~/todo.txt')
		else:
			self.todoFile = os.path.expanduser('./todotest.txt')
		
		#print ("1. taskManager: init - self.todoFile = ", self.todoFile)
		self.todo = todo(self.todoFile)

		#print ("self.todo.fileError = ", self.todo.fileError)
		if self.todo.fileError == False:
			self.dirName = os.path.dirname(self.todoFile)
			self.fileName = os.path.basename(self.todoFile)
			self.todoFile = os.path.abspath(self.todoFile)
			self.setTaskManagerTitle()

			self.taskList.DeleteAllItems()
			self.setTodoTasks()
			self.populateTasks()

		return self.todo.fileError

	def fileOpen(self, event=None):
		result = self.saveIfModified()
		if result != None: #None => Aborted or Save cancelled, False => Discarded, True => Saved or Not modified
			dlg = wx.FileDialog(self, "Choose a todo.txt file to open", self.dirName, "", "*.txt", wx.FD_OPEN)
			if dlg.ShowModal() == wx.ID_OK:
				self.fileName = dlg.GetFilename()
				self.dirName = dlg.GetDirectory()
				fullFileName = os.path.join(self.dirName, self.fileName)
				try:
					#print ("fileOpen: opening ", fullFileName)
					self.openTodoFileAndSetStatus(fullFileName)
				except OSError:
					dlg = wx.MessageDialog (self, "Error: File "+fullFileName+" could not be opened.", caption="File Open Error", style = wx.OK)
					dlg.ShowModal()
					print("Error: File could not be opened for read.")
			#endif
			dlg.Destroy()
		#endif

	def saveIfModified(self, event=None):
		#None => Aborted or Save cancelled, False => Discarded, True => Saved or Not modified
		#if result is None, then user does not want to close window
		#skipping event will continue to default handler which will close the window

		if self.taskContentsDirty == True: #modified
			dlg = wx.MessageDialog (self, "Task Manager has unsaved tasks that will be lost if not saved.", caption="Unsaved contents!", style = wx.YES_NO|wx.CANCEL)
			dlg.SetYesNoCancelLabels("&Save", "&Discard Unsaved Changes", "&Go Back to Task Manager")
			response = dlg.ShowModal()
			if response == wx.ID_YES: #yes/save
				result = self.fileSave()
				if result == True: #saved
					return True
				else: #save cancelled
					return None
			elif response == wx.ID_NO: #discard
				return False
			else: #wx.ID_CANCEL -- save cancelled
				return None #cancel/abort, False = no/discard
		else: #not modified
			return True

	def makeTodoLine (self, due):
		task = self.todoTasksDueDate[due]
		(dueDate, hasError, completed, completionDate, allCompleted,
			priority, creationDate,
			recurrenceCount, recurrenceUnit, 
			recurrenceType2Nth, recurrenceType2Day, 
			recurrenceType2Unit, contexts, projects) = self.todoTasksTask[task]

		_DEBUG1 ("task = ", task)
		_DEBUG1 ("\thasError = ", hasError)
		_DEBUG1 ("\tcompleted =", completed)
		_DEBUG1 ("\tcompletionDate =", completionDate)
		_DEBUG1 ("\tallCompleted =", allCompleted)
		_DEBUG1 ("\tpriority = ", priority)
		_DEBUG1 ("\tcreationDate =", creationDate)
		_DEBUG1 ("\tdueDate  =", dueDate)
		_DEBUG1 ("\trecurrenceCount =", recurrenceCount)
		_DEBUG1 ("\trecurrenceUnit =", recurrenceUnit)
		_DEBUG1 ("\trecurrenceType2Nth =", recurrenceType2Nth)
		_DEBUG1 ("\trecurrenceType2Day =", recurrenceType2Day)
		_DEBUG1 ("\trecurrenceType2Unit  =", recurrenceType2Unit)

		completionMarker = ''
		if allCompleted:
			completionMarker = '#x '
		elif completed:
			completionMarker = 'x '

		priority =  priority.strip()
		completionDate =  completionDate.strip()
		creationDate =  creationDate.strip()
		task =  task.strip() + ' '
		dueDate =  dueDate.strip()

		if priority != '':
			priority += ' '
		if completionDate != '':
			completionDate += ' '
		if creationDate != '':
			creationDate += ' '
		if dueDate != '':
			dueDate = 'due:'+dueDate+' '

		recSpecs = ''
		if recurrenceCount != '':
			recSpecs = 'rec:'+recurrenceCount+recurrenceUnit
		elif recurrenceType2Nth != '':
			recSpecs = 'rec:'+recurrenceType2Nth + '-' + recurrenceType2Day + '-' + recurrenceType2Unit
		text = f'{completionMarker}{priority}{completionDate}{creationDate}{task}{dueDate}{recSpecs}'

		for e in contexts:
			text += ' @'+e
		for e in projects:
			text += ' +'+e

		return text.strip()
		
	def fileSave(self, event=None):
		if self.fileName == '' or self.taskContentsDirty == False:
			return False
		try:
			with open(os.path.join(self.dirName, self.fileName), 'w', encoding="utf8") as f:
				for key in self.todoTasksDueDate.keys():
					text = self.makeTodoLine(key)
					_DEBUG1 (text)
					f.write(text + '\n')
				for text in self.todoFileComments:
					#print (text)
					f.write(text + '\n')
				self.taskContentsDirty = False
				self.setTaskManagerTitle()
				return True
		except OSError:
			dlg = wx.MessageDialog (self, "Error: File could not be saved.", caption="File Save Error", style = wx.OK)
			dlg.ShowModal()
			print("Error: File could not be saved.")
			return False

	def rightClickHandler(self, event):
		# Get TreeItemData
		item = event.GetIndex()
		itemData = self.taskList.GetItemText(item, 1)
		# Create menu
		popupmenu = wx.Menu()
		entries = ['Complete Task', 'Delete Task', 'Edit Task']
		for entry in entries:
		    menuItem = popupmenu.Append(-1, entry)
		    wrapper = lambda event: self.rightClickMenuHandler(event)
		    self.Bind(wx.EVT_MENU, wrapper, menuItem)
		
		# Show menu
		self.PopupMenu(popupmenu, event.GetPoint())

	def rightClickMenuHandler(self, event):
		idSelected = event.GetId()
		obj = event.GetEventObject()
		label = obj.GetLabel(idSelected)

		if label == 'Delete Task':
			self.menuDeleteTaskHandler()
		elif label == 'Edit Task':
			self.editTaskButtonHandler()
		elif label == 'Complete Task':
			self.completeTaskButtonHandler()

	def fileQuit(self, event=None):
		self.fileSave()
		self.Destroy()

	def fontSelect (self, event=None):
		data = wx.FontData()
		data.SetInitialFont(self.fontInformation)
		dialog = wx.FontDialog(self, data)
		if dialog.ShowModal() == wx.ID_OK:
			self.fontInformation = dialog.GetFontData().GetChosenFont()
			self.taskList.SetFont(self.fontInformation)
			#for search and searchTasks bars, limit font size
			if self.fontInformation.GetPointSize() > 72:
				self.fontInformation.SetPointSize(72)
			elif self.fontInformation.GetPointSize() < 10:
				self.fontInformation.SetPointSize(10)
			self.searchTasksBar.SetFont(self.fontInformation)
			self.Refresh()

	def showEditTasksDialog (self, todoTasksTask = '', todoTasksDetails = ()):
		#print ("%%%%%%%% showEditTasksDialog: ", todoTasksDetails)
		newTaskDialog = editTaskDialog(self, todoTasksTask, todoTasksDetails)
		newTaskDialog.ShowModal()
		#print ("Got new task: ", self.newtodoTasksTask[list(self.newtodoTasksTask.keys())[0]])
		#print ("Got new due date: ", self.newTodoTasksDueDate)
		#print ("OLD task: ", self.todoTasksTask[self.selectedTask])
		#if self.newtodoTasksTask[list(self.newtodoTasksTask.keys())[0]] == self.todoTasksTask[self.selectedTask]:
			#print ("old and new events are same")
		#print ("OLD due date: ", self.todoTasksDueDate)
		editMode = todoTasksTask != ''
		self.addTasks(editMode)
		self.populateTasks()

	def addTasks (self, editMode=False):
		#adds newtodoTasksTask to todoTasksTask and
		#newTodoTasksDueDate to todoTasksDueDate

		if self.newtodoTasksTask != {}:
			if editMode:
				#delete the old key
				for dd in self.todoTasksDueDate.keys():
					if self.todoTasksDueDate[dd] == self.selectedTask:
						del self.todoTasksDueDate[dd]
						break
				del self.todoTasksTask[self.selectedTask]
				
			key = list(self.newtodoTasksTask.keys())[0]
			self.todoTasksTask[key] = self.newtodoTasksTask[key]
			self.taskContentsDirty = True
			_DEBUG ("~~~ New key added = ", key)
			_DEBUG ("~~~ self.todoTasksTask = ", self.todoTasksTask)
			_DEBUG ("~~~ self.newtodoTasksTask[key] = ", key, self.newtodoTasksTask[key])

			key = list(self.newTodoTasksDueDate.keys())[0]
			originalKey = key
			if key in self.todoTasksDueDate.keys():
				originalKey = key
				key += '$' #append a uniquifying char
				while key in self.todoTasksDueDate.keys():
					key += '$'
			self.todoTasksDueDate[key] = self.newTodoTasksDueDate[originalKey]

			self.newtodoTasksTask = {}
			self.newTodoTasksDueDate = {}

	def newTaskButtonHandler (self, event=None):
		#print ("~~~~~~~~~~~~~~~~ newTaskButtonHandler")
		self.showEditTasksDialog()

	def editTaskButtonHandler (self, event=None):
		#print ("editTaskButtonHandler", self.todoTasksTask[self.selectedTask])
		selectedItemCount = self.taskList.GetSelectedItemCount()
		#print ("editTaskButtonHandler: selectedItemCount = ", selectedItemCount)
		if selectedItemCount > 1:
			dlg = wx.MessageDialog(None, 'Please select only one task to edit', 'Task Edit', wx.OK )
			dlg.ShowModal()
			dlg.Destroy()
			return
		if self.selectedTask == '':
			self.showEditTasksDialog() #new task
		else:
			self.showEditTasksDialog(self.selectedTask, self.todoTasksTask[self.selectedTask])

	def menuDeleteTaskHandler (self, event=None):
		selectedItemCount = self.taskList.GetSelectedItemCount()
		if selectedItemCount == 0:
			return
		dlg = wx.MessageDialog (self, 
			'Are you sure want to delete '+str(selectedItemCount)+(' task.' if selectedItemCount == 1 else ' tasks.'), 
			caption="Confirm Task Delete", style = wx.OK | wx.CANCEL).ShowModal()
		#print ("-- dlg returned ", dlg, " ... dlg == wx.ID_OK = ", dlg == wx.ID_OK)
		if dlg == wx.ID_OK:
			selectedTasksList = []
			index = -1
			while True:
				index = self.taskList.GetNextItem(index,
									wx.LIST_NEXT_ALL,
									wx.LIST_STATE_SELECTED)
				if index == -1:
					break
				else:
					selectedTasksList.append(self.taskList.GetItemText(index, 1))
			if selectedTasksList != []:
				#print ("menuDeleteTaskHandler: before delete loop, todoTasksTask is ", self.todoTasksTask)
				for task in selectedTasksList:
					#print ("task to delete: ", task)
					#print ("dueDate for task to delete: ", dueDate, "len of dueDate", len(dueDate))
					for dd in self.todoTasksDueDate.keys():
						if self.todoTasksDueDate[dd] == task:
							text = '##-'+self.makeTodoLine(dd)
							self.todoFileComments.append(text)
							del self.todoTasksDueDate[dd]
							break
					del self.todoTasksTask[task]

					#print ("\nAdded ", text, " to comments.")
					
			#print ("Deleted tasks are: ", selectedTasksList)
			#print ("After deletion todoTasksDueDate dict is : ", self.todoTasksDueDate)
			self.taskContentsDirty = True
			self.populateTasks(skipTagsRedraw=True)
		#endif
	#enddef
#endclass

def TaskManagerCoreEntryPoint ():
	todoFile = ''
	if len(sys.argv) > 1:
		todoFile = sys.argv[1]
	#print ("todoFile = ", todoFile)

	#app = wx.App(redirect=True)
	app = wx.App(redirect=False)

	if getattr(sys, 'frozen', False):
		appPath = os.path.dirname(sys.executable)
	elif __file__:
		appPath = os.path.dirname(__file__)

	frame = taskManager(title="TaskManager", 
			todoFile=todoFile)
	frame.SetIcon(wx.Icon(os.path.abspath(appPath+"/task.ico")))
	frame.Show()
	#wx.lib.inspection.InspectionTool().Show()
	app.MainLoop()

#main
if __name__ == "__main__":
	TaskManagerCoreEntryPoint()

#endif main
