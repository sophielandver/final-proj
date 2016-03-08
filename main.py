import flask
from flask import render_template
from flask import request
from flask import url_for
import uuid

import json
import logging

# Date handling 
import arrow # Replacement for datetime, based on moment.js
import datetime # But we still need time
from dateutil import tz  # For interpreting local times


# OAuth2  - Google library implementation for convenience
from oauth2client import client
import httplib2   # used in oauth2 flow

# Google API for services 
from apiclient import discovery

from agenda import *
# Mongo database
from pymongo import MongoClient
from bson.objectid import ObjectId


###
# Globals
###
import CONFIG
app = flask.Flask(__name__)



try: 
    dbclient = MongoClient(CONFIG.MONGO_URL)
    db = dbclient.meetme #meetme is name of database that you created 
    collection = db.meet  #dated is name of collection. you are creating this collection right now

except:
    print("Failure opening database.  Is Mongo running? Correct password?")
    sys.exit(1)

SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = CONFIG.GOOGLE_LICENSE_KEY  ## You'll need this
APPLICATION_NAME = 'MeetMe class project'


"""
Format of flask.session['busy_list']:  (it's a list of dicts)
[{"desc": "Gym", "being": '2016-03-22T13:45:00-08:00', "end": '2016-03-22T15:45:00-08:00'},
 {"desc": "homework", "being": '2016-03-22T15:45:00-08:00', "end": '2016-03-22T18:45:00-08:00'},
 ...]
 
Format of flask.session['free_list']:   (it's a list of dicts)
[{"desc": "Available", "being": '2016-05-22T13:45:00-08:00', "end": '2016-05-22T15:45:00-08:00', "id": 0},
 {"desc": "Available", "being": '2016-06-22T15:45:00-08:00', "end": '2016-06-22T18:45:00-08:00', "id": 1},
 ...]

"""

#############################
#
#  Pages (routed from URLs)
#
#############################

@app.route("/")
@app.route("/index")
def index():
    """
    The user has navigated to the proposer's page, i.e. the 
    page where a meeting proposal is initiated. 
    """
    app.logger.debug("Entering index")
    if 'begin_date' not in flask.session:
        init_session_values()
    return render_template('index.html')
  
  
@app.route("/participant/<proposal_id>")
def participant(proposal_id):
    """
    The user has navigated to the participant's page, i.e.
    the page where a user responds to a meeting proposal that
    was sent to him/her. We right away grab the proposal_id from 
    the URL and use it to get the meeting's begin date, end date, 
    begin time, and end time from the database. Then, we store the 
    propsal_id, meeting begin date, end date, begin time, and end time
    in the session object. In addition, we store the string "True" 
    in flask.session['is_participant']. 
    """
    flask.session['proposal_id'] = proposal_id
    flask.session['is_participant'] = "True"
    for record in collection.find( { "type": "proposal", "_id": flask.session['proposal_id'] } ):
        flask.session['begin_date'] = record['start_date']
        flask.session['end_date'] = record['end_date']
        flask.session['begin_time'] = record['start_time']
        flask.session['end_time'] = record['end_time']
    return render_template('participant.html')
    

@app.route("/choose")
def choose():
    ## We'll need authorization to list calendars 
    ## I wanted to put what follows into a function, but had
    ## to pull it back here because the redirect has to be a
    ## 'return' 
    app.logger.debug("Checking credentials for Google calendar access")
    credentials = valid_credentials()
    if not credentials:
      app.logger.debug("Redirecting to authorization")
      return flask.redirect(flask.url_for('oauth2callback'))

    gcal_service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")
    flask.session['calendars'] = list_calendars(gcal_service)
    
    if flask.session['is_participant'] == "True":
        return render_template('participant.html')
    else:
        return render_template('index.html')

####
#
#  Google calendar authorization:
#      Returns us to the main /choose screen after inserting
#      the calendar_service object in the session state.  May
#      redirect to OAuth server first, and may take multiple
#      trips through the oauth2 callback function.
#
#  Protocol for use ON EACH REQUEST: 
#     First, check for valid credentials
#     If we don't have valid credentials
#         Get credentials (jump to the oauth2 protocol)
#         (redirects back to /choose, this time with credentials)
#     If we do have valid credentials
#         Get the service object
#
#  The final result of successful authorization is a 'service'
#  object.  We use a 'service' object to actually retrieve data
#  from the Google services. Service objects are NOT serializable ---
#  we can't stash one in a cookie.  Instead, on each request we
#  get a fresh serivce object from our credentials, which are
#  serializable. 
#
#  Note that after authorization we always redirect to /choose;
#  If this is unsatisfactory, we'll need a session variable to use
#  as a 'continuation' or 'return address' to use instead. 
#
####

