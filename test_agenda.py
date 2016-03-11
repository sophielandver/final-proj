"""
Nose tests for agenda.py
"""

from agenda import *
import arrow
import io

def test_appt():
    """
    tests for Appt class
    """
    earlier = Appt.from_string("10/31/2012 1:30 PM-10/31/2012 2:30 PM|Before my appt")
    later = Appt.from_string("10/31/2012 4:00 PM-10/31/2012 9:00 PM|Long dinner")
    assert earlier < later
    assert later > earlier
    assert not (earlier < earlier) 
    assert not (earlier > later)
    assert not (earlier.overlaps(later))
    assert not (later.overlaps(earlier))
    
    
    sample = Appt.from_string("10/31/2012 2:30 PM-10/31/2012 3:45 PM|Sample appointment")
    conflict = Appt.from_string("10/31/2012 1:45 PM-10/31/2012 4:00 PM|Conflicting appt")
    assert sample.overlaps(conflict)
    assert conflict.overlaps(sample)
    
    overlap = sample.intersect(conflict)
    assert str(overlap) == "10/31/2012 2:30 PM-10/31/2012 3:45 PM|Sample appointment"
    overlap = conflict.intersect(sample)
    assert str(overlap) == "10/31/2012 2:30 PM-10/31/2012 3:45 PM|Conflicting appt"
    overlap = conflict.intersect(sample,"New desc")
    assert str(overlap) == "10/31/2012 2:30 PM-10/31/2012 3:45 PM|New desc"
    text = "10/31/2012 2:30 PM-10/31/2012 3:45 PM|from text"
    from_text = Appt.from_string(text)
    assert text == str(from_text)
    
def test_agenda1():
    """
    Simple smoke test for Agenda class.
    """

    keiko_agtxt="""# Free times for Keiko on December 1
           12/01/2012 7:00 AM-12/01/2012 8:00 AM|Possible breakfast meeting
           12/01/2012 10:00 AM-12/01/2012 12:00 PM|Late morning meeting
           12/01/2012 2:00 PM-12/01/2012 6:00 PM|Afternoon meeting
         """

    kevin_agtxt="""
          11/30/2012 9:00 AM-11/30/2012 2:00 PM|I have an afternoon commitment on the 30th
          12/01/2012 9:00 AM-12/01/2012 3:00 PM|I prefer morning meetings
          # Kevin always prefers morning, but can be available till 3, except for 
          # 30th of November.
          """

    emanuela_agtxt = """
    12/01/2012 12:00 PM-12/01/2012 2:00 PM|Early afternoon
    12/01/2012 4:00 PM-12/01/2012 6:00 PM|Late afternoon into evening
    12/02/2012 8:00 AM-12/02/2012 5:00 PM|All the next day
    """
    
    keiko_ag = Agenda.from_file(io.StringIO(keiko_agtxt))
    kevin_ag = Agenda.from_file(io.StringIO(kevin_agtxt))
    emanuela_ag = Agenda.from_file(io.StringIO(emanuela_agtxt))


    kevin_emanuela = kevin_ag.intersect(emanuela_ag)
    ke = "12/01/2012 12:00 PM-12/01/2012 2:00 PM|I prefer morning meetings" 
    keactual = str(kevin_emanuela)
    assert keactual == ke

    everyone = kevin_emanuela.intersect(keiko_ag)
    assert len(everyone) == 0

