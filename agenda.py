"""
An Agenda is a list-like container of Appt (appointment).
"""

import datetime
import arrow
import datetime
from dateutil import tz  # For interpreting local times

class Appt:

    """
    A single appointment, starting on a particular
    date and time, and ending at a later time the same day.
    """
    
    def __init__(self, begin, end, desc):
        """Create an appointment.
        
        Arguments:
            begin: An arrow date and time object. When the appointment starts. 
            end:  An arrow date and time object, after begin. When the appointments ends.
            desc: A string describing the appointment
            
        Raises: 
        	ValueError if appointment ends before it begins
        """
        self.begin = begin
        self.end = end
        if begin >= end :
            raise ValueError("Appointment end must be after begin")
        self.desc = desc
        return


    @classmethod
    def from_dict(cls, event_dict): #from an apt in the form of an item in busy_list or free_list; both lists are same form
        """
        This function takes in a dictionary representation of an Appt and returns an Appt object 
        for it. The dictionary representation has a "desc", "begin" and "end" term.  
        """
        desc = event_dict["desc"]
        begin = arrow.get(event_dict["begin"])
        end = arrow.get(event_dict["end"])
        return Appt(begin, end, desc)

   
   
    def to_dict(self):
        """
        This function takes in an Appt object and returns a dictionary representation of it where
        the begin and end times of the appointment are stored in isoformat.
        Returns a dictionary in the form {"desc": description_of_apt, "begin": isoformat_begin_date_time_of_apt,
                                          "end": isoformat_end_date_time_of_apt}
        """
        dict_rep = {}
        dict_rep["desc"] = self.desc
        dict_rep["begin"] = self.begin.isoformat()
        dict_rep["end"] = self.end.isoformat()
        return dict_rep
        

    @classmethod
    def from_string(cls, txt):
        """
        This function takes in a string representation of an Appt and returns an Appt object. 
        """
        fields = txt.split("|")
        if len(fields) != 2:
            raise ValueError("Appt literal requires exactly one '|' before description")
        timespec = fields[0].strip()
        desc = fields[1].strip()
        fields = timespec.split("-")
        if len(fields) != 2:
            raise ValueError("Appt literal must start with date and date seperated by blanks")
        appt_begin_text = fields[0]
        appt_end_text = fields[1]
        
        begin = arrow.get(appt_begin_text, "MM/DD/YYYY h:mm A")
        end = arrow.get(appt_end_text, "MM/DD/YYYY h:mm A")
        
        result = Appt(begin, end, desc)
        return result 
       

        
    def __lt__(self, other):
        """Does this appointment finish before other begins?
        
        Arguments:
        	other: another Appt
        Returns: 
        	True iff this Appt is done by the time other begins.
        """
        return self.end <= other.begin
        
    def __gt__(self, other):
        """Does other appointment finish before this begins?
        
        Arguments:
        	other: another Appt
        Returns: 
        	True iff other is done by the time this Appt begins
        """
        return other < self
        
    def overlaps(self, other):
        """Is there a non-zero overlap between this appointment
        and the other appointment?
		Arguments:
            other is an Appt
        Returns:
            True iff there exists some duration (greater than zero)
            between this Appt and other. 
        """
        return  not (self < other or other < self)
            
    def intersect(self, other, desc=""):
        """Return an appointment representing the period in
        common between this appointment and another.
        Requires self.overlaps(other). 
        
		Arguments: 
			other:  Another Appt
			desc:  (optional) description text for this appointment. 

		Returns: 
			An appointment representing the time period in common
			between self and other.   Description of returned Appt 
			is copied from this (self), unless a non-null string is 
			provided as desc. 
        """
        if desc=="":
            desc = self.desc
        assert(self.overlaps(other))
        # We know the day must be the same. 
        # Find overlap of times: 
        #   Later of two begin times, earlier of two end times
        new_begin = max(self.begin, other.begin)
        new_end = min(self.end, other.end) 
        return Appt(new_begin, new_end, desc)

    def union(self, other, desc=""):
        """Return an appointment representing the combined period in
        common between this appointment and another.
        Requires self.overlaps(other).
        
		Arguments: 
			other:  Another Appt
			desc:  (optional) description text for this appointment. 

		Returns: 
			An appointment representing the time period spanning
                        both self and other.   Description of returned Appt 
			is concatenation of two unless a non-null string is 
			provided as desc. 
        """
        if desc=="":
            desc = self.desc + " " + other.desc
        assert(self.overlaps(other))
        # We know the day must be the same. 
        # Find overlap of times: 
        #   Earlier of two begin times, later of two end times
        begin = min(self.begin, other.begin)
        end = max(self.end, other.end)
        return Appt(begin, end, desc)


    def __str__(self):
        """Returns a string representation of appointment object.
        Example:
            "10/31/2012 4:00 PM-10/31/2012 9:00 PM|Long dinner"
        """
        begstr = self.begin.format("MM/DD/YYYY h:mm A")
        endstr = self.end.format("MM/DD/YYYY h:mm A")
        return  begstr + "-" + endstr + "|" + self.desc