def valid_credentials():
    """
    Returns OAuth2 credentials if we have valid
    credentials in the session.  This is a 'truthy' value.
    Return None if we don't have credentials, or if they
    have expired or are otherwise invalid.  This is a 'falsy' value. 
    """
    if 'credentials' not in flask.session:
      return None

    credentials = client.OAuth2Credentials.from_json(
        flask.session['credentials'])

    if (credentials.invalid or
        credentials.access_token_expired):
      return None
    return credentials


def get_gcal_service(credentials):
  """
  We need a Google calendar 'service' object to obtain
  list of calendars, busy times, etc.  This requires
  authorization. If authorization is already in effect,
  we'll just return with the authorization. Otherwise,
  control flow will be interrupted by authorization, and we'll
  end up redirected back to /choose *without a service object*.
  Then the second call will succeed without additional authorization.
  """
  app.logger.debug("Entering get_gcal_service")
  http_auth = credentials.authorize(httplib2.Http())
  service = discovery.build('calendar', 'v3', http=http_auth)
  app.logger.debug("Returning service")
  return service

@app.route('/oauth2callback')
def oauth2callback():
  """
  The 'flow' has this one place to call back to.  We'll enter here
  more than once as steps in the flow are completed, and need to keep
  track of how far we've gotten. The first time we'll do the first
  step, the second time we'll skip the first step and do the second,
  and so on.
  """
  app.logger.debug("Entering oauth2callback")
  flow =  client.flow_from_clientsecrets(
      CLIENT_SECRET_FILE,
      scope= SCOPES,
      redirect_uri=flask.url_for('oauth2callback', _external=True))
  ## Note we are *not* redirecting above.  We are noting *where*
  ## we will redirect to, which is this function. 
  
  ## The *second* time we enter here, it's a callback 
  ## with 'code' set in the URL parameter.  If we don't
  ## see that, it must be the first time through, so we
  ## need to do step 1. 
  app.logger.debug("Got flow")
  if 'code' not in flask.request.args:
    app.logger.debug("Code not in flask.request.args")
    auth_uri = flow.step1_get_authorize_url()
    return flask.redirect(auth_uri)
    ## This will redirect back here, but the second time through
    ## we'll have the 'code' parameter set
  else:
    ## It's the second time through ... we can tell because
    ## we got the 'code' argument in the URL.
    app.logger.debug("Code was in flask.request.args")
    auth_code = flask.request.args.get('code')
    credentials = flow.step2_exchange(auth_code)
    flask.session['credentials'] = credentials.to_json()
    ## Now I can build the service and execute the query,
    ## but for the moment I'll just log it and go back to
    ## the main screen
    app.logger.debug("Got credentials")
    return flask.redirect(flask.url_for('choose'))


@app.route('/setParticName', methods=['POST'])
def setParticName():
    """
    The participant has entered in his/her name. We save this
    name in the session object, for now, and then redirect the user 
    to the calendar selection. 
    """
    name = request.form.get('name')
    flask.session['name'] = name
    return flask.redirect(flask.url_for("choose"))

@app.route('/setrange', methods=['POST'])
def setrange():
    """
    User chose a date range with the bootstrap daterange
    widget and a time range with a time picker widget. This
    function stores the begin date, end date, start time, and 
    end time in the session object. It also stores the original
    date range and time range in the session object as a simple
    string so that it can be displayed to the user every time 
    the page reloads. 
    """
    app.logger.debug("Entering setrange")  
    flask.flash("Setrange gave us '{}'".format(
      request.form.get('daterange')))
    daterange = request.form.get('daterange')
    starttime = request.form.get('starttime')
    endtime = request.form.get('endtime')
    name = request.form.get('name')
    flask.session['name'] = name
    flask.session['daterange'] = daterange
    flask.session['text_beg_time'] = starttime
    flask.session['text_end_time'] = endtime
    daterange_parts = daterange.split()
    flask.session['begin_date'] = interpret_date(daterange_parts[0])
    
    app.logger.debug(flask.session['begin_date'])
    
    flask.session['end_date'] = interpret_date(daterange_parts[2])
    flask.session['begin_time'] = interpret_time(starttime)
    flask.session['end_time'] = interpret_time(endtime)
    flask.session['is_participant'] = "False"
    
    app.logger.debug("Setrange parsed {} - {}  dates as {} - {}".format(
      daterange_parts[0], daterange_parts[1], 
      flask.session['begin_date'], flask.session['end_date']))
    app.logger.debug("Set time range from {} - {} TO {} - {}".format(starttime, endtime, flask.session['begin_time'], flask.session['end_time']))
    return flask.redirect(flask.url_for("choose"))


