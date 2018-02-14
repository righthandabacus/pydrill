#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:set ts=4 sw=4 et:

from __future__ import print_function
import logging
import threading
import math
import Tkinter as tk
import random
import time
import speech_recognition as sr

# global variable
threadpool = []
appstop = False

class drillengine(object):
    '''
    Holds logic for drill question and updates
    '''
    def __init__(self):
        self.ui = None
        # initialize speech recognition
        self.r = sr.Recognizer()
        self.m = sr.Microphone()
        self.r.pause_threshold = 0.3
        self.r.non_speaking_duration = 0.3
    def use_ui(self, ui):
        self.ui = ui
    def stop(self):
        "when called, whole app stop"
        global appstop
        appstop = True
    def get_question(self):
        "Question generator: single digit multiplication"
        a = random.randrange(1,9+1)
        b = random.randrange(1,9+1)
        question = u"%d × %d" % (a,b)
        return question, str(a*b)
    def counter(self):
        "Update the timer every one second"
        logging.info('Counter launched')
        while not appstop:
            now = time.time()
            if not self.paused and now - self.timerstart > self.timerelapsed:
                self.timerelapsed = int(math.ceil(now - self.timerstart))
                self.ui.curseconds = max(0, self.timerbase - self.timerelapsed)
            time.sleep(0.2)
        logging.info('Counter stopping')
    def run(self):
        logging.info('Engine launched')
        if self.ui is None:
            logging.error("Cannot run without a UI engine specified")
            return
        self.paused = True
        timerthread = threading.Thread(target=self.counter)
        timerthread.start()
        threadpool.append(timerthread)
        while not appstop:
            # generate one question, then wait for answer
            qtext, answer = self.get_question()
            self.ui.question = qtext
            self.ui.answer = '?'
            # reset timer
            self.timerstart = time.time()
            self.timerbase = 10 # number of seconds for this
            self.timerelapsed = 0 # number of seconds elapsed
            self.paused = False
            # microphone, recognize, check answer, report
            is_correct = None # True/False if answered
            while not appstop and time.time() - self.timerstart <= self.timerbase:
                with self.m as source:
                    audio = self.r.listen(source)
                    logging.debug(audio)
                try:
                    value = self.r.recognize_google(audio, show_all=True)
                    # relax verification, if any match in recognized data
                    # format: value = {'final':True, 'alternative':[
                    #                    {'confidence':0.49282876, 'transcript':'27'},
                    #                    {'transcript': '97'}, {'transcript': 'how to 7'}, ...
                    #                  ]}
                    if not value:
                        continue
                    logging.debug(value)
                    candidates = [z for x in value['alternative'] for z in x['transcript'].split() if z.isdigit()]
                    logging.debug("-> %s" % candidates)
                    if not candidates:
                        continue # no valid answer recorded, retry reading
                    self.paused = True # stop timer
                    if answer in candidates:
                        is_correct = True
                        self.ui.answer = answer
                    else:
                        is_correct = False
                        self.ui.answer = candidates[0] + ' (wrong!)'
                        self.ui.anslabel.config(fg='red')
                    break # proceed to next question
                except sr.UnknownValueError:
                    logging.warning("Didn't catch!")
                except sr.RequestError as e:
                    logging.exception("Google Speech Recognition Service fail: {0}".format(e))
                    self.ui.quit()
            self.ui.sumseconds = self.ui.sumseconds + int(time.time() - self.timerstart)
            time.sleep(1) # wait for answer to display
            if is_correct == True:
                self.ui.ncorrect = self.ui.ncorrect + 1
            elif is_correct == False:
                self.ui.nwrong = self.ui.nwrong + 1
                self.ui.anslabel.config(fg='black')
        logging.info('Engine stopped')

