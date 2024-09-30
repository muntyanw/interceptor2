api_id = 22900607  #25965329
api_hash = '2101d7377e8f53d4d356ba1485d79eeb' #"6604012087bc1273f1f918571c02af24"
bot_token = '7738836203:AAHY-A-TUXd-izs-zP8DlsBandrxgjf5OGw' #'7905362232:AAHV2il7ogCFpRLDmM92pLhHYXBsIf87-_M' #''

name_session_client = 'sessionTC'
name_session_bot = 'sessionBot'

#каналы которые слушаем без -100!
channels_to_listen = {
    2023070684: { #Crypto Master | Futures Signals
        'moderation_if_image': False,
        'auto_moderation_and_send_text_message': True, #если это значение труе то будет производить автозамену и отсылать, если фэлз будет делать автозамену и отсылать на сайт человеку
        'replacements': {
            'bingx': 'google',
            'Bingx': 'Google',
            'SamCrypto_Master': 'parampam',
        },
    },
    2204843457: { #Intertest
        'moderation_if_image': False,
        'auto_moderation_and_send_text_message': True, #если это значение труе то будет производить автозамену и отсылать, если фэлз будет делать автозамену и отсылать на сайт человеку
        'replacements': {
            'bingx': 'google',
            'Bingx': 'Google',
            'SamCrypto_Master': 'parampam',
        },
    },
     
}

#каналы куда отсылаем каналы с -100
channels_to_send = [-1002353873572] #, 2170620330

replacements_in_images = { # ключи (первое слово) в нижнем регистре!
    '@samcrypto_master': '@reach_me_here',
}

# # Словарь с заменами (текущий текст кнопки -> новая ссылка)
replacements_in_buttons = {
     'Google': 'https://www.binance.com',
     'Announcements': 'https://www.binance.com',
     'Join Community': 'https://www.binance.com',
     'FAQ': 'https://www.binance.com'
 }