@app.route('/calcBusyFreeTimes')
def calcBusyFreeTimes():
    """
    Once the user has selected the google calendars he wants to use and clicks the 
    'Calculate Busy & Free Times' button this function gets invoked. This function stores in 
    the session object a list of calendar ids, the calendar ids of the calendars the user
    selected. Then, this function calls find_busy() which goes through the list of 
    calendar ids and finds the times in the time span in which the user cannot meet. In 
    addition, this function calls find_free which finds the times in the time span in which
    the user can meet.  
    """
    selected_cal = request.args.getlist("selected[]")
    flask.session['selected_cal'] = selected_cal
    find_busy() #a list of dicts. Finds busy_list
    find_free() #a list of dicts. Finds free_list
    return "nothing"
    
@app.route('/EliminateCandidate')  
def eliminateCandidate():
    """
    The user has checked the "available" times in which he can meet 
    and has pressed "submit". We obtain a revised free list by going 
    through the current free_list and only keeping the available times
    which the user has checked. Then, we store the user's information
    in the database. 
    """
    selected_candidates = request.args.getlist("selected[]")
    flask.session['selected_candidates'] = selected_candidates
    deleteCandidatesFromFree() #now we have revised_free
    if flask.session['is_participant'] == "True":
        storeParticipantInfoInDB()
    else:
        storeProposerInfoInDB()     
    return "nothing"

@app.route('/participantFinish')
def participantFinish():
    """
    We are done collecting and storing, in the database, all 
    the needed information from the participant. Now we create a 
    nice displayable list of free times and then render template participant.html.
    """
    flask.session['display_revised_free'] = createDisplayAptList(flask.session['revised_free'])
    return render_template('participant.html')

@app.route('/proposerFinish')
def proposerFinish():
    """
    We are done collecting and storing, in the database, all 
    the needed information from the proposer. Now we create a nice
    displayable list of free times and the URL to give the proposer
    so that he/she can give the URL to the people he/she wants to meet with.
    Finally we render template index.html.
    """
    #give free list to be displayed 
    #now render index.html cuz now have revised_free and proposal_id
    flask.session['display_revised_free'] = createDisplayAptList(flask.session['revised_free'])
    if CONFIG.PORT == 5000: #on my machine
        url = "localhost:5000/participant/" + flask.session['proposal_id']
    if CONFIG.PORT == 8342: #on ix
        url = "ix.cs.uoregon.edu:8342/participant/" + flask.session['proposal_id']
    flask.session['participant_url'] = url
    return render_template('index.html')

@app.route('/status')
def status():
    """
    The user has clicked the "show current meeting status" button in 
    participant.html and now we collect the meeting info (i.e. the start date,
    end date, start time, and end time of the meeting), the intersected free times
    amongst all the people who have currently responded, and the names of all the 
    people who have currently responded from the database. Finally we render
    template status.html.
    """
    createDisplayMeetingInfo()
    createDisplayIntersectedTimes()
    createDisplayResponders()
    return render_template('status.html')
    
@app.route('/backToPartic')
def backToPartic():
    """
    The user has clicked the "back" button on status.html. 
    We redirect the user back to participant.html. 
    """
    return render_template('participant.html')


@app.route('/displayBusyFreeTimes')
def displayBusyFreeTimes():
    """
    This function gets called once the busy and free times have been calculated and we are 
    ready to display them to the user. This function displays the busy and free times to 
    the user in sorted order by begin date/time.
    """
    createDisplayFreeBusyTimes()
    if flask.session['is_participant'] == "True":
        return render_template('participant.html')
    else:
        return render_template('index.html')
        
##############################################
#
# Functions for creating nice displayable formats 
#
##############################################

