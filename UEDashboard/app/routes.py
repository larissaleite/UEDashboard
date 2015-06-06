# -*- coding: utf-8 -*-
from flask import Flask, render_template, jsonify, make_response, request, flash, json
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
import datetime
  
app = Flask(__name__)

#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqldb://root:root@localhost:3306/sinfominer?charset=utf8'
SQLALCHEMY_BINDS = {
    'db_commits': 'mysql+mysqldb://root:root@localhost:3306/sinfominer?charset=utf8',
    'db_events': 'mysql+mysqldb://root:root@localhost:3306/uedashboard?charset=utf8'
}

app.config['SQLALCHEMY_BINDS'] = SQLALCHEMY_BINDS
db = SQLAlchemy(app) 

user = "arthurmacedo"

months_map = { '1' : "Jan", '2' : "Feb", '3' : "Mar", '4' : "Apr", '5' : "May", '6' : "Jun", '7' : "Jul", '8' : "Aug", '9' : "Sep", '10' : "Oct" , '11' : "Nov", '12' : "Dec" }

def get_all_users():
	sql = text('select distinct developer from commit;')
	result = db.get_engine(app, 'db_commits').execute(sql)

	users = []

	for row in result:
		users.append(str(row["developer"]))
	result.close()
	return users

def get_months_ordered():
	months = []
	sql = text('select distinct MONTH(date) as month from commit;')
	result = db.get_engine(app, 'db_commits').execute(sql)
	
	for row in result:
		months.append(int(row["month"]))
	result.close()
	return months

def get_months_categories():
	months = get_months_ordered()
	months_categories = []

	for month in months:
		month_name = months_map[str(month)]
		months_categories.append(month_name)
	return months_categories

def get_commits_user():
	commits = []
	commits_by_month = []
	for month in get_months_ordered():
		sql = text("select count(*) from commit where author='"+user+"' and MONTH(date)="+str(month))
		result = db.get_engine(app, 'db_commits').execute(sql)
		n = str(result.fetchone()[0])
		commits_by_month.append(int(n))
		result.close()
	commits.append({ 'data' : commits_by_month, 'name' : str(user) })

	return commits

def get_events_user():
	events = []
	sql = text("select commit.id as id_commit, commit.date, commit.message, event.message as msg, event.type, event.id from event inner join commit on event.id_commit = commit.id where commit.developer='"+user+"'")
	result = db.get_engine(app, 'db_events').execute(sql)
	for row in result:
		events.append({ 'date' : row["date"], 'commit_message' : row["message"], 'message' : row["msg"], 'type' : row["type"], 'id' : row["id"], 'id_commit' : row["id_commit"] })
	result.close()
	return events

def get_events_team():
	events = []
	sql = text("select commit.id as id_commit, commit.date, commit.developer, commit.message, event.message as msg, event.type, event.id from event inner join commit on event.id_commit = commit.id")
	result = db.get_engine(app, 'db_events').execute(sql)
	for row in result:
		message = row["msg"]
		if row["type"] == "Time Between Commits":
			message = row["developer"] + " hadn't "+ message[11:-1] + "s"
		events.append({ 'date' : row["date"], 'commit_message' : row["message"], 'message' : message, 'type' : row["type"], 'id' : row["id"], 'id_commit' : row["id_commit"], 'developer' : row["developer"] })
	result.close()
	return events

#TEMPLATE FILES
@app.route('/', methods = ['POST', 'GET'])
def show_home_page():
	commits = get_commits_user()
	months_categories = get_months_categories()
	events = get_events_user()
	return render_template('index.html', commits=commits, months_categories=months_categories, events=events)

@app.route('/team/commits')
def show_team_commits():
	sql = text('select author, count(*) from commit group by author order by count(*) desc limit 10;')
	result = db.get_engine(app, 'db_commits').execute(sql)
	commits = []

	for row in result:
		developer = str(row["author"])
		commits_by_month = []

		if developer != user:
			for month in get_months_ordered():
				sql = text("select count(*) from commit where author='"+developer+"' and MONTH(date)="+str(month))
				res = db.get_engine(app, 'db_commits').execute(sql)
				n = str(res.fetchone()[0])
				commits_by_month.append(int(n))
				res.close()
			commits.append({ 'data' : commits_by_month, 'name' : developer })
	result.close()

	months_categories = get_months_categories()
	events = get_events_team()
	return render_template('team-commits.html', commits=commits, months_categories=months_categories, events=events)

# REST API
@app.route('/api/commits', methods = ['GET'])
def get_all_commits():
	sql = text('select * from commit')
	result = db.get_engine(app, 'db_commits').execute(sql)
	commits = []
	for row in result:
		commits.append({ 'developer' : row["developer"], 'date' : row["date"] })
	result.close()
	return commits

@app.route('/api/commit/detail', methods = ['POST'])
def get_detail_commit():
	commits_detail = []

	id_commit = request.json["id_commit"]

	sql = text("select modification.file, modification.type from modification inner join commit on commit.id = modification.id_commit where commit.id="+id_commit+";")
  	result = db.get_engine(app, 'db_events').execute(sql)
  	modifications = []
  	for row in result:
  		modifications.append({ 'file' : row["file"], 'type' : row["type"] })
  	result.close()

  	sql = text("select commit.message, commit.developer, commit.date from commit where id="+id_commit+";")
  	result = db.get_engine(app, 'db_events').execute(sql)
  	commit = result.fetchone()
  	commits_detail.append({ 'message' : commit["message"], 'developer' : commit["developer"], 'date' : json.dumps(commit["date"].isoformat()), 'modifications' : modifications })
  	result.close()
  	return jsonify(commits_detail=commits_detail)

