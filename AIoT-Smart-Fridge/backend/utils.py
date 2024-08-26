import os
import openai
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

food_items = [
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "hot dog",
    "pizza",
    "cake"
]



def filter_none_food_items(raw_items): 
    filtered_items = []
    for item in raw_items:
        if item in food_items:
            filtered_items.append(item)
    return filtered_items



undetected_times_before_deleted = 3
items_not_detected_count = dict()

# def sync_object_detection():
#     req_data = request.get_json()
#     raw_items = [data for data in req_data['objects']]
#     
#     # 음식 항목 필터링
#     detected_items = filter_none_food_items(raw_items)
#     print("Filtered items:", detected_items)

#     existed_items = []
#     items = db.get("items")
#     if items is not None:
#         existed_items = json.loads(items)

#     db_items = []
#     if len(existed_items) > len(detected_items):
#         if db.get('verified') is None:
#             for ei in existed_items:
#                 if ei["name"] not in detected_items:
#                     db_items.append({"name": ei['name'], "expiration_date": None, "in_fridge_since": ei['in_fridge_since'], 'status': 'stolen'})

#     for name in detected_items:
#         now = datetime.now().strftime("%Y-%m-%d")
#         db_items.append({"name": name, "expiration_date": None, "in_fridge_since": now, 'status': 'save'})

#     db.set('items', json.dumps(db_items))

#     return '', 204


def remove_undetected_items(detected_item_names, db_items):
    print(items_not_detected_count)
    
    # pop any detected items
    for name in detected_item_names:
        if name in items_not_detected_count.keys():
            items_not_detected_count.pop(name, None)
            
    # append currently undetected items
    for db_item in db_items:
        if not db_item["name"] in detected_item_names:
            if not db_item["name"] in items_not_detected_count.keys():
                items_not_detected_count[db_item["name"]] = 0

    # update count of undetected items
    for undetected_name in list(items_not_detected_count.keys()):
        if not undetected_name in detected_item_names:
            items_not_detected_count[undetected_name] += 1
            
        # remove undetected items from db
        if items_not_detected_count[undetected_name] > undetected_times_before_deleted:
            removed_name = undetected_name
            db_items = [db_item for db_item in db_items if db_item["name"] != removed_name]
            items_not_detected_count.pop(removed_name, None)

    return db_items


def get_reply_from_chatgpt(ingredients):
    openai.api_key = os.getenv('OPENAI_API_KEY')
    
    # 시스템 메시지와 사용자 메시지 초기화
    messages = [
        {"role": "system", "content": "You are a brilliant cook."}
    ]
    
    # 재료를 콤마로 구분된 문자열로 변환
    ing_str = ', '.join(ingredients)
    print("Ingredients string:", ing_str)
    
    # 사용자 메시지 생성
    message = f"Provide recipe ideas using {ing_str}. If there are more than two recipes, please tell me only one recipe. You have to tell me 1. Ingredients 2. How to cook."
    # 메시지 리스트에 사용자 메시지 추가
    messages.append(
        {"role": "user", "content": message},
    )
    
    # GPT-3.5-turbo 모델을 사용하여 채팅 생성
    chat = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
        
    # 응답 내용 추출
    reply = chat['choices'][0]['message']['content']
    print('reply:', reply)
    
    return reply

def generate_notification(items):
    notification = []
    
    current_time = datetime.now().date()
    for item in items:
        if item['expiration_date']:
            time_object = datetime.strptime(item['expiration_date'], "%Y-%m-%d").date()
            difference = time_object - current_time

            # Compare if the difference is less than 3 days
            if difference < timedelta(days=3):
                notification.append(f"Your {item['name']} is going to expire soon!")
                
    return notification