def createDisplayIntersectedTimes():
    """
    This function stores, in the session object, a nice 
    displayable list of the intersected free times amongst 
    all the current responders. 
    """
    for record in collection.find({ "type": "proposal", "_id": flask.session['proposal_id'] }):
        free_times = record['free_times']
    begin_date = arrow.get(flask.session['begin_date'])
    end_date = arrow.get(flask.session['end_date'])
    begin_time = arrow.get(flask.session['begin_time'])
    end_time = arrow.get(flask.session['end_time'])
    total = Agenda.timeSpanAgenda(begin_date, end_date, begin_time, end_time)
    for apt_list in free_times:
        agenda = Agenda.from_list(apt_list)
        total = total.intersect(agenda, desc="Available")
    total_list = total.to_list()
    flask.session['display_intersected'] = createDisplayAptList(total_list)

def createDisplayResponders():
    """
    This function stores, in the session object, a displayable list 
    of the names of all the current responders of this proposal. 
    """
    for record in collection.find({ "type": "proposal", "_id": flask.session['proposal_id'] }):
        responders = record['responders']
    flask.session['display_responders'] = responders
    
def createDisplayMeetingInfo():
    """
    This function stores, in the session object, a string containing 
    the date range of the meeting and a string containing the time 
    range of the proposed meeting. 
    """
    begin_date = arrow.get(flask.session['begin_date']).to('local')
    begin_date = begin_date.format('MM/DD/YYYY')
    end_date = arrow.get(flask.session['end_date']).to('local')
    end_date = end_date.format('MM/DD/YYYY')
    begin_time = arrow.get(flask.session['begin_time']).to('local')
    begin_time = begin_time.format('h:mm A')
    end_time = arrow.get(flask.session['end_time']).to('local')
    end_time = end_time.format('h:mm A')
    info_str1 = "Meeting date range is from " + begin_date + " to " + end_date + "."
    info_str2 = "Meeting time range is from " + begin_time + " to " + end_time + "."  
    flask.session['meeting_info1'] = info_str1
    flask.session['meeting_info2'] = info_str2

def createDisplayFreeBusyTimes():
    """
    This function stores, in the session object, a list of strings for 
    displaying the busy and free times in order by begin date/time. 
    """
    free_busy = []
    for busy_dict in flask.session['busy_list']:
        free_busy.append(busy_dict)
    for free_dict in flask.session['free_list']:
        free_busy.append(free_dict)
    free_busy.sort(key=lambda r: r['begin']) #sort by begin date    
    
    flask.session['display_free_busy'] = createDisplayAptList(free_busy)


def createDisplayAptList(apt_list):
    """
    This function takes in a list of appointments and returns a list of strings representing
    the appointments, where the strings are suited for displaying. 
    Arguments:
        apt_list: a list of dictionaries either in the format of busy_list or in 
                  the format of free_list 
                  (see above for a detailed description of the format of busy_list and free_list)
    Returns: a list of strings representing appointments. 
    """
    display_apt_list = [] #list of dicts
    for apt in apt_list:
        info = {}
        if "id" in apt and apt['desc'] == "Available":
            info['id'] = apt['id']
        info['desc'] = apt['desc']
        apt_str = ""
        apt_str = apt_str + apt['desc'] + ": "
        apt_str = apt_str + convertDisplayDateTime(apt['begin']) + " - "
        apt_str = apt_str + convertDisplayDateTime(apt['end']) 
        info['display'] = apt_str
        display_apt_list.append(info)
        
    return display_apt_list
    
def convertDisplayDateTime(date_time):
    """
    This function takes in an isoformat() string, makes it into an arrow object, converts it to the 
    local time of the server, and then returns it as a formatted string for displaying in the
    form MM/DD/YYYY h:mm A. We use this function every time before we want to display a time 
    to the user.
    Arguments:
        date_time: an isoformat string 
    Returns: a string in the form 'MM/DD/YYYY h:mm A'
    """
    arrow_date_time = arrow.get(date_time)
    local_arrow = arrow_date_time.to('local')
    formatted_str = local_arrow.format('MM/DD/YYYY h:mm A')
    return formatted_str


def list_calendars(service):
    """
    Given a google 'service' object, return a list of
    calendars.  Each calendar is represented by a dict, so that
    it can be stored in the session object and converted to
    json for cookies. The returned list is sorted to have
    the primary calendar first, and selected (that is, displayed in
    Google Calendars web app) calendars before unselected calendars.
    """
    app.logger.debug("Entering list_calendars")  
    calendar_list = service.calendarList().list().execute()["items"]
    result = [ ]
    for cal in calendar_list:
        kind = cal["kind"]
        id = cal["id"]
        app.logger.debug("HERE IS CALENDAR ID: {}". format(id))
        if "description" in cal: 
            desc = cal["description"]
        else:
            desc = "(no description)"
        summary = cal["summary"]
        # Optional binary attributes with False as default
        selected = ("selected" in cal) and cal["selected"]
        primary = ("primary" in cal) and cal["primary"]
        

        result.append(
          { "kind": kind,
            "id": id,
            "summary": summary,
            "selected": selected,
            "primary": primary
            })
    return sorted(result, key=cal_sort_key)