@app.route('/api/events/developer', methods = ['GET'])
def get_events_by_developer():
	sql = text("select commit.id as id_commit, commit.date, commit.developer, event.message as msg, event.type, event.id from event inner join commit on event.id_commit = commit.id order by developer")
	result = db.get_engine(app, 'db_events').execute(sql)
	#dev = result.fetchone()["developer"]
	dev = ""
	first = True
	developers = []
	dev_array = {}
	for row in result:
		if first is True:
			dev = row["developer"]
			first = False
			
		if row["developer"] != dev:
			dev_array[dev] = developers
			dev = row["developer"]
			developers = []

		message = row["msg"]
		if row["type"] == "Time Between Commits":
			message = row["developer"] + " hadn't "+ message[11:-1] + "s"
		developers.append({ 'date' : json.dumps(row["date"].isoformat()), 'message' : message, 'type' : row["type"], 'id_event' : row["id"], 'id_commit' : row["id_commit"], 'developer' : row["developer"] })

	result.close()

	#add last developer
	dev_array[dev] = developers
	return jsonify(events=dev_array)

@app.route('/api/events/date', methods = ['GET'])
def get_events_by_date():
	sql = text("select commit.id as id_commit, commit.date, commit.developer, event.message as msg, event.type, event.id from event inner join commit on event.id_commit = commit.id order by date")
	result = db.get_engine(app, 'db_events').execute(sql)
	#date = result.fetchone()["date"]
	date = ""
	first = True
	dates = []
	date_array = {}
	for row in result:
		if first is True:
			date = row["date"]
			first = False

		if row["date"] != date:
			date_array[json.dumps(date.isoformat())] = dates
			date = row["date"]
			dates = []

		message = row["msg"]
		if row["type"] == "Time Between Commits":
			message = row["developer"] + " hadn't "+ message[11:-1] + "s"
		dates.append({ 'message' : message, 'type' : row["type"], 'id_event' : row["id"], 'id_commit' : row["id_commit"], 'developer' : row["developer"] })

	result.close()

	#add last date
	date_array[json.dumps(date.isoformat())] = dates
	return jsonify(events=date_array)

@app.route('/api/events/date/developer', methods = ['GET'])
def get_events_by_date_developer():
	sql = text("select commit.id as id_commit, commit.date, commit.developer, event.message as msg, event.type, event.id from event inner join commit on event.id_commit = commit.id where commit.developer='"+user+"' order by date")
	result = db.get_engine(app, 'db_events').execute(sql)
	#date = result.fetchone()["date"]
	date = ""
	first = True
	dates = []
	date_array = {}
	for row in result:
		if first is True:
			date = row["date"]
			first = False

		if row["date"] != date:
			date_array[json.dumps(date.isoformat())] = dates
			date = row["date"]
			dates = []

		message = row["msg"]
		if row["type"] == "Time Between Commits":
			message = row["developer"] + " hadn't "+ message[11:-1] + "s"
		dates.append({ 'message' : message, 'type' : row["type"], 'id_event' : row["id"], 'id_commit' : row["id_commit"], 'developer' : row["developer"] })

	result.close()

	#add last date
	date_array[json.dumps(date.isoformat())] = dates
	return jsonify(events=date_array)

@app.route('/api/events/commit', methods = ['GET'])
def get_events_by_commit():
	sql = text("select commit.id as id_commit, commit.date, commit.developer, commit.message, event.message as msg, event.type, event.id from event inner join commit on event.id_commit = commit.id order by date")
	result = db.get_engine(app, 'db_events').execute(sql)
	#id_commit = result.fetchone()["id_commit"]
	id_commit = ""
	first = True
	commits = []
	commits_array = {}
	for row in result:
		if first is True:
			id_commit = row["id_commit"]
			first = False

		if row["id_commit"] != id_commit:
			commits_array[id_commit] = commits
			id_commit = row["id_commit"]
			commits = []

		message = row["msg"]
		if row["type"] == "Time Between Commits":
			message = row["developer"] + " hadn't "+ message[11:-1] + "s"
		commits.append({ 'date' : json.dumps(row["date"].isoformat()), 'message' : message, 'type' : row["type"], 'id_event' : row["id"], 'id_commit' : row["id_commit"], 'developer' : row["developer"] })

	result.close()

	#add last commit
	commits_array[id_commit] = commits
	return jsonify(events=commits_array)

@app.route('/api/events/commit/developer', methods = ['GET'])
def get_events_by_commit_developer():
	sql = text("select event.id_commit, commit.date, commit.developer, commit.message, event.message as msg, event.type, event.id from event inner join commit on event.id_commit = commit.id where commit.developer='"+user+"' order by date")
	result = db.get_engine(app, 'db_events').execute(sql)
	#id_commit = result.fetchone()["id_commit"]
	id_commit = ""
	first = True
	commits = []
	commits_array = {}
	for row in result:
		if first is True:
			id_commit = row["id_commit"]
			first = False

		if row["id_commit"] != id_commit:
			commits_array[id_commit] = commits
			id_commit = row["id_commit"]
			commits = []

		message = row["msg"]
		if row["type"] == "Time Between Commits":
			message = row["developer"] + " hadn't "+ message[11:-1] + "s"
		commits.append({ 'date' : json.dumps(row["date"].isoformat()), 'message' : message, 'type' : row["type"], 'id_event' : row["id"], 'id_commit' : row["id_commit"], 'developer' : row["developer"] })

	result.close()

	#add last commit
	commits_array[id_commit] = commits
	return jsonify(events=commits_array)

if __name__ == '__main__':
	app.secret_key = 'secret key'
	app.run(debug=True)