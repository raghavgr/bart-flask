from flask import Flask, request, render_template, jsonify
import requests
from datetime import datetime
from jinja2 import Template

app = Flask(__name__, static_folder='css/', static_url_path='')

BART_BASE_URL = 'http://api.bart.gov/api/'
BART_API_KEY = '&key=MW9S-E7SL-26DU-VV8V&json=y'
GOOGLE_MAPS_API_KEY = 'AIzaSyBw8P4oEsNzsqZgCbCcAfRQ--xDnr8m1QU'
CURRENT_URL = "http://localhost"


@app.route('/stations')
def show_bart():
    # calling BART API
    req_output = requests.get(BART_BASE_URL + 'stn.aspx?cmd=stns' + BART_API_KEY, verify=False)
    response = req_output.json()
    stns_list_json = response['root']['stations']['station']
    stns_list = [{'name': curr_stn['name'], 'stn_code': curr_stn['abbr']} for curr_stn in stns_list_json]
                    
    return jsonify(stns_list)

@app.route('/station')
def station():
    try:
        station = request.args.get('station')
        req_output = requests.get(BART_BASE_URL + 'stn.aspx?cmd=stninfo&orig=' +
        station + BART_API_KEY, verify=False)
        response = req_output.json()
        return jsonify(response)
    except Exception as e:
        print(e)
    return "Failed"

@app.route('/trips')
def trips():
    origin = request.args.get('source')
    dest = request.args.get('dest')
    req_output = requests.get(BART_BASE_URL + 'sched.aspx?cmd=depart&orig=' + origin + '&dest=' + dest + '&date=now' + BART_API_KEY+ '&b=0&a=4', verify=False)
    response = req_output.json()['root']
    parsed_trips = []
    trips = response['schedule']['request']['trip']
    for i in range(0, len(trips)):
        curr_trip = {
        'departure_time': trips[i]['@origTimeMin'],
        'departure_date': trips[i]['@origTimeDate'],
        'arrival_time': trips[i]['@destTimeMin'],
        'arrival_date': trips[i]['@destTimeDate'],
        'trip_time': trips[i]['@tripTime'],
        'cost': trips[i]['fares']['fare']['@amount'],
        'legs': [],
        'num_transfers': -1
        }
        if len(trips[i]['leg']) > 1:
            for leg in trips[i]['leg']:
                curr_trip['legs'].append({
                'origin': leg['@origin'],
                'destination': leg['@destination'],
                'departure_time': leg['@origTimeMin'],
                'departure_date': leg['@origTimeDate'],
                'arrival_time': leg['@destTimeMin'],
                'arrival_date': leg['@destTimeDate'],
                })
                curr_trip['num_transfers'] += 1
        else:
            curr_trip['legs'] = None
            curr_trip['num_transfers'] = 0
        parsed_trips.append(curr_trip)
    formatted_response = {
    'source': origin,
    'destination': dest,
    'trips': parsed_trips
    }
    return jsonify(formatted_response)

@app.route('/start')
def launch_bart():
    message = None
    curr_trip = None
    try:
        origin = request.args.get('source')
        destination = request.args.get('dest')
        if origin and destination:
            if origin != destination:
                curr_trip = retrieve_trip(origin, destination)
            else:
                message = "Origin cannot be the same as destination"
    except Exception as e:
        print(e)
        origin = None
        destination = None
    req_output = requests.get(CURRENT_URL + '/stations', verify=False)
    stns_list = req_output.json()
    return render_template("bart_planner.html", stns_list=stns_list, source=origin, destination=destination, message=message, curr_trip=curr_trip, maps_key=GOOGLE_MAPS_API_KEY)

def retrieve_trip(origin: str, dest: str):
    req_output = requests.get(CURRENT_URL + '/trips?source=' + origin + '&dest=' + dest, verify=False)
    output_response = req_output.json()
    respons_date_string = output_response['trips'][0]['departure_date'] + ' ' + output_response['trips'][0]['departure_time']
    formatted_datetime = datetime.strptime(respons_date_string, '%m/%d/%Y %I:%M %p')
    date_str = formatted_datetime.strftime("'%b %d, %Y %H:%M%:%S'")
    output_response['next_train'] = date_str
    req_output = requests.get(CURRENT_URL + '/station?station=' + origin, verify=False)
    origin_stn_rpr = req_output.json()['root']['stations']['station']
    output_response['src_info'] = {
    'name': origin_stn_rpr['name'],
    'intro': origin_stn_rpr['intro']['#cdata-section'],
    'lat': origin_stn_rpr['gtfs_latitude'],
    'long': origin_stn_rpr['gtfs_longitude']
    }
    req_output = requests.get(CURRENT_URL + '/station?station=' + dest, verify=False)
    final_dest = req_output.json()['root']['stations']['station']
    output_response['dest_info'] = {
    'lat': final_dest['gtfs_latitude'],
    'long': final_dest['gtfs_longitude']
    }
    return output_response

if __name__ == '__main__':
  #app.run()
  app.run(host="0.0.0.0", port=80)