def cal_sort_key( cal ):
    """
    Sort key for the list of calendars:  primary calendar first,
    then other selected calendars, then unselected calendars.
    (" " sorts before "X", and tuples are compared piecewise)
    """
    if cal["selected"]:
       selected_key = " "
    else:
       selected_key = "X"
    if cal["primary"]:
       primary_key = " "
    else:
       primary_key = "X"
    return (primary_key, selected_key, cal["summary"])
        
            

####
#
#   Initialize session variables 
#
####

def init_session_values():
    """
    Start with some reasonable defaults for date and time ranges.
    Note this must be run in app context ... can't call from main. 
    """
    # Default date span = tomorrow to 1 week from now
    now = arrow.now('local')
    tomorrow = now.replace(days=+1)
    nextweek = now.replace(days=+7)
    flask.session["begin_date"] = tomorrow.floor('day').isoformat()
    flask.session["end_date"] = nextweek.ceil('day').isoformat()
    flask.session["daterange"] = "{} - {}".format(
        tomorrow.format("MM/DD/YYYY"),
        nextweek.format("MM/DD/YYYY"))
    # Default time span each day, 8 to 5
    flask.session["begin_time"] = interpret_time("9am")
    flask.session["end_time"] = interpret_time("5pm")

def interpret_time( text ):
    """
    Read time in a human-compatible format and
    interpret as ISO format with local timezone.
    May throw exception if time can't be interpreted. In that
    case it will also flash a message explaining accepted formats.
    """
    app.logger.debug("Decoding time '{}'".format(text))
    time_formats = ["ha", "h:mma",  "h:mm a", "h:mm A", "H:mm"]
    try: 
        as_arrow = arrow.get(text, time_formats).replace(tzinfo=tz.tzlocal())
        app.logger.debug("Succeeded interpreting time")
    except:
        app.logger.debug("Failed to interpret time")
        flask.flash("Time '{}' didn't match accepted formats 13:30 or 1:30pm"
              .format(text))
        raise
    return as_arrow.isoformat()

def interpret_date( text ):
    """
    Convert text of date to ISO format used internally,
    with the local time zone.
    """
    try:
      as_arrow = arrow.get(text, "MM/DD/YYYY").replace(
          tzinfo=tz.tzlocal())
    except:
        flask.flash("Date '{}' didn't fit expected format 12/31/2001")
        raise
    return as_arrow.isoformat()

def next_day(isotext):
    """
    ISO date + 1 day (used in query to Google calendar)
    """
    as_arrow = arrow.get(isotext)
    return as_arrow.replace(days=+1).isoformat()

####
#
#  Functions  
#
####
def deleteCandidatesFromFree():
    """
    This function creates a revised list of free times which contains only the free
    times with an id that is in flask.session['selected_candidates']. The revised
    list of free times is stored in flask.session['revised_free']. 
    """
    to_keep = flask.session['selected_candidates']
    revised_free = []
    for apt in flask.session['free_list']:
        if apt['id'] in to_keep:
            revised_free.append(apt)
    
    flask.session['revised_free'] = revised_free

def storeParticipantInfoInDB():
    """
    This function stores the participant's name and the participant's free times 
    in the database. 
    """
    collection.update({ "type": "proposal", "_id":flask.session['proposal_id'] }, {'$push': {'responders':flask.session['name']}})
    collection.update({ "type": "proposal", "_id":flask.session['proposal_id'] }, {'$push': {'free_times':flask.session['revised_free']}})
    
def storeProposerInfoInDB():
    """
    This function creates a random id to serve as the proposal id. 
    It then stores this proposal id, proposed meeting's start date, end date, 
    start time, end time, proposer's name, and proposer's free times in the database, 
    all in one record.
    """
    #collection.remove({})
    responders = []
    responders.append(flask.session['name'])
    free_times = []
    free_times.append(flask.session['revised_free'])
    proposal_id = str(ObjectId())
    flask.session['proposal_id'] = proposal_id
    record = { "type": "proposal",
           "_id": proposal_id,
           "start_date": flask.session['begin_date'], 
           "end_date": flask.session['end_date'],
           "start_time": flask.session['begin_time'],
           "end_time": flask.session['end_time'],
           "responders": responders,
           "free_times": free_times
          }
    collection.insert(record) 
    

