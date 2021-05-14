# this file imports custom routes into the experiment server
from flask import Blueprint, render_template, request, jsonify, Response, abort, current_app, make_response
from jinja2 import TemplateNotFound
from functools import wraps
from sqlalchemy import or_, not_

from psiturk.psiturk_config import PsiturkConfig
from psiturk.experiment_errors import ExperimentError, InvalidUsageError
from psiturk.user_utils import PsiTurkAuthorization, nocache, print_to_log

# # Database setup
from psiturk.db import db_session, init_db
from psiturk.models import Participant
from json import dumps, loads

# Helper import
from helpers import *

import os

# load the configuration options
config = PsiturkConfig()
config.load_config()
# if you want to add a password protect route use this
myauth = PsiTurkAuthorization(config)

# explore the Blueprint
custom_code = Blueprint('custom_code', __name__,
                        template_folder='templates', static_folder='static')

# ----------------------------------------------
# Accessing data
# ----------------------------------------------
@custom_code.route('/view_data')
@myauth.requires_auth
def list_my_data():
    debug = request.args.get('debug')
    if debug:
        users = Participant.query.all()
    else:
        users = Participant.query.filter(not_(Participant.workerid.startswith('debug')))
    try:
        return render_template('list.html', participants=users)
    except TemplateNotFound:
        abort(404)

# ----------------------------------------------
# Accessing HIT listings
# ----------------------------------------------
@custom_code.route('/admin/HITs')
@myauth.requires_auth
def list_hits():
    status = request.args.get('status')
    hit_data = get_hits(status)
    if not hit_data:
        hit_data = []
    return render_template('listHITs.html', hits=hit_data)


# ----------------------------------------------
# Downloading data
# ----------------------------------------------
@custom_code.route('/get_data')
@myauth.requires_auth
def get_data():
    workerId = request.args.get('id')
    data_type = request.args.get('dataType')
    participant = Participant.query.filter(Participant.workerid == workerId).one()
    output = make_response(get_datafile(participant, data_type))
    output.headers["Content-Disposition"] = "attachment; filename={}-{}.csv".format(workerId,data_type)
    output.headers["Content-Type"] = "text/csv"
    return output


# ----------------------------------------------
# Computing the bonus
# ----------------------------------------------
@custom_code.route('/compute_bonus')
def compute_bonus():
    uniqueId = request.args['uniqueId']
    try:
        user = Participant.query.filter(Participant.uniqueid == uniqueId).one()
        user_data = loads(user.datastring)
        final_record = user_data['data'][-2]
        trial = final_record['trialdata']
        bonus = max(0, min(17, trial['totalReward']))
        user.bonus = "{:.2f}".format(bonus)
        db_session.add(user)
        db_session.commit()
        resp = {"bonusComputed": "success"}
    except:
        resp = {"bonusComputed": "failure"}
    return jsonify(**resp)

# ----------------------------------------------
# For manually providing compensation to users who didnt finish tasks
# ----------------------------------------------
@custom_code.route('/compensation', methods=['GET', 'POST'])
def compensation():
    if request.method == "POST":
        workerId = request.form.get('workerId')
        comment = request.form.get('comment')
        print_to_log("[USER COMMENT -{}- ] {}".format(workerId, comment))
        response = assign_bonus_qualification(workerId)
        return render_template('compensation.html', submitted=True, response=response, workerId=workerId)
    else:
        workerId = request.args['workerId']
        return render_template('compensation.html', submitted=False, workerId=workerId)