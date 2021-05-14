import json
import io
import csv

from workerstuff import ManualBonusGranter
from psiturk.amt_services_wrapper import MTurkServicesWrapper 

# Gets the hits with the given status
def get_hits(status):
    amt_services_wrapper = MTurkServicesWrapper()
    all_studies = False
    if status == 'active':
        hits_data = (amt_services_wrapper.get_active_hits(all_studies=all_studies)).data
    elif status == 'reviewable':
        hits_data = (amt_services_wrapper.get_reviewable_hits(all_studies=all_studies)).data
    else:
        hits_data = (amt_services_wrapper.get_all_hits(all_studies=all_studies)).data
    return hits_data

# Wraps getting question data from a participant, which for some reason
# is broken in PsiTurk 3.0.6. Not sure why.
def get_question_data(participant):
    self = participant
    questiondata = json.loads(self.datastring)["questiondata"]
    with io.StringIO() as outstring:
        csvwriter = csv.writer(outstring)
        for question in questiondata:
            csvwriter.writerow(
                (
                    self.uniqueid,
                    question,
                    questiondata[question]
                    )
            )
        return outstring.getvalue()

# Wraps getting event data frmo a participant, which for some reason is broken
# in PsiTurk 3.0.6. Not sure why.
def get_event_data(participant):
    self = participant
    eventdata = json.loads(self.datastring)["eventdata"]
    with io.StringIO() as outstring:
        csvwriter = csv.writer(outstring)
        for event in eventdata:
            csvwriter.writerow(
                (
                    self.uniqueid,
                    event["eventtype"],
                    event["interval"],
                    event["value"],
                    event["timestamp"]
                    )
            )
        return outstring.getvalue()

# Gets the trial data in csv (with header) format.
def get_datafile(participant, datatype):
    contents = {
        "trialdata": {
            "function": lambda p: p.get_trial_data(),
            "headerline": "uniqueid,currenttrial,time,trialData\n"        
        }, 
        "eventdata": {
            "function": lambda p: get_event_data(p),
            "headerline": "uniqueid,eventtype,interval,value,time\n"        
        }, 
        "questiondata": {
            "function": lambda p: get_question_data(p),
            "headerline": "uniqueid,questionname,response\n"
        },
        }
    ret = contents[datatype]["headerline"] + contents[datatype]["function"](participant)
    return ret

# Wraps assigning a worker the bonus compensation qualification 
def assign_bonus_qualification(workerId, mode="production"):
    try:
        mturk = ManualBonusGranter(mode=mode)
        mturk.setup_mturk_connection()
        response = mturk.assign_bonus_qualification(workerId)
        return response
    except:
        return None