class Agenda:
    """An Agenda is essentially a list of appointments,
    with some agenda-specific methods.
    """

    def __init__(self):
        """An empty agenda."""
        self.appts = [ ]
    
       
    
    @classmethod
    def from_list(cls, apt_list): #list of lists
        """
        Converts a list of dictionaries representing an agenda of appts into an agenda object
        holding Appt objects. 
        """
        total_agenda = Agenda()
        for apt in apt_list:
            apt_obj = Appt.from_dict(apt)
            total_agenda.append(apt_obj)
        
        return total_agenda 
    
    def to_list(self):
        """
        Takes an agenda object and converts to a list of dictionaries. 
        """
        apt_list = []
        for apt in self:
            dict_rep = apt.to_dict()
            apt_list.append(dict_rep)
        return apt_list
       
    @classmethod
    def from_file(cls, f):
        """Factory: Read an agenda from a file
        
        Arguments: 
            f:  A file object (as returned by io.open) or
               an object that emulates a file (like stringio). 
        returns: 
            An Agenda object
        """
        agenda = cls()
        for line in f:
            line = line.strip()
            if line == "" or line.startswith("#"):
                # Skip blank lines and comments
                pass
            else: 
                try: 
                    agenda.append(Appt.from_string(line))
                except ValueError as err: 
                    print("Failed on line: ", line)
                    print(err)
        return agenda


    def append(self,appt):
        """Add an Appt to the agenda."""
        self.appts.append(appt)

    def intersect(self,other,desc=""): 
        """Return a new agenda containing appointments
        that are overlaps between appointments in this agenda
        and appointments in the other agenda.

        Titles of appointments in the resulting agenda are
        taken from this agenda, unless they are overridden with
        the "desc" argument.

        Arguments:
           other: Another Agenda, to be intersected with this one
           desc:  If provided, this string becomes the title of
                all the appointments in the result.
        """
        default_desc = (desc == "")
        result = Agenda()
        for thisappt in self.appts:
            if default_desc: 
                desc = thisappt.desc
            for otherappt in other.appts:
                if thisappt.overlaps(otherappt):
                    result.append(thisappt.intersect(otherappt,desc))
        
        return result

    def normalize(self):
        """Merge overlapping events in an agenda. For example, if 
        the first appointment is from 1pm to 3pm, and the second is
        from 2pm to 4pm, these two are merged into an appt from 
        1pm to 4pm, with a combination description.  
        After normalize, the agenda is in order by date and time, 
        with no overlapping appointments.
        """
        if len(self.appts) == 0:
            return

        ordering = lambda ap: ap.begin #sort by begin date 
        self.appts.sort(key=ordering)

        normalized = [ ]
        # print("Starting normalization")
        cur = self.appts[0]  
        for appt in self.appts[1:]:
            if appt > cur:
                # Not overlapping
                # print("Gap - emitting ", cur)
                normalized.append(cur)
                cur = appt
            else:
                # Overlapping
                # print("Merging ", cur, "\n"+
                #      "with    ", appt)
                cur = cur.union(appt)
                # print("New cur: ", cur)
        # print("Last appt: ", cur)
        normalized.append(cur)
        self.appts = normalized

    def normalized(self):
        """
        A non-destructive normalize
        (like "sorted(l)" vs "l.sort()").
        Returns a normalized copy of this agenda.
        """
        copy = Agenda()
        copy.appts = self.appts
        copy.normalize()
        return copy
        
    def complement(self, freeblock):
        """Produce the complement of an agenda
        within the span of a timeblock represented by 
        an appointment.  For example, 
        if this agenda is a set of appointments, produce a 
        new agenda of the times *not* in appointments in 
        a given time period.
        Args: 
           freeblock: Looking  for time blocks in this period 
               that are not conflicting with appointments in 
               this agenda.
        Returns: 
           A new agenda containing exactly the times that 
           are within the period of freeblock and 
           not within appointments in this agenda. The 
           description of the resulting appointments comes
           from freeblock.desc.
        """
        copy = self.normalized()
        comp = Agenda()
        desc = freeblock.desc
        cur_time = freeblock.begin #arrow date and time 
        for appt in copy.appts:
            if appt < freeblock:
                continue
            if appt > freeblock:
                if cur_time < freeblock.end:
                    comp.append(Appt(cur_time,freeblock.end, desc))
                    cur_time = freeblock.end
                break
            if cur_time < appt.begin:
                # print("Creating free time from", cur_time, "to", appt.begin)
                comp.append(Appt(cur_time, appt.begin, desc))
            cur_time = max(appt.end,cur_time)
        
        if cur_time < freeblock.end:
            # print("Creating final free time from", cur_time, "to", freeblock.end)
            comp.append(Appt(cur_time, freeblock.end, desc))
        return comp

    
    
    def complementTimeSpan(self, begin_date, end_date, begin_time, end_time):
        """
        Calculate the complement of an agenda within a date and time span. This method
        calls the complement method per day in the date span. 
        """
        total_free = Agenda()
        date = begin_date.date()
        end_date = end_date.date()
        while(date <= end_date):
            fb_year = date.year
            fb_month = date.month
            fb_day = date.day
            fb_begin = begin_time.replace(year=fb_year, month=fb_month, day=fb_day).replace(tzinfo=tz.tzlocal())
            fb_end = end_time.replace(year=fb_year, month=fb_month, day=fb_day).replace(tzinfo=tz.tzlocal())
            freeblock = Appt(fb_begin, fb_end, "Available")
            free_agenda = self.complement(freeblock)
            for apt in free_agenda:
                total_free.append(apt)
        
            begin_date = begin_date.replace(days=+1)
            date = begin_date.date()
        
        return total_free
    
    @classmethod
    def timeSpanAgenda(cls, begin_date, end_date, begin_time, end_time):
        total_free = Agenda()
        date = begin_date.date()
        end_date = end_date.date()
        while(date <= end_date):
            fb_year = date.year
            fb_month = date.month
            fb_day = date.day
            fb_begin = begin_time.replace(year=fb_year, month=fb_month, day=fb_day).replace(tzinfo=tz.tzlocal())
            fb_end = end_time.replace(year=fb_year, month=fb_month, day=fb_day).replace(tzinfo=tz.tzlocal())
            freeblock = Appt(fb_begin, fb_end, "Available")
            
            total_free.append(freeblock)
            
            begin_date = begin_date.replace(days=+1)
            date = begin_date.date()
        
        return total_free
    
      

    def __len__(self):
        """Number of appointments, callable as built-in len() function"""
        return len(self.appts)

    def __iter__(self):
        """An iterator through the appointments in this agenda."""
        return self.appts.__iter__()

    def __str__(self):
        """String representation of a whole agenda"""
        rep = ""
        for appt in self.appts:
            rep += str(appt) + "\n"
        return rep[:-1]

    def __eq__(self,other):
        """Equality, ignoring descriptions --- just equal blocks of time"""
        if len(self.appts) != len(other.appts):
            return False
        for i in range(len(self.appts)):
            mine = self.appts[i]
            theirs = other.appts[i]
            if not (mine.begin == theirs.begin and
                    mine.end == theirs.end):
                return False
        return True
    
    