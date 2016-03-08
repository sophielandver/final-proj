Author: Sophie Landver

Path to project10 on ix: slandver@ix-trusty: ~/public_html/cis399/htbin/final-proj

# Project 10
A meeting scheduler application. 
<br>
When the application is first run, the user sees the proposer's page. In this page
the user is directed through a series of steps in order to put together a meeting 
proposal. The user enters his/her name, the date range for the desired meeting, and 
the time range for the desired meeting. Then, if the user gives consent to use his/her google
calendars, hes/she is prompted to select which google calendars he/she would like the app to use. 
At this point the "busy times" (defined below) and "free times" (defined below) are computed
and the user now gets the option of further eliminating some of the free times; i.e. the user
selects the times out of the free times in which he/she are actually available. Finally, 
the finalized free times are displayed to the user and the user is also given a URL. The
user sends an email, with the provided URL, to the people whom he/she would like at the meeting. 
<br>
Now the person, let's call this person the "participant", gets this email, copies and pastes 
the URL into his/her browser and is now directed through a series of steps in order to 
collect his/her available times. On the page at the given URL there is also a "View Current 
Meeting Status" button which displays the date range of the meeting, the time range of the meeting,
the current intersected available time, and the current responders. Thus, the proposer of the meeting
can check the current meeting status and once he/she sees that everyone has responded, he/she can 
look at the current intersected available times and pick a time, out of the listed times, to meet in 
(since the listed times work for everyone). 
<br>
The functions used for the free time calculation can be found in agenda.py
A thorough test suite for the free time calculations can be found in test_agenda.py 
<br>
Definitions:
<br>
busy times: all the appointments from the user's selected google calendars that lie within or 
partially overlap the desired time range and are appointments that block time 
(in iCalendar terms, non-transparent), i.e. the times in the date/time range in which the 
user cannot meet. 
<br>
free times: the times in the date/time range in which the user can meet.

# How to Run:
<br>
1. Run the application as you normally would. The first page you will see is the 
proposer's page. So, follow the steps to make a meeting proposal. <br>
2. Now copy the URL you are given in Step 6. Now you have 2 options for getting to the participant's page: 
(1) quit the server and then start it back up and then now paste the URL you got into your browser or (2) open a new
browser, if you have more than 1 browser, and paste the URL you got into the new browser. <br>
3. Now you are at the participant's page. So, if you are a participant, follow the steps to responding to 
the meeting proposal. You can access the current meeting status by clicking "View Current Meeting Status". 







