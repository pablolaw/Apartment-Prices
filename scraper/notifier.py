from twilio.rest import Client

ACCOUNT_SID = 'ACa266b38b8b23775263bb4fc8560dc7dc'
AUTH_TOKEN = '9358440d0c0583d910998049c6781cb0'

def send_message(message):
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    message = client.messages.create(
        body=message,
        from_='+12513131793',
        to='+14165097194'
    )

def notify_error(e):
    send_message("An exception has been raised: {}".format(repr(e)))

if __name__ == '__main__':
    send_notification()
