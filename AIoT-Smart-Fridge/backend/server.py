import json
from flask import Flask, request
from flask_cors import CORS
from datetime import datetime

from db import connect_redis
import utils


##################추가
from utils import filter_none_food_items
###################

app = Flask(__name__)
CORS(app)

# redis
db = connect_redis()


# init items
# db.set('items', json.dumps([]))
# db.set('temperature', 5)
# db.set('humidity', 75)

# Internal Service sync

####기본 경로("/")에 대한 핸들러를 추가하여 애플리케이션이 실행 중인지 확인##
@app.route('/')
def index():
    return "Hello, this is the Smart Fridge Backend!"

@app.route('/sync/object_detection', methods=['POST'])
def sync_object_detection():
    # update food item list to db
    req_data = request.get_json()
    
    # 원본 요청에서 객체 리스트 추출
    raw_items = [data for data in req_data['objects']]
    
    # 음식 항목만 필터링
    req_items = filter_none_food_items(raw_items)
    print("Filtered items:", req_items)

    existed_items = []
    items = db.get("items")
    if items is not None:
        existed_items = json.loads(items)

    # stolen 상태 처리
    db_items = []
    if len(existed_items) > len(req_items):
        if db.get('verified') is None:
            for ei in existed_items:
                if ei["name"] not in req_items:
                    db_items.append({"name": ei['name'], "expiration_date": None, "in_fridge_since": ei['in_fridge_since'], 'status': 'stolen'})

    # 새로운 항목 저장
    for name in req_items:
        now = datetime.now().strftime("%Y-%m-%d")
        db_items.append({"name": name, "expiration_date": None, "in_fridge_since": now, 'status': 'save'})

    # 데이터베이스에 저장
    db.set('items', json.dumps(db_items))

    return '', 204


@app.route('/sync/face_detection', methods=['POST'])
def sync_face_detection():
    # update new face detection result to db
    data = request.get_json()

    print(data)
    db.set('verified', data['face'], ex=180)
    return '', 200


@app.route('/sync/temp', methods=['POST'])
def sync_temp_humidity():
    # update temperature & humidity to db
    data = request.get_json()

    humidity = "85"

    db.set('temperature', data['temp'])
    db.set('humidity', humidity)
    return '', 200


@app.route('/sync/door', methods=['POST'])
def sync_door():
    # update door status to db
    print('hit')
    data = request.get_json()
    print(data)
    db.set('door', data['door'])

    return '', 200


# frontend
@app.route('/fridge', methods=['GET'])
def get_fridge_state():
    temperature, humidity, item_list, door = db.mget('temperature', 'humidity', 'items', 'door')

    items = []
    if item_list is not None:
        items = json.loads(item_list)

    state = {
        'temperature': temperature,
        'humidity': humidity,
        'status': door,
        'items': items,
        'notification': utils.generate_notification(items)
    }
    return state


@app.route('/fridge/recipe', methods=['GET'])
def get_recipe():
    items = request.args.getlist('items')
    try:
        # 재료 리스트를 바로 사용
        ingredients = items
        print("Ingredients list:", ingredients)
        # GPT-3 호출
        reply = utils.get_reply_from_chatgpt(ingredients)
        return {"reply": reply}, 200
    except Exception as e:
        print('Error:', e)
        return {"reply": "Sorry, ChatGPT service is currently unavailable"}, 400


@app.route('/fridge/item', methods=['PATCH'])
def update_item_expiration_date():
    req_body = request.get_json()
    name = req_body['name']
    expiration_date = req_body['expiration_date']
    print(name, expiration_date)

    items = []
    data = db.get('items')
    if data is not None:
        items = json.loads(data)

    item_to_update = next((item for item in items if item['name'] == name), None)

    if item_to_update:
        item_to_update['expiration_date'] = expiration_date
        print(item_to_update)
        updated_json_data = json.dumps(items)
        db.set('items', updated_json_data)
        return {"status": "success"}, 200
    else:
        print("Object not found in the list.")
        return f'{name} not found in fridge items', 400


# iottalk
@app.route('/sync/iottalk', methods=['GET'])
def send_to_iottalk():
    temperature, humidity, items = db.mget('temperature', 'humidity', 'items')
    items = json.loads(items)

    state = {
        'temperature': temperature,
        'humidity': humidity,
        'status': 'Normal',
        'items': items,
        'notification': utils.generate_notification(items)
    }
    return state


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
