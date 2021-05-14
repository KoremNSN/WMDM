from psiturk.psiturk_config import PsiturkConfig
from psiturk.db import db_session, init_db
from psiturk.models import Participant
import boto3
import pprint

pp = pprint.PrettyPrinter(indent=2)

# COMP_TYPE = "base"
COMP_TYPE = "base"
# WORKER_ID = "A1WPBIRI0HGTWG"

# Base $3.00 compensation
if COMP_TYPE == "base":
    BONUS_QUALIFICATION_PROD = "3R3LL2QS9W4HFPAXJPAND7LQWJKGQ3"
    COMPENSATION_HIT_ID = "3SSN80MU8CPE4KLK3H8CTWODR4DXK0"
# Full $17.40 compensation
else:
    BONUS_QUALIFICATION_PROD = "306JTMJZDKLHJDRNKZ6IH09N3PJ8NR"
    COMPENSATION_HIT_ID = "304QEQWKZPLPXL0OYXBYRZIB1Y10OJ"
# BONUS_QUALIFICATION_SANDBOX = "3HA0CFAXN53ZJBTH2ZT8LVBIYUTAJP"
# COMPENSATION_HIT_ID_SANDBOX = "341YLJU21I0MX9SZFPYBQ2SLM5YI25"

BONUS_REASON='Compensation for issues with the Yale Visual Search Experiment. We apologize for any inconvenience we may have caused. Thank you!'

# worker = Participant.query.filter(Participant.workerid == WORKER_ID).one()
# worker.status = 3
# db_session.add(worker)
# db_session.commit()
# print(worker)

class ManualBonusGranter():

    def __init__(self, mode):
        self.mode = mode
        if self.mode == 'sandbox':
            self.hitId =  COMPENSATION_HIT_ID_SANDBOX
            self.qualificationTypeId = BONUS_QUALIFICATION_SANDBOX
            self.endpoint_url = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com'
        else:
            self.hitId =  COMPENSATION_HIT_ID
            self.qualificationTypeId = BONUS_QUALIFICATION_PROD
            self.endpoint_url = 'https://mturk-requester.us-east-1.amazonaws.com'
        config = PsiturkConfig()
        config.load_config()
        self.config = config
        self.mtc = None

    def setup_mturk_connection(self):
        kwargs = {
            'region_name': 'us-east-1',
            'endpoint_url': self.endpoint_url
        }
        aws_access_key_id = self.config.get('AWS Access', 'aws_access_key_id')
        aws_secret_access_key = self.config.get('AWS Access', 'aws_secret_access_key')
        if aws_access_key_id and aws_secret_access_key:
            kwargs['aws_access_key_id'] = aws_access_key_id
            kwargs['aws_secret_access_key'] = aws_secret_access_key

        self.mtc = boto3.client('mturk', **kwargs)
        return True
    
    # We use this to grant qualifications to workers so they may take the HIT
    # for granting manual bonuses.
    def assign_bonus_qualification(self, workerId):
        return self.mtc.associate_qualification_with_worker(
            QualificationTypeId=self.qualificationTypeId,
            WorkerId=workerId,
            IntegerValue=1,
            SendNotification=True)
    
    def deassign_bonus_qualification(self, workerId):
        return self.mtc.disassociate_qualification_from_worker(
            QualificationTypeId=self.qualificationTypeId,
            WorkerId=workerId,
            Reason='Test')
    
    # Lists the workers who have submitted the dummy HIT and can be bonused
    def list_bonusable_assignments(self, hitId=None):
        response = self.mtc.list_assignments_for_hit(
            HITId=hitId or self.hitId,
            AssignmentStatuses=['Submitted'])
        return [{
            'AssignmentId': assignment['AssignmentId'],
            'WorkerId': assignment['WorkerId']} 
                for assignment in response['Assignments']]
    
    # Gets the assignment ID from a worker ID
    def get_assignment_id(self, workerId):
        assignments = self.list_bonusable_assignments()
        assignment_id = next(filter(lambda x: x['WorkerId'] == workerId, assignments), { 'AssignmentId': None })['AssignmentId']
        return assignment_id

    # Grant a bonus to a worker who has subitted the dummy HIT
    # Note that the amount shoudl be a string!!!
    def grant_bonus(self, workerId, amount):
        assignmentId = self.get_assignment_id(workerId)
        if assignmentId is None:
            print('Worker {} has no bonusable assignment!'.format(workerId))
            return
        else:
            payments = self.list_bonus_payments(assignmentId)
            if payments:
                print('Worker {} has already been paid a bonus of ${}.'.format(workerId, payments[0]['BonusAmount']))
                return
            else:
                return self.mtc.send_bonus(
                    WorkerId=workerId,
                    BonusAmount=amount,
                    AssignmentId=assignmentId,
                    Reason=BONUS_REASON)
    
    # Only needed this to get the dummy bonus HIT id
    def get_bonus_hits_id(self):
        return self.mtc.list_hits_for_qualification_type(
            QualificationTypeId=self.qualificationTypeId)
    
    # Retrieves the amount of bonuses paid or to a specific assignment id
    def list_bonus_payments(self, assignmentId=None):
        if assignmentId:
            response = self.mtc.list_bonus_payments(
                AssignmentId=assignmentId)['BonusPayments']
        else:
            response = self.mtc.list_bonus_payments(
                HITId=self.hitId)['BonusPayments']
        return response


if __name__ == "__main__":
    mturk = ManualBonusGranter(mode='production')
    mturk.setup_mturk_connection()
    # response = mturk.assign_bonus_qualification(WORKER_ID)
    response = mturk.list_bonusable_assignments()
    # response = mturk.get_bonus_hits_id()
    # response = mturk.list_bonus_payments()
    # response = mturk.grant_bonus("A1G187YBG0DVMQ", "17.40")
    pp.pprint(response)