class drill(tk.Frame, object): # need new style class for @property
    '''
    Dumb UI, no logic in it
    '''
    def __init__(self, root, engine):
        tk.Frame.__init__(self, root)
        # variables first
        self._ncorrect = None
        self._nwrong = None
        self._sumseconds = None
        self._curseconds = None
        self._question = None
        self._answer = None
        # GUI set up
        self._engine = engine
        self.pack(fill=tk.BOTH, expand=True) # frame fill the whole root
        self.bind("<Escape>", self.on_key) # hook up key event
        self._create_widgets()
        self.focus_set()
        self._engine.use_ui(self)

    def mainloop(self):
        enginethread = threading.Thread(target=self._engine.run)
        enginethread.start()
        threadpool.append(enginethread)
        tk.Frame.mainloop(self)

    @property
    def ncorrect(self):
        return self._ncorrect
    @ncorrect.setter
    def ncorrect(self, value):
        assert(isinstance(value, int))
        self._ncorrect = value
        if not appstop:
            self.correct.set("Correct: %d" % self.ncorrect)

    @property
    def nwrong(self):
        return self._nwrong
    @nwrong.setter
    def nwrong(self, value):
        assert(isinstance(value, int))
        self._nwrong = value
        if not appstop:
            self.wrong.set("Wrong: %d" % self.nwrong)

    @property
    def sumseconds(self):
        return self._sumseconds
    @sumseconds.setter
    def sumseconds(self, value):
        assert(isinstance(value, int))
        self._sumseconds = value
        secpart = self._sumseconds % 60
        minpart = self._sumseconds / 60
        if not appstop:
            self.sumtime.set("%02d:%02d" % (minpart, secpart))

    @property
    def curseconds(self):
        return self._curseconds
    @curseconds.setter
    def curseconds(self, value):
        assert(isinstance(value, int))
        self._curseconds = value
        secpart = self._curseconds % 60
        minpart = self._curseconds / 60
        if not appstop:
            self.curtime.set("%02d:%02d" % (minpart, secpart))

    @property
    def question(self):
        return self._question
    @question.setter
    def question(self, string):
        assert(isinstance(string, basestring))
        self._question = string
        if not appstop:
            self.qtext.set(string)

    @property
    def answer(self):
        return self._answer
    @answer.setter
    def answer(self, string):
        assert(isinstance(string, basestring))
        self._answer = string
        if not appstop:
            self.atext.set(string)

    def on_key(self, event):
        if event.char == '\x1b':
            logging.warning("Closing")
            self.quit()

    def quit(self):
        self._engine.stop()
        self.winfo_toplevel().destroy()
        for thread in threadpool:
            thread.join()

    def _create_widgets(self):
        # grid weights
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=5)
        self.rowconfigure(3, weight=5)
        self.rowconfigure(4, weight=3)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.columnconfigure(2, weight=1)
        # widgets: text on label are editable by a StringVar
        self.correct = tk.StringVar()
        self.ncorrect = 0
        tk.Label(self, textvariable=self.correct, font=('Verdana','16')).grid(column=2, row=0)

        self.wrong = tk.StringVar()
        self.nwrong = 0
        tk.Label(self, textvariable=self.wrong, font=('Verdana','16')).grid(column=2, row=1)

        self.sumtime = tk.StringVar()
        self.sumseconds = 0
        tk.Label(self, textvariable=self.sumtime, font=('Verdana','16')).grid(column=0, row=0)

        self.curtime = tk.StringVar()
        self.curseconds = 0
        tk.Label(self, textvariable=self.curtime, font=('Verdana','16')).grid(column=1, row=4)

        self.qtext = tk.StringVar()
        self.question = '2 x 2'
        tk.Label(self, textvariable=self.qtext, font=('Verdana','48')).grid(column=1, row=2)

        self.atext = tk.StringVar()
        self.answer = '?'
        self.anslabel = tk.Label(self, textvariable=self.atext, font=('Verdana','48'))
        self.anslabel.grid(column=1, row=3)

def main():
    root = tk.Tk()
    root.title("Drill")
    root.geometry("800x600+0+0")
    root.option_readfile('option.tkinter')
    #root.overrideredirect(1) # cannot hide the frame or event fails
    engine = drillengine()
    app = drill(root, engine)
    app.mainloop()

if __name__ == "__main__":
    logging.getLogger('').setLevel(logging.DEBUG)
    main()