def find_free():
    """
    This function takes flask.session['busy_list'], flask.session['begin_date], 
    flask.session['end_date'], flask.session['begin_time'], and flask.session['end_time'] 
    and computes the free times in which the user can meet within the date and time 
    range and stores these free times in flask.session['free_list'] as a list of dictionaries.  
    """
    busy_agenda = Agenda.from_list(flask.session['busy_list'])
        
    span_begin_date = arrow.get(flask.session['begin_date'])
    span_end_date = arrow.get(flask.session['end_date'])
    span_begin_time = arrow.get(flask.session['begin_time'])
    span_end_time = arrow.get(flask.session['end_time'])
    
    free_agenda = busy_agenda.complementTimeSpan(span_begin_date, span_end_date, span_begin_time, span_end_time)
    
    free_list = free_agenda.to_list()
    i = 0
    for apt_dict in free_list:
        apt_dict['id'] = str(i)
        i= i+1
    
    
    flask.session['free_list'] = free_list


def find_busy():
    """
    This function goes through the list of selected calendar ids, which is stored in the 
    session object, and collects all the appointments that lie within or partially overlap
    the desired meeting time range and are not transparent. It stores all the busy times
    it collects in flask.session['busy_list'] as a list of dictionaries.  
    """
    busy_list = [] #list of dicts
    credentials = client.OAuth2Credentials.from_json(flask.session['credentials'])
    service = get_gcal_service(credentials)
    for id in flask.session['selected_cal']:
        events = service.events().list(calendarId=id, pageToken=None).execute()
        for event in events['items']:
            if ('transparency' in event) and event['transparency']=='transparent':
                continue 
            start_datetime = arrow.get(event['start']['dateTime'])
            end_datetime = arrow.get(event['end']['dateTime'])
            if overlap(start_datetime, end_datetime): 
                event_dict = {"desc":event['summary'], "begin":start_datetime.isoformat(), "end":end_datetime.isoformat()}
                busy_list.append(event_dict)
                
    flask.session['busy_list'] = busy_list


def overlap(event_sdt, event_edt):
    """
    This function returns true IFF the inputed event overlaps the desired meeting 
    time and date range.
    Arguments:
        event_sdt: arrow object representing the event's start date and time 
        event_edt: arrow object representing the event's end date and time 
    Returns: true IFF the inputed event overlaps the desired meeting 
    time and date range. 
    """
#sdt = start date time 
#edt = end date time 
    event_sd = event_sdt.date()
    event_ed = event_edt.date()
    event_st = event_sdt.time()
    event_et = event_edt.time()
    desired_sd= arrow.get(flask.session['begin_date']).date()
    desired_ed = arrow.get(flask.session['end_date']).date()
    desired_st = arrow.get(flask.session['begin_time']).time()
    desired_et = arrow.get(flask.session['end_time']).time()
    if not (desired_sd <= event_sd <= desired_ed) or not (desired_sd <= event_ed <= desired_ed):
        return False 
    elif (event_et <= desired_st):
        return False 
    elif (event_st >= desired_et):
        return False
    else:
        return True



#################
#
# Functions used within the templates
#
#################

@app.template_filter( 'fmtdate' )
def format_arrow_date( date ):
    try: 
        normal = arrow.get( date )
        return normal.format("ddd MM/DD/YYYY")
    except:
        return "(bad date)"

@app.template_filter( 'fmttime' )
def format_arrow_time( time ):
    try:
        normal = arrow.get( time )
        return normal.format("HH:mm")
    except:
        return "(bad time)"
    
#############


if __name__ == "__main__":
  # App is created above so that it will
  # exist whether this is 'main' or not
  # (e.g., if we are running in a CGI script)

  app.secret_key = str(uuid.uuid4())  
  app.debug=CONFIG.DEBUG
  app.logger.setLevel(logging.DEBUG)
  # We run on localhost only if debugging,
  # otherwise accessible to world
  if CONFIG.DEBUG:
    # Reachable only from the same computer
    app.run(port=CONFIG.PORT)
  else:
    # Reachable from anywhere 
    app.run(port=CONFIG.PORT,host="0.0.0.0")
    
