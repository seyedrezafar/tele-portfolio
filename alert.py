import os
from datetime import datetime
import time
import requests
from api import fetch_wallet_balance
from influxdb import InfluxDBClient
import logging

def telegram_bot_sendtext(bot_message):
    
    bot_token = os.environ['BOT_TOKEN']
    bot_chatID = os.environ['BOT_CHATID']
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message

    response = requests.get(send_text)

    return response.json()


def report(balance, change):
    my_message = "Alert! Current balance is: {}, changed from last time by %s percent!".format(balance, change)   ## Customize your message
    telegram_bot_sendtext(my_message)


    
def start_alerting_forever():
    client = InfluxDBClient(host=os.environ['INFLUXDB_HOST'], port=os.environ['INFLUXDB_PORT'])
    client.switch_database('portfolio_balance')
    while True:
        # get current portfolio price
        _, balance = fetch_wallet_balance(os.environ['WALLET_ADDRESS'], os.environ['CURRENCY'])
        result = client.query('SELECT * FROM portfolio_balance GROUP BY * ORDER BY DESC LIMIT 1;')
        points = result.get_points(tags={'currency': os.environ['CURRENCY']})
        points = list(points)
        print(points)
        if len(points) > 0:
            previous_balance = points[0]['value']
            # Alert if new balance changes more than one percent from the last time.
            change = (balance - previous_balance)/previous_balance
            if abs(change) >= 0.01:
                report(balance, change*100.0)
        # Now we write our new record to influxdb
        json_body = [
            {
                "measurement": "balance",
                "tags": {
                    "currency": os.environ['CURRENCY']
                },
                "time": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                "fields": {
                    "value": balance
                }
            }
        ]
        ok = client.write_points(json_body)
        
        if not ok:
            logging.warning("couldn't write data to influxdb!")
        # Sleep 1 hour
        time.sleep(1 * 10)

start_alerting_forever()