def test_agenda2():
    """
    Additional tests for agenda normalization and complement.
    Also contains a test for complementTimeSpan function.
    """
    keiko_agtxt = """ 
    12/02/2013 12:00 PM-12/02/2013 2:00 PM|Late lunch
    12/01/2013 1:00 PM-12/01/2013 2:00 PM|Sunday brunch
    12/02/2013 8:00 AM-12/02/2013 3:00 PM|Long long meeting
    12/02/2013 3:00 PM-12/02/2013 4:00 PM|Coffee after the meeting
    """
    keiko_ag = Agenda.from_file(io.StringIO(keiko_agtxt))

    # Torture test for normalization
    day_in_life_agtxt = """
    # A torture-test agenda.  I am seeing a lot of code 
    # that may not work well with sequences of three or more
    # appointments that need to be merged.  Here's an agenda
    # with such a sequence.  Also some Beatles lyrics that have
    # been running through my head.  
    # 
    11/26/2013 9:00 AM-11/26/2013 10:30 AM|got up
    11/26/2013 10:00 AM-11/26/2013 11:30 AM|got out of bed
    11/26/2013 11:00 AM-11/26/2013 12:30 PM|drug a comb across my head
    11/26/2013 12:00 PM-11/26/2013 1:30 PM|on the way down stairs I had a smoke
    11/26/2013 1:00 PM-11/26/2013 2:30 PM|and somebody spoke
    11/26/2013 2:00 PM-11/26/2013 3:30 PM|and I went into a dream
    #
    # A gap here, from 15:30 to 17:00
    # 
    11/26/2013 5:00 PM-11/26/2013 6:30 PM|he blew his mind out in a car
    11/26/2013 6:00 PM-11/26/2013 7:30 PM|hadn't noticed that the lights had changed
    11/26/2013 7:00 PM-11/26/2013 8:30 PM|a crowd of people stood and stared
    #
    # A gap here, from 20:30 to 21:00
    #
    11/26/2013 9:00 PM-11/26/2013 10:30 PM|they'd seen his face before
    11/26/2013 10:00 PM-11/26/2013 11:00 PM|nobody was really sure ...
    """
    day_in_life = Agenda.from_file(io.StringIO(day_in_life_agtxt))
    day_in_life.normalize()
    # How are we going to test this?  I want to ignore the text descriptions.
    # Defined __eq__ method in Agenda just for this
    should_be_txt = """
    11/26/2013 9:00 AM-11/26/2013 3:30 PM|I read the news today oh, boy
    11/26/2013 5:00 PM-11/26/2013 8:30 PM|about a lucky man who made the grade
    11/26/2013 9:00 PM-11/26/2013 11:00 PM|and though the news was rather sad
    """
    should_be_ag = Agenda.from_file(io.StringIO(should_be_txt))
    assert day_in_life == should_be_ag

    
    # Start with the simplest cases of "complement"
    simple_agtxt = "12/01/2013 12:00 PM-12/01/2013 2:00 PM|long lunch"
    simple_ag = Agenda.from_file(io.StringIO(simple_agtxt))
    
    # Different day - should have no effect
    tomorrow = Appt.from_string("12/02/2013 11:00 AM-12/02/2013 3:00 PM|tomorrow")
    simple_ag = simple_ag.complement(tomorrow)
    assert str(simple_ag.appts[0]) == "12/02/2013 11:00 AM-12/02/2013 3:00 PM|tomorrow"
    # And the freeblock should not be altered
    assert str(tomorrow) == "12/02/2013 11:00 AM-12/02/2013 3:00 PM|tomorrow"

    
    # Freeblock different times same day
    simple_agtxt = "12/01/2013 12:00 PM-12/01/2013 2:00 PM|long lunch" 
    simple_ag = Agenda.from_file(io.StringIO(simple_agtxt))
    dinner = Appt.from_string("12/01/2013 7:30 PM-12/01/2013 8:30 PM|dinner")
    simple_ag = simple_ag.complement(dinner)
    assert str(simple_ag).strip() == "12/01/2013 7:30 PM-12/01/2013 8:30 PM|dinner"
 
    #
    # More complex agendas - try with two appointments
    #
    simple_agtxt = """
    12/01/2013 9:00 AM-12/01/2013 11:00 AM|morning meeting
    12/01/2013 1:00 PM-12/01/2013 2:00 PM|afternoon meeting
    """
    # Cover first part first appt
    simple_ag = Agenda.from_file(io.StringIO(simple_agtxt))
    part_cover_first = Appt.from_string("12/01/2013 8:30 AM-12/01/2013 9:30 AM|morning coffee")
    simple_ag = simple_ag.complement(part_cover_first)
    assert str(simple_ag).strip() == "12/01/2013 8:30 AM-12/01/2013 9:00 AM|morning coffee"
    
    # Cover first part first appt
    simple_ag = Agenda.from_file(io.StringIO(simple_agtxt))
    part_cover_first = Appt.from_string("12/01/2013 9:30 AM-12/01/2013 11:30 AM|morning coffee")
    simple_ag = simple_ag.complement(part_cover_first)
    assert str(simple_ag).strip() == "12/01/2013 11:00 AM-12/01/2013 11:30 AM|morning coffee"
    
    # Cover first part first appt
    simple_ag = Agenda.from_file(io.StringIO(simple_agtxt))
    part_cover_first = Appt.from_string("12/01/2013 12:30 PM-12/01/2013 1:30 PM|afternoon coffee")
    simple_ag = simple_ag.complement(part_cover_first)
    assert str(simple_ag).strip() == "12/01/2013 12:30 PM-12/01/2013 1:00 PM|afternoon coffee"

    # Cover first part first appt
    simple_ag = Agenda.from_file(io.StringIO(simple_agtxt))
    part_cover_first = Appt.from_string("12/01/2013 1:30 PM-12/01/2013 2:30 PM|afternoon coffee")
    simple_ag = simple_ag.complement(part_cover_first)
    assert str(simple_ag).strip() == "12/01/2013 2:00 PM-12/01/2013 2:30 PM|afternoon coffee"

    # Cover first part first appt
    simple_ag = Agenda.from_file(io.StringIO(simple_agtxt))
    part_cover_first = Appt.from_string("12/01/2013 10:30 AM-12/01/2013 1:30 PM|mid-day")
    simple_ag = simple_ag.complement(part_cover_first)
    assert str(simple_ag).strip() == "12/01/2013 11:00 AM-12/01/2013 1:00 PM|mid-day"
    
    # Cover first part first appt
    simple_ag = Agenda.from_file(io.StringIO(simple_agtxt))
    part_cover_first = Appt.from_string("12/01/2013 8:00 AM-12/01/2013 3:00 PM|most of day")
    simple_ag = simple_ag.complement(part_cover_first)
    assert str(simple_ag).strip() == ("12/01/2013 8:00 AM-12/01/2013 9:00 AM|most of day" +
                                    "\n" + "12/01/2013 11:00 AM-12/01/2013 1:00 PM|most of day" +
                                    "\n" + "12/01/2013 2:00 PM-12/01/2013 3:00 PM|most of day")

    #TEST complement
    freeblock = Appt.from_string("02/22/2016 10:00 AM-02/22/2016 4:00 PM|Freeblock")
    busy_agtxt = """
    02/22/2016 8:00 AM-02/22/2016 9:00 AM|busy
    02/22/2016 10:00 AM-02/22/2016 12:00 PM|busy
    02/22/2016 1:00 PM-02/22/2016 2:00 PM|busy
    02/22/2016 3:00 PM-02/22/2016 5:00 PM|busy
    02/22/2016 6:00 PM-02/22/2016 7:00 PM|busy
    """
    busy_agenda = Agenda.from_file(io.StringIO(busy_agtxt))
    expected_txt = """
    02/22/2016 12:00 PM-02/22/2016 1:00 PM|Available
    02/22/2016 2:00 PM-02/22/2016 3:00 PM|Available
    """
    expected_agenda = Agenda.from_file(io.StringIO(expected_txt))
    assert busy_agenda.complement(freeblock) == expected_agenda
    
   
    


